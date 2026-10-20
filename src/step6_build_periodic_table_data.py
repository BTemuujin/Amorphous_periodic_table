"""
Step 6A: Build 118-Element Amorphous Periodic Table Dataset

Merges baseline 118-element periodic table metadata (atomic number, symbol, name,
atomic mass, period, group, block, radioactivity, electronic configuration,
chemical bonding, crystallography, and physical properties) with the verified
SQLite database (`amorphous_materials.db`) and statistical attribution analysis
(`data/statistical_analysis_results.json`).

Assigns each of the 118 elements to a visual fill mode and structural category:
- `fill_mode = "full"` (49 elements): Elements that make the amorphous phase possible
  by forming the continuous random network (CRN) or icosahedral/polytetrahedral
  cluster backbone:
  1a. Primary Tetrahedral Network Formers (5): Si, Ge, P, B, As
  1b. Bridging Anion Network Formers (7): O, S, Se, N, F, Cl, Br
  2a. Conditional Tetrahedral Intermediates (12): Al, Ga, Zn, Be, C, V, Mo, W, Ti, Sn, In, Cd
  2b. Oxide / Chalcogenide / Halide Intermediates (13): Te, Sb, Bi, Pb, Fe, Zr, Hf, Nb, Ta, Sc, Tl, Os, Th
  2c. Metallic Cluster / Host Intermediates (12): Cu, Ni, Co, Pd, Pt, Au, Cr, Mn, Ru, Rh, Re, Ir
- `fill_mode = "half"` (28 elements): Elements that are part of reported amorphous
  systems as Network Modifiers, Charge Compensators, or Topological Cages (rendered
  with a diagonal 50/50 split):
  3. Network Modifiers / Participants (28): Li, Na, K, Rb, Cs, Ag, Mg, Ca, Sr, Ba,
     Y, La, Ce, Pr, Nd, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb, Lu, U, I, H
- `fill_mode = "none"` (41 elements): Elements with zero verified inorganic amorphous
  systems in `amorphous_materials.db` (rendered with a white cell background).

Exports `data/amorphous_periodic_table_118.json`.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import re
from src.step5_generate_report import (
    CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES as CRYSTALLINE_TO_AMORPHOUS_EXAMPLES,
)


CATEGORY_VISUAL_META: Dict[str, Dict[str, str]] = {
    "primary_tetrahedral_former": {
        "category_key": "primary_tetrahedral_former",
        "category_label": "Primary Tetrahedral Network Former",
        "short_label": "Tet Former",
        "fill_mode": "full",
        "color_hex": "#7EC8E3",
        "border_hex": "#0284C7",
        "text_hex": "#0F172A",
        "badge_hex": "#0369A1",
        "description": (
            "Forms continuous random networks (CRNs) via corner-sharing MX4 tetrahedra "
            "or mixed trigonal/tetrahedral polyhedra (CN=3-4) and acts as a metalloid "
            "solute center in bulk metallic glasses."
        ),
    },
    "bridging_anion_former": {
        "category_key": "bridging_anion_former",
        "category_label": "Bridging Anion Network Former",
        "short_label": "Bridging Anion",
        "fill_mode": "full",
        "color_hex": "#A7F3D0",
        "border_hex": "#059669",
        "text_hex": "#064E3B",
        "badge_hex": "#047857",
        "description": (
            "Provides low-coordination flexible bridges (-O-, -S-, -Se-, -N<, -F-, -Cl-, -Br-; "
            "CN=2-3) between cation polyhedra, enabling bond-angle disorder without "
            "cleaving covalent network connectivity."
        ),
    },
    "conditional_tetrahedral_intermediate": {
        "category_key": "conditional_tetrahedral_intermediate",
        "category_label": "Conditional Tetrahedral Intermediate",
        "short_label": "Cond. Tet",
        "fill_mode": "full",
        "color_hex": "#C4B5FD",
        "border_hex": "#7C3AED",
        "text_hex": "#1E1B4B",
        "badge_hex": "#6D28D9",
        "description": (
            "Adopts 4-coordinate tetrahedral network coordination (e.g., AlO4-, GaO4-, "
            "BeF4, ZnCl4/ZnBr4, sp3 C4, VO4, MoO4, WO4, TiO4, InP4, CdGeAs2) when charge-compensated "
            "or covalently bonded; also stabilizes multicomponent metallic glasses."
        ),
    },
    "oxide_chalcogenide_intermediate": {
        "category_key": "oxide_chalcogenide_intermediate",
        "category_label": "Oxide / Chalcogenide / BMG Intermediate",
        "short_label": "Poly. Interm.",
        "fill_mode": "full",
        "color_hex": "#FDE68A",
        "border_hex": "#D97706",
        "text_hex": "#451A03",
        "badge_hex": "#B45309",
        "description": (
            "Forms pyramidal, disphenoidal, octahedral, or antiprismatic glass polyhedra (TeO4, SbO3, "
            "BiO6, PbO4, TlSe3/TlSe4, NbO6, TaO6, OsO6, ZrF7/ZrO6, HfO6, FeO6, ThF8/ThF9) and/or "
            "serves as an early/late transition-metal matrix host in bulk metallic glasses."
        ),
    },
    "metallic_cluster_intermediate": {
        "category_key": "metallic_cluster_intermediate",
        "category_label": "Metallic Cluster / BMG Host Intermediate",
        "short_label": "BMG Cluster",
        "fill_mode": "full",
        "color_hex": "#FDBA74",
        "border_hex": "#EA580C",
        "text_hex": "#431407",
        "badge_hex": "#C2410C",
        "description": (
            "Stabilizes five-fold symmetric icosahedral <0,0,12,0> (CN=12), polytetrahedral "
            "Frank-Kasper, and capped trigonal-prismatic clusters in metallic melts that "
            "frustrate periodic FCC/BCC/HCP crystallization."
        ),
    },
    "network_modifier": {
        "category_key": "network_modifier",
        "category_label": "Network Modifier / Charge Compensator (Half-Cell)",
        "short_label": "Modifier",
        "fill_mode": "half",
        "color_hex": "#F9A8D4",
        "border_hex": "#DB2777",
        "text_hex": "#500724",
        "badge_hex": "#BE185D",
        "description": (
            "Participates in multicomponent amorphous systems by modifying tetrahedral "
            "networks (creating non-bridging anions), charge-compensating [AlO4]-/[BO4]- "
            "tetrahedra, passivating dangling bonds (H), or providing large-atom topological "
            "cages in rare-earth/alkaline-earth/actinide glasses."
        ),
    },
    "unreported": {
        "category_key": "unreported",
        "category_label": "Unreported / No Verified Inorganic Glass in Dataset",
        "short_label": "No Amorphous Data",
        "fill_mode": "none",
        "color_hex": "#FFFFFF",
        "border_hex": "#CBD5E1",
        "text_hex": "#475569",
        "badge_hex": "#64748B",
        "description": (
            "Not present in the experimentally verified inorganic amorphous systems "
            "(includes noble gases, short-lived synthetic/radioactive elements, "
            "and superheavy transactinides lacking peer-reviewed bulk/thin-film "
            "inorganic glass verification)."
        ),
    },
}


def determine_coordination_3d_motif(
    symbol: str,
    category_key: str,
    tet_count: int,
    crystal_system: str,
) -> Dict[str, Any]:
    """Return a structured 3D coordination motif specification for the WebGL viewer."""
    if category_key == "primary_tetrahedral_former":
        if symbol in {"B", "As"}:
            return {
                "motif_id": "mixed_trigonal_tetrahedral",
                "title": f"{symbol}O3 / {symbol}O4 Mixed Polyhedral & Tetrahedral Network",
                "coordination_number": "CN = 3 & 4",
                "short_cn_label": "CN=3,4",
                "bond_angle": "120.0° (trigonal) / 109.5° (tetrahedral)",
                "central_symbol": symbol,
                "ligand_symbol": "O" if symbol == "B" else "Se",
                "geometry_summary": (
                    f"{symbol} bridges planar/pyramidal 3-coordinate units ({symbol}X3) and "
                    f"4-coordinate tetrahedra ({symbol}X4), plus M9{symbol} trigonal prisms in BMGs."
                ),
            }
        return {
            "motif_id": "corner_sharing_tetrahedra",
            "title": f"Corner-Sharing {symbol}X4 Continuous Random Network (CRN)",
            "coordination_number": "CN = 4 (Tetrahedral)",
            "short_cn_label": "CN=4",
            "bond_angle": "109.47° intra-tetrahedral; 130°–150° inter-tetrahedral",
            "central_symbol": symbol,
            "ligand_symbol": "O" if symbol in {"Si", "P"} else "Se",
            "geometry_summary": (
                f"Zachariasen-Phillips-Thorpe corner-sharing {symbol}X4 tetrahedra (z=4) "
                "linked by flexible 2-coordinate bridging anions with rotational disorder."
            ),
        }

    if category_key == "bridging_anion_former":
        if symbol == "N":
            return {
                "motif_id": "trigonal_bridging_anion",
                "title": "3-Coordinate N(Si)3 Cross-Linking Nitride Bridge",
                "coordination_number": "CN = 3 (Trigonal Planar)",
                "short_cn_label": "CN=3",
                "bond_angle": "~120.0° Si–N–Si",
                "central_symbol": "N",
                "ligand_symbol": "Si",
                "geometry_summary": (
                    "Triply bridging nitrogen links three SiN4/BN3 polyhedra, increasing "
                    "topological cross-link density and raising Tg above 1200 K."
                ),
            }
        cation = "Si" if symbol == "O" else ("Ge" if symbol in {"S", "Se"} else ("Be" if symbol == "F" else "Zn"))
        return {
            "motif_id": "bridging_anion_dimer",
            "title": f"Flexible Bridging -{symbol}- Anion Linkage ({cation}–{symbol}–{cation})",
            "coordination_number": "CN = 2 (Angular Bridge)",
            "short_cn_label": "CN=2",
            "bond_angle": "125°–152° (broad bond-angle distribution Δθ)",
            "central_symbol": symbol,
            "ligand_symbol": cation,
            "geometry_summary": (
                f"Two {cation}{symbol}4 tetrahedra sharing a central 2-coordinated {symbol} "
                "vertex; variability in the inter-tetrahedral angle absorbs topological strain."
            ),
        }

    if category_key == "conditional_tetrahedral_intermediate":
        ligand = (
            "F" if symbol == "Be"
            else ("Cl" if symbol == "Zn"
                  else ("C" if symbol == "C"
                        else ("As" if symbol in {"Cd", "Sn"}
                              else ("P" if symbol == "In" else "O"))))
        )
        return {
            "motif_id": "conditional_tetrahedron",
            "title": f"Conditional Tetrahedral {symbol}{ligand}4 Network Unit",
            "coordination_number": "CN = 4 (Tetrahedral)",
            "short_cn_label": "CN=4",
            "bond_angle": "109.5° ± 6° (charge-compensated / covalent tetrahedron)",
            "central_symbol": symbol,
            "ligand_symbol": ligand,
            "geometry_summary": (
                f"{symbol} enters the 4-coordinate tetrahedral network backbone ({symbol}{ligand}4) "
                f"across {tet_count} verified non-metallic glass systems."
            ),
        }

    if category_key == "oxide_chalcogenide_intermediate":
        ligand = "Se" if symbol == "Tl" else ("F" if symbol == "Th" else "O")
        title_str = (
            "Distorted TlSe3 / TlSe4 Lone-Pair Pyramidal Intermediate"
            if symbol == "Tl"
            else (
                "High-Coordination ThF8 / ThF9 Actinide Fluoride Polyhedron"
                if symbol == "Th"
                else f"Distorted {symbol}O6 / {symbol}O4 Intermediate Glass Polyhedron"
            )
        )
        cn_str = (
            "CN = 3–4 (Lone-Pair Pyramidal)"
            if symbol == "Tl"
            else (
                "CN = 8–9 (Square Antiprismatic)"
                if symbol == "Th"
                else "CN = 4–7 (Octahedral / Disphenoidal)"
            )
        )
        short_cn = "CN=3–4" if symbol == "Tl" else ("CN=8–9" if symbol == "Th" else "CN=4–7")
        return {
            "motif_id": "octahedral_polyhedral_intermediate",
            "title": title_str,
            "coordination_number": cn_str,
            "short_cn_label": short_cn,
            "bond_angle": "90° / 180° distorted polyhedral angles",
            "central_symbol": symbol,
            "ligand_symbol": ligand,
            "geometry_summary": (
                f"High-field-strength or lone-pair {symbol} polyhedra cross-linked by "
                "corner-sharing network formers (or forming polytetrahedral BMG cages)."
            ),
        }

    if category_key == "metallic_cluster_intermediate":
        return {
            "motif_id": "icosahedral_cluster_cn12",
            "title": f"{symbol}-Centered <0,0,12,0> Icosahedral Metallic Glass Cluster",
            "coordination_number": "CN = 12 (Five-Fold Icosahedron)",
            "short_cn_label": "CN=12",
            "bond_angle": "63.43° / 116.57° (5-fold rotational symmetry)",
            "central_symbol": symbol,
            "ligand_symbol": "Zr" if symbol in {"Cu", "Ni", "Co", "Pd", "Pt", "Au"} else "B",
            "geometry_summary": (
                f"13-atom icosahedral short-range order centered on {symbol}; five-fold "
                "local symmetry cannot tile 3D Euclidean space periodically, frustrating crystallization."
            ),
        }

    if category_key == "network_modifier":
        if symbol == "H":
            return {
                "motif_id": "hydrogen_passivated_tetrahedron",
                "title": "Monovalent Si–H Dangling-Bond Terminator in a-Si:H",
                "coordination_number": "CN = 1 (Terminal Passivator)",
                "short_cn_label": "CN=1",
                "bond_angle": "109.5° H–Si–Si",
                "central_symbol": "H",
                "ligand_symbol": "Si",
                "geometry_summary": (
                    "Terminal Si–H bond relieves overconstrained 4-fold a-Si random networks "
                    "and eliminates mid-gap dangling-bond electronic defects."
                ),
            }
        return {
            "motif_id": "modifier_nbo_cage",
            "title": f"{symbol}+/n+ Network Modifier Cage & Non-Bridging Anions (NBO)",
            "coordination_number": "CN = 6–9 (Ionic Cage / Topological Frustrator)",
            "short_cn_label": "CN=6–9",
            "bond_angle": "Irregular multi-oxygen / multi-atom coordination shell",
            "central_symbol": symbol,
            "ligand_symbol": "O",
            "geometry_summary": (
                f"{symbol} occupies interstitial cages coordinated by non-bridging anions "
                "(depolymerizing Q4 -> Q3) or forms large-radius Z15-Z17 cages in metallic glasses."
            ),
        }

    return {
        "motif_id": "crystalline_reference",
        "title": f"Periodic Crystalline Ground State ({crystal_system or 'Standard Lattice'})",
        "coordination_number": "Periodic Lattice (Not in Amorphous Catalog)",
        "short_cn_label": "—",
        "bond_angle": "Translational crystallographic symmetry",
        "central_symbol": symbol,
        "ligand_symbol": symbol,
        "geometry_summary": (
            f"{symbol} has zero verified inorganic amorphous systems in amorphous_materials.db; "
            "shown in its periodic crystalline reference lattice for comparison."
        ),
    }


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "amorphous_materials.db"
DEFAULT_STATS_JSON_PATH = PROJECT_ROOT / "data" / "statistical_analysis_results.json"
DEFAULT_REFERENCE_JSON_PATH = PROJECT_ROOT / "data" / "baseline_elements_118.json"
DEFAULT_OUTPUT_JSON_PATH = PROJECT_ROOT / "data" / "amorphous_periodic_table_118.json"

_BASELINE_ELEMENT_KEYS = (
    "atomic_number",
    "symbol",
    "name",
    "atomic_mass",
    "period",
    "group",
    "chemical_family",
    "category",
    "radioactive",
    "crystallography",
    "electronic_configuration",
    "chemical_bonding",
    "physical_properties",
    "materials_project",
)


def _load_or_init_baseline_elements_118(
    reference_json_path: Path,
    fallback_output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
) -> List[Dict[str, Any]]:
    """Load baseline 118-element metadata from local data/baseline_elements_118.json.

    If data/baseline_elements_118.json does not yet exist on disk, initializes it
    from the existing data/amorphous_periodic_table_118.json so the repository is
    100% self-contained with no external path dependencies.
    """
    if reference_json_path.exists():
        with open(reference_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["elements"] if isinstance(data, dict) and "elements" in data else data

    if fallback_output_json_path.exists():
        with open(fallback_output_json_path, "r", encoding="utf-8") as f:
            existing_payload = json.load(f)
        raw_elements = (
            existing_payload["elements"]
            if isinstance(existing_payload, dict) and "elements" in existing_payload
            else existing_payload
        )
        baseline_list: List[Dict[str, Any]] = []
        for el in sorted(raw_elements, key=lambda x: int(x["atomic_number"])):
            item: Dict[str, Any] = {}
            for k in _BASELINE_ELEMENT_KEYS:
                if k in el:
                    item[k] = el[k]
            if "category" not in item and "chemical_family" in item:
                item["category"] = item["chemical_family"]
            baseline_list.append(item)
        reference_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(reference_json_path, "w", encoding="utf-8") as f:
            json.dump(baseline_list, f, indent=2, ensure_ascii=False)
        return baseline_list

    raise FileNotFoundError(
        f"Baseline 118-element reference file not found at {reference_json_path}"
    )


def build_periodic_table_118_dataset(
    db_path: Path = DEFAULT_DB_PATH,
    stats_json_path: Path = DEFAULT_STATS_JSON_PATH,
    reference_enriched_json_path: Path = DEFAULT_REFERENCE_JSON_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
) -> Dict[str, Any]:
    """Compile the complete 118-element amorphous dataset and write to JSON."""
    with open(stats_json_path, "r", encoding="utf-8") as f:
        stats_data = json.load(f)

    base_elements_118 = _load_or_init_baseline_elements_118(
        reference_enriched_json_path, output_json_path
    )

    # Map element statistics from Step 4
    el_stats_map: Dict[str, Dict[str, Any]] = {}
    for entry in stats_data["element_statistics_by_frequency"]:
        el_stats_map[entry["element_symbol"]] = entry

    # Partition sets from Step 4 tetrahedral_sub_analysis
    t_sub = stats_data["tetrahedral_sub_analysis"]
    primary_tet_set = {e["element_symbol"] for e in t_sub["primary_tetrahedral_network_formers"]}
    bridging_anion_set = {e["element_symbol"] for e in t_sub["bridging_anion_network_formers"]}
    cond_tet_set = {e["element_symbol"] for e in t_sub["secondary_conditional_tetrahedral_elements"]}
    oxide_interm_set = {e["element_symbol"] for e in t_sub["non_tetrahedral_oxide_chalcogenide_intermediates"]}
    metallic_interm_set = {e["element_symbol"] for e in t_sub["metallic_cluster_host_intermediates"]}
    modifier_set = {e["element_symbol"] for e in t_sub["network_modifiers"]}

    # Query all systems per element from amorphous_materials.db
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            me.element_symbol,
            me.atomic_fraction,
            me.tetrahedral_coordination_flag,
            me.coordination_environment AS local_coordination,
            me.element_role AS structural_role,
            m.id AS material_id,
            m.formula,
            m.raw_formula,
            m.class AS material_class,
            m.synthesis_regime,
            m.synthesis_regime_label,
            m.verification_method,
            m.reference_doi,
            m.source_reference AS reference_citation,
            m.paper_title,
            m.crystalline_conversion_note AS notes,
            m.fsdp_q1_inv_A,
            m.r1_bond_length_A,
            m.mean_bond_angle_deg,
            m.dominant_ring_or_voronoi,
            m.structural_characterization_json
        FROM material_elements me
        JOIN materials m ON m.id = me.material_id
        ORDER BY me.element_symbol ASC, me.atomic_fraction DESC, m.formula ASC
        """
    )
    systems_by_element: Dict[str, List[Dict[str, Any]]] = {}
    for row in cur.fetchall():
        sym = row["element_symbol"]
        tet_flag = int(row["tetrahedral_coordination_flag"])
        local_coord = row["local_coordination"]
        struct_role = row["structural_role"]
        ref_doi = row["reference_doi"] or ""
        doi_url = (
            ref_doi
            if ref_doi.startswith("http")
            else f"https://doi.org/{ref_doi}"
        )
        ref_cit = row["reference_citation"]
        conv_note = row["notes"]
        sc_raw = row["structural_characterization_json"]
        sc_obj = json.loads(sc_raw) if sc_raw else {}
        systems_by_element.setdefault(sym, []).append(
            {
                "material_id": int(row["material_id"]),
                "formula": row["formula"],
                "raw_formula": row["raw_formula"],
                "material_class": row["material_class"],
                "synthesis_regime": row["synthesis_regime"] or "bulk_melt_quenched",
                "synthesis_regime_label": row["synthesis_regime_label"] or "Bulk Melt-Quenched Glass",
                "atomic_fraction": round(float(row["atomic_fraction"]), 4),
                "tetrahedral_flag": tet_flag,
                "tetrahedral_coordination_flag": tet_flag,
                "local_coordination": local_coord,
                "coordination_environment": local_coord,
                "structural_role": struct_role,
                "element_role": struct_role,
                "verification_method": row["verification_method"],
                "reference_doi": ref_doi,
                "doi_url": doi_url,
                "reference_citation": ref_cit,
                "source_reference": ref_cit,
                "paper_title": row["paper_title"] or "",
                "notes": conv_note,
                "crystalline_conversion_note": conv_note,
                "fsdp_q1_inv_A": (
                    round(float(row["fsdp_q1_inv_A"]), 3)
                    if row["fsdp_q1_inv_A"] is not None
                    else None
                ),
                "r1_bond_length_A": (
                    round(float(row["r1_bond_length_A"]), 3)
                    if row["r1_bond_length_A"] is not None
                    else None
                ),
                "mean_bond_angle_deg": (
                    round(float(row["mean_bond_angle_deg"]), 2)
                    if row["mean_bond_angle_deg"] is not None
                    else None
                ),
                "dominant_ring_or_voronoi": row["dominant_ring_or_voronoi"] or "",
                "structural_characterization": sc_obj,
            }
        )
    conn.close()

    # Map systems by (element, formula) for fast lookup of shared systems per element pair
    element_formula_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for el_sym, sys_list in systems_by_element.items():
        element_formula_map[el_sym] = {s["formula"]: s for s in sys_list}

    def _get_shared_systems(el_a: str, el_b: str) -> List[Dict[str, Any]]:
        map_a = element_formula_map.get(el_a, {})
        map_b = element_formula_map.get(el_b, {})
        shared_formulas = [f for f in map_a if f in map_b]
        return [
            {
                "formula": f,
                "raw_formula": map_a[f]["raw_formula"],
                "material_class": map_a[f]["material_class"],
                "reference_doi": map_a[f]["reference_doi"],
                "doi_url": map_a[f]["doi_url"],
            }
            for f in shared_formulas
        ]

    # Map pair correlations per element from all_pairwise_correlations (with fallback to top_co_occurring_pairs)
    pair_correlations_by_element: Dict[str, List[Dict[str, Any]]] = {}
    raw_pairs = stats_data.get(
        "all_pairwise_correlations",
        stats_data.get("top_co_occurring_pairs", []),
    )
    for p in raw_pairs:
        ea, eb = p["element_a"], p["element_b"]
        co_cnt = int(p.get("co_occurrence_count", p.get("co_occurrences", 0)))
        if co_cnt <= 0:
            continue
        phi_val = float(p.get("pearson_phi_binary", 0.0))
        r_val = float(
            p.get(
                "pearson_r_atomic_fraction_union",
                p.get("pearson_r_union_fraction", 0.0),
            )
        )
        mi_val = float(p.get("mutual_information_bits", 0.0))
        nmi_val = float(
            p.get("normalized_mutual_information", p.get("normalized_mi", 0.0))
        )
        pmi_val = float(
            p.get("pointwise_mutual_information_bits", p.get("pointwise_mi_bits", 0.0))
        )
        for src_el, partner_el in ((ea, eb), (eb, ea)):
            shared_sys = _get_shared_systems(src_el, partner_el)
            pair_correlations_by_element.setdefault(src_el, []).append(
                {
                    "partner": partner_el,
                    "co_occurrences": co_cnt,
                    "cooccurrence_count": co_cnt,
                    "shared_systems": shared_sys,
                    "shared_system_formulas": [s["formula"] for s in shared_sys],
                    "pearson_phi_binary": phi_val,
                    "pearson_phi": phi_val,
                    "pearson_r_union_fraction": r_val,
                    "stoichiometric_r": r_val,
                    "mutual_information_bits": mi_val,
                    "normalized_mi": nmi_val,
                    "normalized_mutual_info": nmi_val,
                    "pointwise_mi_bits": pmi_val,
                }
            )

    # Map crystalline-to-amorphous benchmark examples per element
    benchmarks_by_element: Dict[str, List[Dict[str, Any]]] = {}
    for ex in CRYSTALLINE_TO_AMORPHOUS_EXAMPLES:
        enriched_ex = {
            **ex,
            "parent_crystalline_system": ex["crystalline_parent"],
            "promoting_element": ex["added_element"],
            "amorphous_system_induced": ex["amorphous_system"],
            "structural_mechanism": ex["mechanism"],
            "reference_doi": ex["doi"],
        }
        tokens = set(
            re.findall(
                r"[A-Z][a-z]?",
                ex["amorphous_system"] + " " + ex["added_element"] + " " + ex["crystalline_parent"],
            )
        )
        for sym in el_stats_map:
            if sym in tokens:
                benchmarks_by_element.setdefault(sym, []).append(enriched_ex)

    compiled_elements: List[Dict[str, Any]] = []
    fill_counts = {"full": 0, "half": 0, "none": 0}
    category_counts: Dict[str, int] = {k: 0 for k in CATEGORY_VISUAL_META}

    for base_el in sorted(base_elements_118, key=lambda x: int(x["atomic_number"])):
        z = int(base_el["atomic_number"])
        sym = base_el["symbol"]
        st = el_stats_map.get(sym)

        if sym in primary_tet_set:
            cat_key = "primary_tetrahedral_former"
        elif sym in bridging_anion_set:
            cat_key = "bridging_anion_former"
        elif sym in cond_tet_set:
            cat_key = "conditional_tetrahedral_intermediate"
        elif sym in oxide_interm_set:
            cat_key = "oxide_chalcogenide_intermediate"
        elif sym in metallic_interm_set:
            cat_key = "metallic_cluster_intermediate"
        elif sym in modifier_set:
            cat_key = "network_modifier"
        else:
            cat_key = "unreported"

        vis_meta = CATEGORY_VISUAL_META[cat_key]
        fill_mode = vis_meta["fill_mode"]
        fill_counts[fill_mode] += 1
        category_counts[cat_key] += 1

        occ_cnt = int(st["occurrence_count"]) if st else 0
        tet_cnt = int(st["tetrahedral_count"]) if st else 0
        score = float(st["amorphous_induction_score"]) if st else 0.0
        rank = int(st["induction_rank"]) if st else None
        freq_val = float(st["frequency"]) if st else 0.0
        tet_ratio_val = float(st["tetrahedral_ratio"]) if st else 0.0
        mean_af = float(st["mean_atomic_fraction"]) if st else 0.0
        max_af = float(st["max_atomic_fraction"]) if st else 0.0
        min_af = float(st["min_atomic_fraction"]) if st else 0.0
        uniq_partners = int(st["unique_partner_elements"]) if st else 0

        rb_raw = st["role_breakdown"] if st else {}
        role_counts = {
            "network_former": (
                int(rb_raw.get("Primary Tetrahedral Network Former", 0))
                + int(rb_raw.get("Trigonal/Pyramidal Network Former", 0))
            ),
            "intermediate": (
                int(rb_raw.get("Tetrahedral Intermediate / Network Former", 0))
                + int(rb_raw.get("Network Intermediate", 0))
            ),
            "modifier": int(rb_raw.get("Network Modifier / Charge Compensator", 0)),
            "metallic_glass_matrix": (
                int(rb_raw.get("Metallic Glass Matrix / Cluster Former", 0))
                + int(rb_raw.get("Glass-Forming Metalloid Solute", 0))
                + int(rb_raw.get("Topological/Electronic Stabilizer (Metalloid/Simple Metal)", 0))
            ),
            "bridging_anion": int(rb_raw.get("Bridging/Terminal Anion Ligand", 0)),
        }

        raw_partners = st["top_co_occurring_partners"] if st else []
        enriched_partners = [
            {
                "partner": p["partner"],
                "count": int(p["count"]),
                "cooccurrence_count": int(p["count"]),
                "shared_systems": _get_shared_systems(sym, p["partner"]),
                "shared_system_formulas": [s["formula"] for s in _get_shared_systems(sym, p["partner"])],
            }
            for p in raw_partners
        ]

        sorted_corrs = sorted(
            pair_correlations_by_element.get(sym, []),
            key=lambda x: (-x["co_occurrences"], -x["mutual_information_bits"], x["partner"]),
        )

        cryst = base_el.get("crystallography") or {}
        elec_cfg = base_el.get("electronic_configuration") or {}
        chem_bond = base_el.get("chemical_bonding") or {}
        crystal_sys = cryst.get("crystal_system") or "Unknown"

        motif_3d = determine_coordination_3d_motif(sym, cat_key, tet_cnt, crystal_sys)
        motif_3d["motif_label"] = motif_3d["title"]
        motif_3d["typical_coordination"] = motif_3d["coordination_number"]
        motif_3d["prototype_unit"] = motif_3d["bond_angle"]
        motif_3d["description"] = motif_3d["geometry_summary"]

        chem_family = base_el.get("category") or base_el.get("chemical_family") or ""
        cryst_ref = {
            "crystal_structure": cryst.get("crystal_system") or "—",
            "space_group": cryst.get("space_group_symbol") or "",
            "lattice_constants": cryst.get("lattice_parameters") or {},
        }

        el_sys_list = systems_by_element.get(sym, [])
        if el_sys_list:
            proto_sys = el_sys_list[0]
            q1_vals = [
                float(s["fsdp_q1_inv_A"])
                for s in el_sys_list
                if s.get("fsdp_q1_inv_A") is not None
            ]
            r1_vals = [
                float(s["r1_bond_length_A"])
                for s in el_sys_list
                if s.get("r1_bond_length_A") is not None
            ]
            ang_vals = [
                float(s["mean_bond_angle_deg"])
                for s in el_sys_list
                if s.get("mean_bond_angle_deg") is not None
            ]
            dom_motifs = []
            for s in el_sys_list:
                dm = s.get("dominant_ring_or_voronoi")
                if dm and dm not in dom_motifs:
                    dom_motifs.append(dm)
            exp_bench_cnt = sum(
                1
                for s in el_sys_list
                if (s.get("structural_characterization") or {}).get("provenance", {}).get("overall_type")
                == "direct_experimental_benchmark"
            )
            comp_recon_cnt = len(el_sys_list) - exp_bench_cnt
            struct_char_summary = {
                "has_structural_data": True,
                "systems_with_sro_mro_count": len(el_sys_list),
                "direct_experimental_benchmark_count": exp_bench_cnt,
                "composition_weighted_reconstruction_count": comp_recon_cnt,
                "prototype_formula": proto_sys["formula"],
                "prototype_material_class": proto_sys["material_class"],
                "prototype_doi": proto_sys["reference_doi"],
                "prototype_citation": proto_sys["reference_citation"],
                "prototype_paper_title": proto_sys.get("paper_title", ""),
                "fsdp_q1_range_inv_A": (
                    {
                        "min": round(min(q1_vals), 3),
                        "mean": round(sum(q1_vals) / len(q1_vals), 3),
                        "max": round(max(q1_vals), 3),
                    }
                    if q1_vals
                    else None
                ),
                "r1_bond_length_range_A": (
                    {
                        "min": round(min(r1_vals), 3),
                        "mean": round(sum(r1_vals) / len(r1_vals), 3),
                        "max": round(max(r1_vals), 3),
                    }
                    if r1_vals
                    else None
                ),
                "mean_bond_angle_range_deg": (
                    {
                        "min": round(min(ang_vals), 2),
                        "mean": round(sum(ang_vals) / len(ang_vals), 2),
                        "max": round(max(ang_vals), 2),
                    }
                    if ang_vals
                    else None
                ),
                "dominant_motifs": dom_motifs[:6],
                "prototype_characterization": proto_sys.get("structural_characterization", {}),
            }
        else:
            struct_char_summary = {
                "has_structural_data": False,
                "systems_with_sro_mro_count": 0,
                "direct_experimental_benchmark_count": 0,
                "composition_weighted_reconstruction_count": 0,
            }

        el_record = {
            "atomic_number": z,
            "symbol": sym,
            "name": base_el["name"],
            "atomic_mass": base_el["atomic_mass"],
            "period": base_el["period"],
            "group": base_el["group"],
            "chemical_family": chem_family,
            "chemical_series": chem_family,
            "radioactive": bool(base_el.get("radioactive", False)),
            # Amorphous Periodic Table Visual & Structural Classification
            "in_amorphous_dataset": st is not None,
            "fill_mode": fill_mode,  # "full" (49), "half" (28), "none" (41)
            "amorphous_category_key": cat_key,
            "category_code": cat_key,
            "amorphous_category_label": vis_meta["category_label"],
            "category_title": vis_meta["category_label"],
            "short_role_label": vis_meta["short_label"],
            "color_hex": vis_meta["color_hex"],
            "border_hex": vis_meta["border_hex"],
            "text_hex": vis_meta["text_hex"],
            "badge_hex": vis_meta["badge_hex"],
            "category_description": vis_meta["description"],
            # Quantitative Amorphous Metrics from SQLite & Step 4
            "occurrence_count": occ_cnt,
            "frequency": freq_val,
            "system_frequency": freq_val,
            "frequency_pct": round(freq_val * 100.0, 1),
            "amorphous_induction_score": score,
            "induction_rank": rank,
            "mean_atomic_fraction": mean_af,
            "multicomponent_mean_atomic_fraction": (
                float(st["multicomponent_mean_atomic_fraction"]) if st else 0.0
            ),
            "max_atomic_fraction": max_af,
            "min_atomic_fraction": min_af,
            "stoichiometry_stats": {
                "min": min_af,
                "mean": mean_af,
                "max": max_af,
            },
            "tetrahedral_count": tet_cnt,
            "tetrahedral_ratio": tet_ratio_val,
            "tetrahedral_fraction": tet_ratio_val,
            "tetrahedral_ratio_pct": round(tet_ratio_val * 100.0, 1),
            "non_metallic_occurrences": int(st["non_metallic_occurrences"]) if st else 0,
            "metallic_glass_occurrences": int(st["metallic_glass_occurrences"]) if st else 0,
            "non_metallic_tetrahedral_ratio": (
                float(st["non_metallic_tetrahedral_ratio"]) if st else 0.0
            ),
            "non_metallic_tetrahedral_ratio_pct": (
                round(float(st["non_metallic_tetrahedral_ratio"]) * 100.0, 1) if st else 0.0
            ),
            "has_tetrahedral_motif": tet_cnt > 0,
            "short_cn_label": motif_3d.get("short_cn_label", "—"),
            "classes_spanned": int(st["classes_spanned"]) if st else 0,
            "class_breakdown": st["class_breakdown"] if st else {},
            "synthesis_regime_breakdown": st.get("synthesis_regime_breakdown", {}) if st else {},
            "role_breakdown": rb_raw,
            "role_counts": role_counts,
            "unique_partner_elements": uniq_partners,
            "partner_diversity": uniq_partners,
            "partner_diversity_entropy_bits": (
                float(st["partner_diversity_entropy_bits"]) if st else 0.0
            ),
            "tetrahedral_system_pearson_phi": (
                float(st["tetrahedral_system_pearson_phi"]) if st else 0.0
            ),
            "tetrahedral_system_mi_bits": (
                float(st["tetrahedral_system_mi_bits"]) if st else 0.0
            ),
            "tetrahedral_system_pmi_bits": (
                float(st["tetrahedral_system_pmi_bits"]) if st else 0.0
            ),
            "category_derivation_rule": (
                st["category_derivation_rule"]
                if st
                else "0 occurrences in amorphous_materials.db (unreported)"
            ),
            "mechanism_summary": (
                st["mechanism_summary"]
                if st
                else "No verified inorganic amorphous systems recorded in this dataset."
            ),
            "top_co_occurring_partners": enriched_partners,
            "top_cooccurring_partners": enriched_partners,
            "pair_correlations": sorted_corrs,
            "top_correlations": sorted_corrs,
            "verified_systems": el_sys_list,
            "structural_characterization_summary": struct_char_summary,
            "conversion_benchmarks": benchmarks_by_element.get(sym, []),
            "conversion_examples": benchmarks_by_element.get(sym, []),
            "motif_3d": motif_3d,
            # Fundamental Atomic, Electronic, Bonding & Crystalline Reference Metadata
            "electron_configuration": elec_cfg.get("abbreviated") or elec_cfg.get("full") or "—",
            "electronegativity_pauling": chem_bond.get("electronegativity_pauling"),
            "atomic_radius_pm": chem_bond.get("atomic_radius_pm"),
            "crystalline_reference": cryst_ref,
            "crystallography": cryst,
            "electronic_configuration": elec_cfg,
            "chemical_bonding": chem_bond,
            "physical_properties": base_el.get("physical_properties", {}),
            "materials_project": base_el.get("materials_project", {}),
        }
        compiled_elements.append(el_record)

    payload = {
        "metadata": {
            "title": "The Amorphous Periodic Table of the Elements",
            "total_elements": len(compiled_elements),
            "total_verified_amorphous_systems": stats_data["metadata"]["total_amorphous_materials"],
            "active_amorphous_elements": stats_data["metadata"]["total_unique_elements"],
            "fill_mode_counts": fill_counts,
            "category_counts": category_counts,
            "categories": list(CATEGORY_VISUAL_META.values()),
            "class_summary": stats_data["metadata"]["class_summary"],
            "synthesis_regime_summary": stats_data["metadata"].get("synthesis_regime_summary", []),
            "group_comparison_summary": t_sub["group_comparison_summary"],
        },
        "elements": compiled_elements,
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return payload


# Alias expected by run_pipeline.py
build_periodic_table_118 = build_periodic_table_118_dataset


if __name__ == "__main__":
    payload = build_periodic_table_118_dataset()
    meta = payload["metadata"]
    print(
        f"[Step 6A] Built data/amorphous_periodic_table_118.json: "
        f"{meta['total_elements']} elements | "
        f"Full={meta['fill_mode_counts']['full']}, "
        f"Half={meta['fill_mode_counts']['half']}, "
        f"None={meta['fill_mode_counts']['none']}"
    )
