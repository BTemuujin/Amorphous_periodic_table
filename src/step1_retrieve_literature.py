"""Step 1: Literature and Database Consolidation & DOI Registry Audit.

Consolidates the curated peer-reviewed experimental benchmark catalogs of
Oxides, Chalcogenides, Metallic Glasses, and Covalent Networks (plus negative
organic glass controls for Step 2 verification), verifies every record's DOI
against the Crossref/OpenAlex-audited `data/verified_doi_registry.json`, and
optionally runs live connectivity/metadata probes against Crossref, OpenAlex,
and Semantic Scholar REST APIs.

Filters strictly for experimentally verified amorphous structures confirmed by
diffuse XRD halos, TEM selected area electron diffraction (SAED), or glass
transition (Tg) signatures from DSC.

Outputs structured records to `data/raw_amorphous_records.json`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import requests

from src.catalog_extended_systems import EXTENDED_AMORPHOUS_SYSTEMS
from src.catalog_metals_covalent import METALS_COVALENT_AND_CONTROL_SYSTEMS
from src.catalog_oxides_chalcogenides import OXIDE_AND_CHALCOGENIDE_SYSTEMS

ELEMENT_REGEX = re.compile(r"([A-Z][a-z]?)")

VALID_ELEMENTS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U",
}


def extract_constituents_from_formula(formula: str) -> List[str]:
    """Extract unique valid chemical element symbols in appearance order."""
    seen = []
    for match in ELEMENT_REGEX.finditer(formula):
        el = match.group(1)
        if el in VALID_ELEMENTS and el not in seen:
            seen.append(el)
    return seen


def query_live_literature_apis(timeout_sec: float = 4.0) -> Dict[str, Any]:
    """Run live REST API connectivity & metadata probes against Crossref, OpenAlex, and Semantic Scholar.

    Records API reachability and sample literature hit counts in `api_retrieval_status`,
    while the deterministic system dataset is consolidated from the curated catalog
    modules and audited against `data/verified_doi_registry.json`.
    Uses short timeouts and graceful fallback so offline/sandboxed environments
    never block pipeline execution.
    """
    api_metadata: Dict[str, Any] = {
        "crossref_queried": False,
        "crossref_hits": 0,
        "openalex_queried": False,
        "openalex_hits": 0,
        "semantic_scholar_queried": False,
        "semantic_scholar_hits": 0,
        "sample_api_dois": [],
    }

    queries = [
        "amorphous oxide glass XRD halo Tg DSC tetrahedral",
        "chalcogenide glass GeSe2 As2Se3 XRD DSC glass transition",
        "bulk metallic glass XRD diffuse halo TEM SAED DSC Tg",
        "amorphous silicon nitride carbide tetrahedral network XRD",
    ]

    headers = {
        "User-Agent": "AmorphousPeriodicTablePipeline/1.0 (mailto:research@example.org)"
    }

    # 1. Crossref API
    try:
        for q in queries[:2]:
            resp = requests.get(
                "https://api.crossref.org/works",
                params={"query": q, "rows": 5, "filter": "type:journal-article"},
                headers=headers,
                timeout=timeout_sec,
            )
            if resp.status_code == 200:
                api_metadata["crossref_queried"] = True
                items = resp.json().get("message", {}).get("items", [])
                api_metadata["crossref_hits"] += len(items)
                for item in items:
                    doi = item.get("DOI")
                    if doi and len(api_metadata["sample_api_dois"]) < 10:
                        api_metadata["sample_api_dois"].append(doi)
    except Exception as exc:
        api_metadata["crossref_error"] = str(exc)[:120]

    # 2. OpenAlex API
    try:
        resp = requests.get(
            "https://api.openalex.org/works",
            params={"search": "amorphous metallic glass XRD DSC Tg", "per-page": 5},
            headers=headers,
            timeout=timeout_sec,
        )
        if resp.status_code == 200:
            api_metadata["openalex_queried"] = True
            results = resp.json().get("results", [])
            api_metadata["openalex_hits"] = len(results)
    except Exception as exc:
        api_metadata["openalex_error"] = str(exc)[:120]

    # 3. Semantic Scholar API
    try:
        resp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": "amorphous glass XRD diffuse halo DSC Tg",
                "limit": 5,
                "fields": "title,externalIds,year",
            },
            headers=headers,
            timeout=timeout_sec,
        )
        if resp.status_code == 200:
            api_metadata["semantic_scholar_queried"] = True
            data = resp.json().get("data", [])
            api_metadata["semantic_scholar_hits"] = len(data)
    except Exception as exc:
        api_metadata["semantic_scholar_error"] = str(exc)[:120]

    return api_metadata


def verify_experimental_signature(verification_text: str) -> bool:
    """Confirm record explicitly cites diffuse XRD halo, TEM SAED, or DSC Tg."""
    text_lower = verification_text.lower()
    has_xrd = "xrd" in text_lower or "diffraction" in text_lower or "halo" in text_lower
    has_saed = "saed" in text_lower or "tem" in text_lower or "electron diffraction" in text_lower
    has_dsc_tg = "dsc" in text_lower or "tg" in text_lower or "calorimetr" in text_lower
    return has_xrd or has_saed or has_dsc_tg


def build_raw_amorphous_dataset(
    output_path: Path, run_live_queries: bool = True
) -> Dict[str, Any]:
    """Consolidate literature records into structured JSON format and audit against verified DOI registry."""
    api_status = (
        query_live_literature_apis()
        if run_live_queries
        else {"note": "Live API queries skipped in unit test mode"}
    )

    registry_path = Path(__file__).resolve().parent.parent / "data" / "verified_doi_registry.json"
    verified_dois: Dict[str, Any] = {}
    if registry_path.exists():
        try:
            reg_data = json.loads(registry_path.read_text(encoding="utf-8"))
            verified_dois = reg_data.get("verified_dois", {})
        except Exception:
            verified_dois = {}

    combined_tuples = (
        list(OXIDE_AND_CHALCOGENIDE_SYSTEMS)
        + list(METALS_COVALENT_AND_CONTROL_SYSTEMS)
        + list(EXTENDED_AMORPHOUS_SYSTEMS)
    )

    seen_formulas = set()
    records: List[Dict[str, Any]] = []
    registry_verified_count = 0

    for entry in combined_tuples:
        (
            formula,
            mat_class,
            verification_method,
            doi,
            source_ref,
            coord_dict,
            conversion_note,
        ) = entry

        if formula in seen_formulas:
            continue
        if not verify_experimental_signature(verification_method):
            continue

        seen_formulas.add(formula)
        constituents = extract_constituents_from_formula(formula)
        doi_entry = verified_dois.get(doi.lower().strip(), {})
        is_reg_verified = bool(doi_entry.get("verified") and doi_entry.get("http_status") == 200)
        if is_reg_verified:
            registry_verified_count += 1

        records.append(
            {
                "chemical_formula": formula,
                "constituents": constituents,
                "material_class": mat_class,
                "amorphous_verification_technique": verification_method,
                "doi": doi,
                "source_reference": source_ref,
                "reported_coordination": coord_dict,
                "crystalline_conversion_note": conversion_note,
                "doi_registry_verified": is_reg_verified,
            }
        )

    api_status["verified_doi_registry_path"] = "data/verified_doi_registry.json"
    api_status["registry_verified_records"] = registry_verified_count
    api_status["total_catalog_records"] = len(records)

    payload = {
        "metadata": {
            "step": "Step 1: Literature and Database Retrieval",
            "total_records": len(records),
            "verification_criteria": "Diffuse XRD halos, TEM SAED diffuse rings, or DSC glass transition (Tg) signatures + Crossref/OpenAlex DOI Registry Audit",
            "queried_classes": ["Oxide", "Chalcogenide", "Metallic Glass", "Covalent Network", "Organic Glass (Negative Control)"],
            "api_retrieval_status": api_status,
        },
        "records": records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out_file = root / "data" / "raw_amorphous_records.json"
    result = build_raw_amorphous_dataset(out_file, run_live_queries=True)
    print(f"[Step 1] Wrote {result['metadata']['total_records']} records to {out_file}")
