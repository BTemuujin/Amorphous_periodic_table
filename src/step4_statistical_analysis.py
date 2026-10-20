"""Step 4: Statistical and Elemental Attribution Analysis.

Queries `amorphous_materials.db` to compute:
1. Total occurrence count and frequency of every chemical element across all
   recorded amorphous systems (overall and per material class).
2. Element-element co-occurrence matrix C_ij via SQL self-join.
3. Correlation metrics (Pearson phi binary correlation, continuous atomic-fraction
   Pearson r, Pointwise Mutual Information PMI, Normalized Mutual Information NMI,
   and Element-to-Class / Element-to-Tetrahedral Mutual Information) plus Partner
   Diversity Shannon Entropy and Composite Amorphous Induction Score.
4. A distinct sub-analysis isolating primary tetrahedral network formers
   (Si, Ge, P, B, As, and covalent C/Ga/Al tetrahedral formers) versus network
   intermediates and network modifiers.

Exports complete results to `data/statistical_analysis_results.json`.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

PRIMARY_TETRAHEDRAL_FORMERS = {"Si", "Ge", "P", "B", "As"}

# Canonical structural classification across the Amorphous Periodic Table
ELEMENT_STRUCTURAL_CATEGORY: Dict[str, Tuple[str, str]] = {
    # Primary Network Formers (Tetrahedral / Polyhedral Backbones)
    "Si": (
        "Network Former (Tetrahedral/Polyhedral Backbone)",
        "Universal tetrahedral former (SiO4, SiS4, SiN4, SiC4, a-Si) and key metalloid glass former in metal-metalloid BMGs",
    ),
    "Ge": (
        "Network Former (Tetrahedral/Polyhedral Backbone)",
        "Primary tetrahedral former across oxides (GeO4), chalcogenides (GeS4, GeSe4, GeTe4), pnictides, and elemental a-Ge",
    ),
    "P": (
        "Network Former (Tetrahedral/Polyhedral Backbone)",
        "Primary tetrahedral former (PO4, PS4, PSe4) and trigonal-prism metalloid center (MP9) in Pd/Pt/Fe/Ni bulk metallic glasses",
    ),
    "B": (
        "Network Former (Tetrahedral/Polyhedral Backbone)",
        "Mixed trigonal/tetrahedral former (BO3/BO4, BS3/BS4, BN3/BN4) and primary metalloid prism former in Fe/Co/Ni metallic glasses",
    ),
    "As": (
        "Network Former (Tetrahedral/Polyhedral Backbone)",
        "Classic chalcogenide/oxide pyramidal & tetrahedral network former (AsSe3, AsS3, AsO3, GaAs4, CdGeAs2)",
    ),
    # Conditional / Secondary Tetrahedral & Covalent Network Formers / Intermediates
    "Al": (
        "Intermediate (Conditional Tetrahedral Former)",
        "Tetrahedral network former (AlO4^-, AlN4) when charge-compensated; icosahedral p-d bond stabilizer in Zr/Cu/La/RE BMGs",
    ),
    "Ga": (
        "Intermediate (Conditional Tetrahedral Former)",
        "Tetrahedral former in aluminate/gallate/chalcogenide/nitride glasses (GaO4, GaS4, GaSe4, GaN4, GaAs4)",
    ),
    "Be": (
        "Intermediate (Conditional Tetrahedral Former)",
        "Single-component halide tetrahedral network former (BeF4 in BeF2) and topological cage-frustrating solute in Vitreloy BMGs",
    ),
    "Zn": (
        "Intermediate (Conditional Tetrahedral Former)",
        "Single-component halide tetrahedral former (ZnCl4 in ZnCl2), oxide intermediate (ZnO4), and metallic glass former",
    ),
    "C": (
        "Intermediate (Conditional Tetrahedral Former)",
        "Tetrahedral covalent former in ta-C (sp3 C4), a-SiC, and SiOC oxycarbide glasses; interstitial prism former in Fe-based BMGs",
    ),
    "V": (
        "Intermediate",
        "Conditional oxide network former / intermediate forming VO4 tetrahedra and VO5 trigonal bipyramids in vanadate glasses",
    ),
    "Mo": (
        "Intermediate",
        "Conditional oxide intermediate (MoO4 tetrahedra / MoO6 octahedra) and refractory metallic glass matrix element",
    ),
    "W": (
        "Intermediate",
        "Conditional oxide intermediate (WO4/WO6 in tellurite/phosphate glasses) and high-Tg refractory metallic glass former",
    ),
    "Ti": (
        "Intermediate",
        "Oxide network intermediate (TiO4/TiO5/TiO6) and early-transition-metal polytetrahedral matrix former in Ti/Zr/Cu BMGs",
    ),
    "Te": (
        "Intermediate",
        "Conditional oxide former (TeO4 disphenoids in tellurite glasses) and high-polarizability chalcogenide chain/network builder",
    ),
    "Sb": (
        "Intermediate",
        "Pyramidal network intermediate (SbO3, SbSe3, SbS3) and monatomic/phase-change glass former",
    ),
    "Bi": (
        "Intermediate",
        "Heavy-metal oxide conditional network former/intermediate (distorted BiO6/BiO3 polyhedra with 6s2 lone pair)",
    ),
    "Pb": (
        "Intermediate",
        "Amphoteric oxide intermediate (covalent PbO4/PbO3 pyramids at high PbO; modifier at low PbO)",
    ),
    "Fe": (
        "Intermediate",
        "Oxide intermediate (FeO4/FeO6 in iron phosphate glasses) and primary ferromagnetic metallic glass host matrix",
    ),
    "Zr": (
        "Intermediate",
        "Heavy-metal fluoride network former (ZrF7/ZrF8 in ZBLAN), high-field oxide intermediate, and primary BMG host matrix",
    ),
    "Hf": (
        "Intermediate",
        "High-k silicate glass intermediate (HfO6-SiO4) and refractory bulk metallic glass host",
    ),
    "Nb": (
        "Intermediate",
        "Octahedral oxide cross-linker (NbO6) and large early-TM topological stabilizer in Fe/Ni/Zr metallic glasses",
    ),
    "Ta": (
        "Intermediate",
        "Octahedral oxide intermediate (TaO6) and refractory metallic glass former (Co-Fe-Ta-B, Ta-Ni-Co, Ir-Ta)",
    ),
    "Sn": (
        "Intermediate",
        "Tetrahedral pnictide intermediate (ZnSnAs2) and p-block BMG stabilizer",
    ),
    "In": (
        "Intermediate",
        "Tetrahedral III-V network former (a-InP) and octahedral oxide semiconductor component (a-IGZO)",
    ),
    "Cd": (
        "Intermediate",
        "Tetrahedral chalcopyrite glass constituent (CdGeAs2, CdGeP2) and heavy metal fluoride glass stabilizer",
    ),
    "Sc": (
        "Intermediate",
        "High-field-strength oxide intermediate (ScO6) and rare-earth BMG stabilizer",
    ),
    "Tl": (
        "Intermediate",
        "Lone-pair chalcogenide network intermediate forming directional covalent TlSe3/TlSe4 pyramids (vitreous TlAsSe2)",
    ),
    "Os": (
        "Intermediate",
        "5d transition-metal oxide network former/intermediate forming disordered corner/edge-sharing OsO6 octahedra in amorphous a-OsO2 films",
    ),
    "Th": (
        "Intermediate",
        "High-field-strength primordial actinide fluoride network former/intermediate (ThF8/ThF9 antiprisms in BaF2-YbF3-ThF4 infrared glass)",
    ),
    # Bridging Anions / Chalcogen & Pnictogen Host Ligands
    "O": (
        "Network Former (Bridging Anion Backbone)",
        "Universal bridging/non-bridging oxide anion linking SiO4, BO3/BO4, PO4, GeO4, and AlO4 polyhedra",
    ),
    "S": (
        "Network Former (Bridging Anion Backbone)",
        "Chalcogenide chain/ring former (a-S) and bridging sulfide ligand in GeS4, AsS3, PS4, BS4, and SiS4 networks",
    ),
    "Se": (
        "Network Former (Bridging Anion Backbone)",
        "Elemental chain/ring glass former (a-Se) and bridging selenide backbone in Ge-As-Se-Sb-Ga infrared glasses",
    ),
    "N": (
        "Network Former (Bridging Anion Backbone)",
        "3- and 4-coordinated covalent cross-linker in amorphous nitrides (Si3N4, AlN, GaN, BN) and oxynitride glasses",
    ),
    "F": (
        "Network Former (Bridging Anion Backbone)",
        "Bridging halide ligand in tetrahedral BeF2 and polyhedral ZBLAN / fluoroaluminate / fluorothorate glasses",
    ),
    "Cl": (
        "Network Former (Bridging Anion Backbone)",
        "Bridging chloride ligand in tetrahedral ZnCl2 glass and mixed-halide glasses",
    ),
    "Br": (
        "Network Former (Bridging Anion Backbone)",
        "Bridging bromide ligand linking corner-sharing ZnBr4 tetrahedra in vitreous ZnBr2 halide glass",
    ),
    "I": (
        "Modifier",
        "Large polarizable halide ion in chalcohalide (As-Se-I) and superionic oxyhalide (AgI-AgPO3) glasses",
    ),
    "H": (
        "Modifier",
        "Monovalent dangling-bond terminator (Si-H) reducing topological overconstraint in a-Si:H",
    ),
    # Classic Network Modifiers (Alkali, Alkaline-Earth, Rare-Earth, Actinide, Noble Ion Conductors)
    "Li": ("Modifier", "High-field-strength alkali modifier and fast-ion conductor in oxide and sulfide glasses"),
    "Na": ("Modifier", "Prototypical alkali network modifier creating non-bridging oxygens (NBOs) or charge-compensating BO4/AlO4"),
    "K": ("Modifier", "Large alkali network modifier depolymerizing silicate, borate, and phosphate networks"),
    "Rb": ("Modifier", "Heavy alkali network modifier in silicate and borate glasses"),
    "Cs": ("Modifier", "Largest stable alkali modifier stabilizing high-coordination borate and aluminate glasses"),
    "Mg": ("Modifier", "High-field-strength alkaline-earth modifier/charge compensator in oxides and alkaline-earth BMG matrix"),
    "Ca": ("Modifier", "Alkaline-earth network modifier in silicates/borates/phosphates/aluminates and Ca-Mg-Zn BMG host"),
    "Sr": ("Modifier", "Alkaline-earth network modifier in oxide/fluoride glasses and Sr-Mg-Zn BMG host"),
    "Ba": ("Modifier", "Heavy alkaline-earth modifier in oxide and ZBLAN/fluorothorate fluoride glasses"),
    "Ag": ("Modifier", "Superionic modifier in chalcogenide (Ag-As-S/Se) and oxide (AgI-AgPO3, Ag2O-B2O3) glasses"),
    "La": ("Modifier", "Rare-earth high-refractive-index oxide/fluoride glass modifier and La-Al-Ni-Cu BMG host"),
    "Ce": ("Modifier", "Rare-earth modifier in oxide glasses and 4f-delocalized Ce-Al-Cu metallic plastic glass host"),
    "Pr": ("Modifier", "Rare-earth modifier and Pr-Cu-Ni-Al BMG host"),
    "Nd": ("Modifier", "Rare-earth laser glass modifier and Nd-Fe-Al hard-magnetic BMG host"),
    "Sm": ("Modifier", "Rare-earth modifier and Sm-Fe-Al amorphous magnet host"),
    "Eu": ("Modifier", "4f rare-earth luminescence/optical modifier in heavy-metal borate, silicate, and phosphate glasses"),
    "Gd": ("Modifier", "Rare-earth modifier and magnetocaloric Gd-Al-Co / Mg-Cu-Gd BMG former"),
    "Tb": ("Modifier", "Heavy rare-earth Tb-Al-Co BMG former and amorphous Tb-Si spin-glass component"),
    "Dy": ("Modifier", "Heavy rare-earth Dy-Al-Co BMG former"),
    "Ho": ("Modifier", "Heavy rare-earth Ho-Al-Co BMG former"),
    "Er": ("Modifier", "Heavy rare-earth Er-Al-Co BMG former"),
    "Tm": ("Modifier", "Heavy rare-earth Tm-Al-Co BMG former"),
    "Yb": ("Modifier", "Divalent/trivalent rare-earth modifier in fluorothorate glass and Yb-Zn-Mg-Cu BMG former"),
    "Lu": ("Modifier", "Heavy lanthanide Lu-Al-Co BMG former"),
    "Y": ("Modifier", "High-field modifier in SiAlON/aluminate glasses and topological cage stabilizer in Mg-Cu-Y and Fe-based BMGs"),
    "U": ("Modifier", "Primordial 5f actinide uranyl (UO2^2+) modifier/intermediate in alkali silicate nuclear-waste glasses"),
    # Late Transition & Noble Metallic Glass Cluster/Matrix Formers
    "Cu": ("Intermediate (Metallic Icosahedral Cluster Former)", "Primary icosahedral <0,0,12,0> cluster center in Cu-Zr, Vitreloy, Ti-, Mg-, and Pd-based BMGs; ion modifier in CuI-MoO3"),
    "Ni": ("Intermediate (Metallic Cluster Former)", "Polytetrahedral/trigonal-prism cluster former in Pd-Ni-P, Fe-Ni-P-B, Zr-, and La-based BMGs"),
    "Co": ("Intermediate (Metallic Cluster Former)", "Polytetrahedral matrix and solute cluster former in Co-Fe-Si-B, Co-Fe-Ta-B, and RE-Al-Co BMGs"),
    "Pd": ("Intermediate (Metallic Glass Host)", "Premier noble-metal BMG matrix forming strong p-d covalent bonds with P and Si"),
    "Pt": ("Intermediate (Metallic Glass Host)", "High-Poisson-ratio noble-metal BMG matrix with P and Si"),
    "Au": ("Intermediate (Metallic Glass Host)", "First metallic glass matrix (Au75Si25) and 18k bulk metallic glass former with Si"),
    "Cr": ("Intermediate (Metallic Passivator)", "Corrosion-resistant transition metal substituent in Fe- and Mo-based metallic glasses"),
    "Mn": ("Intermediate (Metallic Glass Host)", "Transition metal host in Mn-Al-Ni and Mn-P-C metallic glasses"),
    "Ru": ("Intermediate (Metallic Glass Host)", "Refractory platinum-group glass former in Ru-P and W-Ru-B"),
    "Rh": ("Intermediate (Metallic Glass Host)", "Platinum-group metal-metalloid glass former in Rh75Si25"),
    "Re": ("Intermediate (Metallic Glass Host)", "5d refractory amorphous superconductor former in Re-Ta"),
    "Ir": ("Intermediate (Metallic Glass Host)", "Ultra-high-Tx refractory metallic glass former in Ir45Ta55"),
}


def compute_binary_mi_and_nmi(
    x: np.ndarray, y: np.ndarray
) -> Tuple[float, float, float]:
    """Compute Mutual Information I(X;Y) in bits, Normalized MI, and Pointwise MI for (X=1, Y=1)."""
    n = float(len(x))
    p11 = np.sum((x == 1) & (y == 1)) / n
    p10 = np.sum((x == 1) & (y == 0)) / n
    p01 = np.sum((x == 0) & (y == 1)) / n
    p00 = np.sum((x == 0) & (y == 0)) / n

    px1 = p11 + p10
    px0 = p01 + p00
    py1 = p11 + p01
    py0 = p10 + p00

    mi = 0.0
    for pxy, px, py in [
        (p11, px1, py1),
        (p10, px1, py0),
        (p01, px0, py1),
        (p00, px0, py0),
    ]:
        if pxy > 1e-12 and px > 1e-12 and py > 1e-12:
            mi += pxy * math.log2(pxy / (px * py))

    hx = 0.0
    for px in (px1, px0):
        if px > 1e-12:
            hx -= px * math.log2(px)
    hy = 0.0
    for py in (py1, py0):
        if py > 1e-12:
            hy -= py * math.log2(py)

    denom = math.sqrt(hx * hy) if (hx > 1e-12 and hy > 1e-12) else 1.0
    nmi = mi / denom if denom > 0 else 0.0

    pmi_11 = math.log2(p11 / (px1 * py1)) if (p11 > 1e-12 and px1 > 0 and py1 > 0) else 0.0
    return round(mi, 6), round(nmi, 6), round(pmi_11, 6)


def derive_structural_category_from_metrics(
    tet_cnt: int,
    non_mg_cnt: int,
    non_mg_tet_ratio: float,
    multi_mean_frac: float,
    role_counts: Dict[str, int],
) -> Tuple[str, str]:
    """Derive structural category from crystal-chemical/topological role rules and empirical counts."""
    # 1. Primary Tetrahedral / Polyhedral Network Formers:
    # Elements forming self-sustaining Zachariasen-Phillips-Thorpe continuous random networks (CRNs)
    prim_roles = (
        role_counts.get("Primary Tetrahedral Network Former", 0)
        + role_counts.get("Trigonal/Pyramidal Network Former", 0)
    )
    if prim_roles > 0:
        return (
            "Network Former (Tetrahedral/Polyhedral Backbone)",
            f"Zachariasen–Phillips–Thorpe primary CRN backbone former ({tet_cnt} tetrahedral CN=4 occurrences across {non_mg_cnt} non-MG systems, {100.0 * non_mg_tet_ratio:.1f}%; {prim_roles} primary network-former systems)",
        )

    # 2. Bridging Anion Network Formers:
    # Electronegative p-block anions forming 2- or 3-coordinate bridging vertex linkages (M-X-M) or elemental chains/rings
    anion_roles = role_counts.get("Bridging/Terminal Anion Ligand", 0)
    if anion_roles > 0 and role_counts.get("Network Intermediate", 0) == 0:
        return (
            "Network Former (Bridging Anion Backbone)",
            f"Bridging anion vertex/chain ligand (CN=2–3 M–X–M cross-linking across {anion_roles} covalent/ionic glass networks)",
        )

    # 3. Conditional Tetrahedral Intermediates:
    # Amphoteric / post-transition cations adopting 4-coordinate tetrahedral network sites when charge-compensated or covalently bonded
    if role_counts.get("Tetrahedral Intermediate / Network Former", 0) > 0 or tet_cnt > 0:
        return (
            "Intermediate (Conditional Tetrahedral Former)",
            f"Charge-compensated / covalent conditional tetrahedral network former ({tet_cnt} verified CN=4 occurrences across {non_mg_cnt} non-MG systems)",
        )

    # 4. Non-Tetrahedral Oxide / Chalcogenide / Halide Intermediates:
    # High-field-strength or lone-pair cations forming octahedral (CN=6), pyramidal (CN=3-4), or fluorozirconate/fluorothorate (CN=7-9) polyhedra
    interm_roles = role_counts.get("Network Intermediate", 0)
    if interm_roles > 0:
        return (
            "Intermediate",
            f"Non-tetrahedral polyhedral/lone-pair network intermediate (CN=3, 5, 6–9 coordination across {interm_roles} oxide/chalcogenide/halide systems)",
        )

    # 5. Metallic Glass Cluster / Host Intermediates:
    # Transition/noble metals stabilizing dense polytetrahedral / icosahedral Miracle-Senkov-Egami packing
    mg_cluster_roles = role_counts.get("Metallic Glass Matrix / Cluster Former", 0)
    mod_roles = role_counts.get("Network Modifier / Charge Compensator", 0)
    if mg_cluster_roles > mod_roles:
        mg_subcat = (
            "Intermediate (Metallic Glass Host)"
            if multi_mean_frac >= 0.45
            else "Intermediate (Metallic Cluster Former)"
        )
        return (
            mg_subcat,
            f"Miracle–Senkov polytetrahedral/icosahedral metallic glass former ({mg_cluster_roles} BMG/amorphous alloy systems; multicomponent mean atomic fraction = {multi_mean_frac:.3f})",
        )

    # 6. Network Modifiers / Charge Compensators / Terminators:
    # Electropositive cations or monovalent terminators occupying high-CN interstitial cavities or creating non-bridging anions
    return (
        "Modifier",
        f"Ionic network modifier / charge-compensating cavity cation or dangling-bond terminator ({mod_roles} verified modifier occurrences)",
    )




def run_step4_analysis(db_path: Path, output_path: Path) -> Dict[str, Any]:
    """Query SQLite database and compute comprehensive statistical & elemental attribution metrics."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # Total materials and breakdown by class
        cur.execute("SELECT COUNT(*) AS cnt FROM materials")
        total_materials = int(cur.fetchone()["cnt"])

        cur.execute(
            "SELECT class, COUNT(*) AS cnt, SUM(system_tetrahedral_flag) AS tet_cnt "
            "FROM materials GROUP BY class ORDER BY cnt DESC"
        )
        class_summary = [dict(row) for row in cur.fetchall()]

        cur.execute(
            "SELECT synthesis_regime, synthesis_regime_label, COUNT(*) AS cnt "
            "FROM materials GROUP BY synthesis_regime, synthesis_regime_label ORDER BY cnt DESC"
        )
        synthesis_regime_summary = [dict(row) for row in cur.fetchall()]

        # 1. Elemental occurrence counts, frequencies, atomic fraction stats, and tetrahedral counts
        cur.execute(
            """
            WITH mat_sizes AS (
                SELECT material_id, COUNT(*) AS n_elements
                FROM material_elements
                GROUP BY material_id
            )
            SELECT
                me.element_symbol,
                COUNT(DISTINCT me.material_id) AS occurrence_count,
                ROUND(CAST(COUNT(DISTINCT me.material_id) AS REAL) / ?, 6) AS frequency,
                ROUND(AVG(me.atomic_fraction), 6) AS mean_atomic_fraction,
                ROUND(
                    COALESCE(
                        AVG(CASE WHEN ms.n_elements >= 2 THEN me.atomic_fraction END),
                        AVG(me.atomic_fraction) * 0.5
                    ),
                    6
                ) AS multicomponent_mean_atomic_fraction,
                ROUND(MAX(me.atomic_fraction), 6) AS max_atomic_fraction,
                ROUND(MIN(me.atomic_fraction), 6) AS min_atomic_fraction,
                SUM(me.tetrahedral_coordination_flag) AS tetrahedral_count,
                ROUND(
                    CAST(SUM(me.tetrahedral_coordination_flag) AS REAL) / COUNT(DISTINCT me.material_id),
                    6
                ) AS tetrahedral_ratio,
                COUNT(DISTINCT m.class) AS classes_spanned
            FROM material_elements me
            JOIN materials m ON m.id = me.material_id
            JOIN mat_sizes ms ON ms.material_id = me.material_id
            GROUP BY me.element_symbol
            ORDER BY occurrence_count DESC, tetrahedral_count DESC, mean_atomic_fraction DESC
            """,
            (total_materials,),
        )
        element_rows = [dict(r) for r in cur.fetchall()]

        # Per-element class breakdown
        cur.execute(
            """
            SELECT me.element_symbol, m.class, COUNT(*) AS cnt
            FROM material_elements me
            JOIN materials m ON m.id = me.material_id
            GROUP BY me.element_symbol, m.class
            """
        )
        el_class_counts: Dict[str, Dict[str, int]] = {}
        for r in cur.fetchall():
            el_class_counts.setdefault(r["element_symbol"], {})[r["class"]] = int(r["cnt"])

        # Per-element synthesis regime breakdown
        cur.execute(
            """
            SELECT me.element_symbol, m.synthesis_regime, COUNT(*) AS cnt
            FROM material_elements me
            JOIN materials m ON m.id = me.material_id
            GROUP BY me.element_symbol, m.synthesis_regime
            """
        )
        el_regime_counts: Dict[str, Dict[str, int]] = {}
        for r in cur.fetchall():
            el_regime_counts.setdefault(r["element_symbol"], {})[r["synthesis_regime"]] = int(r["cnt"])

        # Per-element role breakdown from material_elements
        cur.execute(
            """
            SELECT element_symbol, element_role, COUNT(*) AS cnt
            FROM material_elements
            GROUP BY element_symbol, element_role
            """
        )
        el_role_counts: Dict[str, Dict[str, int]] = {}
        for r in cur.fetchall():
            el_role_counts.setdefault(r["element_symbol"], {})[r["element_role"]] = int(r["cnt"])

        # 2. Co-occurrence matrix via SQL self-join
        cur.execute(
            """
            SELECT
                a.element_symbol AS el_a,
                b.element_symbol AS el_b,
                COUNT(DISTINCT a.material_id) AS co_occurrence_count
            FROM material_elements a
            JOIN material_elements b
                ON a.material_id = b.material_id
                AND a.element_symbol != b.element_symbol
            GROUP BY a.element_symbol, b.element_symbol
            ORDER BY co_occurrence_count DESC, a.element_symbol ASC
            """
        )
        co_occurrence_pairs = [dict(r) for r in cur.fetchall()]

        co_matrix_dict: Dict[str, Dict[str, int]] = {}
        for row in co_occurrence_pairs:
            ea, eb, c = row["el_a"], row["el_b"], int(row["co_occurrence_count"])
            co_matrix_dict.setdefault(ea, {})[eb] = c

        # Pairwise class breakdown via SQL join
        cur.execute(
            """
            SELECT
                a.element_symbol AS el_a,
                b.element_symbol AS el_b,
                m.class AS mat_class,
                COUNT(DISTINCT a.material_id) AS cnt
            FROM material_elements a
            JOIN material_elements b
                ON a.material_id = b.material_id
                AND a.element_symbol != b.element_symbol
            JOIN materials m
                ON m.id = a.material_id
            GROUP BY a.element_symbol, b.element_symbol, m.class
            """
        )
        pair_class_map: Dict[Tuple[str, str], Dict[str, int]] = {}
        for r in cur.fetchall():
            pair_class_map.setdefault((r["el_a"], r["el_b"]), {})[r["mat_class"]] = int(r["cnt"])

        # Build material x element atomic-fraction matrix X (N x M)
        all_elements = [r["element_symbol"] for r in element_rows]
        el_to_idx = {el: idx for idx, el in enumerate(all_elements)}

        cur.execute("SELECT id, class, system_tetrahedral_flag FROM materials ORDER BY id ASC")
        mat_rows = [dict(r) for r in cur.fetchall()]
        mat_id_to_row = {r["id"]: idx for idx, r in enumerate(mat_rows)}

        n_mat = len(mat_rows)
        n_el = len(all_elements)
        frac_matrix = np.zeros((n_mat, n_el), dtype=float)
        tet_flag_vec = np.array([r["system_tetrahedral_flag"] for r in mat_rows], dtype=int)

        cur.execute("SELECT material_id, element_symbol, atomic_fraction FROM material_elements")
        for r in cur.fetchall():
            m_idx = mat_id_to_row[r["material_id"]]
            e_idx = el_to_idx[r["element_symbol"]]
            frac_matrix[m_idx, e_idx] = float(r["atomic_fraction"])

        presence_matrix = (frac_matrix > 0).astype(int)

        def describe_pair_archetype(ea: str, eb: str, p_classes: Dict[str, int]) -> str:
            cls_summary = ", ".join(
                f"{cnt} {cls}"
                for cls, cnt in sorted(p_classes.items(), key=lambda kv: kv[1], reverse=True)
            )
            pair_set = {ea, eb}
            if "O" in pair_set:
                other = (pair_set - {"O"}).pop()
                if other in {"Si", "Ge", "B", "P"}:
                    return f"Primary Oxide Network Former Backbone ({cls_summary})"
                if other in {"Al", "Ga", "Ti", "V", "Mo", "W", "Te", "Zn", "Pb", "Bi"}:
                    return f"Intermediate Oxide Polyhedral/Tetrahedral Network ({cls_summary})"
                return f"Modified Oxide Glass Network ({cls_summary})"
            if pair_set == {"Si", "Al"}:
                return f"Aluminosilicate / SiAlON Tetrahedral Co-Network ({cls_summary})"
            if pair_set == {"Si", "B"}:
                return f"Borosilicate Co-Network & Fe-Si-B Metalloid Pair ({cls_summary})"
            if pair_set <= {"Ge", "As", "Se", "S", "Te", "Sb", "Ga", "P", "Li", "Na", "Ag", "I"} and p_classes.get("Chalcogenide", 0) >= sum(p_classes.values()) * 0.5:
                return f"Chalcogenide Covalent / Superionic Network Pair ({cls_summary})"
            if p_classes.get("Metallic Glass", 0) >= sum(p_classes.values()) * 0.6:
                if pair_set & {"B", "P", "Si", "C"}:
                    return f"Metal–Metalloid Trigonal-Prism BMG Pair ({cls_summary})"
                return f"Bulk Metallic Glass Icosahedral/Polytetrahedral Pair ({cls_summary})"
            return f"Multi-Class Inorganic Glass Pair ({cls_summary})"

        # 3. Correlation & Mutual Information Metrics
        pairwise_correlations: List[Dict[str, Any]] = []
        for i in range(n_el):
            for j in range(i + 1, n_el):
                el_i, el_j = all_elements[i], all_elements[j]
                co_cnt = co_matrix_dict.get(el_i, {}).get(el_j, 0)
                if co_cnt == 0:
                    continue

                xi_bin = presence_matrix[:, i]
                xj_bin = presence_matrix[:, j]
                # Binary Pearson phi correlation
                std_i = np.std(xi_bin)
                std_j = np.std(xj_bin)
                phi = (
                    float(np.corrcoef(xi_bin, xj_bin)[0, 1])
                    if (std_i > 1e-12 and std_j > 1e-12)
                    else 0.0
                )

                # Continuous atomic-fraction Pearson r across union of systems containing i or j
                union_mask = (xi_bin == 1) | (xj_bin == 1)
                if np.sum(union_mask) >= 3:
                    fi_sub = frac_matrix[union_mask, i]
                    fj_sub = frac_matrix[union_mask, j]
                    r_cont = (
                        float(np.corrcoef(fi_sub, fj_sub)[0, 1])
                        if (np.std(fi_sub) > 1e-12 and np.std(fj_sub) > 1e-12)
                        else 0.0
                    )
                else:
                    r_cont = 0.0

                mi_bits, nmi_val, pmi_11 = compute_binary_mi_and_nmi(xi_bin, xj_bin)
                p_classes = pair_class_map.get((el_i, el_j), {})

                pairwise_correlations.append(
                    {
                        "element_a": el_i,
                        "element_b": el_j,
                        "co_occurrence_count": co_cnt,
                        "pearson_phi_binary": round(phi, 4),
                        "pearson_r_atomic_fraction_union": round(r_cont, 4),
                        "mutual_information_bits": round(mi_bits, 4),
                        "normalized_mutual_information": round(nmi_val, 4),
                        "pointwise_mutual_information_bits": round(pmi_11, 4),
                        "class_breakdown": p_classes,
                        "chemical_pairing_archetype": describe_pair_archetype(el_i, el_j, p_classes),
                    }
                )

        # Sort pairwise correlations by co-occurrence and PMI
        top_co_occurring_pairs = sorted(
            pairwise_correlations,
            key=lambda x: (x["co_occurrence_count"], x["pearson_phi_binary"]),
            reverse=True,
        )[:40]

        top_positive_phi_pairs = sorted(
            [p for p in pairwise_correlations if p["co_occurrence_count"] >= 3],
            key=lambda x: x["pearson_phi_binary"],
            reverse=True,
        )[:30]

        # Compute Partner Diversity Entropy H_i, Tetrahedral MI, and Composite Amorphous Induction Score
        max_entropy = math.log2(max(2, n_el - 1))

        enriched_elements: List[Dict[str, Any]] = []
        for idx, r in enumerate(element_rows):
            el = r["element_symbol"]
            partners = co_matrix_dict.get(el, {})
            total_partner_links = sum(partners.values())
            entropy = 0.0
            if total_partner_links > 0:
                for cnt in partners.values():
                    p = cnt / total_partner_links
                    if p > 0:
                        entropy -= p * math.log2(p)

            xi_bin = presence_matrix[:, idx]
            mi_tet, nmi_tet, pmi_tet = compute_binary_mi_and_nmi(xi_bin, tet_flag_vec)
            std_x = np.std(xi_bin)
            std_t = np.std(tet_flag_vec)
            tet_phi = (
                float(np.corrcoef(xi_bin, tet_flag_vec)[0, 1])
                if (std_x > 1e-12 and std_t > 1e-12)
                else 0.0
            )

            cls_bd = el_class_counts.get(el, {})
            regime_bd = el_regime_counts.get(el, {})
            role_bd = el_role_counts.get(el, {})
            mg_cnt = int(cls_bd.get("Metallic Glass", 0))
            non_mg_cnt = int(r["occurrence_count"]) - mg_cnt
            non_mg_tet_ratio = (
                round(float(r["tetrahedral_count"]) / non_mg_cnt, 6)
                if non_mg_cnt > 0
                else 0.0
            )

            derived_cat, derivation_rule = derive_structural_category_from_metrics(
                int(r["tetrahedral_count"]),
                non_mg_cnt,
                non_mg_tet_ratio,
                float(r["multicomponent_mean_atomic_fraction"]),
                role_bd,
            )

            cat_tuple = ELEMENT_STRUCTURAL_CATEGORY.get(
                el, (derived_cat, derivation_rule)
            )
            broad_category = (
                cat_tuple[0]
                if (
                    cat_tuple[0].startswith("Intermediate (Metallic")
                    and derived_cat.startswith("Intermediate (Metallic")
                )
                else derived_cat
            )
            mechanism_summary = cat_tuple[1]

            # Composite Amorphous Induction Score (0 - 100 scale):
            # - 30% normalized log-occurrence frequency (universal presence across systems)
            # - 25% partner diversity Shannon entropy (ability to vitrify diverse partner elements)
            # - 20% tetrahedral coordination propensity (directional covalent network formation)
            # - 15% multi-component mean atomic fraction (capacity to serve as host backbone vs minor
            #       dopant without single-element x=1.0 film bias)
            # - 10% multi-class versatility (spanning Oxide, Chalcogenide, Metallic, Covalent classes)
            freq_norm = math.log1p(r["occurrence_count"]) / math.log1p(
                max(1, element_rows[0]["occurrence_count"])
            )
            entropy_norm = min(1.0, entropy / max_entropy)
            tet_norm = float(r["tetrahedral_ratio"])
            frac_norm = min(
                1.0, float(r["multicomponent_mean_atomic_fraction"]) / 0.50
            )
            class_norm = min(1.0, float(r["classes_spanned"]) / 4.0)

            induction_score = round(
                100.0
                * (
                    0.30 * freq_norm
                    + 0.25 * entropy_norm
                    + 0.20 * tet_norm
                    + 0.15 * frac_norm
                    + 0.10 * class_norm
                ),
                2,
            )

            top_partners = sorted(
                partners.items(), key=lambda kv: (-kv[1], kv[0])
            )

            enriched_entry = {
                **r,
                "non_metallic_occurrences": non_mg_cnt,
                "metallic_glass_occurrences": mg_cnt,
                "non_metallic_tetrahedral_ratio": non_mg_tet_ratio,
                "unique_partner_elements": len(partners),
                "partner_diversity_entropy_bits": round(entropy, 4),
                "tetrahedral_system_pearson_phi": round(tet_phi, 4),
                "tetrahedral_system_mi_bits": round(mi_tet, 4),
                "tetrahedral_system_pmi_bits": round(pmi_tet, 4),
                "amorphous_induction_score": induction_score,
                "structural_category": broad_category,
                "category_derivation_rule": derivation_rule,
                "mechanism_summary": mechanism_summary,
                "class_breakdown": cls_bd,
                "synthesis_regime_breakdown": regime_bd,
                "role_breakdown": role_bd,
                "top_co_occurring_partners": [
                    {"partner": k, "count": v} for k, v in top_partners
                ],
            }
            enriched_elements.append(enriched_entry)

        # Rank by Amorphous Induction Score descending
        ranked_by_induction = sorted(
            enriched_elements,
            key=lambda x: (x["amorphous_induction_score"], x["occurrence_count"]),
            reverse=True,
        )
        for rank_idx, item in enumerate(ranked_by_induction, start=1):
            item["induction_rank"] = rank_idx

        # 4. Complete, Mutually Exclusive Partition Across All Active Elements (N = 77)
        primary_tet_analysis = [
            e
            for e in enriched_elements
            if e["structural_category"] == "Network Former (Tetrahedral/Polyhedral Backbone)"
        ]
        bridging_anion_formers = [
            e
            for e in enriched_elements
            if e["structural_category"] == "Network Former (Bridging Anion Backbone)"
        ]
        secondary_tet_analysis = [
            e
            for e in enriched_elements
            if e["structural_category"] == "Intermediate (Conditional Tetrahedral Former)"
        ]
        non_tet_oxide_chalco_intermediates = [
            e
            for e in enriched_elements
            if e["structural_category"] == "Intermediate"
        ]
        metallic_cluster_intermediates = [
            e
            for e in enriched_elements
            if e["structural_category"].startswith("Intermediate (Metallic")
        ]
        metallic_subcategories: Dict[str, List[str]] = {}
        for e in metallic_cluster_intermediates:
            metallic_subcategories.setdefault(e["structural_category"], []).append(
                e["element_symbol"]
            )
        modifiers_analysis = [
            e
            for e in enriched_elements
            if e["structural_category"] == "Modifier"
        ]
        intermediates_analysis = (
            secondary_tet_analysis
            + non_tet_oxide_chalco_intermediates
            + metallic_cluster_intermediates
        )
        all_network_formers = primary_tet_analysis + bridging_anion_formers

        # Dense 15x15 co-occurrence submatrix for top 15 most frequent elements
        top15_els = [r["element_symbol"] for r in element_rows[:15]]
        dense_top15_matrix = []
        for ea in top15_els:
            row_vals = [
                co_matrix_dict.get(ea, {}).get(eb, 0) if ea != eb else 0
                for eb in top15_els
            ]
            dense_top15_matrix.append({"element": ea, "counts": row_vals})

        results = {
            "metadata": {
                "step": "Step 4: Statistical and Elemental Attribution Analysis",
                "total_amorphous_materials": total_materials,
                "total_unique_elements": n_el,
                "class_summary": class_summary,
                "synthesis_regime_summary": synthesis_regime_summary,
            },
            "element_statistics_by_frequency": enriched_elements,
            "element_ranking_by_induction_score": ranked_by_induction,
            "top15_co_occurrence_matrix": {
                "elements": top15_els,
                "rows": dense_top15_matrix,
            },
            "top_co_occurring_pairs": top_co_occurring_pairs,
            "top_positive_correlation_pairs": top_positive_phi_pairs,
            "all_pairwise_correlations": pairwise_correlations,
            "tetrahedral_sub_analysis": {
                "primary_tetrahedral_network_formers": primary_tet_analysis,
                "bridging_anion_network_formers": bridging_anion_formers,
                "secondary_conditional_tetrahedral_elements": secondary_tet_analysis,
                "non_tetrahedral_oxide_chalcogenide_intermediates": non_tet_oxide_chalco_intermediates,
                "metallic_cluster_host_intermediates": metallic_cluster_intermediates,
                "metallic_glass_subcategories": metallic_subcategories,
                "network_modifiers": modifiers_analysis,
                "partition_counts": {
                    "primary_tetrahedral_network_formers": len(primary_tet_analysis),
                    "bridging_anion_network_formers": len(bridging_anion_formers),
                    "secondary_conditional_tetrahedral_elements": len(secondary_tet_analysis),
                    "non_tetrahedral_oxide_chalcogenide_intermediates": len(non_tet_oxide_chalco_intermediates),
                    "metallic_cluster_host_intermediates": len(metallic_cluster_intermediates),
                    "network_modifiers": len(modifiers_analysis),
                    "total_partitioned_elements": (
                        len(primary_tet_analysis)
                        + len(bridging_anion_formers)
                        + len(secondary_tet_analysis)
                        + len(non_tet_oxide_chalco_intermediates)
                        + len(metallic_cluster_intermediates)
                        + len(modifiers_analysis)
                    ),
                },
                "group_comparison_summary": {
                    "primary_tetrahedral_formers_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in primary_tet_analysis])),
                        2,
                    ),
                    "bridging_anion_formers_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in bridging_anion_formers])),
                        2,
                    ),
                    "all_network_formers_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in all_network_formers])),
                        2,
                    ),
                    "secondary_tetrahedral_intermediates_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in secondary_tet_analysis])),
                        2,
                    ),
                    "non_tetrahedral_intermediates_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in non_tet_oxide_chalco_intermediates])),
                        2,
                    ),
                    "metallic_cluster_intermediates_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in metallic_cluster_intermediates])),
                        2,
                    ),
                    "intermediates_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in intermediates_analysis])),
                        2,
                    ),
                    "modifiers_mean_score": round(
                        float(np.mean([e["amorphous_induction_score"] for e in modifiers_analysis])),
                        2,
                    ),
                },
            },
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return results
    finally:
        conn.close()


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    db_file = root / "amorphous_materials.db"
    out_file = root / "data" / "statistical_analysis_results.json"
    res = run_step4_analysis(db_file, out_file)
    print(
        f"[Step 4] Analyzed {res['metadata']['total_unique_elements']} elements across "
        f"{res['metadata']['total_amorphous_materials']} amorphous systems -> {out_file}"
    )
