"""Phase B: LBNL / Campus VPN Full-Text PDF & XML Extractor for Amorphous SRO/MRO Data.

Tracked under Beads task `Amorphous_periodic_table-at4.6`.
Designed to be executed locally when connected to the Lawrence Berkeley National
Laboratory (LBNL) or UC Berkeley campus VPN:

    python3 -m src.vpn_fulltext_extractor [--limit N]

Workflow:
1. Loads all 203+ Crossref/OpenAlex-verified DOIs from `data/verified_doi_registry.json`.
2. Queries Crossref TDM (`link` array) and OpenAlex (`open_access.oa_url` / `primary_location.pdf_url`)
   plus direct publisher DOI resolution (`https://doi.org/{doi}`) using institutional session headers.
3. Downloads accessible full-text PDFs or JATS/Elsevier XMLs into `data/vpn_papers/`.
4. Parses text/captions for quantitative experimental Short- & Medium-Range Order (SRO/MRO)
   parameters:
   - First Sharp Diffraction Peak (`Q_1` / FSDP in Å⁻¹ or nm⁻¹)
   - Nearest-neighbor bond lengths (`r_1`, `r_ij` in Å)
   - Coordination numbers (`CN`, `N_ij`)
   - Bond-angle distributions (`θ` in deg)
   - Ring size or Voronoi index `<n3, n4, n5, n6>` statistics
5. Exports extracted full-text snippets and numerical parameters to
   `data/vpn_extracted_sro_mro.json` for merging into `src/structural_characterization_data.py`.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT_DIR / "data" / "verified_doi_registry.json"
PAPERS_DIR = ROOT_DIR / "data" / "vpn_papers"
OUTPUT_JSON_PATH = ROOT_DIR / "data" / "vpn_extracted_sro_mro.json"
OUTPUT_TABLES_JSON_PATH = ROOT_DIR / "data" / "vpn_extracted_structural_tables.json"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "AmorphousPeriodicTable-VPN-Extractor/1.0 (mailto:research@lbl.gov)"
)

# Regex patterns for extracting quantitative SRO/MRO metrics from full text
PATTERNS = {
    "q1_fsdp": re.compile(
        r"(?:FSDP|first\s+sharp\s+diffraction\s+peak|Q_?1|q_?1|pre-?peak)[^.\n]{0,60}?"
        r"(\d+\.\d+)\s*(?:Å\s*[\-⁻]\s*1|A\s*[\-⁻]\s*1|nm\s*[\-⁻]\s*1)",
        re.IGNORECASE,
    ),
    "bond_length_A": re.compile(
        r"(?:bond\s+length|nearest[\-\s]neighbor|first\s+peak|r_?1|d\s*\([A-Z][a-z]?\s*[\-–]\s*[A-Z][a-z]?\))"
        r"[^.\n]{0,60}?(\d\.\d{2,3})\s*(?:Å|angstrom)",
        re.IGNORECASE,
    ),
    "bond_angle_deg": re.compile(
        r"(?:bond\s+angle|tetrahedral\s+angle|intertetrahedral\s+angle|\b[A-Z][a-z]?[\-–][A-Z][a-z]?[\-–][A-Z][a-z]?\s+angle)"
        r"[^.\n]{0,60}?(\d{2,3}(?:\.\d+)?)\s*(?:°|deg)",
        re.IGNORECASE,
    ),
    "voronoi_index": re.compile(r"<\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*>"),
    "ring_size": re.compile(r"\b([3-9]|1[0-2])[\-\s]membered\s+rings?\b", re.IGNORECASE),
}


def fetch_candidate_urls(doi: str) -> list[dict[str, str]]:
    """Query Crossref and OpenAlex for direct PDF/XML full-text links for a DOI."""
    candidates: list[dict[str, str]] = []
    encoded_doi = urllib.parse.quote(doi, safe="")

    # 1. Crossref TDM links
    cr_url = f"https://api.crossref.org/works/{encoded_doi}"
    req = urllib.request.Request(cr_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            links = data.get("message", {}).get("link", []) or []
            for lk in links:
                u = lk.get("URL")
                ct = lk.get("content-type", "application/octet-stream")
                if u:
                    candidates.append({"url": u, "content_type": ct, "source": "crossref_tdm"})
    except Exception:
        pass

    # 2. OpenAlex OA / institutional links
    oa_url = f"https://api.openalex.org/works/https://doi.org/{encoded_doi}"
    req_oa = urllib.request.Request(oa_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req_oa, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pdf_url = (data.get("primary_location") or {}).get("pdf_url")
            oa_best = (data.get("open_access") or {}).get("oa_url")
            if pdf_url:
                candidates.append({"url": pdf_url, "content_type": "application/pdf", "source": "openalex_pdf"})
            if oa_best and oa_best != pdf_url:
                candidates.append({"url": oa_best, "content_type": "application/pdf", "source": "openalex_oa"})
    except Exception:
        pass

    # 3. Direct DOI resolver (redirected through campus/LBNL VPN IP entitlement)
    candidates.append({
        "url": f"https://doi.org/{doi}",
        "content_type": "text/html",
        "source": "doi_landing_page",
    })
    return candidates


def extract_text_from_pdf(pdf_path: Path, raw_bytes: bytes) -> str:
    """Extract text from a downloaded PDF using pypdf, pdftotext, or zlib stream decoding."""
    # 1. Try pypdf if available
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        joined = "\n".join(pages_text).strip()
        if joined:
            return joined
    except Exception:
        pass

    # 2. Try pdftotext CLI if installed on Linux
    if shutil.which("pdftotext") and pdf_path.exists():
        try:
            proc = subprocess.run(
                ["pdftotext", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if proc.stdout and proc.stdout.strip():
                return proc.stdout
        except Exception:
            pass

    # 3. Built-in fallback: decompress PDF FlateDecode streams and extract text literals
    chunks: list[str] = []
    for match in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.DOTALL):
        stream_data = match.group(1)
        try:
            decompressed = zlib.decompress(stream_data)
            text_chunk = decompressed.decode("latin-1", errors="ignore")
            literals = re.findall(r"\(([^()]{2,})\)", text_chunk)
            if literals:
                chunks.append(" ".join(literals))
        except Exception:
            continue
    if chunks:
        return "\n".join(chunks)
    return raw_bytes.decode("latin-1", errors="ignore")


def extract_metrics_from_text(text: str) -> dict[str, Any]:
    """Scan downloaded PDF/XML/HTML/text for quantitative SRO/MRO structural parameters."""
    extracted: dict[str, Any] = {}
    for key, regex in PATTERNS.items():
        matches = list(dict.fromkeys(m.group(0).strip() for m in regex.finditer(text)))
        if matches:
            extracted[key] = matches[:10]
    return extracted


def run_vpn_extraction(limit: int | None = None) -> dict[str, Any]:
    """Iterate through verified DOIs and attempt institutional full-text retrieval."""
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Verified DOI registry not found at {REGISTRY_PATH}")

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry_payload = json.load(f)

    registry: dict[str, dict[str, Any]] = (
        registry_payload.get("verified_dois") or registry_payload.get("registry") or {}
    )
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    dois = sorted(registry.keys())
    if limit is not None and limit > 0:
        dois = dois[:limit]

    results: dict[str, Any] = {}
    downloaded_count = 0

    print(f"[VPN Extractor] Auditing {len(dois)} verified DOIs via institutional network...")
    for idx, doi in enumerate(dois, start=1):
        meta = registry[doi]
        safe_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", doi)
        candidates = fetch_candidate_urls(doi)

        entry_res: dict[str, Any] = {
            "doi": doi,
            "title": meta.get("title", ""),
            "canonical_citation": meta.get("canonical_citation", ""),
            "attempted_urls": len(candidates),
            "downloaded_file": None,
            "extracted_sro_mro_mentions": {},
        }

        for cand in candidates:
            url = cand["url"]
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/pdf,application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    body = resp.read(8_000_000)  # Cap read at 8 MB per document
                    if b"%PDF-" in body[:1024] or "application/pdf" in ctype:
                        pdf_path = PAPERS_DIR / f"{safe_slug}.pdf"
                        with open(pdf_path, "wb") as pf:
                            pf.write(body)
                        entry_res["downloaded_file"] = str(pdf_path.relative_to(ROOT_DIR))
                        pdf_text = extract_text_from_pdf(pdf_path, body)
                        metrics = extract_metrics_from_text(pdf_text)
                        if metrics:
                            entry_res["extracted_sro_mro_mentions"] = metrics
                        downloaded_count += 1
                        break
                    elif "xml" in ctype or "html" in ctype:
                        decoded = body.decode("utf-8", errors="ignore")
                        metrics = extract_metrics_from_text(decoded)
                        if metrics:
                            entry_res["extracted_sro_mro_mentions"] = metrics
                        if "xml" in ctype:
                            xml_path = PAPERS_DIR / f"{safe_slug}.xml"
                            with open(xml_path, "w", encoding="utf-8") as xf:
                                xf.write(decoded)
                            entry_res["downloaded_file"] = str(xml_path.relative_to(ROOT_DIR))
                            downloaded_count += 1
                            break
            except Exception:
                continue

        results[doi] = entry_res
        print(
            f"  [{idx}/{len(dois)}] {doi} -> "
            f"file={entry_res['downloaded_file']} | "
            f"mentions={len(entry_res['extracted_sro_mro_mentions'])}"
        )
        time.sleep(0.25)

    summary = {
        "metadata": {
            "total_dois_processed": len(dois),
            "fulltext_files_downloaded": downloaded_count,
            "papers_dir": str(PAPERS_DIR.relative_to(ROOT_DIR)),
        },
        "results": results,
    }
    for out_path in (OUTPUT_JSON_PATH, OUTPUT_TABLES_JSON_PATH):
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"[VPN Extractor] Saved extraction report -> {OUTPUT_JSON_PATH} & {OUTPUT_TABLES_JSON_PATH}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and extract SRO/MRO full-text data over LBNL/Campus VPN."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of DOIs to process in this run.",
    )
    args = parser.parse_args()
    run_vpn_extraction(limit=args.limit)


if __name__ == "__main__":
    main()
