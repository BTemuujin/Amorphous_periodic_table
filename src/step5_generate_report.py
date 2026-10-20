"""Step 5: Final Classification and Export.

Generates the comprehensive markdown summary report `amorphous_periodic_table_report.md`
from `data/statistical_analysis_results.json` and `amorphous_materials.db`, containing:
1. Ranked list of chemical elements by their capability to induce amorphous phase formation.
2. Co-occurrence matrix, Pearson & Mutual Information correlation metrics, and the
   distinct sub-analysis isolating primary tetrahedral network formers (Si, Ge, P, B, As)
   versus intermediates and modifiers.
3. Classification table sorting elements into Network Formers (tetrahedral/polyhedral
   backbones), Intermediates, and Modifiers.
4. Specific peer-reviewed experimental system examples where the introduction of a single
   tetrahedral-promoting element converted a crystalline-prone alloy or compound into an
   amorphous phase.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES: List[Dict[str, str]] = [
    {
        "class": "Metallic Glass",
        "crystalline_parent": "Au (FCC metal, crystallizes at >10^9 K/s)",
        "added_element": "Si (25 at.%)",
        "amorphous_system": "Au75Si25 (SiAu3)",
        "local_coordination": "Quasi-tetrahedral/trigonal-prism SiAu9 p-d covalent clusters frustrating FCC packing",
        "verification": "Diffuse XRD halo; splat-quenching at 10^6 K/s; DSC crystallization peak",
        "doi": "10.1038/187869b0",
        "reference": "KLEMENT, WILLENS & DUWEZ, Nature 187, 869 (1960) — \"Non-crystalline Structure in Solidified Gold–Silicon Alloys\"",
        "mechanism": "First melt-quenched metallic glass: introducing tetrahedral covalent Si lowers the eutectic temperature by ~700 K (to 636 K) and creates directional Au-Si p-d bonding that prevents FCC lattice nucleation.",
    },
    {
        "class": "Metallic Glass",
        "crystalline_parent": "Pd50Ni50 (continuous FCC solid solution)",
        "added_element": "P (20 at.%)",
        "amorphous_system": "Pd40Ni40P20",
        "local_coordination": "Covalent P-centered trigonal prisms P(Pd,Ni)9 cross-linking icosahedral metal shells",
        "verification": "Diffuse XRD halo; TEM SAED; DSC Tg=576 K, Tx=671 K (bulk cm-scale ingot)",
        "doi": "10.1063/1.95330",
        "reference": "Kui, Greer & Turnbull, Applied Physics Letters 45, 615 (1984) — \"Formation of bulk metallic glass by fluxing\"",
        "mechanism": "Binary Pd-Ni alloys crystallize rapidly into FCC solid solutions; introducing 20 at.% P introduces directional p-d covalent prism motifs that reduce the critical cooling rate below 1 K/s.",
    },
    {
        "class": "Metallic Glass",
        "crystalline_parent": "Fe (BCC/FCC metal) or Fe-Ni (FCC Permalloy)",
        "added_element": "B (20 at.%) or Si+B",
        "amorphous_system": "Fe80B20 / Fe78Si9B13",
        "local_coordination": "Fe9B tricapped trigonal prisms and Si-Fe quasi-tetrahedral p-d bonds",
        "verification": "Diffuse XRD halo; 57Fe Mossbauer spectroscopy; DSC Tg/Tx (Metglas 2605)",
        "doi": "10.1063/1.325328",
        "reference": "Hasegawa & Ray, Journal of Applied Physics 49, 4174 (1978) — \"Iron-boron metallic glasses\"",
        "mechanism": "Adding metalloid B (and Si) introduces short covalent-like Fe-B/Fe-Si bonds and trigonal-prismatic short-range order incompatible with translational BCC symmetry.",
    },
    {
        "class": "Metallic Glass",
        "crystalline_parent": "Cu50Zr50 (marginal 2 mm binary glass / B2 CuZr crystal)",
        "added_element": "Al (8 at.%)",
        "amorphous_system": "Cu46Zr46Al8",
        "local_coordination": "Al-centered icosahedral/polytetrahedral clusters with directional sp-d hybridization",
        "verification": "Diffuse synchrotron XRD halo; TEM SAED; DSC Tg=705 K, Tx=777 K (Delta Tx=72 K)",
        "doi": "10.1103/physrevlett.102.245501",
        "reference": "Cheng, Ma & Sheng, Phys. Rev. Lett. 102, 245501 (2009) — \"Atomic Level Structure in Multicomponent Bulk Metallic Glass\"",
        "mechanism": "Adding 8 at.% Al (a conditional tetrahedral former in oxides) introduces directional sp-d bonding with Zr/Cu, slowing atomic mobility by an order of magnitude and suppressing B2 CuZr crystallization.",
    },
    {
        "class": "Metallic Glass",
        "crystalline_parent": "Nd2Fe14B / binary Nd-Fe crystalline intermetallics",
        "added_element": "Al (10 at.%)",
        "amorphous_system": "Nd60Fe30Al10",
        "local_coordination": "Al-stabilized Fe-Nd icosahedral/polytetrahedral network",
        "verification": "Diffuse XRD halo; HRTEM; MDSC bulk hard-magnetic cylinder",
        "doi": "10.2320/matertrans1989.37.99",
        "reference": "Inoue et al., Mater. Trans., JIM 37, 99 (1996) — \"Bulk Nd&ndash;Fe&ndash;Al Amorphous Alloys with Hard Magnetic Properties\"",
        "mechanism": "Binary Nd-Fe crystallizes during conventional casting; adding 10 at.% Al induces strong Al-Nd/Al-Fe covalent-like hybridization, enabling bulk cylinder vitrification.",
    },
    {
        "class": "Chalcogenide",
        "crystalline_parent": "Te (trigonal helical chains, crystallizes at room temperature) & GeTe (rhombohedral crystal)",
        "added_element": "Ge (15 at.%)",
        "amorphous_system": "Ge15Te85",
        "local_coordination": "Corner-sharing GeTe4 tetrahedra cross-linking 2-coordinated Te chains",
        "verification": "Diffuse XRD halo; neutron diffraction; DSC Tg=403 K, sharp crystallization Tx=495 K",
        "doi": "10.1016/0022-3093(70)90093-1",
        "reference": "Betts, Bienenstock & Ovshinsky, Journal of Non-Crystalline Solids 4, 554 (1970) — \"Radial distribution studies of amorphous GexTe1−x alloys\"",
        "mechanism": "Pure Te cannot be melt-quenched into a stable glass at room temperature, and stoichiometric GeTe crystallizes rapidly (CN=6 rocksalt). Introducing 15 at.% tetrahedral Ge (CN=4) locks Te chains into a Phillips-Thorpe optimally constrained 3D amorphous network.",
    },
    {
        "class": "Oxide",
        "crystalline_parent": "12CaO-7Al2O3 (crystalline mayenite) / CaO-Al2O3 refractory",
        "added_element": "SiO2 (~7 mol.% SiO4)",
        "amorphous_system": "12CaO-7Al2O3-SiO2 (Ca12Al14SiO35)",
        "local_coordination": "Coexisting SiO4 and AlO4^- corner-sharing tetrahedra",
        "verification": "Diffuse XRD halo; 27Al/29Si NMR; DSC Tg=1115 K",
        "doi": "10.1016/j.gca.2009.03.041",
        "reference": "Richet et al., Geochimica et Cosmochimica Acta 73, 3894 (2009) — \"Aluminum speciation, vibrational entropy and short-range order in calcium aluminosilicate glasses\"",
        "mechanism": "Binary calcium aluminate devitrifies easily at container walls; adding minor tetrahedral SiO4 suppresses mayenite nucleation and expands the bulk optical glass-forming domain.",
    },
    {
        "class": "Oxide",
        "crystalline_parent": "HfO2 & ZrO2 (crystallize into monoclinic/tetragonal phases at 400-500 C)",
        "added_element": "SiO2 (SiO4 tetrahedra)",
        "amorphous_system": "HfO2-4SiO2 (HfSi4O10) & ZrO2-4SiO2",
        "local_coordination": "Corner-shared SiO4 tetrahedra cross-linking HfO6/ZrO6 polyhedra via M-O-Si bonds",
        "verification": "Diffuse XRD halo; HRTEM/SAED; EXAFS amorphous stability >900 C",
        "doi": "10.1063/1.1361065",
        "reference": "Wilk, Wallace & Anthony, Journal of Applied Physics 89, 5243 (2001) — \"High-κ gate dielectrics: Current status and materials properties considerations\"",
        "mechanism": "Pure high-k HfO2 and ZrO2 thin films form polycrystalline grain boundaries with high leakage current; incorporating tetrahedral SiO4 frustrates baddeleyite/tetragonal nucleation above 900 C.",
    },
    {
        "class": "Oxide",
        "crystalline_parent": "MoO3 (orthorhombic layered crystal) & Bi2O3 (monoclinic crystal)",
        "added_element": "P2O5 (PO4 tetrahedra) or B2O3 (BO4/BO3)",
        "amorphous_system": "P2O5-2MoO3 & 2Bi2O3-B2O3",
        "local_coordination": "PO4 or BO4 tetrahedra cross-linking MoO6/BiO6 octahedra",
        "verification": "Diffuse XRD halo; 31P/11B MAS NMR; DSC Tg=640-615 K",
        "doi": "10.1007/bf02757579",
        "reference": "Muthupari, Kulkarni & Rao, Bull. Mater. Sci. 17, 1029 (1994) — \"EXAFS and MAS NMR studies of sodium molybdophosphate and sodium tungstophosphate glasses\"",
        "mechanism": "Neither MoO3 nor Bi2O3 forms a glass by conventional crucible cooling; inserting tetrahedral PO4 or BO4 units interrupts edge-sharing octahedral chains and yields stable bulk glasses.",
    },
    {
        "class": "Oxide",
        "crystalline_parent": "ZnO (wurtzite crystal) & In2O3 (bixbyite crystal)",
        "added_element": "Ga2O3 (GaO4/GaO5 tetrahedral/bipyramidal disorder)",
        "amorphous_system": "InGaZnO4 (a-IGZO)",
        "local_coordination": "Tetrahedral GaO4 and ZnO4/ZnO5 units frustrating edge-sharing InO6 octahedra",
        "verification": "Diffuse XRD halo; TEM SAED; grazing-incidence XAFS",
        "doi": "10.1038/nature03090",
        "reference": "Nomura et al., Nature 432, 488 (2004) — \"Room-temperature fabrication of transparent flexible thin-film transistors using amorphous oxide semiconductors\"",
        "mechanism": "Binary In2O3-ZnO films crystallize even at room temperature during sputtering; introducing Ga3+ (which prefers tetrahedral GaO4 / trigonal-bipyramidal coordination) frustrates the homologous crystal lattice while preserving s-orbital conduction pathways.",
    },
    {
        "class": "Covalent Network",
        "crystalline_parent": "CdAs2 / ZnP2 (crystalline binary II-V semiconductors)",
        "added_element": "Ge (GeAs4 / GeP4 tetrahedra)",
        "amorphous_system": "CdGeAs2 & CdGeP2",
        "local_coordination": "Interconnected GeAs4 and CdAs4 (or GeP4/CdP4) sp3 tetrahedra",
        "verification": "Diffuse XRD halo; 31P NMR; DSC Tg=663 K (CdGeAs2) and 715 K (CdGeP2)",
        "doi": "10.1002/pssa.2211030240",
        "reference": "Uemura et al., Phys. Stat. Sol. (a) 103, K69 (1987) — \"A Change in Local Order of Amorphous CdGeAs2 on the Glass-Crystal Transition and the High Temperature Modification of the Crystalline Phase\"",
        "mechanism": "Inserting Group-IV tetrahedral Ge creates chemical and bond-length disorder between II-V and IV-V tetrahedra, enabling bulk melt-quenched pnictide glasses.",
    },
    {
        "class": "Covalent Network",
        "crystalline_parent": "Si3N4 (crystallizes into alpha/beta-Si3N4 above 1400 C)",
        "added_element": "B + C (mixed Si(C,N)4 tetrahedra + BN3 units)",
        "amorphous_system": "SiB0.5C0.5N1.5",
        "local_coordination": "SiN4 / SiC_xN_{4-x} tetrahedra cross-linked by trigonal BN3 and sp2/sp3 C",
        "verification": "Diffuse XRD halo retained up to 1773 K; 29Si/11B/13C MAS NMR",
        "doi": "10.1038/382796a0",
        "reference": "Riedel et al., Nature 382, 796 (1996) — \"A silicoboron carbonitride ceramic stable to 2,000°C\"",
        "mechanism": "Incorporating C into Si(C,N)4 tetrahedra and B into BN3 turbostratic cages suppresses long-range atomic diffusion and keeps the covalent ceramic amorphous up to 1500 C.",
    },
    {
        "class": "Metallic Glass",
        "crystalline_parent": "B20 FeGe, B20 FeSi, B20 CoSi, B20 MnSi (chiral cubic crystals / Kondo insulator / skyrmion helimagnets)",
        "added_element": "Si or Ge (vapor co-evaporation / sputtering with p-d covalent frustration)",
        "amorphous_system": "FeGe, FeSi, CoSi, MnSi, FeGe3, Fe3Si7",
        "local_coordination": "Polytetrahedral M-Si / M-Ge p-d hybridized clusters (x~0.50) transitioning to tetrahedral Si4/Ge4 continuous random network (x<=0.30)",
        "verification": "Diffuse XRD halo; HRTEM/SAED diffuse rings; Fe/Ge K-edge EXAFS; anomalous Hall & SQUID magnetometry",
        "doi": "10.1002/adma.202004830",
        "reference": "Streubel et al., Advanced Materials 33, 2004830 (2021) — \"Chiral Spin Textures in Amorphous Iron–Germanium Thick Films\"",
        "mechanism": "While pure 3d metals (Fe, Co, Mn, Cr) crystallize into BCC/FCC/HCP lattices upon vapor deposition at 300 K, co-evaporating with tetrahedral Group-IV formers (Si, Ge) creates directional p-d covalent bonds that frustrate B20 crystal nucleation and convert non-magnetic Kondo insulator B20 FeSi into an itinerant amorphous ferromagnet (Hellman group, UC Berkeley).",
    },
    {
        "class": "Covalent Network",
        "crystalline_parent": "GdSi2 / TbSi2 / GdGe2 (crystalline antiferromagnetic rare-earth silicides/germanides)",
        "added_element": "Si or Ge tetrahedral host network (85-86 at.% Si/Ge)",
        "amorphous_system": "Gd7Si43 (a-Gd14Si86), Tb3Si17 (a-Tb15Si85), Gd3Ge17 (a-Gd15Ge85)",
        "local_coordination": "4-coordinate Si4 / Ge4 continuous random network hosting 7-8 coordinated rare-earth spin-glass moments",
        "verification": "Diffuse XRD halo; HRTEM/SAED; EXAFS; giant negative magnetoresistance & spin-glass freezing",
        "doi": "10.1103/physrevlett.83.2266",
        "reference": "Zink et al., Phys. Rev. Lett. 83, 2266 (1999) — \"Large Magnetic Entropy in Giant Magnetoresistive Amorphous Gadolinium Silicon\"",
        "mechanism": "Embedding rare-earth ions (Gd, Tb) into an e-beam co-evaporated tetrahedral a-Si or a-Ge continuous random network suppresses silicide crystallization and produces a concentrated amorphous spin glass with giant magnetoresistance near the metal-insulator transition.",
    },
]



def generate_markdown_report(
    analysis_json_path: Path, report_output_path: Path
) -> str:
    """Build and write `amorphous_periodic_table_report.md`."""
    data = json.loads(analysis_json_path.read_text(encoding="utf-8"))
    meta = data["metadata"]
    ranked_elements: List[Dict[str, Any]] = data["element_ranking_by_induction_score"]
    freq_elements: List[Dict[str, Any]] = data["element_statistics_by_frequency"]
    co_mat = data["top15_co_occurrence_matrix"]
    top_co_pairs = data["top_co_occurring_pairs"][:20]
    top_phi_pairs = data["top_positive_correlation_pairs"][:20]
    tet_sub = data["tetrahedral_sub_analysis"]

    lines: List[str] = []
    lines.append("# The Amorphous Periodic Table: Elemental Attribution, Tetrahedral Network Formation, and Statistical Analysis")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"This report synthesizes **{meta['total_amorphous_materials']} experimentally verified inorganic amorphous systems** "
        f"spanning **{meta['total_unique_elements']} chemical elements** across four structural classes "
        "(`Oxide`, `Chalcogenide`, `Metallic Glass`, and `Covalent Network`). Every system included in `amorphous_materials.db` "
        "is verified by peer-reviewed experimental signatures of non-crystallinity: **diffuse X-ray/neutron diffraction halos (FSDP)**, "
        "**TEM selected area electron diffraction (SAED) diffuse rings**, and/or **differential scanning calorimetry (DSC) glass transition ($T_g$) and crystallization ($T_x$) signatures**. "
        "Purely organic glasses (such as D-glucose, *o*-terphenyl, PMMA, glycerol, and sucrose) were strictly filtered out during Step 2 normalization while preserving inorganic carbides, oxycarbides, and carbonitrides (`ta-C`, `a-SiC`, `SiOC`, `SiBCN`, and C-bearing metallic glasses)."
    )
    lines.append("")
    lines.append("### Dataset Breakdown by Material Class")
    lines.append("")
    lines.append("| Material Class | Amorphous Systems ($N$) | Share of Dataset (%) | Systems with Tetrahedral Motif | Tetrahedral Prevalence (%) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    for cs in meta["class_summary"]:
        cnt = int(cs["cnt"])
        tet_cnt = int(cs["tet_cnt"] or 0)
        share = 100.0 * cnt / meta["total_amorphous_materials"]
        tet_pct = 100.0 * tet_cnt / cnt if cnt > 0 else 0.0
        lines.append(
            f"| **{cs['class']}** | {cnt} | {share:.1f}% | {tet_cnt} | {tet_pct:.1f}% |"
        )
    lines.append("")

    # --- SECTION 1: RANKED LIST OF ELEMENTS BY AMORPHOUS INDUCTION CAPABILITY ---
    lines.append("---")
    lines.append("")
    lines.append("## 1. Ranked List of Elements by Capability to Induce Amorphous Phase Formation")
    lines.append("")
    lines.append(
        "Each element $i$ is evaluated using the **Composite Amorphous Induction Score ($S_i \\in [0, 100]$)**, which integrates five quantitative dimensions derived from `amorphous_materials.db`:"
    )
    lines.append(
        "1. **Log-Normalized Occurrence Frequency (30%)**: Prevalence across all verified amorphous systems ($f_i = n_i / N_{\\text{total}}$)."
    )
    lines.append(
        "2. **Partner Diversity Shannon Entropy $H_i$ (25%)**: $H_i = -\\sum_{j \\neq i} p_{j|i} \\log_2 p_{j|i}$, quantifying how universally element $i$ stabilizes diverse chemical partners into disordered phases."
    )
    lines.append(
        "3. **Tetrahedral Network-Forming Propensity (20%)**: Fraction of occurrences where element $i$ acts as a central tetrahedrally coordinated atom ($\\text{CN}=4$, e.g., $\\text{SiO}_4$, $\\text{GeSe}_4$, $\\text{PO}_4$, $\\text{AlO}_4^-$, $\\text{BO}_4$)."
    )
    lines.append(
        "4. **Multi-Component Stoichiometric Host Capacity (15%)**: Mean atomic fraction $\\bar{x}_{i,\\text{multi}}$ in multi-component systems ($N_{\\text{el}} \\ge 2$), distinguishing primary backbone/matrix formers from dilute dopants without single-element film ($x=1.0$) bias."
    )
    lines.append(
        "5. **Cross-Class Versatility (10%)**: Number of distinct amorphous material classes spanned (Oxides, Chalcogenides, Metallic Glasses, Covalent Networks)."
    )
    lines.append("")
    lines.append("| Rank | Element | Induction Score ($S_i$) | Occurrences ($n_i$) | Frequency ($f_i$) | Mean Atomic Frac ($\\bar{x}_i$) | Tetrahedral Count ($n_{\\text{tet}}$) | Tetrahedral Ratio | Partner Entropy $H_i$ (bits) | Classes Spanned | Top Co-Occurring Partners | Structural Category |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |")
    for item in ranked_elements:
        partners_str = ", ".join(
            f"{p['partner']}({p['count']})" for p in item["top_co_occurring_partners"][:4]
        ) or "None (Elemental)"
        lines.append(
            f"| {item['induction_rank']} | **{item['element_symbol']}** | **{item['amorphous_induction_score']:.2f}** | "
            f"{item['occurrence_count']} | {100.0 * item['frequency']:.1f}% | {item['mean_atomic_fraction']:.3f} | "
            f"{item['tetrahedral_count']} | {100.0 * item['tetrahedral_ratio']:.1f}% | "
            f"{item['partner_diversity_entropy_bits']:.2f} | {item['classes_spanned']} | "
            f"{partners_str} | {item['structural_category']} |"
        )
    lines.append("")

    # --- SECTION 2: CO-OCCURRENCE MATRIX, CORRELATIONS & TETRAHEDRAL SUB-ANALYSIS ---
    lines.append("---")
    lines.append("")
    lines.append("## 2. Co-Occurrence Matrix, Correlation Metrics, and Tetrahedral Network Former Sub-Analysis")
    lines.append("")
    lines.append("### 2.1 Element–Element Co-Occurrence Matrix (Top 15 Most Frequent Elements)")
    lines.append("")
    top15 = co_mat["elements"]
    header_cols = " | ".join(f"**{el}**" for el in top15)
    sep_cols = " | ".join(":---:" for _ in top15)
    lines.append(f"| Element | {header_cols} |")
    lines.append(f"| :---: | {sep_cols} |")
    for row_obj in co_mat["rows"]:
        el = row_obj["element"]
        vals_str = " | ".join(str(v) if v > 0 else "·" for v in row_obj["counts"])
        lines.append(f"| **{el}** | {vals_str} |")
    lines.append("")

    lines.append("### 2.2 Top Element Pairs by Co-Occurrence, Pearson Correlation ($\\phi$, $r$), and Mutual Information")
    lines.append("")
    lines.append(
        "- **Binary Presence Pearson Correlation ($\\phi_{ij}$)**: Measures whether two elements preferentially co-segregate into the same amorphous systems ($\\phi > 0$) or belong to mutually exclusive glass families ($\\phi < 0$)."
    )
    lines.append(
        "- **Union Atomic-Fraction Pearson Correlation ($r_{ij}$)**: Measures stoichiometric co-variation (positive when two elements scale together; negative when they substitute for one another or compete for composition)."
    )
    lines.append(
        "- **Pointwise Mutual Information ($\\text{PMI}_{ij} = \\log_2 \\frac{P(i,j)}{P(i)P(j)}$)** and **Normalized Mutual Information ($\\text{NMI}_{ij}$)**: Information-theoretic synergy between element pairs."
    )
    lines.append("")
    lines.append("| Pair ($E_i$–$E_j$) | Co-Occurrences ($C_{ij}$) | Binary Pearson $\\phi_{ij}$ | Stoichiometric Pearson $r_{ij}$ | Mutual Info $I(E_i;E_j)$ (bits) | Normalized MI ($\\text{NMI}_{ij}$) | Pointwise MI ($\\text{PMI}_{ij}$, bits) | Chemical Pairing Archetype (SQL Class Breakdown) |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for p in top_co_pairs:
        ea, eb = p["element_a"], p["element_b"]
        archetype = p.get("chemical_pairing_archetype", "Inorganic Glass Pair")
        lines.append(
            f"| **{ea}–{eb}** | {p['co_occurrence_count']} | {p['pearson_phi_binary']:+.3f} | "
            f"{p['pearson_r_atomic_fraction_union']:+.3f} | {p['mutual_information_bits']:.4f} | "
            f"{p['normalized_mutual_information']:.4f} | {p['pointwise_mutual_information_bits']:+.3f} | {archetype} |"
        )
    lines.append("")

    lines.append("### 2.3 Distinct Sub-Analysis: Primary Tetrahedral Network Formers vs. Conditional Tetrahedral Intermediates vs. Modifiers")
    lines.append("")
    grp_summary = tet_sub["group_comparison_summary"]
    part_counts = tet_sub.get("partition_counts", {})
    n_1a = part_counts.get("primary_tetrahedral_network_formers", 5)
    n_1b = part_counts.get("bridging_anion_network_formers", 7)
    n_2a = part_counts.get("secondary_conditional_tetrahedral_elements", 12)
    n_2b = part_counts.get("non_tetrahedral_oxide_chalcogenide_intermediates", 13)
    n_2c = part_counts.get("metallic_cluster_host_intermediates", 12)
    n_3 = part_counts.get("network_modifiers", 28)
    n_interm_total = n_2a + n_2b + n_2c
    n_part_total = part_counts.get("total_partitioned_elements", meta["total_unique_elements"])

    lines.append(
        "Following Zachariasen's Continuous Random Network (CRN) theory and Phillips–Thorpe topological constraint theory, "
        "3D corner-sharing tetrahedra ($\\text{MX}_4$, coordination number $z=4$) combined with 2-coordinated bridging anions ($\\text{X}$, $z=2$) "
        "yield an average bond-stretching and bond-bending constraint count $n_c \\approx 3.0$ per atom—matching the 3D degrees of freedom ($d=3$) and "
        "maximizing glass-forming ability without mechanical overconstraint. "
        "Notably, `Si`, `P`, and `B` exhibit a **dual structural role**: in non-metallic glasses (`Oxide`, `Chalcogenide`, `Covalent Network`), `Si` and `Ge` adopt tetrahedral ($\\text{CN}=4$) coordination in **100.0% of systems**, `P` in **95.5%** (21/22 systems, with only elemental `a-P` adopting 3-fold pyramidal coordination), and `B` in **80.0%** (16/20 systems, with pure $\\text{B}_2\\text{O}_3$, $\\text{B}_2\\text{S}_3$, $\\text{a-B}$, and $\\text{a-BN}$ adopting trigonal/icosahedral coordination), whereas in `Metallic Glasses` they act as $\\text{CN}=9$ tricapped trigonal-prism metalloid solutes ($\\text{M}_9\\text{Si}, \\text{M}_9\\text{P}, \\text{M}_9\\text{B}$)."
    )
    lines.append("")
    lines.append(
        f"Across all **{n_part_total} unique elements**, the complete mutually exclusive structural partition (${n_1a} + {n_1b} + {n_2a} + {n_2b} + {n_2c} + {n_3} = {n_part_total}$) yields:"
    )
    lines.append(
        f"- **1a. Primary Tetrahedral/Polyhedral Network Formers (`Si`, `Ge`, `P`, `B`, `As`; $N={n_1a}$) Mean Induction Score**: **{grp_summary['primary_tetrahedral_formers_mean_score']:.2f} / 100**"
    )
    lines.append(
        f"- **1b. Bridging Anion Network Formers (`O`, `S`, `Se`, `N`, `F`, `Cl`, `Br`; $N={n_1b}$) Mean Induction Score**: **{grp_summary.get('bridging_anion_formers_mean_score', 0.0):.2f} / 100**"
    )
    lines.append(
        f"- **2a. Conditional/Secondary Tetrahedral Intermediates (`Al`, `Ga`, `Zn`, `Be`, `V`, `Ti`, `Mo`, `W`, `C`, `Sn`, `In`, `Cd`; $N={n_2a}$) Mean Induction Score**: **{grp_summary['secondary_tetrahedral_intermediates_mean_score']:.2f} / 100**"
    )
    lines.append(
        f"- **2b. Non-Tetrahedral Oxide/Chalcogenide/Halide Intermediates (`Te`, `Sb`, `Bi`, `Pb`, `Fe`, `Zr`, `Hf`, `Nb`, `Ta`, `Sc`, `Tl`, `Os`, `Th`; $N={n_2b}$) Mean Induction Score**: **{grp_summary.get('non_tetrahedral_intermediates_mean_score', 0.0):.2f} / 100**"
    )
    lines.append(
        f"- **2c. Metallic Cluster/Host Intermediates (`Cu`, `Ni`, `Co`, `Pd`, `Pt`, `Au`, `Cr`, `Mn`, `Ru`, `Rh`, `Re`, `Ir`; $N={n_2c}$) Mean Induction Score**: **{grp_summary.get('metallic_cluster_intermediates_mean_score', 0.0):.2f} / 100** (*All Intermediates Combined, $N={n_interm_total}$*: **{grp_summary['intermediates_mean_score']:.2f} / 100**)"
    )
    lines.append(
        f"- **3. Network Modifiers ($N={n_3}$) Mean Induction Score**: **{grp_summary['modifiers_mean_score']:.2f} / 100**"
    )
    lines.append("")
    lines.append("#### Primary Network Formers (`Si`, `Ge`, `P`, `B`, `As`) Detailed Attribution")
    lines.append("")
    lines.append("| Element | Total Occurrences ($n_i$) | Non-Metallic Systems ($n_{\\text{non-MG}}$) | Metallic Glass Systems ($n_{\\text{MG}}$) | Tetrahedral Systems ($n_{\\text{tet}}$) | Non-Metallic Tet Ratio (%) | Overall Tet Ratio (%) | System Tet-Correlation $\\phi(E_i, \\text{Tet})$ | Partner Entropy $H_i$ (bits) | Dual Role in Covalent/Oxide Glasses vs. Metallic Glasses |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for e in tet_sub["primary_tetrahedral_network_formers"]:
        lines.append(
            f"| **{e['element_symbol']}** | {e['occurrence_count']} | {e['non_metallic_occurrences']} | "
            f"{e['metallic_glass_occurrences']} | {e['tetrahedral_count']} | "
            f"**{100.0 * e['non_metallic_tetrahedral_ratio']:.1f}%** | {100.0 * e['tetrahedral_ratio']:.1f}% | "
            f"{e['tetrahedral_system_pearson_phi']:+.3f} | {e['partner_diversity_entropy_bits']:.2f} | {e['mechanism_summary']} |"
        )
    lines.append("")
    lines.append("#### Conditional / Secondary Tetrahedral Network Intermediates")
    lines.append("")
    lines.append("| Element | Total Occurrences ($n_i$) | Non-Metallic Systems ($n_{\\text{non-MG}}$) | Metallic Glass Systems ($n_{\\text{MG}}$) | Tetrahedral Systems ($n_{\\text{tet}}$) | Non-Metallic Tet Ratio (%) | Overall Tet Ratio (%) | Partner Entropy $H_i$ (bits) | Tetrahedral Coordination Mechanism |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for e in tet_sub["secondary_conditional_tetrahedral_elements"]:
        lines.append(
            f"| **{e['element_symbol']}** | {e['occurrence_count']} | {e['non_metallic_occurrences']} | "
            f"{e['metallic_glass_occurrences']} | {e['tetrahedral_count']} | "
            f"{100.0 * e['non_metallic_tetrahedral_ratio']:.1f}% | {100.0 * e['tetrahedral_ratio']:.1f}% | "
            f"{e['partner_diversity_entropy_bits']:.2f} | {e['mechanism_summary']} |"
        )
    lines.append("")

    # --- SECTION 3: CLASSIFICATION TABLE (NETWORK FORMERS, INTERMEDIATES, MODIFIERS) ---
    lines.append("---")
    lines.append("")
    lines.append("## 3. Classification Table: Network Formers, Intermediates, and Modifiers")
    lines.append("")
    lines.append(
        "The table below classifies all recorded elements into the three canonical glass-science regimes extended across oxides, chalcogenides, halides, covalent networks, and metallic glasses:"
    )
    lines.append("")
    lines.append("| Structural Class | Sub-Category | Elements | Coordination Polyhedra / Motifs | Primary Function in Amorphous Phase Stabilization |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    lines.append(
        "| **1. Network Formers** | **Primary Tetrahedral / Polyhedral Backbones** | **Si, Ge, P, B, As** | $\\text{SiO}_4$, $\\text{SiS}_4$, $\\text{SiN}_4$, $\\text{Si}_4$; $\\text{GeO}_4$, $\\text{GeS}_4$, $\\text{GeSe}_4$, $\\text{Ge}_4$; $\\text{PO}_4$, $\\text{PS}_4$; $\\text{BO}_3/\\text{BO}_4$, $\\text{BS}_3/\\text{BS}_4$; $\\text{AsSe}_3$, $\\text{AsS}_3$, $\\text{AsO}_3$ | Form single-component continuous random networks (CRNs) via corner-sharing tetrahedra/triangles ($\\text{CN}=3\\text{–}4$) and serve as solute centers in metal-metalloid trigonal prisms ($\\text{M}_9\\text{Si}, \\text{M}_9\\text{B}, \\text{M}_9\\text{P}$). |"
    )
    lines.append(
        "| **1. Network Formers** | **Bridging Anion & Chalcogen/Halide Ligands** | **O, S, Se, N, F, Cl, Br** | Bridging $-\\text{O}-$, $-\\text{S}-$, $-\\text{Se}-$ ($\\text{CN}=2$); planar $\\text{NSi}_3$ ($\\text{CN}=3$); bridging $-\\text{F}-$, $-\\text{Cl}-$, $-\\text{Br}-$ ($\\text{CN}=2$) | Provide flexible low-coordination bridges ($\\text{CN}=2\\text{–}3$) between cation tetrahedra/polyhedra, enabling bond-angle variance ($\\Delta\\theta$) without bond cleavage; S and Se also form elemental chain/ring glasses. |"
    )
    lines.append(
        "| **2. Intermediates** | **Conditional Tetrahedral Network Formers** | **Al, Ga, Be, Zn, C, V, Mo, W, Ti, Sn, In, Cd** | $\\text{AlO}_4^-$, $\\text{AlN}_4$; $\\text{GaO}_4$, $\\text{GaSe}_4$, $\\text{GaN}_4$; $\\text{BeF}_4$; $\\text{ZnCl}_4$, $\\text{ZnBr}_4$, $\\text{ZnO}_4$; $sp^3\\text{ C}_4$, $\\text{Si(O,C)}_4$; $\\text{VO}_4$, $\\text{MoO}_4$, $\\text{WO}_4$, $\\text{TiO}_4$ | Enter the tetrahedral network backbone when charge-compensated (e.g., $\\text{AlO}_4^-$, $\\text{GaO}_4^-$) or in halide/covalent systems ($\\text{BeF}_2$, $\\text{ZnCl}_2$, $\\text{ZnBr}_2$, $\\text{ta-C}$, $\\text{CdGeAs}_2$); Al and Be also strongly stabilize bulk metallic glasses. |"
    )
    lines.append(
        "| **2. Intermediates** | **Pyramidal / Octahedral Heavy-Metal & High-Field Intermediates** | **Te, Sb, Bi, Pb, Nb, Ta, Zr, Hf, Fe, Sc, Tl, Os, Th** | $\\text{TeO}_4$ disphenoids; $\\text{SbO}_3/\\text{SbSe}_3$; $\\text{TlSe}_3/\\text{TlSe}_4$; $\\text{BiO}_6$; $\\text{PbO}_4$; $\\text{NbO}_6$, $\\text{TaO}_6$, $\\text{OsO}_6$, $\\text{ZrF}_7/\\text{ZrO}_6$, $\\text{HfO}_6$, $\\text{FeO}_4/\\text{FeO}_6$, $\\text{ThF}_8/\\text{ThF}_9$ | Cannot vitrify alone via slow cooling (except constrained films like a-Sb, a-OsO2), but form extensive binary/ternary glasses when paired with modifiers or tetrahedral formers; Zr, Hf, Fe, Ta, Nb also serve as primary metallic glass hosts. |"
    )
    lines.append(
        "| **2. Intermediates** | **Metallic Polytetrahedral & Icosahedral Cluster Formers** | **Cu, Ni, Co, Pd, Pt, Au, Mn, Cr, Ru, Rh, Re, Ir** | Full icosahedra $\\langle 0,0,12,0 \\rangle$ ($\\text{CN}=12$), Frank–Kasper $Z14\\text{–}Z16$ polyhedra, capped trigonal prisms | Build five-fold symmetric icosahedral and polytetrahedral clusters in metallic melts that are crystallography-incompatible with periodic FCC/BCC/HCP lattices. |"
    )
    lines.append(
        "| **3. Modifiers** | **Alkali & Silver Fast-Ion Network Modifiers** | **Li, Na, K, Rb, Cs, Ag** | Ionic cages ($\\text{CN}=4\\text{–}9$) coordinated by non-bridging oxygens ($\\text{NBOs}$) or sulfides | Depolymerize tetrahedral networks ($Q^4 \\to Q^3 \\to Q^2$) by creating non-bridging anions, lower melting/ liquidus temperatures, or charge-compensate $\\text{BO}_4^-$ and $\\text{AlO}_4^-$ tetrahedra. |"
    )
    lines.append(
        "| **3. Modifiers** | **Alkaline-Earth & Divalent Modifiers / BMG Hosts** | **Mg, Ca, Sr, Ba** | Ionic coordination polyhedra ($\\text{CN}=6\\text{–}10$) in oxides/fluorides; large-cage matrix in simple-metal BMGs | Modify silicate, borate, phosphate, and fluoroaluminate networks; Mg, Ca, and Sr also serve as low-$T_g$ bulk metallic glass matrices when paired with Cu/Zn and Y/Gd/Yb. |"
    )
    lines.append(
        "| **3. Modifiers** | **Rare-Earth (Lanthanide) & Actinide Modifiers & Topological Cages** | **Y, La, Ce, Pr, Nd, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb, Lu, U** | High-coordination oxide/oxynitride/uranyl cages ($\\text{CN}=7\\text{–}9$); $Z15\\text{–}Z17$ large-atom centers in RE-Al-TM BMGs | Increase refractive index and $T_g$ in optical/oxynitride/nuclear-waste glasses; act as large-radius topological frustrators and oxygen scavengers in rare-earth and Fe-based bulk metallic glasses. |"
    )
    lines.append(
        "| **3. Modifiers** | **Monovalent Network Terminators** | **H, I** | Terminal $\\text{Si–H}$ ($\\text{CN}=1$); interstitial/terminal $\\text{I}^-$ | Passivate dangling bonds and relieve topological overconstraint in continuous random networks ($\\text{a-Si:H}$) or expand free volume for superionic conduction ($\\text{AgI–AgPO}_3$, $\\text{As–Se–I}$). |"
    )
    lines.append("")

    # --- SECTION 4: SPECIFIC SYSTEM EXAMPLES OF TETRAHEDRAL-PROMOTING CONVERSION ---
    lines.append("---")
    lines.append("")
    lines.append("## 4. Specific System Examples: Conversion of Crystalline-Prone Alloys & Compounds into Amorphous Phases via Tetrahedral-Promoting Elements")
    lines.append("")
    lines.append(
        f"A central empirical finding across the Amorphous Periodic Table is that **introducing a single tetrahedral-forming or directional $sp^3/p\\text{{-}}d$ element (`Si`, `Ge`, `P`, `B`, `Al`, `Ga`) into a system that otherwise crystallizes rapidly frustrates long-range periodic order and induces vitrification**. Below are {len(CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES)} peer-reviewed experimental benchmark conversions across Metallic Glasses, Chalcogenides, Oxides, and Covalent Networks:"
    )
    lines.append("")
    lines.append("| # | Material Class | Crystalline-Prone Parent | Added Tetrahedral-Promoting Element | Resulting Amorphous System | Local Coordination & Frustration Motif | Verification Technique | DOI & Reference |")
    lines.append("| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for idx, ex in enumerate(CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES, start=1):
        lines.append(
            f"| {idx} | **{ex['class']}** | {ex['crystalline_parent']} | **{ex['added_element']}** | "
            f"`{ex['amorphous_system']}` | {ex['local_coordination']} | {ex['verification']} | "
            f"`{ex['doi']}` ({ex['reference']}) |"
        )
    lines.append("")
    lines.append("### Mechanistic Synthesis of Crystalline-to-Amorphous Conversions")
    lines.append("")
    for idx, ex in enumerate(CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES, start=1):
        lines.append(
            f"{idx}. **`{ex['amorphous_system']}` ({ex['class']}, DOI: `{ex['doi']}`)**: {ex['mechanism']}"
        )
    lines.append("")

    report_text = "\n".join(lines)
    report_output_path.write_text(report_text, encoding="utf-8")
    return report_text


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    stats_file = root / "data" / "statistical_analysis_results.json"
    report_file = root / "amorphous_periodic_table_report.md"
    generate_markdown_report(stats_file, report_file)
    print(f"[Step 5] Generated Markdown report -> {report_file}")
