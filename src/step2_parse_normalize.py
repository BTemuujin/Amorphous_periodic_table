"""Step 2: Data Parsing and Normalization.

Parses experimental amorphous records into a normalized schema:
- Splits chemical formulas (including hyphenated multi-component oxide/chalcogenide/halide
  compositions) into individual elemental constituents and normalized stoichiometric
  atomic fractions (sum x_i = 1.0).
- Strictly filters out purely organic compounds while retaining inorganic carbides,
  oxycarbides, carbonitrides, and metal-metalloid glasses.
- Normalizes formulas to standard IUPAC electropositive-to-electronegative notation.
- Flags systems and central network-forming elements reported with tetrahedral local
  coordination (e.g., SiO4, GeO4, AlO4, PO4, BO4, GaO4, BeF4, ZnCl4, SiS4, GeSe4, PS4,
  SiN4, sp3 Si4/Ge4/C4).
- Exports the clean dataset to `amorphous_systems.json`.
"""

from __future__ import annotations

from fractions import Fraction
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Approximate IUPAC Table VI electronegativity/electropositivity sequence
# (lower rank = more electropositive, placed earlier in IUPAC formula).
IUPAC_ORDER_RANK: Dict[str, int] = {
    # Alkali metals
    "Cs": 1, "Rb": 2, "K": 3, "Na": 4, "Li": 5,
    # Alkaline earth metals
    "Ba": 6, "Sr": 7, "Ca": 8, "Mg": 9, "Be": 10,
    # Rare earths / Lanthanides, Actinides & Group 3
    "La": 11, "Ce": 12, "Pr": 13, "Nd": 14, "Sm": 15, "Eu": 16,
    "Gd": 17, "Tb": 18, "Dy": 19, "Ho": 20, "Er": 21, "Tm": 22,
    "Yb": 23, "Lu": 24, "Th": 25, "U": 26, "Y": 27, "Sc": 28,
    # Group 4-12 Transition Metals
    "Hf": 29, "Zr": 30, "Ti": 31,
    "Ta": 32, "Nb": 33, "V": 34,
    "W": 35, "Mo": 36, "Cr": 37,
    "Re": 38, "Mn": 39,
    "Os": 40, "Ru": 41, "Fe": 42,
    "Ir": 43, "Rh": 44, "Co": 45,
    "Pt": 46, "Pd": 47, "Ni": 48,
    "Au": 49, "Ag": 50, "Cu": 51,
    "Hg": 52, "Cd": 53, "Zn": 54,
    # Post-transition metals & Metalloids (Group 13-15)
    "Tl": 55, "In": 56, "Ga": 57, "Al": 58, "B": 59,
    "Pb": 60, "Sn": 61, "Ge": 62, "Si": 63, "C": 64,
    "Bi": 65, "Sb": 66, "As": 67, "P": 68, "N": 69,
    # Hydrogen & Chalcogens & Halogens
    "H": 70,
    "Te": 71, "Se": 72, "S": 73, "O": 74,
    "I": 75, "Br": 76, "Cl": 77, "F": 78,
}

COMPONENT_REGEX = re.compile(r"^([0-9]*\.?[0-9]+)?(.*)$")
ELEMENT_TOKEN_REGEX = re.compile(r"([A-Z][a-z]?)([0-9]*\.?[0-9]+)?")
INNER_GROUP_REGEX = re.compile(r"[\(\[]([^\(\)\[\]]+)[\)\]]([0-9]*\.?[0-9]+)?")
WORD_BOUNDARY_TETRAHEDR_REGEX = re.compile(r"\btetrahedr", re.IGNORECASE)

# Central cations/metalloids eligible for tetrahedral_coordination_flag = 1 when their
# reported coordination environment explicitly describes tetrahedral (CN=4) geometry.
CENTRAL_TETRAHEDRAL_CANDIDATES = {
    "Si", "Ge", "Al", "P", "B", "Ga", "As", "V", "Ti", "Mo", "W",
    "Zn", "Be", "C", "Sn", "In", "Cd",
}

ANION_LIGANDS = {"O", "S", "Se", "Te", "N", "F", "Cl", "Br"}

PRIMARY_NETWORK_FORMERS = {"Si", "Ge", "B", "P", "As"}
INTERMEDIATE_ELEMENTS = {
    "Al", "Ga", "Ti", "V", "Mo", "W", "Te", "Se", "S", "Sb", "Bi",
    "Zn", "Pb", "Be", "Fe", "Nb", "Ta", "Zr", "Hf", "Sn", "In", "Cd", "C", "N", "Sc",
    "Tl", "Os", "Th",
}
ELECTROPOSITIVE_MODIFIER_CATIONS = {
    "Li", "Na", "K", "Rb", "Cs", "Ag",
    "Mg", "Ca", "Sr", "Ba",
    "Y", "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "U",
}




def parse_single_formula_unit(sub_formula: str) -> Dict[str, float]:
    """Parse a single chemical formula unit, recursively expanding parenthesized/bracketed groups.

    Examples:
        'Ca(PO3)2' -> {'Ca': 1.0, 'P': 2.0, 'O': 6.0}
        '(Zr0.5Cu0.5)90Al10' -> {'Zr': 45.0, 'Cu': 45.0, 'Al': 10.0}
    """
    expr = sub_formula.strip()
    # Iteratively expand innermost (...)m or [...]m groups until flat
    while True:
        match = INNER_GROUP_REGEX.search(expr)
        if not match:
            break
        inner_content, mult_str = match.groups()
        group_mult = float(mult_str) if mult_str else 1.0
        inner_counts = parse_single_formula_unit(inner_content)
        expanded_str = "".join(
            f"{el}{cnt * group_mult:g}" for el, cnt in inner_counts.items()
        )
        expr = expr[: match.start()] + expanded_str + expr[match.end() :]

    unit_counts: Dict[str, float] = {}
    for el_match in ELEMENT_TOKEN_REGEX.finditer(expr):
        el, count_str = el_match.groups()
        count = float(count_str) if count_str else 1.0
        unit_counts[el] = unit_counts.get(el, 0.0) + count
    return unit_counts


def parse_molar_counts(formula: str) -> Tuple[Dict[str, float], int]:
    """Parse single or hyphenated multi-component formula into unnormalized molar counts and part count.

    Note:
        Hyphenated multi-component formulas (e.g., ``xA-yB`` such as ``2Fe2O3-3P2O5``
        or ``WO3-4TeO2``) interpret leading numerical coefficients as molar ratios of
        the respective oxide/chalcogenide/halide components (defaulting to 1.0 when
        omitted, e.g., equimolar ``ZnO-B2O3``). Weight-percent (wt.%) or unprefixed
        phase-system notations must be converted to explicit molar stoichiometry before
        catalog ingestion.
    """
    parts = [p.strip() for p in formula.split("-") if p.strip()]
    raw_counts: Dict[str, float] = {}

    for part in parts:
        comp_match = COMPONENT_REGEX.match(part)
        if not comp_match:
            continue
        mult_str, sub_formula = comp_match.groups()
        multiplier = float(mult_str) if mult_str else 1.0
        unit_counts = parse_single_formula_unit(sub_formula)
        for el, count in unit_counts.items():
            raw_counts[el] = raw_counts.get(el, 0.0) + multiplier * count

    return raw_counts, len(parts)


def parse_chemical_formula(formula: str) -> Dict[str, float]:
    """Parse single or hyphenated multi-component chemical formula into normalized atomic fractions.

    Hyphenated formulas ``xA-yB`` are treated as molar combinations of components ``A`` and ``B``.

    Examples:
        'SiO2' -> {'Si': 1/3, 'O': 2/3}
        'Na2O-CaO-5SiO2' -> Na:2, Ca:1, Si:5, O:12 -> normalized to sum = 1.0
        'Ca(PO3)2' -> Ca:1/9, P:2/9, O:6/9
        '(Zr0.5Cu0.5)90Al10' -> Zr:0.45, Cu:0.45, Al:0.10
    """
    raw_counts, _ = parse_molar_counts(formula)
    total = sum(raw_counts.values())
    if total <= 0:
        raise ValueError(f"Could not parse any valid elements from formula: {formula}")

    normalized: Dict[str, float] = {}
    running_sum = 0.0
    items = list(raw_counts.items())
    for idx, (el, val) in enumerate(items):
        if idx < len(items) - 1:
            frac = round(val / total, 6)
            normalized[el] = frac
            running_sum += frac
        else:
            normalized[el] = round(max(0.0, 1.0 - running_sum), 6)

    return normalized


def is_purely_organic(elements: List[str], material_class: str) -> bool:
    """Return True if the entry is a purely organic compound (e.g., glucose, PMMA, o-terphenyl).

    Preserves elemental tetrahedral amorphous carbon ('C') and inorganic carbides/oxycarbides/
    carbonitrides/metallic glasses (which contain Si, B, Fe, Mn, Mo, Cr, Ca, etc.).
    """
    if material_class.lower().startswith("organic"):
        return True
    el_set = set(elements)
    if el_set == {"C"}:
        # Elemental tetrahedral amorphous carbon (ta-C) is an inorganic covalent network
        return False
    organic_only_alphabet = {"C", "H", "O", "N"}
    if "C" in el_set and "H" in el_set and el_set.issubset(organic_only_alphabet):
        return True
    return False


def format_iupac_formula(
    raw_formula: str, atomic_fractions: Dict[str, float] | None = None
) -> str:
    """Format chemical formula in standard IUPAC electropositive-to-electronegative order.

    - Preserves standard metallurgical atomic-percentage convention (sum = 100) for single-unit
      alloy formulas such as `Fe80B20` -> `Fe80B20` or `(Zr0.5Cu0.5)90Al10` -> `Zr45Cu45Al10`.
    - For stoichiometric oxide, chalcogenide, halide, and covalent compounds (whether written as
      single units like `Ca(PO3)2` / `Li2B2S4` or hyphenated like `CaO-P2O5` / `Li2S-B2S3` /
      `2MgO-2Al2O3-5SiO2`), uses `fractions.Fraction` + LCM/GCD reduction to produce a canonical
      empirical IUPAC formula (`CaP2O6`, `LiBS2`, `Mg2Al4Si5O18`).
    """
    molar_counts, num_parts = parse_molar_counts(raw_formula)
    if not molar_counts and atomic_fractions:
        molar_counts = dict(atomic_fractions)
        num_parts = 1

    sorted_elements = sorted(
        molar_counts.keys(), key=lambda el: (IUPAC_ORDER_RANK.get(el, 99), el)
    )

    total_moles = sum(molar_counts.values())
    # Preserve metallurgical atomic-percentage convention (sum == 100) for single-part alloy formulas
    is_atomic_percent = abs(total_moles - 100.0) < 1e-2 and num_parts == 1

    if not is_atomic_percent:
        fracs = [
            Fraction(molar_counts[el]).limit_denominator(1000)
            for el in sorted_elements
        ]
        # Compute LCM of denominators so all ratios become exact integers
        denom_lcm = 1
        for f in fracs:
            denom_lcm = math.lcm(denom_lcm, f.denominator)
        scaled_ints = [int(f * denom_lcm) for f in fracs]
        if all(val > 0 for val in scaled_ints):
            common_div = scaled_ints[0]
            for val in scaled_ints[1:]:
                common_div = math.gcd(common_div, val)
            common_div = max(1, common_div)
            reduced_ints = [val // common_div for val in scaled_ints]
            # Use canonical reduced empirical integers when denominators are clean
            if max(reduced_ints) <= 60 and denom_lcm <= 20:
                tokens = [
                    f"{el}{c if c > 1 else ''}"
                    for el, c in zip(sorted_elements, reduced_ints)
                ]
                return "".join(tokens)

    tokens = []
    for el in sorted_elements:
        val = molar_counts[el]
        if abs(val - 1.0) < 1e-4 and not is_atomic_percent:
            tokens.append(el)
        elif abs(val - round(val)) < 1e-4:
            tokens.append(f"{el}{int(round(val))}")
        else:
            formatted = f"{val:.2f}".rstrip("0").rstrip(".")
            tokens.append(f"{el}{formatted}")
    return "".join(tokens)


def is_element_tetrahedral_former(
    el: str, coord_desc: str, material_class: str = ""
) -> bool:
    """Determine if a specific element is a central tetrahedrally coordinated atom (Resolution A3).

    Sets flag = 1 strictly for central tetrahedral network formers/intermediates (CN=4)
    (e.g., Si in SiO4/SiS4/SiN4/Si4, Ge in GeO4/GeS4/GeSe4/Ge4, Al in AlO4/AlN4,
    P in PO4/PS4/PSe4, B when BO4/BS4/BN4 is present, Ga in GaO4/GaS4/GaSe4/GaN4/GaAs4,
    Be in BeF4, Zn in ZnO4/ZnCl4/ZnAs4, V in VO4, Ti in TiO4, Mo in MoO4, W in WO4,
    C in sp3 C4/SiC/SiOC).
    Metallic glasses (CN=8-15 polytetrahedral/icosahedral/trigonal-prism packing),
    anions (O, S, Se, Te, F, Cl, I), and modifiers (Na, K, Li, Ca, Mg, Ba, etc.) return False.
    """
    if material_class == "Metallic Glass":
        return False
    if el not in CENTRAL_TETRAHEDRAL_CANDIDATES:
        return False
    desc_lower = coord_desc.lower()
    # Explicitly strip Frank-Kasper/metallic 'polytetrahedral', 'quasi-tetrahedral',
    # and 'tetrahedral interstices' phrases before testing for true 4-coordinate motifs
    desc_cleaned = (
        desc_lower.replace("polytetrahedral", " ")
        .replace("polytetrahedra", " ")
        .replace("quasi-tetrahedral", " ")
        .replace("quasi-tetrahedra", " ")
        .replace("tetrahedral interstices", " ")
        .replace("tetrahedral interstice", " ")
        .replace("icosahedral/tetrahedral", " ")
    )
    if any(
        high_cn in desc_cleaned
        for high_cn in (
            "cn=7", "cn=8", "cn=9", "cn=10", "cn=11",
            "cn=12", "cn=13", "cn=14", "cn=15", "cn=16",
        )
    ):
        return False
    if WORD_BOUNDARY_TETRAHEDR_REGEX.search(desc_cleaned):
        return True
    # Match explicit MX4 motifs like SiO4, GeO4, AlO4, PO4, BO4, BS4, GaO4, BeF4, ZnCl4, ZnBr4, sp3
    tet_patterns = [
        f"{el.lower()}o4", f"{el.lower()}s4", f"{el.lower()}se4", f"{el.lower()}te4",
        f"{el.lower()}n4", f"{el.lower()}f4", f"{el.lower()}cl4", f"{el.lower()}br4",
        f"{el.lower()}4",
        "sp3", "cn=4", "cn=3,4", "cn=4,6", "cn=4-5", "cn=4-6",
    ]
    return any(pat in desc_cleaned for pat in tet_patterns)


def classify_element_role_in_material(
    el: str, material_class: str, is_tet_center: bool, coord_desc: str
) -> str:
    """Assign functional structural role for the element in this specific material."""
    if is_tet_center:
        if el in PRIMARY_NETWORK_FORMERS:
            return "Primary Tetrahedral Network Former"
        return "Tetrahedral Intermediate / Network Former"

    if el in PRIMARY_NETWORK_FORMERS:
        if material_class == "Metallic Glass":
            return "Glass-Forming Metalloid Solute"
        return "Trigonal/Pyramidal Network Former"

    if material_class == "Metallic Glass":
        if el in {"C", "Si", "B", "P", "Ge", "Sn", "Al", "Ga", "Be"}:
            return "Topological/Electronic Stabilizer (Metalloid/Simple Metal)"
        if el in ELECTROPOSITIVE_MODIFIER_CATIONS:
            return "Network Modifier / Charge Compensator"
        return "Metallic Glass Matrix / Cluster Former"


    if el == "Te" and material_class == "Oxide":
        return "Network Intermediate"

    if el in ANION_LIGANDS:
        return "Bridging/Terminal Anion Ligand"

    if el in INTERMEDIATE_ELEMENTS:
        return "Network Intermediate"

    return "Network Modifier / Charge Compensator"



VAPOR_THIN_FILM_FORMULAS: set[str] = {
    "Si", "Ge", "C", "SiH0.12", "SiC", "Si3N4", "BN", "BC2N", "P", "As", "Sb", "B",
    "Si0.5Ge0.5", "GaAs", "InP", "GaN", "AlN",
    "FeGe", "FeGe3", "FeSi", "Fe3Si7", "CoSi", "CoGe", "MnSi", "Cr3Si7",
    "Gd7Si43", "Tb3Si17", "Gd3Ge17", "MoGe", "NbSi",
    "Re0.5Ta0.5", "Ir45Ta55", "Rh75Si25", "Ru75P25", "Ta42Ni40Co18", "V45Zr55",
    "HfO2-4SiO2", "ZrO2-4SiO2", "InGaZnO4", "TiO2", "Ta2O5", "HfO2", "ZrO2",
    "ZnSnO3", "In2O3", "OsO2",
    "Bi2Se3", "Bi2Te3", "Sb2Te3", "Sb2S3", "Ge2Sb2Te5", "Sb2Se3", "GeTe",
    "Ag5In5Sb60Te30", "MoS3", "MoS2", "Li10GeP2S12", "Na3PS4",
}

RAPID_QUENCHED_OXIDE_FORMULAS: set[str] = {
    "Al2O3", "Ca3Al4O9", "Y3Al5O12", "BaTi2O5", "MgSiO3",
}


def classify_synthesis_regime(
    raw_formula: str,
    iupac_formula: str,
    material_class: str,
    verification_method: str,
    note: str,
) -> Tuple[str, str]:
    """Classify each amorphous system into its canonical experimental synthesis regime."""
    if raw_formula in VAPOR_THIN_FILM_FORMULAS or iupac_formula in VAPOR_THIN_FILM_FORMULAS:
        return "vapor_thin_film", "Vapor / Thin-Film / Solid-State"

    if raw_formula in RAPID_QUENCHED_OXIDE_FORMULAS or iupac_formula in RAPID_QUENCHED_OXIDE_FORMULAS:
        return "rapid_quenched_ribbon", "Rapid Ribbon / Splat / Levitation"

    combined = f"{verification_method} {note}".lower()
    if any(
        kw in combined
        for kw in (
            "sputter",
            "co-evaporat",
            "e-beam",
            "uhv-deposited",
            "uhv – deposited",
            "thermally evaporated",
            "pecvd",
            "chemical-vapor-deposited",
            "cathodic vacuum arc",
            "flash-evaporated",
            "flash evaporation",
            "ion-beam sputtered",
            "ball milling",
            "mechanochemically",
        )
    ):
        return "vapor_thin_film", "Vapor / Thin-Film / Solid-State"

    if material_class == "Metallic Glass":
        has_explicit_bmg = any(
            bmg_kw in combined
            for bmg_kw in (
                "bmg",
                "bulk",
                "vitreloy",
                "sam1651",
                "casting diameter",
                "critical cooling rate",
                "fluxed",
                "ingot",
                "rod",
                "cylinder",
            )
        ) or bool(re.search(r"\b\d+(?:\.\d+)?\s*mm\b(?!\s*2)", combined))
        has_explicit_ribbon = any(
            rib_kw in combined
            for rib_kw in (
                "ribbon",
                "melt-spun",
                "melt spun",
                "splat",
                "electroplat",
                "rapidly solidified",
                "metglas",
            )
        )
        if has_explicit_bmg and not has_explicit_ribbon:
            return "bulk_melt_quenched", "Bulk Melt-Quenched Glass"
        return "rapid_quenched_ribbon", "Rapid Ribbon / Splat / Levitation"

    return "bulk_melt_quenched", "Bulk Melt-Quenched Glass"


def canonical_stoichiometry_key(
    atomic_fractions: Dict[str, float]
) -> Tuple[Tuple[str, float], ...]:
    """Build a canonical stoichiometry key sorted by IUPAC order rounded to 4 decimal places."""
    sorted_els = sorted(
        atomic_fractions.keys(), key=lambda e: (IUPAC_ORDER_RANK.get(e, 99), e)
    )
    return tuple((el, round(atomic_fractions[el], 4)) for el in sorted_els)


def run_step2_normalization(
    input_path: Path, output_path: Path
) -> Dict[str, Any]:
    """Execute Step 2 parsing, organic filtering, IUPAC normalization, and tetrahedral flagging."""
    from src.structural_characterization_data import compute_system_structural_characterization

    raw_payload = json.loads(input_path.read_text(encoding="utf-8"))
    raw_records = raw_payload.get("records", [])

    registry_path = Path(__file__).resolve().parent.parent / "data" / "verified_doi_registry.json"
    verified_dois_map: Dict[str, Dict[str, Any]] = {}
    if registry_path.exists():
        try:
            reg_data = json.loads(registry_path.read_text(encoding="utf-8"))
            verified_dois_map = reg_data.get("verified_dois", {})
        except Exception:
            verified_dois_map = {}

    normalized_systems: List[Dict[str, Any]] = []
    filtered_organics: List[Dict[str, str]] = []
    seen_iupac_formulas: set[str] = set()
    seen_stoich_keys: set[Tuple[Tuple[str, float], ...]] = set()

    for rec in raw_records:
        raw_formula = rec["chemical_formula"]
        mat_class = rec["material_class"]
        constituents = rec["constituents"]

        if is_purely_organic(constituents, mat_class):
            filtered_organics.append(
                {
                    "raw_formula": raw_formula,
                    "material_class": mat_class,
                    "reason": "Purely organic glass filtered out per Step 2 requirement",
                }
            )
            continue

        atomic_fractions = parse_chemical_formula(raw_formula)
        iupac_formula = format_iupac_formula(raw_formula, atomic_fractions)
        stoich_key = canonical_stoichiometry_key(atomic_fractions)
        if iupac_formula in seen_iupac_formulas or stoich_key in seen_stoich_keys:
            continue
        seen_iupac_formulas.add(iupac_formula)
        seen_stoich_keys.add(stoich_key)

        coord_map: Dict[str, str] = rec.get("reported_coordination", {})

        element_entries: List[Dict[str, Any]] = []
        tet_elements_in_system: List[str] = []

        # Sort constituent entries in IUPAC order
        sorted_els = sorted(
            atomic_fractions.keys(), key=lambda e: (IUPAC_ORDER_RANK.get(e, 99), e)
        )

        for el in sorted_els:
            coord_desc = coord_map.get(el, "Not explicitly specified")
            tet_flag = (
                1 if is_element_tetrahedral_former(el, coord_desc, mat_class) else 0
            )
            if tet_flag == 1:
                tet_elements_in_system.append(el)
            role = classify_element_role_in_material(el, mat_class, tet_flag == 1, coord_desc)

            element_entries.append(
                {
                    "element_symbol": el,
                    "atomic_fraction": atomic_fractions[el],
                    "tetrahedral_coordination_flag": tet_flag,
                    "coordination_environment": coord_desc,
                    "element_role": role,
                }
            )

        system_tet_flag = 1 if len(tet_elements_in_system) > 0 else 0

        doi_str = rec["doi"].strip()
        doi_meta = verified_dois_map.get(doi_str.lower(), {})
        oa_meta = doi_meta.get("openalex") or {}
        paper_title = doi_meta.get("title", "")
        journal_name = doi_meta.get("journal", "")
        pub_year = doi_meta.get("year")
        authors_list = doi_meta.get("authors", [])
        abstract_snippet = oa_meta.get("abstract") or doi_meta.get("crossref_abstract") or ""

        synth_regime, synth_label = classify_synthesis_regime(
            raw_formula=raw_formula,
            iupac_formula=iupac_formula,
            material_class=mat_class,
            verification_method=rec["amorphous_verification_technique"],
            note=rec.get("crystalline_conversion_note", ""),
        )

        struct_char = compute_system_structural_characterization(
            formula=iupac_formula,
            raw_formula=raw_formula,
            material_class=mat_class,
            atomic_fractions=atomic_fractions,
            coord_map=coord_map,
            verification_method=rec["amorphous_verification_technique"],
        )

        normalized_systems.append(
            {
                "formula": iupac_formula,
                "raw_formula": raw_formula,
                "material_class": mat_class,
                "synthesis_regime": synth_regime,
                "synthesis_regime_label": synth_label,
                "verification_method": rec["amorphous_verification_technique"],
                "reference_doi": doi_str,
                "source_reference": rec.get("source_reference", ""),
                "paper_title": paper_title,
                "journal": journal_name,
                "publication_year": pub_year,
                "authors": authors_list,
                "openalex_id": oa_meta.get("openalex_id", ""),
                "abstract_snippet": abstract_snippet[:500] if abstract_snippet else "",
                "system_tetrahedral_flag": system_tet_flag,
                "tetrahedral_former_elements": tet_elements_in_system,
                "crystalline_conversion_note": rec.get("crystalline_conversion_note", ""),
                "structural_characterization": struct_char,
                "elements": element_entries,
            }
        )

    regime_counts: Dict[str, int] = {
        "bulk_melt_quenched": sum(1 for s in normalized_systems if s["synthesis_regime"] == "bulk_melt_quenched"),
        "rapid_quenched_ribbon": sum(1 for s in normalized_systems if s["synthesis_regime"] == "rapid_quenched_ribbon"),
        "vapor_thin_film": sum(1 for s in normalized_systems if s["synthesis_regime"] == "vapor_thin_film"),
    }

    output_payload = {
        "metadata": {
            "step": "Step 2: Data Parsing and Normalization",
            "total_input_records": len(raw_records),
            "filtered_organic_records_count": len(filtered_organics),
            "filtered_organic_records": filtered_organics,
            "total_normalized_inorganic_systems": len(normalized_systems),
            "systems_with_tetrahedral_coordination": sum(
                1 for s in normalized_systems if s["system_tetrahedral_flag"] == 1
            ),
            "synthesis_regime_counts": regime_counts,
            "unique_elements_count": len(
                {
                    el["element_symbol"]
                    for s in normalized_systems
                    for el in s["elements"]
                }
            ),
        },
        "systems": normalized_systems,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    return output_payload


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    in_file = root / "data" / "raw_amorphous_records.json"
    out_file = root / "amorphous_systems.json"
    res = run_step2_normalization(in_file, out_file)
    print(
        f"[Step 2] Normalized {res['metadata']['total_normalized_inorganic_systems']} "
        f"inorganic amorphous systems (filtered {res['metadata']['filtered_organic_records_count']} "
        f"purely organic glasses) -> {out_file}"
    )
