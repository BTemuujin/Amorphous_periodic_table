"""Phase B: LBNL / Campus VPN Full-Text PDF & XML Extractor for Amorphous SRO/MRO Data.

Tracked under Beads task `Amorphous_periodic_table-at4.6`.
Designed to be executed locally when connected to the Lawrence Berkeley National
Laboratory (LBNL) or UC Berkeley campus institutional network/VPN:

    python3 -m src.vpn_fulltext_extractor [--limit N] [--workers W]

Workflow:
1. Loads all Crossref/OpenAlex-verified DOIs from `data/verified_doi_registry.json`.
2. Queries Crossref TDM (`link` array), OpenAlex (`locations[*].pdf_url`, `open_access.oa_url`,
   and `abstract_inverted_index`), publisher-specific institutional PDF endpoints
   (APS `journals.aps.org/.../pdf/...`, Nature `nature.com/articles/...pdf`,
   Springer `link.springer.com/content/pdf/...`, J-STAGE `_pdf`, Elsevier XML API),
   and direct DOI resolution (`https://doi.org/{doi}`) with an HTTP cookie jar.
3. Downloads accessible full-text PDFs or XMLs into `data/vpn_papers/` (up to 50 MB per file).
4. Extracts full text via `pdftotext` (or `pypdf` / zlib stream fallback) and parses
   quantitative experimental Short- & Medium-Range Order (SRO/MRO) parameters and tables:
   - First Sharp Diffraction Peak (`Q_1` / FSDP in Å⁻¹ or nm⁻¹)
   - Nearest-neighbor bond lengths (`r_1`, `r_ij` in Å or nm)
   - Coordination numbers (`CN`, `N_ij`, tetrahedral/icosahedral coordination)
   - Bond-angle distributions (`θ` in deg)
   - Ring size or Voronoi index `<n3, n4, n5, n6>` statistics
   - Glass transition / crystallization temperatures (`T_g`, `T_x`, `ΔT_x`)
   - Table blocks (`Table 1`, `Table I`, `Table 2`, etc.)
5. Exports extracted full-text snippets, tables, and numerical parameters to
   `data/vpn_extracted_sro_mro.json` and `data/vpn_extracted_structural_tables.json`.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import http.cookiejar
import io
import json
import re
import shutil
import subprocess
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
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

MAX_PDF_BYTES = 50_000_000  # 50 MB cap so large linearized PDFs are never truncated

# Regex patterns for extracting quantitative SRO/MRO & glass metrics from full text
PATTERNS = {
    "q1_fsdp": re.compile(
        r"(?:FSDP|first\s+sharp\s+diffraction\s+peak|pre-?peak|main\s+diffraction\s+peak|\b[Qq]_?[1pP]\b|\bS\s*\(\s*[QqKk]\s*\))"
        r"[^\n]{0,90}?(\d+\.\d+)\s*(?:Å\s*[\-⁻]\s*1|A\s*[\-⁻]\s*1|\u212b\s*[\-⁻]\s*1|nm\s*[\-⁻]\s*1)",
        re.IGNORECASE,
    ),
    "bond_length_A": re.compile(
        r"(?:bond\s+length|bond\s+distance|nearest[\-\s]neighbor|first\s+(?:RDF|PDF|coordination|shell|peak)\s*(?:peak|distance|at)?|"
        r"interatomic\s+distance|\b[rR]_?1\b|\bd\s*\([A-Z][a-z]?\s*[\-–]\s*[A-Z][a-z]?\)|"
        r"\b[A-Z][a-z]?\s*[\-–]\s*[A-Z][a-z]?\s+(?:bond|distance|length|correlation|pair|pairs))"
        r"[^\n]{0,90}?(\d\.\d{2,3})\s*(?:Å|\u212b|angstrom|nm\b|A\b)",
        re.IGNORECASE,
    ),
    "coordination_number": re.compile(
        r"(?:(?:coordination\s+numbers?|\bN_?\{?coord\}?\b)[^\n]{0,70}?\b\d+(?:\.\d+)?\b|"
        r"\bCN\s*(?:=|:|is|of|≈|~)\s*\d+(?:\.\d+)?|"
        r"\b[3456789][\-\s]fold\s+coordinat\w*[^\n]{0,50}|"
        r"(?:tetrahedral|trigonal|octahedral)\s+coordinat\w*[^\n]{0,50}|"
        r"icosahedral\s+(?:cluster|short[\-\s]range|order|coordinat)\w*[^\n]{0,50})",
        re.IGNORECASE,
    ),
    "bond_angle_deg": re.compile(
        r"(?:bond\s+angle|tetrahedral\s+angle|intertetrahedral\s+angle|bridging\s+angle|"
        r"\b[A-Z][a-z]?[\-–][A-Z][a-z]?[\-–][A-Z][a-z]?\s+angle)"
        r"[^\n]{0,80}?(\d{2,3}(?:\.\d+)?)\s*(?:°|deg)",
        re.IGNORECASE,
    ),
    "voronoi_index": re.compile(
        r"(?:<|\\langle|⟨)\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*\d+)?\s*(?:>|\\rangle|⟩)"
    ),
    "ring_size": re.compile(
        r"\b([3-9]|1[0-2])[\-\s]membered\s+rings?\b",
        re.IGNORECASE,
    ),
    "thermal_Tg_Tx_K": re.compile(
        r"(?:\bT_?g\b|\bT_?x\b|ΔT_?x|glass\s+transition\s+temperature|crystallization\s+temperature|"
        r"supercooled\s+liquid\s+region)"
        r"[^\n]{0,70}?(\d{2,4}(?:\.\d+)?)\s*(?:K\b|°C)",
        re.IGNORECASE,
    ),
    "cooling_rate_or_dmax": re.compile(
        r"(?:critical\s+cooling\s+rate|cooling\s+rate|critical\s+(?:diameter|thickness|casting)|"
        r"\bd_?\{?max\}?\b|bulk\s+metallic\s+glass\s+rod)"
        r"[^\n]{0,70}?(\d+(?:\.\d+)?(?:\s*[×x]\s*10[\-⁻⁺+]?\d+)?)\s*(?:K\s*/\s*s|K\s*s[\-⁻]1|mm\b)",
        re.IGNORECASE,
    ),
}

TABLE_CAPTION_RE = re.compile(
    r"(?:^|\n)[ \t]*(Table\s+(?:[1-9]\d*|I|II|III|IV|V|VI|VII|VIII)\b(?:\s*[\.:\-\–—]|\s+[A-Z])[^\n]{0,200}(?:\n[^\n]{0,220}){2,35})",
    re.IGNORECASE,
)
PROSE_TABLE_REF_RE = re.compile(
    r"^Table\s+(?:[1-9]\d*|I|II|III|IV|V|VI|VII|VIII)\s+"
    r"(?:compares|shows|lists|gives|summarizes|presents|reports|contains|displays|illustrates|is|was|are|were|in|and|or|for|with|from|to|of|that|which|where|,|\))",
    re.IGNORECASE,
)


def build_opener() -> urllib.request.OpenerDirector:
    """Create a thread-local urllib opener with an active CookieJar and browser headers."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [
        ("User-Agent", USER_AGENT),
        (
            "Accept",
            "application/pdf,application/xml,text/xml,text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        ),
        ("Accept-Language", "en-US,en;q=0.9"),
    ]
    return opener


def reconstruct_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct plain-text abstract from an OpenAlex abstract_inverted_index."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_to_word: dict[int, str] = {}
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for p in positions:
                if isinstance(p, int):
                    pos_to_word[p] = word
    if not pos_to_word:
        return ""
    return " ".join(pos_to_word[idx] for idx in sorted(pos_to_word))


def fetch_candidate_urls(
    doi: str, opener: urllib.request.OpenerDirector
) -> tuple[list[dict[str, str]], str]:
    """Query publisher patterns, Crossref TDM, and OpenAlex for direct PDF/XML links and abstracts."""
    candidates: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    abstract_texts: list[str] = []

    def add_cand(url: str | None, ctype: str, source: str) -> None:
        if not url or url in seen_urls:
            return
        if "api.wiley.com/onlinelibrary/tdm" in url:
            return
        seen_urls.add(url)
        candidates.append({"url": url, "content_type": ctype, "source": source})

    doi_lower = doi.lower()
    prefix, _, suffix = doi.partition("/")

    # 1. Publisher-specific direct institutional PDF patterns (LBNL / Campus IP entitled)
    if prefix == "10.1038" and suffix:
        add_cand(f"https://www.nature.com/articles/{suffix}.pdf", "application/pdf", "nature_direct_pdf")
    elif prefix == "10.1007" and suffix:
        add_cand(f"https://link.springer.com/content/pdf/{doi}.pdf", "application/pdf", "springer_direct_pdf")
    elif prefix == "10.1103" and suffix:
        # Map PhysRev journal slug to APS URL path
        s_low = suffix.lower()
        aps_j = None
        if s_low.startswith("physrevlett."):
            aps_j = "prl"
        elif s_low.startswith("physrevb."):
            aps_j = "prb"
        elif s_low.startswith("physrevmaterials."):
            aps_j = "prmaterials"
        elif s_low.startswith("physrevx."):
            aps_j = "prx"
        elif s_low.startswith("revmodphys."):
            aps_j = "rmp"
        elif s_low.startswith("physreva."):
            aps_j = "pra"
        elif s_low.startswith("physrevc."):
            aps_j = "prc"
        elif s_low.startswith("physrevd."):
            aps_j = "prd"
        elif s_low.startswith("physreve."):
            aps_j = "pre"
        elif s_low.startswith("physrevapplied."):
            aps_j = "prapplied"
        elif s_low.startswith("physrev."):
            aps_j = "pr"
        if aps_j:
            add_cand(
                f"https://journals.aps.org/{aps_j}/pdf/{doi}",
                "application/pdf",
                "aps_direct_pdf",
            )
        add_cand(f"https://link.aps.org/accepted/{doi}", "application/pdf", "aps_accepted_pdf")

    encoded_doi = urllib.parse.quote(doi, safe="")

    # 2. OpenAlex OA / institutional / repository locations + abstract_inverted_index
    oa_url = f"https://api.openalex.org/works/https://doi.org/{encoded_doi}"
    try:
        with opener.open(oa_url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            oa_abs = reconstruct_openalex_abstract(data.get("abstract_inverted_index"))
            if oa_abs:
                abstract_texts.append(oa_abs)
            prim_pdf = (data.get("primary_location") or {}).get("pdf_url")
            add_cand(prim_pdf, "application/pdf", "openalex_primary_pdf")
            best_pdf = (data.get("best_oa_location") or {}).get("pdf_url")
            add_cand(best_pdf, "application/pdf", "openalex_best_oa_pdf")
            oa_best = (data.get("open_access") or {}).get("oa_url")
            add_cand(oa_best, "application/pdf", "openalex_oa_url")
            for loc in data.get("locations") or []:
                add_cand(loc.get("pdf_url"), "application/pdf", "openalex_location_pdf")
    except Exception:
        pass

    # 3. Crossref TDM links + abstract
    cr_url = f"https://api.crossref.org/works/{encoded_doi}"
    try:
        with opener.open(cr_url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data.get("message", {}) or {}
            cr_abs = msg.get("abstract")
            if cr_abs and isinstance(cr_abs, str):
                clean_abs = re.sub(r"<[^>]+>", " ", cr_abs)
                clean_abs = re.sub(r"\s+", " ", clean_abs).strip()
                if clean_abs:
                    abstract_texts.append(clean_abs)
            links = msg.get("link", []) or []
            for lk in links:
                u = lk.get("URL")
                ct = (lk.get("content-type") or "application/octet-stream").lower()
                if u and "api.aps.org" not in u and "harvest.aps.org" not in u:
                    add_cand(u, ct, "crossref_tdm")
    except Exception:
        pass

    # 4. Elsevier structured XML metadata endpoint for 10.1016 DOIs
    if prefix == "10.1016":
        add_cand(
            f"https://api.elsevier.com/content/article/doi/{doi}?httpAccept=text/xml",
            "text/xml",
            "elsevier_xml_api",
        )

    # 5. Direct DOI landing page resolver (follows institutional redirects)
    add_cand(f"https://doi.org/{doi}", "text/html", "doi_landing_page")

    combined_abstract = "\n".join(dict.fromkeys(abstract_texts))
    return candidates, combined_abstract


def extract_text_from_pdf(pdf_path: Path, raw_bytes: bytes) -> str:
    """Extract text from a downloaded PDF using pdftotext -layout or pypdf.

    Returns an empty string for scanned image-only PDFs lacking an embedded text
    layer rather than decoding raw binary PDF bytes as Latin-1.
    """
    # 1. Try pdftotext CLI with -layout so multi-column tables stay on horizontal rows
    if shutil.which("pdftotext") and pdf_path.exists():
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
            if proc.stdout and proc.stdout.strip():
                return proc.stdout
            if proc.returncode == 0:
                # Valid PDF with zero embedded text (scanned image-only PDF without OCR)
                return ""
        except Exception:
            pass

    # 2. Try pypdf if available
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        joined = "\n".join(pages_text).strip()
        if joined:
            return joined
    except Exception:
        pass

    return ""


def extract_metrics_from_text(text: str) -> dict[str, Any]:
    """Scan downloaded PDF/XML/HTML/abstract text for quantitative SRO/MRO structural parameters."""
    extracted: dict[str, Any] = {}
    # Normalize hyphenated linebreaks common in 2-column PDFs
    cleaned = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    for key, regex in PATTERNS.items():
        matches = list(
            dict.fromkeys(
                re.sub(r"\s+", " ", m.group(0)).strip() for m in regex.finditer(cleaned)
            )
        )
        if matches:
            extracted[key] = matches[:12]
    return extracted


def extract_tables_from_text(text: str) -> list[str]:
    """Extract Table captions and adjacent tabular rows from full-text PDF/HTML."""
    tables: list[str] = []
    for m in TABLE_CAPTION_RE.finditer(text):
        raw_block = m.group(1).strip()
        first_line = raw_block.split("\n", 1)[0].strip()
        if PROSE_TABLE_REF_RE.match(first_line):
            continue
        lines = [re.sub(r"[ \t]{2,}", "  ", ln.strip()) for ln in raw_block.splitlines() if ln.strip()]
        # Require at least 2 lines containing 2 or more decimal/integer numbers (true tabular data)
        numeric_rows = sum(
            1 for ln in lines[1:] if len(re.findall(r"\b\d+(?:\.\d+)?\b", ln)) >= 2
        )
        if numeric_rows < 2:
            continue
        snippet = "\n".join(lines)[:1500]
        if len(snippet) >= 40 and snippet not in tables:
            tables.append(snippet)
        if len(tables) >= 8:
            break
    return tables


def is_elsevier_metadata_only_xml(xml_text: str) -> bool:
    """Return True if an XML payload is an Elsevier TDM <coredata> metadata stub with no body text."""
    lower = xml_text.lower()
    if "<coredata>" in lower and "<originaltext>" not in lower and "<body" not in lower:
        return True
    clean = re.sub(r"<[^>]+>", " ", xml_text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return len(clean) < 1200


def process_single_doi(
    idx: int,
    total: int,
    doi: str,
    meta: dict[str, Any],
    cached_only: bool = False,
    prior_entry: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Worker function to download full text and extract SRO/MRO parameters for one DOI."""
    safe_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", doi)
    cached_pdf_path = PAPERS_DIR / f"{safe_slug}.pdf"
    cached_xml_path = PAPERS_DIR / f"{safe_slug}.xml"

    if cached_only:
        entry_res: dict[str, Any] = {
            "doi": doi,
            "title": meta.get("title", ""),
            "canonical_citation": meta.get("canonical_citation", ""),
            "journal": meta.get("journal", ""),
            "year": meta.get("year"),
            "attempted_urls": (prior_entry or {}).get("attempted_urls", 0),
            "downloaded_file": (prior_entry or {}).get("downloaded_file"),
            "download_source": (prior_entry or {}).get("download_source"),
            "content_status": "metadata_only",
            "text_char_length": 0,
            "has_abstract": (prior_entry or {}).get("has_abstract", False),
            "extracted_sro_mro_mentions": {},
            "extracted_tables": [],
        }
        if cached_pdf_path.exists() and cached_pdf_path.stat().st_size > 1024:
            raw_bytes = cached_pdf_path.read_bytes()
            pdf_text = extract_text_from_pdf(cached_pdf_path, raw_bytes)
            entry_res["downloaded_file"] = str(cached_pdf_path.relative_to(ROOT_DIR))
            entry_res["download_source"] = entry_res["download_source"] or "cached_pdf"
            entry_res["text_char_length"] = len(pdf_text)
            if len(pdf_text.strip()) >= 200:
                entry_res["content_status"] = "fulltext_pdf_extracted"
                entry_res["extracted_sro_mro_mentions"] = extract_metrics_from_text(pdf_text)
                entry_res["extracted_tables"] = extract_tables_from_text(pdf_text)
            else:
                entry_res["content_status"] = "scanned_image_pdf_no_ocr"
                entry_res["text_char_length"] = 0
                entry_res["extracted_sro_mro_mentions"] = {}
                entry_res["extracted_tables"] = []
        elif cached_xml_path.exists() and cached_xml_path.stat().st_size > 128:
            decoded = cached_xml_path.read_text(encoding="utf-8", errors="ignore")
            clean_xml_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", decoded)).strip()
            entry_res["downloaded_file"] = str(cached_xml_path.relative_to(ROOT_DIR))
            entry_res["download_source"] = entry_res["download_source"] or "cached_xml"
            entry_res["text_char_length"] = len(clean_xml_text)
            if is_elsevier_metadata_only_xml(decoded):
                entry_res["content_status"] = "elsevier_xml_metadata_stub"
                # Preserve any OpenAlex/Crossref abstract metrics from prior run if present,
                # but never claim full-text XML extraction on a <coredata> metadata stub.
                prior_mentions = dict((prior_entry or {}).get("extracted_sro_mro_mentions") or {})
                if "coordination_number" in prior_mentions:
                    cleaned_cn = [
                        m for m in prior_mentions["coordination_number"] if len(m.strip()) > 22
                    ]
                    if cleaned_cn:
                        prior_mentions["coordination_number"] = cleaned_cn
                    else:
                        del prior_mentions["coordination_number"]
                entry_res["extracted_sro_mro_mentions"] = prior_mentions
                entry_res["extracted_tables"] = []
            else:
                entry_res["content_status"] = "fulltext_xml_extracted"
                entry_res["extracted_sro_mro_mentions"] = extract_metrics_from_text(clean_xml_text)
                entry_res["extracted_tables"] = extract_tables_from_text(clean_xml_text)
        else:
            entry_res["content_status"] = (
                "abstract_only" if entry_res["has_abstract"] else "metadata_only"
            )
            entry_res["text_char_length"] = (prior_entry or {}).get("text_char_length", 0)
            prior_mentions = dict((prior_entry or {}).get("extracted_sro_mro_mentions") or {})
            if "coordination_number" in prior_mentions:
                cleaned_cn = [
                    m for m in prior_mentions["coordination_number"] if len(m.strip()) > 22
                ]
                if cleaned_cn:
                    prior_mentions["coordination_number"] = cleaned_cn
                else:
                    del prior_mentions["coordination_number"]
            entry_res["extracted_sro_mro_mentions"] = prior_mentions
        return doi, entry_res

    opener = build_opener()
    candidates, abstract_text = fetch_candidate_urls(doi, opener)

    entry_res = {
        "doi": doi,
        "title": meta.get("title", ""),
        "canonical_citation": meta.get("canonical_citation", ""),
        "journal": meta.get("journal", ""),
        "year": meta.get("year"),
        "attempted_urls": len(candidates),
        "downloaded_file": None,
        "download_source": None,
        "text_char_length": 0,
        "has_abstract": bool(abstract_text),
        "extracted_sro_mro_mentions": {},
        "extracted_tables": [],
    }

    full_text_corpus = abstract_text

    # Reuse locally downloaded PDF if already present and valid
    if cached_pdf_path.exists() and cached_pdf_path.stat().st_size > 1024:
        raw_bytes = cached_pdf_path.read_bytes()
        if b"%PDF-" in raw_bytes[:1024]:
            pdf_text = extract_text_from_pdf(cached_pdf_path, raw_bytes)
            entry_res["downloaded_file"] = str(cached_pdf_path.relative_to(ROOT_DIR))
            entry_res["download_source"] = (prior_entry or {}).get("download_source") or "cached_pdf"
            entry_res["text_char_length"] = len(pdf_text)
            full_text_corpus = (abstract_text + "\n" + pdf_text).strip()
            entry_res["extracted_tables"] = extract_tables_from_text(pdf_text)
            candidates = []

    for cand in candidates:
        url = cand["url"]
        try:
            with opener.open(url, timeout=18) as resp:
                ctype = (resp.headers.get("Content-Type") or "").lower()
                final_url = resp.url or url
                body = resp.read(MAX_PDF_BYTES)

                # If APS or J-STAGE HTML landing page was reached, try swapping to PDF URL
                if b"%PDF-" not in body[:1024] and "journals.aps.org/" in final_url and "/abstract/" in final_url:
                    pdf_url = final_url.replace("/abstract/", "/pdf/")
                    try:
                        with opener.open(pdf_url, timeout=18) as pdf_resp:
                            pdf_body = pdf_resp.read(MAX_PDF_BYTES)
                            if b"%PDF-" in pdf_body[:1024]:
                                body = pdf_body
                                ctype = "application/pdf"
                                cand = {"url": pdf_url, "source": "aps_redirect_pdf"}
                    except Exception:
                        pass

                if b"%PDF-" in body[:1024] or ("application/pdf" in ctype and b"<html" not in body[:512].lower()):
                    pdf_path = PAPERS_DIR / f"{safe_slug}.pdf"
                    with open(pdf_path, "wb") as pf:
                        pf.write(body)
                    entry_res["downloaded_file"] = str(pdf_path.relative_to(ROOT_DIR))
                    entry_res["download_source"] = cand["source"]
                    pdf_text = extract_text_from_pdf(pdf_path, body)
                    entry_res["text_char_length"] = len(pdf_text)
                    full_text_corpus = (abstract_text + "\n" + pdf_text).strip()
                    entry_res["extracted_tables"] = extract_tables_from_text(pdf_text)
                    break
                elif "xml" in ctype and b"<" in body[:256]:
                    decoded = body.decode("utf-8", errors="ignore")
                    xml_path = PAPERS_DIR / f"{safe_slug}.xml"
                    with open(xml_path, "w", encoding="utf-8") as xf:
                        xf.write(decoded)
                    entry_res["downloaded_file"] = str(xml_path.relative_to(ROOT_DIR))
                    entry_res["download_source"] = cand["source"]
                    clean_xml_text = re.sub(r"<[^>]+>", " ", decoded)
                    entry_res["text_char_length"] = len(clean_xml_text)
                    full_text_corpus = (abstract_text + "\n" + clean_xml_text).strip()
                    # Continue checking if a later candidate has a full PDF, unless this XML is large
                    if len(clean_xml_text) > 5000:
                        break
                elif "html" in ctype and b"validate.perfdrive.com" not in body[:2048] and b"Are you a robot?" not in body[:4096]:
                    decoded = body.decode("utf-8", errors="ignore")
                    clean_html = re.sub(r"<script.*?</script>", " ", decoded, flags=re.S | re.I)
                    clean_html = re.sub(r"<style.*?</style>", " ", clean_html, flags=re.S | re.I)
                    clean_html = re.sub(r"<[^>]+>", " ", clean_html)
                    clean_html = re.sub(r"\s+", " ", clean_html).strip()
                    if len(clean_html) > entry_res["text_char_length"]:
                        entry_res["text_char_length"] = len(clean_html)
                        full_text_corpus = (abstract_text + "\n" + clean_html).strip()
        except Exception:
            continue

    if full_text_corpus:
        metrics = extract_metrics_from_text(full_text_corpus)
        if metrics:
            entry_res["extracted_sro_mro_mentions"] = metrics
        if not entry_res["extracted_tables"] and len(full_text_corpus) > 1000:
            entry_res["extracted_tables"] = extract_tables_from_text(full_text_corpus)

    print(
        f"  [{idx}/{total}] {doi} -> "
        f"file={entry_res['downloaded_file']} ({entry_res['download_source']}) | "
        f"chars={entry_res['text_char_length']:,} | "
        f"metric_types={len(entry_res['extracted_sro_mro_mentions'])} | "
        f"tables={len(entry_res['extracted_tables'])}"
    )
    return doi, entry_res


def run_vpn_extraction(
    limit: int | None = None, workers: int = 8, cached_only: bool = False
) -> dict[str, Any]:
    """Iterate through verified DOIs in parallel and perform institutional full-text retrieval."""
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Verified DOI registry not found at {REGISTRY_PATH}")

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry_payload = json.load(f)

    prior_results: dict[str, Any] = {}
    if OUTPUT_JSON_PATH.exists():
        try:
            with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as pf:
                prior_results = json.load(pf).get("results", {})
        except Exception:
            prior_results = {}

    registry: dict[str, dict[str, Any]] = (
        registry_payload.get("verified_dois") or registry_payload.get("registry") or {}
    )
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    dois = sorted(registry.keys())
    if limit is not None and limit > 0:
        dois = dois[:limit]

    total = len(dois)
    print(
        f"[VPN Extractor] Auditing {total} verified DOIs via LBNL institutional network "
        f"(workers={workers}, cached_only={cached_only})..."
    )

    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                process_single_doi,
                idx,
                total,
                doi,
                registry[doi],
                cached_only,
                prior_results.get(doi),
            ): doi
            for idx, doi in enumerate(dois, start=1)
        }
        for fut in as_completed(futures):
            doi, entry_res = fut.result()
            results[doi] = entry_res

    # Sort results deterministically by DOI
    ordered_results = {k: results[k] for k in sorted(results.keys())}

    pdf_count = sum(
        1 for r in ordered_results.values() if (r.get("downloaded_file") or "").endswith(".pdf")
    )
    extractable_pdf_count = sum(
        1
        for r in ordered_results.values()
        if r.get("content_status") == "fulltext_pdf_extracted"
    )
    scanned_pdf_count = sum(
        1
        for r in ordered_results.values()
        if r.get("content_status") == "scanned_image_pdf_no_ocr"
    )
    xml_count = sum(
        1 for r in ordered_results.values() if (r.get("downloaded_file") or "").endswith(".xml")
    )
    xml_stub_count = sum(
        1
        for r in ordered_results.values()
        if r.get("content_status") == "elsevier_xml_metadata_stub"
    )
    fulltext_metrics_count = sum(
        1
        for r in ordered_results.values()
        if r.get("content_status") == "fulltext_pdf_extracted"
        and r.get("extracted_sro_mro_mentions")
    )
    abstract_metrics_count = sum(
        1
        for r in ordered_results.values()
        if r.get("content_status") != "fulltext_pdf_extracted"
        and r.get("extracted_sro_mro_mentions")
    )
    with_metrics_count = sum(
        1 for r in ordered_results.values() if r.get("extracted_sro_mro_mentions")
    )
    with_tables_count = sum(
        1 for r in ordered_results.values() if r.get("extracted_tables")
    )

    summary = {
        "metadata": {
            "total_dois_processed": total,
            "fulltext_files_downloaded": extractable_pdf_count,
            "pdf_files_downloaded": pdf_count,
            "pdf_files_with_extractable_text": extractable_pdf_count,
            "scanned_image_pdfs_without_ocr": scanned_pdf_count,
            "xml_files_downloaded": xml_count,
            "elsevier_xml_metadata_stubs": xml_stub_count,
            "dois_with_fulltext_sro_mro_metrics": fulltext_metrics_count,
            "dois_with_abstract_sro_mro_metrics": abstract_metrics_count,
            "dois_with_extracted_sro_mro_metrics": with_metrics_count,
            "dois_with_extracted_tables": with_tables_count,
            "papers_dir": str(PAPERS_DIR.relative_to(ROOT_DIR)),
        },
        "results": ordered_results,
    }

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    tables_only = {
        "metadata": summary["metadata"],
        "tables_by_doi": {
            doi: {
                "title": r["title"],
                "canonical_citation": r["canonical_citation"],
                "downloaded_file": r["downloaded_file"],
                "content_status": r.get("content_status", ""),
                "extracted_sro_mro_mentions": r["extracted_sro_mro_mentions"],
                "extracted_tables": r["extracted_tables"],
            }
            for doi, r in ordered_results.items()
            if r.get("extracted_sro_mro_mentions") or r.get("extracted_tables")
        },
    }
    with open(OUTPUT_TABLES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(tables_only, f, indent=2, ensure_ascii=False)

    print(
        f"[VPN Extractor] Completed: {pdf_count} PDFs ({extractable_pdf_count} extractable text, "
        f"{scanned_pdf_count} scanned image-only) + {xml_stub_count} Elsevier XML metadata stubs, "
        f"{fulltext_metrics_count} full-text DOIs + {abstract_metrics_count} abstract DOIs with SRO/MRO metrics, "
        f"{with_tables_count} DOIs with tables."
    )
    print(f"[VPN Extractor] Saved -> {OUTPUT_JSON_PATH} & {OUTPUT_TABLES_JSON_PATH}")
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
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel download/extraction worker threads (default: 8).",
    )
    parser.add_argument(
        "--cached-only",
        action="store_true",
        help="Re-run text/table extraction on already-downloaded files in data/vpn_papers/ without network calls.",
    )
    args = parser.parse_args()
    run_vpn_extraction(limit=args.limit, workers=args.workers, cached_only=args.cached_only)


if __name__ == "__main__":
    main()
