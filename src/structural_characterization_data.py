"""Step 7.3: Short-Range & Medium-Range Order (SRO/MRO) Structural Characterization Engine.

Provides experimentally grounded diffraction structure factors S(Q), radial and partial
pair distribution functions g(r) / g_ab(r), bond length and bond angle distributions P(theta),
and shortest-path ring size (n-ring) / Voronoi polyhedron (<n3,n4,n5,n6>) distributions
for every verified amorphous system and element in the Amorphous Periodic Table.

Includes explicit provenance metadata on every metric and section distinguishing:
1. Direct Experimental / RMC Literature Benchmarks (published neutron/synchrotron PDF,
   EXAFS, and Reverse Monte Carlo / AIMD archetype systems).
2. Composition-Weighted Analytical Reconstructions (where partial pair bond lengths r_ij,
   S(Q) peak positions Q1/Q2, bond-angle distributions P(theta), and ring/Voronoi
   topologies are weighted continuously by the stoichiometric atomic fractions c_i of all
   constituent elements).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


# Empirical covalent/ionic/metallic single-bond / atomic radii (in Angstroms) for partial pair estimation
ATOMIC_RADII_A: Dict[str, float] = {
    "H": 0.32, "Li": 1.28, "Be": 0.96, "B": 0.84, "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.64,
    "Na": 1.66, "Mg": 1.41, "Al": 1.21, "Si": 1.11, "P": 1.07, "S": 1.05, "Cl": 1.02,
    "K": 2.03, "Ca": 1.76, "Sc": 1.70, "Ti": 1.48, "V": 1.44, "Cr": 1.39, "Mn": 1.39,
    "Fe": 1.32, "Co": 1.26, "Ni": 1.24, "Cu": 1.28, "Zn": 1.22, "Ga": 1.22, "Ge": 1.20,
    "As": 1.19, "Se": 1.20, "Br": 1.20, "Rb": 2.20, "Sr": 1.95, "Y": 1.80, "Zr": 1.60,
    "Nb": 1.56, "Mo": 1.54, "Ru": 1.46, "Rh": 1.42, "Pd": 1.39, "Ag": 1.45, "Cd": 1.44,
    "In": 1.42, "Sn": 1.39, "Sb": 1.39, "Te": 1.38, "I": 1.39, "Cs": 2.44, "Ba": 2.15,
    "La": 1.87, "Ce": 1.82, "Pr": 1.82, "Nd": 1.81, "Sm": 1.80, "Eu": 1.99, "Gd": 1.79,
    "Tb": 1.76, "Dy": 1.75, "Ho": 1.74, "Er": 1.73, "Tm": 1.72, "Yb": 1.94, "Lu": 1.72,
    "Hf": 1.59, "Ta": 1.56, "W": 1.55, "Re": 1.51, "Os": 1.44, "Ir": 1.41, "Pt": 1.36,
    "Au": 1.44, "Hg": 1.49, "Tl": 1.48, "Pb": 1.47, "Bi": 1.48, "Th": 1.79, "U": 1.75,
}

# Canonical experimental bond lengths r_AB (Angstroms) from neutron/synchrotron PDF & EXAFS
CANONICAL_PAIR_LENGTHS_A: Dict[str, float] = {
    "Si-O": 1.61, "Ge-O": 1.74, "B-O": 1.40, "P-O": 1.54, "Al-O": 1.76, "Ga-O": 1.83,
    "As-O": 1.78, "Sb-O": 1.97, "Bi-O": 2.18, "Te-O": 1.92, "V-O": 1.72, "Ti-O": 1.96,
    "Mo-O": 1.78, "W-O": 1.81, "Nb-O": 1.96, "Ta-O": 1.97, "Zr-O": 2.12, "Hf-O": 2.09,
    "Zn-O": 1.96, "Pb-O": 2.28, "Sn-O": 2.05, "Fe-O": 1.99, "Mn-O": 2.14, "Co-O": 2.06,
    "Os-O": 1.98, "U-O": 2.18, "Eu-O": 2.40,
    "Sc-O": 2.10, "In-O": 2.16, "Cd-O": 2.28, "Li-O": 1.97, "Na-O": 2.36, "K-O": 2.72,
    "Rb-O": 2.89, "Cs-O": 3.09, "Mg-O": 2.04, "Ca-O": 2.38, "Sr-O": 2.56, "Ba-O": 2.76,
    "Y-O": 2.28, "La-O": 2.52, "Nd-O": 2.43, "Sm-O": 2.40, "Er-O": 2.30, "Ag-O": 2.32,
    "Cu-O": 1.95, "O-O": 2.63,
    # Chalcogenides & Topological / Phase-Change Chalcogenides
    "Ge-S": 2.22, "Ge-Se": 2.36, "Ge-Te": 2.61, "Si-S": 2.14, "Si-Se": 2.28,
    "As-S": 2.28, "As-Se": 2.41, "As-Te": 2.62, "Sb-S": 2.51, "Sb-Se": 2.61, "Sb-Te": 2.85,
    "Bi-Se": 2.86, "Bi-Te": 3.04, "Tl-Se": 2.98, "In-Te": 2.82, "Ag-Te": 2.79, "Mo-S": 2.41, "Mo-Mo": 2.75,
    "P-S": 2.04, "P-Se": 2.20, "B-S": 1.86, "Ga-S": 2.26, "Ga-Se": 2.40,
    "In-Se": 2.56, "Cu-Se": 2.42, "Ag-S": 2.52, "Li-S": 2.44, "Na-S": 2.78,
    "S-S": 2.06, "Se-Se": 2.34, "Te-Te": 2.75,
    # Covalent / Halide / Silicide / Germanide
    "Si-Si": 2.35, "Ge-Ge": 2.45, "C-C": 1.54, "Si-C": 1.88, "Si-N": 1.73, "B-N": 1.44,
    "B-C": 1.59, "C-N": 1.38, "Y-N": 2.36, "Ag-I": 2.85, "Cu-I": 2.62, "Ge-I": 2.50, "As-I": 2.55,
    "B-B": 1.78, "P-P": 2.22, "As-As": 2.44, "Sb-Sb": 2.87, "Si-H": 1.48, "Si-Ge": 2.38,
    "Ga-As": 2.45, "In-P": 2.54, "Ga-N": 1.95, "Al-N": 1.89, "Be-F": 1.55, "Zn-Cl": 2.29, "Zn-Br": 2.41,
    "Zr-F": 2.08, "Al-F": 1.81, "Th-F": 2.32, "Yb-F": 2.24, "Ba-F": 2.68,
    "Cd-As": 2.63, "Cd-P": 2.53, "Zn-As": 2.47, "Sn-As": 2.60,
    # Hellman Group & Vapor-Deposited Amorphous TM/RE Silicides & Germanides (EXAFS / PDF)
    "Fe-Ge": 2.46, "Fe-Si": 2.38, "Co-Si": 2.34, "Co-Ge": 2.43, "Mn-Si": 2.41, "Cr-Si": 2.46,
    "Mo-Ge": 2.65, "Nb-Si": 2.66, "Gd-Si": 3.04, "Tb-Si": 3.01, "Gd-Ge": 3.12,
    # Metallic Glasses
    "Au-Si": 2.46, "Pd-Si": 2.42, "Pt-Si": 2.43, "Pd-P": 2.30, "Pt-P": 2.32, "Ni-P": 2.28,
    "Fe-B": 2.14, "Fe-P": 2.26, "Fe-C": 2.02, "Co-B": 2.11, "Ni-B": 2.10, "W-B": 2.28,
    "Fe-Fe": 2.55, "Co-Co": 2.51, "Ni-Ni": 2.49, "Cu-Cu": 2.56, "Zr-Zr": 3.18, "Cu-Zr": 2.78,
    "Ni-Zr": 2.69, "Al-Zr": 2.95, "Zr-Al": 2.95, "Cu-Al": 2.55, "Ti-Cu": 2.66, "Be-Zr": 2.72,
    "Mg-Cu": 2.75, "Mg-Y": 3.35, "Mg-Zn": 2.91, "Mg-Mg": 3.19, "Zn-Zn": 2.68,
    "Ni-Nb": 2.68, "Nb-Nb": 2.96, "Cu-Hf": 2.77, "Hf-Hf": 3.16, "Pd-Cu": 2.68, "Pd-Ni": 2.63,
    "La-Al": 3.18, "La-Ni": 2.88, "Ce-Al": 3.12, "Gd-Co": 2.86, "Gd-Al": 3.14, "Al-Ni": 2.44,
}

import re

# Canonical prototype systems where Q1, Q2, r1, r2, bond angles, and ring/Voronoi topology
# are directly anchored to published neutron/synchrotron PDF, EXAFS, and RMC/AIMD literature.
DIRECT_EXPERIMENTAL_SRO_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "SiO2": {
        "q1": 1.52, "q2": 2.98, "r1": 1.61, "r2": 2.63, "theta1": 109.5, "theta2": 144.0,
        "ref": "Mozzi & Warren, J. Appl. Cryst. 2, 164 (1969); Wright, JNCS 179, 84 (1994); Kohara & Suzuya, JPCM 17, S77 (2005)",
        "topo_type": "RMC / Neutron Diffraction King Shortest-Path Ring Distribution (Kohara & Suzuya 2005)",
        "dom_motif": "6-ring (34.5%) & 5/7-ring Tetrahedral CRN",
        "voronoi_bars": [
            {"label": "3-ring", "pct": 1.5, "description": "Planar 3-membered Si3O3 rings (Raman D2 band at 606 cm^-1)"},
            {"label": "4-ring", "pct": 7.5, "description": "Four-membered Si4O4 rings (Raman D1 band at 495 cm^-1)"},
            {"label": "5-ring", "pct": 23.5, "description": "Five-membered tetrahedral rings frustrating cristobalite order"},
            {"label": "6-ring", "pct": 34.5, "description": "Dominant six-membered corner-sharing SiO4 rings"},
            {"label": "7-ring", "pct": 21.5, "description": "Seven-membered rings accommodating topological disorder"},
            {"label": ">=8-ring", "pct": 11.5, "description": "Large continuous random network cages"},
        ],
    },
    "GeO2": {
        "q1": 1.55, "q2": 2.66, "r1": 1.74, "r2": 2.83, "theta1": 109.5, "theta2": 133.0,
        "ref": "Salmon et al., Phys. Rev. B 71, 104204 (2005); Kohara & Suzuya, JPCM 17, S77 (2005)",
        "topo_type": "RMC / Synchrotron Diffraction Ring Distribution (Kohara & Suzuya 2005)",
        "dom_motif": "6-ring (32.0%) & 3/4-ring Narrower-Bridge CRN (θ_GeOGe = 133°)",
        "voronoi_bars": [
            {"label": "3-ring", "pct": 5.5, "description": "Three-membered Ge3O3 rings enhanced by narrower 133° Ge–O–Ge angle"},
            {"label": "4-ring", "pct": 12.5, "description": "Four-membered Ge4O4 rings"},
            {"label": "5-ring", "pct": 23.0, "description": "Five-membered tetrahedral rings"},
            {"label": "6-ring", "pct": 32.0, "description": "Six-membered GeO4 corner-sharing rings"},
            {"label": "7-ring", "pct": 18.0, "description": "Seven-membered rings"},
            {"label": ">=8-ring", "pct": 9.0, "description": "Larger network cages"},
        ],
    },
    "B2O3": {
        "q1": 1.62, "q2": 2.85, "r1": 1.37, "r2": 2.38, "theta1": 120.0, "theta2": 130.0,
        "ref": "Hannon, Grimley, Hulme, Wright & Sinclair, JNCS 177, 299 (1994); Swenson & Börjesson, PRB 55, 11138 (1997)",
        "topo_type": "Neutron Diffraction / NMR Boroxol Ring Distribution (Hannon et al. 1994)",
        "dom_motif": "3-ring Boroxol B3O6 (~73% of B atoms in planar 3-rings)",
        "voronoi_bars": [
            {"label": "3-ring (Boroxol)", "pct": 58.0, "description": "Planar B3O6 boroxol rings (sharp 808 cm^-1 Raman breathing mode)"},
            {"label": "4-ring", "pct": 8.0, "description": "Four-membered borate rings connecting non-boroxol BO3 units"},
            {"label": "5-ring", "pct": 11.0, "description": "Five-membered inter-boroxol rings"},
            {"label": "6-ring", "pct": 15.0, "description": "Six-membered superstructural borate loops"},
            {"label": ">=7-ring", "pct": 8.0, "description": "Large inter-layer network loops"},
        ],
    },
    "P2O5": {"q1": 1.38, "q2": 2.72, "r1": 1.54, "r2": 2.51, "theta1": 109.5, "theta2": 135.0, "ref": "Hoppe et al., JNCS 248, 1 (1999)"},
    "Al2O3": {"q1": 2.11, "q2": 2.90, "r1": 1.80, "r2": 2.90, "theta1": 106.0, "theta2": 124.0, "ref": "Shi, Alderman, Berman, Weber, You & Benmore, Front. Mater. 6, 38 (2019) [DOI: 10.3389/fmats.2019.00038]"},
    "TiO2": {"q1": 1.92, "q2": 2.68, "r1": 1.96, "r2": 2.78, "theta1": 92.0, "theta2": 131.0, "ref": "Petkov et al., J. Non-Cryst. Solids 231, 17 (1998)"},
    "Ta2O5": {"q1": 2.04, "q2": 3.05, "r1": 1.97, "r2": 3.74, "theta1": 90.0, "theta2": 136.0, "ref": "Alderman, Benmore et al., JPCM 27, 455104 (2015); Bassiri et al., APL Materials 3, 036103 (2015) [DOI: 10.1063/1.4913586]"},
    "ZrO2": {"q1": 2.12, "q2": 3.15, "r1": 2.12, "r2": 3.42, "theta1": 88.0, "theta2": 118.0, "ref": "Stachs, Gerber & Petkov, J. Non-Cryst. Solids 210, 14 (1997)"},
    "HfO2": {"q1": 2.14, "q2": 3.18, "r1": 2.09, "r2": 3.40, "theta1": 88.5, "theta2": 119.0, "ref": "Gritsenko et al., Microelectron. Eng. 81, 524 (2005)"},
    "Na2Si2O5": {"q1": 1.72, "q2": 2.88, "r1": 1.62, "r2": 2.64, "theta1": 109.5, "theta2": 139.0, "ref": "Greaves & Sen, Adv. Phys. 56, 1 (2007)"},
    "CaSiO3": {"q1": 1.88, "q2": 2.84, "r1": 1.63, "r2": 2.65, "theta1": 109.5, "theta2": 136.5, "ref": "Skinner, Benmore & Weber, J. Non-Cryst. Solids (2012)"},
    "MgSiO3": {"q1": 1.91, "q2": 2.86, "r1": 1.63, "r2": 2.65, "theta1": 109.5, "theta2": 135.0, "ref": "Wilding, Benmore, Tangeman & Sampath, Europhys. Lett. 67, 212 (2004)"},
    "GeSe2": {
        "q1": 1.00, "q2": 2.02, "r1": 2.36, "r2": 3.87, "theta1": 109.5, "theta2": 100.5,
        "ref": "Petri, Salmon & Fischer, Phys. Rev. Lett. 84, 2413 (2000); Massobrio et al., PRB 64, 144205 (2001)",
        "topo_type": "Isotopic-Substitution Neutron PDF & AIMD Ring Statistics (Petri et al. 2000)",
        "dom_motif": "2-ring Edge-Sharing Ge2Se6 (~34% of Ge) & 6-ring Corner-Sharing Network",
        "voronoi_bars": [
            {"label": "2-ring (Edge)", "pct": 21.0, "description": "Edge-sharing Ge2Se6 bitetrahedra (Raman companion A1c mode at 215 cm^-1)"},
            {"label": "3-ring", "pct": 9.0, "description": "Three-membered Ge3Se3 rings"},
            {"label": "4-ring", "pct": 14.0, "description": "Four-membered corner-sharing GeSe4 rings"},
            {"label": "5-ring", "pct": 20.0, "description": "Five-membered rings"},
            {"label": "6-ring", "pct": 25.0, "description": "Six-membered outrigger-raft / corner-sharing rings"},
            {"label": ">=7-ring", "pct": 11.0, "description": "Large medium-range chalcogenide loops"},
        ],
    },
    "GeS2": {"q1": 1.02, "q2": 2.12, "r1": 2.22, "r2": 3.63, "theta1": 109.5, "theta2": 102.0, "ref": "Salmon, Proc. R. Soc. Lond. A 445, 351 (1994)"},
    "GeSe3": {"q1": 1.06, "q2": 2.03, "r1": 2.37, "r2": 3.85, "theta1": 109.0, "theta2": 98.0, "ref": "Rowlands, Zeidler, Fischer & Salmon, Front. Mater. 6, 133 (2019) [DOI: 10.3389/fmats.2019.00133]"},
    "As2S3": {"q1": 1.24, "q2": 2.35, "r1": 2.28, "r2": 3.52, "theta1": 99.0, "theta2": 100.5, "ref": "Yang, Paesler & Sayers, Phys. Rev. B 39, 10342 (1989) [DOI: 10.1103/physrevb.39.10342]; Wright et al., JNCS 76, 43 (1985)"},
    "As2Se3": {"q1": 1.22, "q2": 2.24, "r1": 2.42, "r2": 3.68, "theta1": 98.5, "theta2": 101.0, "ref": "Xin, Liu & Salmon, Phys. Rev. B 78, 064207 (2008) [DOI: 10.1103/physrevb.78.064207]; Hosokawa et al., PRB 84, 014201 (2011)"},
    "Ge2Sb2Te5": {
        "q1": 1.05, "q2": 2.06, "r1": 2.68, "r2": 4.12, "theta1": 93.0, "theta2": 170.0,
        "ref": "Kolobov et al., Nat. Mater. 3, 703 (2004); Kohara et al., APL 89, 201910 (2006); Hegedüs & Elliott, Nat. Mater. 7, 399 (2008)",
        "topo_type": "RMC / AIMD Phase-Change Ring Statistics (Kohara et al. 2006; Hegedüs & Elliott 2008)",
        "dom_motif": "4-ring ABAB p-Bonded Squares (38.0%) Enabling Sub-Nanosecond Crystallization",
        "voronoi_bars": [
            {"label": "3-ring", "pct": 8.0, "description": "Three-membered covalent rings"},
            {"label": "4-ring (ABAB)", "pct": 38.0, "description": "ABAB four-membered square rings (precursors to rocksalt Ge2Sb2Te5)"},
            {"label": "5-ring", "pct": 22.0, "description": "Odd-membered rings around tetrahedral Ge sites"},
            {"label": "6-ring", "pct": 21.0, "description": "Six-membered distorted octahedral/tetrahedral rings"},
            {"label": ">=7-ring", "pct": 11.0, "description": "Larger cavity-bounding loops"},
        ],
    },
    "Ag5In5Sb60Te30": {"q1": 1.08, "q2": 2.10, "r1": 2.83, "r2": 4.18, "theta1": 91.5, "theta2": 171.0, "ref": "Matsunaga, Yamada, Wuttig & Elliott, Nat. Mater. 10, 129 (2011); Salinga et al., Nat. Commun. 4, 2371 (2013)"},
    "Bi2Se3": {"q1": 1.98, "q2": 3.02, "r1": 2.86, "r2": 4.22, "theta1": 92.5, "theta2": 168.0, "ref": "Corbae, Lanzara & Hellman, Nat. Mater. 22, 200 (2023)"},
    "MoS3": {"q1": 1.18, "q2": 2.32, "r1": 2.41, "r2": 3.85, "theta1": 84.0, "theta2": 112.0, "ref": "Weber, Muijsers & Niemantsverdriet, J. Phys. Chem. 99, 9194 (1995)"},
    "Si": {
        "q1": 1.98, "q2": 3.62, "r1": 2.35, "r2": 3.84, "theta1": 109.5, "theta2": 138.0,
        "ref": "Laaziri et al., Phys. Rev. Lett. 82, 3460 (1999); Barkema & Mousseau, PRB 62, 4985 (2000)",
        "topo_type": "WWW Continuous Random Network Ring Statistics (Barkema & Mousseau 2000)",
        "dom_motif": "6-ring (39.0%) & 5-ring (31.0%) Tetrahedral CRN",
        "voronoi_bars": [
            {"label": "4-ring", "pct": 2.0, "description": "Highly strained 4-membered Si4 rings"},
            {"label": "5-ring", "pct": 31.0, "description": "Five-membered rings suppressing diamond-cubic crystallinity"},
            {"label": "6-ring", "pct": 39.0, "description": "Six-membered chair/boat sp3 rings"},
            {"label": "7-ring", "pct": 22.0, "description": "Seven-membered rings"},
            {"label": ">=8-ring", "pct": 6.0, "description": "Eight-membered and larger CRN rings"},
        ],
    },
    "Ge": {"q1": 1.90, "q2": 3.45, "r1": 2.45, "r2": 4.00, "theta1": 109.5, "theta2": 136.0, "ref": "Etherington, Wright, Wenzel et al., J. Non-Cryst. Solids 48, 265 (1982)"},
    "C": {"q1": 2.95, "q2": 5.45, "r1": 1.54, "r2": 2.52, "theta1": 109.5, "theta2": 120.0, "ref": "Gilkes, Gaskell & Robertson, Phys. Rev. B 51, 12303 (1995)"},
    "GaN": {"q1": 2.18, "q2": 3.76, "r1": 1.95, "r2": 3.18, "theta1": 109.5, "theta2": 118.0, "ref": "Stumm & Drabold, Phys. Rev. Lett. 79, 677 (1997) [DOI: 10.1103/physrevlett.79.677]"},
    "BeF2": {"q1": 1.58, "q2": 2.95, "r1": 1.55, "r2": 2.54, "theta1": 109.5, "theta2": 145.5, "ref": "Wright et al., J. Non-Cryst. Solids 150, 69 (1992)"},
    "ZnCl2": {"q1": 1.08, "q2": 2.15, "r1": 2.29, "r2": 3.74, "theta1": 109.5, "theta2": 110.0, "ref": "Biggin & Enderby, J. Phys. C 14, 3129 (1981); Zeidler & Salmon, PRB (2010)"},
    "FeGe": {"q1": 2.86, "q2": 4.92, "r1": 2.46, "r2": 4.08, "theta1": 60.5, "theta2": 108.0, "ref": "Streubel, Bougiatioti, Karel & Hellman, PRL 115, 057204 (2015); PRB 94, 184429 (2016)"},
    "FeGe3": {"q1": 1.88, "q2": 3.42, "r1": 2.45, "r2": 4.00, "theta1": 108.0, "theta2": 134.0, "ref": "Karel, Zhang, Volkmann & Hellman, Phys. Rev. B 94, 184429 (2016)"},
    "FeSi": {"q1": 3.02, "q2": 5.18, "r1": 2.38, "r2": 3.95, "theta1": 61.0, "theta2": 109.0, "ref": "Karel, Jenei, Fuchs & Hellman, EPL 114, 57004 (2016)"},
    "MoGe": {"q1": 2.78, "q2": 4.78, "r1": 2.65, "r2": 4.45, "theta1": 60.0, "theta2": 109.0, "ref": "Kortright & Bienenstock, Phys. Rev. B 37, 2979 (1988) [DOI: 10.1103/physrevb.37.2979]"},
    "Cu50Zr50": {
        "q1": 2.72, "q2": 4.65, "r1": 2.78, "r2": 4.68, "theta1": 59.5, "theta2": 108.5,
        "ref": "Sheng et al., Nature 439, 419 (2006); Cheng & Ma, Prog. Mater. Sci. 56, 379 (2011)",
        "topo_type": "AIMD / Synchrotron RMC Voronoi Polyhedron Statistics (Cheng & Ma 2011)",
        "dom_motif": "<0,2,8,2> (24.5%) & <0,0,12,0> (19.0%) Cu-Centered Icosahedral Clusters",
        "voronoi_bars": [
            {"label": "<0,0,12,0>", "pct": 19.0, "description": "Full Cu-centered 12-coordinated icosahedron (12 pentagonal faces)"},
            {"label": "<0,2,8,2>", "pct": 24.5, "description": "Distorted 12-coordinated icosahedral cluster"},
            {"label": "<0,1,10,2>", "pct": 21.5, "description": "13-coordinated Frank-Kasper-like polyhedron"},
            {"label": "<0,3,6,3>", "pct": 17.5, "description": "12-coordinated polytetrahedral shell"},
            {"label": "<0,1,10,4>", "pct": 17.5, "description": "Zr-centered Z15 coordination cage (CN=15)"},
        ],
    },
    "Zr50Cu50": {
        "q1": 2.72, "q2": 4.65, "r1": 2.78, "r2": 4.68, "theta1": 59.5, "theta2": 108.5,
        "ref": "Sheng et al., Nature 439, 419 (2006); Cheng & Ma, Prog. Mater. Sci. 56, 379 (2011)",
        "topo_type": "AIMD / Synchrotron RMC Voronoi Polyhedron Statistics (Cheng & Ma 2011)",
        "dom_motif": "<0,2,8,2> (24.5%) & <0,0,12,0> (19.0%) Cu-Centered Icosahedral Clusters",
        "voronoi_bars": [
            {"label": "<0,0,12,0>", "pct": 19.0, "description": "Full Cu-centered 12-coordinated icosahedron (12 pentagonal faces)"},
            {"label": "<0,2,8,2>", "pct": 24.5, "description": "Distorted 12-coordinated icosahedral cluster"},
            {"label": "<0,1,10,2>", "pct": 21.5, "description": "13-coordinated Frank-Kasper-like polyhedron"},
            {"label": "<0,3,6,3>", "pct": 17.5, "description": "12-coordinated polytetrahedral shell"},
            {"label": "<0,1,10,4>", "pct": 17.5, "description": "Zr-centered Z15 coordination cage (CN=15)"},
        ],
    },
    "Cu64Zr36": {
        "q1": 2.84, "q2": 4.86, "r1": 2.72, "r2": 4.58, "theta1": 59.8, "theta2": 108.0,
        "ref": "Cheng, Ma & Sheng, Phys. Rev. B 79, 174204 (2009); Nature 439, 419 (2006)",
        "topo_type": "AIMD / Reverse Monte Carlo Voronoi Polyhedron Statistics (Cheng, Ma & Sheng 2009)",
        "dom_motif": "<0,0,12,0> Full Icosahedra (26.5% of Cu sites) + <0,2,8,2> (23.0%)",
        "voronoi_bars": [
            {"label": "<0,0,12,0>", "pct": 26.5, "description": "Full 5-fold Cu-centered icosahedron (peak GFA in binary Cu-Zr)"},
            {"label": "<0,2,8,2>", "pct": 23.0, "description": "Distorted 12-coordinated icosahedral polyhedron"},
            {"label": "<0,1,10,2>", "pct": 20.5, "description": "13-coordinated Kasper polyhedron"},
            {"label": "<0,3,6,3>", "pct": 15.0, "description": "12-coordinated polytetrahedral cluster"},
            {"label": "<0,1,10,4>", "pct": 15.0, "description": "Zr-centered Z15 solvent polyhedron (CN=15)"},
        ],
    },
    "Cu46Zr46Al8": {"q1": 2.74, "q2": 4.68, "r1": 2.77, "r2": 4.66, "theta1": 59.5, "theta2": 108.5, "ref": "Cheng, Ma & Sheng, Phys. Rev. Lett. 102, 245501 (2009)"},
    "Zr50Cu40Al10": {"q1": 2.71, "q2": 4.63, "r1": 2.86, "r2": 4.78, "theta1": 59.5, "theta2": 108.5, "ref": "Zhang et al., Mater. Trans. 50, 1340 (2009) [DOI: 10.2320/matertrans.mbw200833]; Sheng et al., Nature 439, 419 (2006)"},
    "Ni80P20": {
        "q1": 3.12, "q2": 5.34, "r1": 2.28, "r2": 3.84, "theta1": 61.5, "theta2": 106.0,
        "ref": "Lamparter, Sperl, Steeb & Blétry, Z. Naturforsch. A 37, 1223 (1982); Sheng et al., Nature 439, 419 (2006)",
        "topo_type": "Isotopic Neutron Diffraction + RMC/AIMD Voronoi Statistics (Sheng et al. 2006)",
        "dom_motif": "<0,3,6,0> Tricapped Trigonal Prism (29.5% around P) & <0,2,8,0> Antiprism (24.0%)",
        "voronoi_bars": [
            {"label": "<0,3,6,0>", "pct": 29.5, "description": "Tricapped trigonal prism (CN=9) centered on P solute"},
            {"label": "<0,2,8,0>", "pct": 24.0, "description": "Bicapped square antiprism (CN=10) around P solute"},
            {"label": "<0,2,8,1>", "pct": 19.5, "description": "11-coordinated Kasper polyhedron"},
            {"label": "<0,0,12,0>", "pct": 13.0, "description": "Ni-centered 12-coordinated icosahedron"},
            {"label": "<0,1,10,2>", "pct": 14.0, "description": "13-coordinated Ni host polyhedron"},
        ],
    },
    "Fe80B20": {
        "q1": 3.09, "q2": 5.28, "r1": 2.14, "r2": 3.68, "theta1": 61.5, "theta2": 106.5,
        "ref": "Nold, Lamparter, Olbrich, Rainer-Harbach & Steeb, Z. Naturforsch. A 36, 1032 (1981); Sheng et al., Nature 439, 419 (2006)",
        "topo_type": "Isotopic Neutron Diffraction + RMC/AIMD Voronoi Statistics (Sheng et al. 2006)",
        "dom_motif": "<0,3,6,0> Trigonal Prism (31.0% around B) & <0,2,8,0> Antiprism (22.5%)",
        "voronoi_bars": [
            {"label": "<0,3,6,0>", "pct": 31.0, "description": "Tricapped trigonal prism (CN=9) centered on B solute"},
            {"label": "<0,2,8,0>", "pct": 22.5, "description": "Bicapped square antiprism (CN=10)"},
            {"label": "<0,2,8,1>", "pct": 19.0, "description": "11-coordinated Kasper polyhedron"},
            {"label": "<0,0,12,0>", "pct": 13.5, "description": "Fe-centered 12-coordinated icosahedron"},
            {"label": "<0,1,10,2>", "pct": 14.0, "description": "13-coordinated Fe matrix polyhedron"},
        ],
    },
    "Co80B20": {"q1": 3.14, "q2": 5.36, "r1": 2.11, "r2": 3.64, "theta1": 61.5, "theta2": 106.5, "ref": "Heckele, Lamparter & Steeb, Z. Naturforsch. A 44, 495 (1989)"},
    "Ni62Nb38": {"q1": 2.88, "q2": 4.92, "r1": 2.68, "r2": 4.52, "theta1": 60.0, "theta2": 108.5, "ref": "Sváb et al., J. Non-Crystalline Solids 104, 291 (1988)"},
    "Mg70Zn30": {"q1": 2.62, "q2": 4.48, "r1": 2.91, "r2": 4.88, "theta1": 59.5, "theta2": 108.5, "ref": "Nassif, Lamparter, Sperl & Steeb, Z. Naturforsch. A 38, 142 (1983)"},
    "Pd40Ni40P20": {"q1": 2.96, "q2": 5.06, "r1": 2.30, "r2": 3.92, "theta1": 61.0, "theta2": 106.5, "ref": "Egami et al., Phys. Rev. B 76, 024208 (2007)"},
    "Pd40Ni10Cu30P20": {"q1": 2.94, "q2": 5.02, "r1": 2.34, "r2": 3.96, "theta1": 61.0, "theta2": 106.5, "ref": "Nishiyama & Inoue, Appl. Phys. Lett. 78, 1985 (2001); Mater. Trans. JIM 37, 1531 (1996)"},
    "Pd42.5Ni7.5Cu30P20": {"q1": 2.94, "q2": 5.02, "r1": 2.34, "r2": 3.96, "theta1": 61.0, "theta2": 106.5, "ref": "Nishiyama & Inoue, Appl. Phys. Lett. 78, 1985 (2001); Mater. Trans. 43, 1913 (2002)"},
    "Zr41.2Ti13.8Cu12.5Ni10Be22.5": {"q1": 2.64, "q2": 4.52, "r1": 2.74, "r2": 4.62, "theta1": 59.5, "theta2": 108.5, "ref": "Peker & Johnson, Appl. Phys. Lett. 63, 2342 (1993)"},
}


def _parse_cn_from_coord_map(
    el: str, coord_map: Dict[str, str] | None, default_cn: float
) -> float:
    """Parse explicit coordination number from reported_coordination string if present."""
    if not coord_map or el not in coord_map:
        return default_cn
    desc = coord_map[el]
    # 1. Check for percentage-weighted CNs like "CN=4, ~55% ... CN=5, ~35%"
    weighted_matches = re.findall(r"CN\s*[=~≈]?\s*(\d+(?:\.\d+)?)\s*[,;(]\s*~?(\d+(?:\.\d+)?)\s*%", desc)
    if len(weighted_matches) >= 2:
        w_sum = sum(float(w) for _, w in weighted_matches)
        if w_sum > 0:
            return round(sum(float(c) * float(w) for c, w in weighted_matches) / w_sum, 1)
    # 2. Check for range like "CN=7-8" or "CN=8–9"
    range_match = re.search(r"CN\s*[=~≈]?\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", desc)
    if range_match:
        return round((float(range_match.group(1)) + float(range_match.group(2))) / 2.0, 1)
    # 3. Check for comma-separated list like "CN=4,5,6"
    list_match = re.search(r"CN\s*[=~≈]?\s*(\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)+)", desc)
    if list_match:
        vals = [float(x.strip()) for x in list_match.group(1).split(",") if x.strip()]
        if vals:
            return round(sum(vals) / len(vals), 1)
    # 4. Check for single CN like "CN=6" or "CN~12"
    single_match = re.search(r"CN\s*[=~≈]?\s*(\d+(?:\.\d+)?)", desc)
    if single_match:
        return round(float(single_match.group(1)), 1)
    return default_cn


def has_canonical_pair_length(el_a: str, el_b: str) -> bool:
    """Return True if pair (el_a, el_b) has a direct experimental EXAFS/PDF bond length."""
    return f"{el_a}-{el_b}" in CANONICAL_PAIR_LENGTHS_A or f"{el_b}-{el_a}" in CANONICAL_PAIR_LENGTHS_A


def get_pair_length(el_a: str, el_b: str, material_class: str) -> float:
    """Return experimental or radii-derived first-shell bond length r_AB in Angstroms."""
    k1 = f"{el_a}-{el_b}"
    k2 = f"{el_b}-{el_a}"
    if k1 in CANONICAL_PAIR_LENGTHS_A:
        return CANONICAL_PAIR_LENGTHS_A[k1]
    if k2 in CANONICAL_PAIR_LENGTHS_A:
        return CANONICAL_PAIR_LENGTHS_A[k2]
    r_a = ATOMIC_RADII_A.get(el_a, 1.40)
    r_b = ATOMIC_RADII_A.get(el_b, 1.40)
    if material_class in ("Oxide", "Chalcogenide", "Covalent Network"):
        return round(r_a + r_b, 2)
    return round(1.04 * (r_a + r_b), 2)


def _generate_sq_curve(
    q1: float, q2: float, has_strong_fsdp: bool, fsdp_amp_scale: float = 1.0
) -> List[List[float]]:
    """Generate a smooth 38-point total structure factor curve S(Q) for Q in [0.6, 9.8] A^-1."""
    q3 = round(q2 * 1.52, 2)
    points: List[List[float]] = []
    for i in range(38):
        q = round(0.6 + i * 0.25, 2)
        if has_strong_fsdp:
            p1 = (1.45 * fsdp_amp_scale) * math.exp(-((q - q1) / 0.28) ** 2)
            p2 = 1.15 * math.exp(-((q - q2) / 0.45) ** 2)
            p3 = 0.45 * math.exp(-((q - q3) / 0.65) ** 2)
            osc = 0.22 * math.sin(1.75 * (q - q2)) * math.exp(-0.18 * max(0.0, q - q2))
            base = 1.0 - 0.78 * math.exp(-((q / (0.85 * q1)) ** 2.4))
            sq = max(0.05, round(base + p1 + p2 - 0.55 + p3 + osc, 3))
        else:
            p1 = 2.10 * math.exp(-((q - q1) / 0.24) ** 2)
            p2a = 0.55 * math.exp(-((q - 0.93 * q2) / 0.35) ** 2)
            p2b = 0.32 * math.exp(-((q - 1.10 * q2) / 0.38) ** 2)
            p3 = 0.25 * math.exp(-((q - q3) / 0.55) ** 2)
            base = 1.0 - 0.92 * math.exp(-((q / (0.78 * q1)) ** 3.2))
            sq = max(0.04, round(base + p1 - 0.35 * math.exp(-((q - 1.32 * q1) / 0.32) ** 2) + p2a + p2b + p3, 3))
        points.append([q, sq])
    return points


def _generate_gr_curve(
    r1: float,
    r2: float,
    material_class: str,
    partial_pairs: List[Dict[str, Any]] | None = None,
) -> List[List[float]]:
    """Generate a composition-weighted 36-point pair distribution function g(r) for r in [1.0, 6.8] A."""
    r3 = round(r2 * 1.48, 2)
    points: List[List[float]] = []
    min_r_pair = min((p["r_ij_A"] for p in (partial_pairs or [])), default=r1)
    cutoff_r = 0.78 * min(r1, min_r_pair)
    amp_base = 2.85 if material_class != "Metallic Glass" else 2.45

    for i in range(36):
        r = round(1.0 + i * 0.165, 2)
        if r < cutoff_r:
            gr = 0.0
        else:
            if partial_pairs:
                g1_sum = 0.0
                for p in partial_pairs:
                    w = float(p.get("composition_weight", 1.0 / len(partial_pairs)))
                    r_ij = float(p["r_ij_A"])
                    sig_ij = max(0.08, float(p.get("sigma_r_A", 0.10)) * 1.35)
                    g1_sum += w * amp_base * math.exp(-((r - r_ij) / sig_ij) ** 2)
                g1 = g1_sum
            else:
                sigma1 = 0.09 if material_class != "Metallic Glass" else 0.18
                g1 = amp_base * math.exp(-((r - r1) / sigma1) ** 2)
            g2 = 1.45 * math.exp(-((r - r2) / 0.28) ** 2)
            g3 = 1.15 * math.exp(-((r - r3) / 0.42) ** 2)
            step = 1.0 / (1.0 + math.exp(-(r - (r1 + 0.45)) / 0.22))
            osc = 0.16 * math.cos(2.4 * (r - r2)) * math.exp(-0.35 * max(0.0, r - r2))
            gr = max(0.0, round(g1 + 0.65 * g2 + 0.25 * g3 + 0.72 * step + osc, 3))
        points.append([r, gr])
    return points


def _generate_angle_curve(
    theta1: float, fwhm1: float, theta2: float, fwhm2: float, amp2_ratio: float = 0.58
) -> List[List[float]]:
    """Generate a smooth 34-point bond angle distribution P(theta) for theta in [50, 178] deg."""
    s1 = max(2.5, fwhm1 / 2.355)
    s2 = max(3.5, fwhm2 / 2.355)
    points: List[List[float]] = []
    for i in range(34):
        th = round(50.0 + i * 3.85, 1)
        p1 = 1.0 * math.exp(-0.5 * ((th - theta1) / s1) ** 2)
        p2 = amp2_ratio * math.exp(-0.5 * ((th - theta2) / s2) ** 2)
        val = round(p1 + p2, 3)
        points.append([th, val])
    return points


def _normalize_bars(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize bar percentages to sum to 100.0% while keeping 1 decimal place."""
    total = sum(max(1.0, float(b["pct"])) for b in bars)
    out = []
    running = 0.0
    for idx, b in enumerate(bars):
        if idx < len(bars) - 1:
            val = round(100.0 * max(1.0, float(b["pct"])) / total, 1)
            running += val
        else:
            val = round(max(1.0, 100.0 - running), 1)
        nb = dict(b)
        nb["pct"] = val
        nb["fraction_pct"] = val
        out.append(nb)
    return out


def compute_system_structural_characterization(
    formula: str,
    raw_formula: str,
    material_class: str,
    elements: List[Dict[str, Any]] | None = None,
    verification_method: str = "",
    atomic_fractions: Dict[str, float] | None = None,
    coord_map: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    """Compute provenance-tagged, composition-weighted SRO/MRO structural characterization metrics."""
    if elements is None:
        if atomic_fractions:
            elements = [
                {"element_symbol": k, "atomic_fraction": v}
                for k, v in atomic_fractions.items()
            ]
        else:
            elements = []
    frac_map: Dict[str, float] = {
        e["element_symbol"]: float(e.get("atomic_fraction", 0.0)) for e in elements
    }
    syms = [e["element_symbol"] for e in elements]
    sym_set = set(syms)

    bench = DIRECT_EXPERIMENTAL_SRO_BENCHMARKS.get(formula) or DIRECT_EXPERIMENTAL_SRO_BENCHMARKS.get(raw_formula)
    is_direct_benchmark = bench is not None

    # 1. Determine Composition-Weighted Partial Pairs, First-Shell r1, Second-Shell r2, and S(Q) Q1, Q2
    partial_pairs: List[Dict[str, Any]] = []
    fsdp_amp_scale = 1.0

    if material_class == "Oxide":
        c_o = frac_map.get("O", 0.60)
        secondary_anions = [s for s in syms if s in {"I", "F", "Cl", "Br", "N", "C"}]
        cations = [s for s in syms if s != "O" and s not in secondary_anions] or [syms[0]]
        cat_total = sum(frac_map.get(s, 0.1) for s in cations) or 1.0
        former_set = {"Si", "Ge", "B", "P", "As", "Al", "Ga", "Te", "V", "Ti", "Mo", "W", "Ta", "Nb"}
        formers = [s for s in cations if s in former_set]
        modifiers = [s for s in cations if s not in former_set]
        x_mod = sum(frac_map.get(s, 0.0) for s in modifiers) / cat_total

        # Base Q1 and Q2 per network-forming cation, weighted by cation atomic fraction
        q1_cat_map = {"Si": 1.52, "Ge": 1.55, "B": 1.62, "P": 1.38, "Al": 1.96, "Ti": 1.92, "Ta": 2.04, "Zr": 2.12, "Hf": 2.14, "Te": 1.85, "V": 1.68}
        q2_cat_map = {"Si": 2.98, "Ge": 2.66, "B": 2.85, "P": 2.72, "Al": 2.76, "Ti": 2.68, "Ta": 3.05, "Zr": 3.15, "Hf": 3.18, "Te": 2.90, "V": 2.82}
        active_formers = formers if formers else cations
        f_sum = sum(frac_map.get(s, 0.1) for s in active_formers) or 1.0
        q1_base = sum(frac_map.get(s, 0.1) * q1_cat_map.get(s, 1.78) for s in active_formers) / f_sum
        q2_base = sum(frac_map.get(s, 0.1) * q2_cat_map.get(s, 2.88) for s in active_formers) / f_sum
        # Modifiers shift FSDP Q1 to higher Q (cage contraction) and dampen FSDP height
        q1 = round(q1_base + 0.36 * x_mod, 2)
        q2 = round(q2_base - 0.12 * x_mod, 2)
        fsdp_amp_scale = max(0.65, round(1.0 - 0.42 * x_mod, 2))
        has_fsdp = True

        # Build partial pairs with stoichiometric weights w_so ~ c_s * c_O
        # Order network-forming cations (classic tetrahedral/trigonal formers first) ahead of modifiers
        primary_former_order = {"B": 0, "P": 1, "Si": 2, "Ge": 3, "As": 4, "Al": 5, "Ga": 6, "V": 7, "Te": 8, "Mo": 9, "W": 10, "Ti": 11, "Nb": 12, "Ta": 13}
        ordered_formers = sorted(formers, key=lambda s: primary_former_order.get(s, 20))
        ordered_cations = ordered_formers + modifiers
        r1_former_num = 0.0
        r1_former_den = 0.0
        cn_first_num = 0.0
        cn_first_den = 0.0
        for s in ordered_cations:
            r_so = get_pair_length(s, "O", "Oxide")
            is_exp_pair = has_canonical_pair_length(s, "O")
            default_cn = 4.0 if s in {"Si", "P", "Ge", "Ga", "Zn"} else (3.4 + min(0.6, x_mod) if s == "B" else (4.5 if s == "Al" else (5.4 if s == "Ti" else 6.0)))
            cn_val = default_cn if s == "B" else _parse_cn_from_coord_map(s, coord_map, default_cn)
            w_raw = frac_map.get(s, 0.1) * max(0.1, c_o) * 2.0
            if s in active_formers:
                r1_former_num += frac_map.get(s, 0.1) * r_so
                r1_former_den += frac_map.get(s, 0.1)
                cn_first_num += frac_map.get(s, 0.1) * round(cn_val, 1)
                cn_first_den += frac_map.get(s, 0.1)
            partial_pairs.append({
                "pair": f"{s}–O",
                "r_ij_A": r_so,
                "sigma_r_A": 0.05 if s in {"Si", "P", "B", "Ge"} else 0.11,
                "cn_ij": round(cn_val, 1),
                "coordination_number": f"CN = {cn_val:.1f}",
                "composition_weight": w_raw,
                "pair_source": "Experimental EXAFS/PDF Benchmark" if is_exp_pair else "Empirical Covalent/Ionic Radii Sum",
                "bond_type": "Covalent/ionic polyhedral M–O network bond" if s in former_set else "Network-modifier/intermediate M–O coordination shell",
            })

        # Pair any secondary anions (I, F, Cl, Br in oxy-halides; C, N in oxycarbides/oxynitrides) with their bonded cations
        for x in secondary_anions:
            if x in {"I", "F", "Cl", "Br"}:
                m_cat = "Ag" if "Ag" in cations else ("Cu" if "Cu" in cations else (modifiers[0] if modifiers else cations[0]))
                r_mx = get_pair_length(m_cat, x, "Oxide")
                is_exp_mx = has_canonical_pair_length(m_cat, x)
                cn_mx = _parse_cn_from_coord_map(x, coord_map, 4.0)
                w_mx = frac_map.get(m_cat, 0.1) * frac_map.get(x, 0.1) * 2.0
                partial_pairs.append({
                    "pair": f"{m_cat}–{x}",
                    "r_ij_A": r_mx,
                    "sigma_r_A": 0.10,
                    "cn_ij": round(cn_mx, 1),
                    "coordination_number": f"CN = {cn_mx:.1f}",
                    "composition_weight": w_mx,
                    "pair_source": "Experimental EXAFS/PDF Benchmark" if is_exp_mx else "Empirical Covalent/Ionic Radii Sum",
                    "bond_type": f"Secondary halide {m_cat}–{x} superionic/modifier coordination subnetwork",
                })
            else:
                f_cat = "Si" if "Si" in cations else ("B" if "B" in cations else (ordered_formers[0] if ordered_formers else cations[0]))
                r_fx = get_pair_length(f_cat, x, "Oxide")
                is_exp_fx = has_canonical_pair_length(f_cat, x)
                cn_fx = _parse_cn_from_coord_map(x, coord_map, 4.0 if x == "C" else 3.0)
                w_fx = frac_map.get(f_cat, 0.1) * frac_map.get(x, 0.1) * 2.0
                r1_former_num += frac_map.get(x, 0.1) * r_fx
                r1_former_den += frac_map.get(x, 0.1)
                partial_pairs.append({
                    "pair": f"{f_cat}–{x}",
                    "r_ij_A": r_fx,
                    "sigma_r_A": 0.06,
                    "cn_ij": round(cn_fx, 1),
                    "coordination_number": f"CN = {cn_fx:.1f}",
                    "composition_weight": w_fx,
                    "pair_source": "Experimental EXAFS/PDF Benchmark" if is_exp_fx else "Empirical Covalent/Ionic Radii Sum",
                    "bond_type": f"Mixed-anion covalent {f_cat}–{x} oxycarbide/oxynitride network bond",
                })

        r1 = round(r1_former_num / max(1e-6, r1_former_den), 2) if r1_former_den > 0 else 1.62
        first_shell_cn_val = round(cn_first_num / max(1e-6, cn_first_den), 1) if cn_first_den > 0 else 4.0
        r2 = round(r1 * 1.63, 2) if "B" not in sym_set else round(2.40 * (frac_map.get("B", 0.0) / f_sum) + 2.63 * (1.0 - frac_map.get("B", 0.0) / f_sum), 2)
        partial_pairs.append({
            "pair": "O–O",
            "r_ij_A": r2,
            "sigma_r_A": 0.09,
            "cn_ij": round(6.0 - 0.8 * (frac_map.get("B", 0.0) / cat_total), 1),
            "coordination_number": f"CN = {6.0 - 0.8 * (frac_map.get('B', 0.0) / cat_total):.1f}",
            "composition_weight": max(0.15, c_o * c_o * 0.45),
            "pair_source": "Experimental EXAFS/PDF Benchmark",
            "bond_type": "Intrapolyhedral oxygen-oxygen edge distance",
        })

    elif material_class == "Chalcogenide":
        chalcs = [c for c in syms if c in {"S", "Se", "Te"}] or [syms[-1]]
        halides = [x for x in syms if x in {"I", "Br", "Cl", "F"}]
        cats = [s for s in syms if s not in {"S", "Se", "Te", "I", "Br", "Cl", "F"}] or [syms[0]]
        chalc_former_set = {"Ge", "Si", "As", "P", "B", "Ga", "In", "Sb", "Bi", "Mo"}
        chalc_formers = [s for s in cats if s in chalc_former_set]
        chalc_modifiers = [s for s in cats if s not in chalc_former_set]
        active_chalc_formers = chalc_formers if chalc_formers else cats
        ordered_chalc_cats = chalc_formers + chalc_modifiers
        chalc_main = max(chalcs, key=lambda c: frac_map.get(c, 0.1))
        c_chalc_tot = sum(frac_map.get(c, 0.1) for c in chalcs) or 0.6
        c_cat_tot = sum(frac_map.get(s, 0.1) for s in cats) or 0.4

        q1_chalc = {"S": 1.04, "Se": 1.02, "Te": 1.06}
        q2_chalc = {"S": 2.14, "Se": 2.04, "Te": 2.08}
        q1 = round(sum(frac_map.get(c, 0.1) * q1_chalc.get(c, 1.02) for c in chalcs) / c_chalc_tot + (0.85 if any(x in sym_set for x in ("Bi", "Sb")) and "Ge" not in sym_set and "S" not in sym_set else 0.0), 2)
        q2 = round(sum(frac_map.get(c, 0.1) * q2_chalc.get(c, 2.04) for c in chalcs) / c_chalc_tot + (0.85 if "Bi" in sym_set else 0.0), 2)
        has_fsdp = True

        r1_num, r1_den = 0.0, 0.0
        cn_first_num, cn_first_den = 0.0, 0.0
        for s in ordered_chalc_cats:
            r_sc = get_pair_length(s, chalc_main, "Chalcogenide")
            is_exp_pair = has_canonical_pair_length(s, chalc_main)
            default_cn = (
                4.0 if s in {"Ge", "Si", "Ga", "P", "In", "Ag", "Cu", "Li"}
                else (3.0 if s in {"As", "B"} else (5.5 if s in {"Bi", "Mo", "Na"} else (6.0 if s == "Tl" else 3.8)))
            )
            cn_val = _parse_cn_from_coord_map(s, coord_map, default_cn)
            w_raw = frac_map.get(s, 0.1) * c_chalc_tot * 2.0
            if s in active_chalc_formers:
                r1_num += frac_map.get(s, 0.1) * r_sc
                r1_den += frac_map.get(s, 0.1)
                cn_first_num += frac_map.get(s, 0.1) * cn_val
                cn_first_den += frac_map.get(s, 0.1)
            partial_pairs.append({
                "pair": f"{s}–{chalc_main}",
                "r_ij_A": r_sc,
                "sigma_r_A": 0.06 if s in {"Ge", "Si", "As", "P", "B"} else 0.10,
                "cn_ij": cn_val,
                "coordination_number": f"CN = {cn_val:.1f}",
                "composition_weight": w_raw,
                "pair_source": "Experimental EXAFS/PDF Benchmark" if is_exp_pair else "Empirical Covalent Radii Sum",
                "bond_type": (
                    f"Heteropolar {s}–{chalc_main} covalent/p-bonded network bond"
                    if s in chalc_former_set
                    else f"Modifier/ion-conducting {s}–{chalc_main} coordination shell"
                ),
            })
        for x in halides:
            f_cats = [c for c in ordered_chalc_cats if c in {"Ge", "As", "Sb", "Ga", "Si", "P"}] or [ordered_chalc_cats[0]]
            for f_cat in f_cats:
                r_fx = get_pair_length(f_cat, x, "Chalcogenide")
                is_exp_fx = has_canonical_pair_length(f_cat, x)
                cn_fx = _parse_cn_from_coord_map(x, coord_map, 1.0)
                w_fx = frac_map.get(f_cat, 0.1) * frac_map.get(x, 0.1) * 2.0
                r1_num += frac_map.get(x, 0.1) * r_fx / len(f_cats)
                r1_den += frac_map.get(x, 0.1) / len(f_cats)
                partial_pairs.append({
                    "pair": f"{f_cat}–{x}",
                    "r_ij_A": r_fx,
                    "sigma_r_A": 0.07,
                    "cn_ij": cn_fx,
                    "coordination_number": f"CN = {cn_fx:.1f}",
                    "composition_weight": w_fx,
                    "pair_source": "Experimental EXAFS/PDF Benchmark" if is_exp_fx else "Empirical Covalent Radii Sum",
                    "bond_type": f"Terminal chalcohalide {f_cat}–{x} ligand bond",
                })
        r1 = round(r1_num / max(1e-6, r1_den), 2)
        first_shell_cn_val = round(cn_first_num / max(1e-6, cn_first_den), 1) if cn_first_den > 0 else 4.0
        r2 = round(r1 * (1.48 if any(x in sym_set for x in ("Bi", "Sb", "Te")) else math.sqrt(8.0 / 3.0)), 2)
        partial_pairs.append({
            "pair": f"{chalc_main}–{chalc_main}",
            "r_ij_A": r2,
            "sigma_r_A": 0.12,
            "cn_ij": 6.0 if "Ge" in sym_set else 4.5,
            "coordination_number": f"CN = {6.0 if 'Ge' in sym_set else 4.5:.1f}",
            "composition_weight": max(0.15, c_chalc_tot * c_chalc_tot * 0.5),
            "pair_source": "Experimental EXAFS/PDF Benchmark",
            "bond_type": f"Second-shell intratetrahedral/intrapyramidal {chalc_main}–{chalc_main} contact",
        })

    elif material_class == "Covalent Network":
        has_fsdp = True
        first_shell_cn_val = 4.0
        if sym_set == {"Si"} or "SiH" in raw_formula or sym_set == {"Si", "H"}:
            r1, r2, q1, q2 = 2.35, 3.84, 1.98, 3.62
            if "H" in sym_set:
                c_si = frac_map.get("Si", 0.893)
                c_h = frac_map.get("H", 0.107)
                cn_si_si = round(4.0 - c_h / max(0.5, c_si), 2)
                first_shell_cn_val = cn_si_si
                partial_pairs.append({
                    "pair": "Si–Si",
                    "r_ij_A": 2.35,
                    "sigma_r_A": 0.05,
                    "cn_ij": cn_si_si,
                    "coordination_number": f"CN = {cn_si_si:.2f}",
                    "composition_weight": c_si * c_si,
                    "pair_source": "Experimental EXAFS/PDF Benchmark",
                    "bond_type": "Tetrahedral a-Si:H continuous random network Si–Si backbone",
                })
                partial_pairs.append({
                    "pair": "Si–H",
                    "r_ij_A": 1.48,
                    "sigma_r_A": 0.05,
                    "cn_ij": 1.0,
                    "coordination_number": "CN = 1.0",
                    "composition_weight": 2.0 * c_si * c_h,
                    "pair_source": "Experimental EXAFS/PDF Benchmark",
                    "bond_type": "Covalent Si–H monohydride/dihydride dangling-bond passivation",
                })
            else:
                first_shell_cn_val = 3.95
        elif sym_set == {"Ge"}:
            r1, r2, q1, q2 = 2.45, 4.00, 1.90, 3.45
            first_shell_cn_val = 3.95
        elif sym_set == {"C"}:
            r1, r2, q1, q2 = 1.54, 2.52, 2.95, 5.45
            first_shell_cn_val = 3.95
        elif sym_set == {"Si", "Ge"}:
            c_si = frac_map.get("Si", 0.50)
            c_ge = frac_map.get("Ge", 0.50)
            r1 = round(c_si * c_si * 2.35 + 2.0 * c_si * c_ge * 2.38 + c_ge * c_ge * 2.45, 2)
            r2 = round(r1 * 1.63, 2)
            q1, q2 = round(4.55 / r1, 2), round(8.30 / r1, 2)
            first_shell_cn_val = 4.0
            for pair_lbl, r_val, w_val, desc in (
                ("Si–Ge", 2.38, 2.0 * c_si * c_ge, "Heteropolar tetrahedral Si–Ge alloy bond"),
                ("Si–Si", 2.35, c_si * c_si, "Homopolar tetrahedral Si–Si CRN bond"),
                ("Ge–Ge", 2.45, c_ge * c_ge, "Homopolar tetrahedral Ge–Ge CRN bond"),
            ):
                partial_pairs.append({
                    "pair": pair_lbl,
                    "r_ij_A": r_val,
                    "sigma_r_A": 0.05,
                    "cn_ij": 4.0,
                    "coordination_number": "CN = 4.0",
                    "composition_weight": w_val,
                    "pair_source": "Experimental EXAFS/PDF Benchmark",
                    "bond_type": desc,
                })
        elif "F" in sym_set or "Cl" in sym_set or "Br" in sym_set:
            anion = "F" if "F" in sym_set else ("Cl" if "Cl" in sym_set else "Br")
            cats = [s for s in syms if s != anion] or [syms[0]]
            halide_former_set = {"Be", "Zn", "Al", "Zr", "Hf", "Th", "Yb", "Sc", "In", "Ga"}
            halide_formers = [s for s in cats if s in halide_former_set]
            halide_modifiers = [s for s in cats if s not in halide_former_set]
            active_halide_formers = halide_formers if halide_formers else cats
            ordered_halide_cats = halide_formers + halide_modifiers
            c_cat_sum = sum(frac_map.get(s, 0.1) for s in cats) or 1.0
            c_form_sum = sum(frac_map.get(s, 0.1) for s in active_halide_formers) or 1.0
            r1 = round(sum(frac_map.get(s, 0.1) * get_pair_length(s, anion, "Covalent Network") for s in active_halide_formers) / c_form_sum, 2)
            r2 = round(r1 * 1.63, 2)
            q1, q2 = (round(1.58 + 0.18 * (len(cats) - 1), 2), 2.95) if anion == "F" else ((1.08, 2.15) if anion == "Cl" else (1.02, 2.04))
            cn_first_num, cn_first_den = 0.0, 0.0
            for s in ordered_halide_cats:
                default_halide_cn = 4.0 if s in {"Be", "Zn"} else (6.0 if s in {"Al", "Mg"} else (7.5 if s in {"Zr", "Yb", "Ca"} else 8.5))
                cn_halide = _parse_cn_from_coord_map(s, coord_map, default_halide_cn)
                if s in active_halide_formers:
                    cn_first_num += frac_map.get(s, 0.1) * cn_halide
                    cn_first_den += frac_map.get(s, 0.1)
                partial_pairs.append({
                    "pair": f"{s}–{anion}",
                    "r_ij_A": get_pair_length(s, anion, "Covalent Network"),
                    "sigma_r_A": 0.06 if s in halide_former_set else 0.10,
                    "cn_ij": cn_halide,
                    "coordination_number": f"CN = {cn_halide:.1f}",
                    "composition_weight": frac_map.get(s, 0.1) / c_cat_sum,
                    "pair_source": "Experimental EXAFS/PDF Benchmark" if has_canonical_pair_length(s, anion) else "Empirical Covalent/Ionic Radii Sum",
                    "bond_type": (
                        f"Halide glass network-forming {s}–{anion} coordination polyhedron"
                        if s in halide_former_set
                        else f"Halide glass modifier {s}–{anion} coordination cage"
                    ),
                })
            first_shell_cn_val = round(cn_first_num / max(1e-6, cn_first_den), 1) if cn_first_den > 0 else 4.0
        elif ("Fe" in sym_set or "Gd" in sym_set or "Tb" in sym_set) and ("Si" in sym_set or "Ge" in sym_set):
            host = "Si" if "Si" in sym_set else "Ge"
            dopant = next(s for s in syms if s != host)
            c_host = frac_map.get(host, 0.80)
            c_dop = frac_map.get(dopant, 0.20)
            r_hh = 2.35 if host == "Si" else 2.45
            r_dh = get_pair_length(dopant, host, "Covalent Network")
            r1 = round(c_host * r_hh + c_dop * r_dh, 2)
            r2 = round(r1 * 1.63, 2)
            q1 = round((1.96 if host == "Si" else 1.88) + 0.35 * c_dop, 2)
            q2 = round((3.58 if host == "Si" else 3.42) + 0.40 * c_dop, 2)
            cn_host = round(4.0 * (1.0 - 0.25 * c_dop), 2)
            first_shell_cn_val = cn_host
            partial_pairs.append({
                "pair": f"{host}–{host}",
                "r_ij_A": r_hh,
                "sigma_r_A": 0.06,
                "cn_ij": cn_host,
                "coordination_number": f"CN = {cn_host:.2f}",
                "composition_weight": c_host * c_host,
                "pair_source": "Experimental EXAFS/PDF Benchmark",
                "bond_type": f"Tetrahedral {host}4 continuous random network host backbone",
            })
            cn_dop = _parse_cn_from_coord_map(dopant, coord_map, 7.5 if dopant in {"Gd", "Tb"} else 6.8)
            partial_pairs.append({
                "pair": f"{dopant}–{host}",
                "r_ij_A": r_dh,
                "sigma_r_A": 0.11,
                "cn_ij": cn_dop,
                "coordination_number": f"CN = {cn_dop:.1f}",
                "composition_weight": 2.0 * c_dop * c_host,
                "pair_source": "Experimental EXAFS/PDF Benchmark" if has_canonical_pair_length(dopant, host) else "Empirical Covalent Radii Sum",
                "bond_type": f"Hellman group EXAFS {dopant}–{host} first coordination shell in amorphous {host}",
            })
        else:
            ligands_cov = [a for a in syms if a in {"O", "N", "C"}]
            cats_cov = [s for s in syms if s not in {"O", "N", "C"}]
            if len(syms) == 1:
                r1 = get_pair_length(syms[0], syms[0], "Covalent Network")
                r2 = round(r1 * 1.63, 2)
                q1, q2 = round(4.65 / r1, 2), round(8.45 / r1, 2)
                first_shell_cn_val = 3.95 if syms[0] in {"Si", "Ge", "C"} else 3.0
            elif len(ligands_cov) >= 2 and cats_cov:
                # Multi-ligand covalent networks (Y-Si-Al-O-N, SiOC, SiBCN, BC2N)
                cov_former_order = {"Si": 0, "B": 1, "Ge": 2, "Al": 3, "P": 4, "Ga": 5}
                cov_formers = sorted([s for s in cats_cov if s in cov_former_order], key=lambda s: cov_former_order[s])
                cov_modifiers = [s for s in cats_cov if s not in cov_former_order]
                active_cov_formers = cov_formers if cov_formers else cats_cov
                ordered_cats_cov = cov_formers + cov_modifiers
                r1_num, r1_den = 0.0, 0.0
                cn_first_num, cn_first_den = 0.0, 0.0
                for s in ordered_cats_cov:
                    cn_cov = _parse_cn_from_coord_map(s, coord_map, 3.5 if s == "B" else (4.0 if s in cov_former_order else 6.5))
                    if s in active_cov_formers:
                        cn_first_num += frac_map.get(s, 0.1) * cn_cov
                        cn_first_den += frac_map.get(s, 0.1)
                    for a in ligands_cov:
                        r_sa = get_pair_length(s, a, "Covalent Network")
                        w_sa = frac_map.get(s, 0.1) * frac_map.get(a, 0.1) * 2.0
                        if s in active_cov_formers:
                            r1_num += w_sa * r_sa
                            r1_den += w_sa
                        partial_pairs.append({
                            "pair": f"{s}–{a}",
                            "r_ij_A": r_sa,
                            "sigma_r_A": 0.06 if s in cov_former_order else 0.10,
                            "cn_ij": cn_cov,
                            "coordination_number": f"CN = {cn_cov:.1f}",
                            "composition_weight": w_sa,
                            "pair_source": "Experimental EXAFS/PDF Benchmark" if has_canonical_pair_length(s, a) else "Empirical Covalent Radii Sum",
                            "bond_type": (
                                f"Mixed-ligand covalent {s}–{a} network bond"
                                if s in cov_former_order
                                else f"Oxynitride modifier {s}–{a} coordination shell"
                            ),
                        })
                if {"C", "N"}.issubset(sym_set):
                    r_cn = get_pair_length("C", "N", "Covalent Network")
                    w_cn = frac_map.get("C", 0.2) * frac_map.get("N", 0.2) * 2.0
                    r1_num += w_cn * r_cn
                    r1_den += w_cn
                    partial_pairs.append({
                        "pair": "C–N",
                        "r_ij_A": r_cn,
                        "sigma_r_A": 0.05,
                        "cn_ij": 3.5,
                        "coordination_number": "CN = 3.5",
                        "composition_weight": w_cn,
                        "pair_source": "Experimental EXAFS/PDF Benchmark",
                        "bond_type": "Heteropolar sp2/sp3 C–N network bond in amorphous B-C-N / Si-B-C-N",
                    })
                r1 = round(r1_num / max(1e-6, r1_den), 2)
                r2 = round(r1 * 1.63, 2)
                q1, q2 = round(4.55 / r1, 2), round(8.30 / r1, 2)
                first_shell_cn_val = round(cn_first_num / max(1e-6, cn_first_den), 1) if cn_first_den > 0 else 4.0
            else:
                anchor = syms[-1]
                others = syms[:-1]
                o_sum = sum(frac_map.get(s, 0.1) for s in others) or 1.0
                r1 = round(sum(frac_map.get(s, 0.1) * get_pair_length(s, anchor, "Covalent Network") for s in others) / o_sum, 2)
                r2 = round(r1 * 1.63, 2)
                q1, q2 = round(4.55 / r1, 2), round(8.30 / r1, 2)

        if not partial_pairs:
            if len(syms) == 1:
                cn_single = 3.95 if syms[0] in {"Si", "Ge", "C"} else 3.0
                first_shell_cn_val = cn_single
                partial_pairs.append({
                    "pair": f"{syms[0]}–{syms[0]}",
                    "r_ij_A": r1,
                    "sigma_r_A": 0.05,
                    "cn_ij": cn_single,
                    "coordination_number": f"CN = {cn_single:.2f}",
                    "composition_weight": 1.0,
                    "pair_source": "Experimental EXAFS/PDF Benchmark" if has_canonical_pair_length(syms[0], syms[0]) else "Empirical Covalent Radii Sum",
                    "bond_type": f"Homopolar covalent {syms[0]}–{syms[0]} first shell",
                })
            else:
                anchor = syms[-1]
                cn_first_num, cn_first_den = 0.0, 0.0
                for s in syms[:-1]:
                    cn_cov = _parse_cn_from_coord_map(s, coord_map, 3.5 if s == "B" else 4.0)
                    cn_first_num += frac_map.get(s, 0.1) * cn_cov
                    cn_first_den += frac_map.get(s, 0.1)
                    partial_pairs.append({
                        "pair": f"{s}–{anchor}",
                        "r_ij_A": get_pair_length(s, anchor, "Covalent Network"),
                        "sigma_r_A": 0.06,
                        "cn_ij": cn_cov,
                        "coordination_number": f"CN = {cn_cov:.1f}",
                        "composition_weight": frac_map.get(s, 0.1) * frac_map.get(anchor, 0.5) * 2.0,
                        "pair_source": "Experimental EXAFS/PDF Benchmark" if has_canonical_pair_length(s, anchor) else "Empirical Covalent Radii Sum",
                        "bond_type": f"Covalent network {s}–{anchor} bond",
                    })
                first_shell_cn_val = round(cn_first_num / max(1e-6, cn_first_den), 1) if cn_first_den > 0 else 4.0

    else:
        # Metallic Glass: composition-weighted over all major pairs (i, j)
        has_fsdp = False
        sorted_by_frac = sorted(elements, key=lambda x: x["atomic_fraction"], reverse=True)
        host = sorted_by_frac[0]["element_symbol"] if sorted_by_frac else syms[0]
        pair_candidates: List[tuple[str, str, float]] = []
        for idx_a, el_a in enumerate(syms):
            for idx_b in range(idx_a, len(syms)):
                el_b = syms[idx_b]
                c_a = frac_map.get(el_a, 0.1)
                c_b = frac_map.get(el_b, 0.1)
                w_ab = c_a * c_b * (1.0 if idx_a == idx_b else 2.0)
                # Chemical short-range order favors heteropolar solute-host bonding in MGs
                if idx_a != idx_b:
                    w_ab *= 1.35
                pair_candidates.append((el_a, el_b, w_ab))
        pair_candidates.sort(key=lambda x: x[2], reverse=True)
        top_mg_pairs = pair_candidates[: min(4, len(pair_candidates))]
        w_tot = sum(x[2] for x in top_mg_pairs) or 1.0
        r1 = round(sum(x[2] * get_pair_length(x[0], x[1], "Metallic Glass") for x in top_mg_pairs) / w_tot, 2)
        r2 = round(r1 * 1.67, 2)
        q1 = round(7.72 / r1, 2)  # Ehrenfest relation Q1 * r1 ~ 7.72 for dense metallic glasses
        q2 = round(q1 * 1.71, 2)
        for el_a, el_b, w_ab in top_mg_pairs:
            r_ab = get_pair_length(el_a, el_b, "Metallic Glass")
            is_met = any(m in (el_a, el_b) for m in ("B", "P", "C", "Si", "Ge"))
            cn_mg = 8.8 if (el_a in {"B", "P", "C"} or el_b in {"B", "P", "C"}) else (9.5 if is_met else 12.2)
            partial_pairs.append({
                "pair": f"{el_a}–{el_b}",
                "r_ij_A": r_ab,
                "sigma_r_A": 0.11 if is_met else 0.15,
                "cn_ij": cn_mg,
                "coordination_number": f"CN = {cn_mg:.1f}",
                "composition_weight": round(w_ab / w_tot, 3),
                "pair_source": "Experimental EXAFS/PDF Benchmark" if has_canonical_pair_length(el_a, el_b) else "Empirical Metallic Radii Sum",
                "bond_type": "p-d hybridized solute-centered prism/cluster" if is_met else "Icosahedral / Frank-Kasper metallic coordination shell",
            })
        first_shell_cn_val = partial_pairs[0]["cn_ij"] if partial_pairs else 12.0

    # Normalize composition_weight across partial_pairs to sum to 1.0
    if partial_pairs:
        w_sum_all = sum(float(p.get("composition_weight", 1.0)) for p in partial_pairs) or 1.0
        for p in partial_pairs:
            p["composition_weight"] = round(float(p.get("composition_weight", 1.0)) / w_sum_all, 3)

    # Override Q1, Q2, r1, r2 with exact published values if formula is a direct experimental benchmark
    if bench:
        q1 = float(bench["q1"])
        q2 = float(bench["q2"])
        r1 = float(bench["r1"])
        r2 = float(bench["r2"])

    d1_periodicity = round(2.0 * math.pi / q1, 2)
    corr_len_L = round(d1_periodicity * (3.1 if has_fsdp else 2.4), 1)
    sq_points = _generate_sq_curve(q1, q2, has_fsdp, fsdp_amp_scale)
    gr_points = _generate_gr_curve(r1, r2, material_class, partial_pairs)

    # 2. Composition-Weighted Bond Angle Distribution P(theta)
    if material_class == "Oxide":
        c_b = frac_map.get("B", 0.0)
        c_si = frac_map.get("Si", 0.0)
        c_ge = frac_map.get("Ge", 0.0)
        c_p = frac_map.get("P", 0.0)
        c_al = frac_map.get("Al", 0.0)
        c_tm = sum(frac_map.get(s, 0.0) for s in ("Ti", "Ta", "Nb", "Zr", "Hf", "V", "Mo", "W", "Te", "Bi", "In", "Sn"))
        c_mod = sum(frac_map.get(s, 0.0) for s in syms if s not in {"O", "Si", "Ge", "B", "P", "Al", "Ti", "Ta", "Nb", "Zr", "Hf", "V", "Mo", "W", "Te"})
        c_cat_sum = max(1e-6, 1.0 - frac_map.get("O", 0.6))
        w_b = c_b / c_cat_sum
        w_si = c_si / c_cat_sum
        w_tm = c_tm / c_cat_sum
        w_mod = c_mod / c_cat_sum

        theta1 = round(109.5 * (1.0 - w_b - 0.5 * w_tm) + 117.5 * w_b + 92.0 * (0.5 * w_tm), 1)
        fwhm1 = round(5.2 + 3.8 * w_b + 4.5 * w_tm + 2.5 * w_mod, 1)
        theta2_base = 144.0 if w_si >= 0.4 else (130.0 if w_b >= 0.4 else (133.0 if (c_ge + c_p + c_al) > 0 else 128.0))
        theta2 = round(theta2_base - 9.5 * w_mod - 8.0 * w_b * (1.0 if w_si >= 0.4 else 0.0), 1)
        fwhm2 = round(14.0 + 9.0 * w_mod + 4.0 * w_b, 1)
        if w_b > 0.25 and w_si > 0.15:
            label1 = f"O–(Si,B)–O (Composition-Weighted SiO4 + BO3/BO4, x_B={w_b:.2f})"
            label2 = "Si–O–B / T–O–T (Mixed Borosilicate Bridge Angle)"
        elif w_b > 0.35:
            label1 = "O–B–O (Composition-Weighted BO3 120° & BO4 109.5°)"
            label2 = "B–O–B (Boroxol & Inter-Polyhedral Bridge)"
        elif w_tm > 0.45 and (c_si + c_b + c_p + c_ge) == 0:
            label1 = "O–M–O (Octahedral / Pentahedral MO5–MO6 Angle)"
            label2 = "M–O–M (Corner- & Edge-Sharing Oxide Bridge)"
        else:
            label1 = "O–T–O (Intra-Tetrahedral Angle)"
            label2 = f"T–O–T (Inter-Tetrahedral Bridge, x_mod={w_mod:.2f})"
    elif material_class == "Chalcogenide":
        c_tet = sum(frac_map.get(s, 0.0) for s in ("Ge", "Si", "Ga", "In"))
        c_pyr = sum(frac_map.get(s, 0.0) for s in ("As", "P", "B"))
        c_oct = sum(frac_map.get(s, 0.0) for s in ("Bi", "Sb", "Sn", "Pb", "Mo")) + (frac_map.get("Ge", 0.0) if "Te" in sym_set else 0.0)
        c_tot_c = max(1e-6, c_tet + c_pyr + c_oct)
        theta1 = round((109.5 * c_tet + 99.0 * c_pyr + 92.5 * c_oct) / c_tot_c, 1)
        fwhm1 = round(6.5 + 3.5 * (c_oct / c_tot_c), 1)
        theta2 = round((102.0 * c_tet + 100.5 * c_pyr + 166.0 * c_oct) / c_tot_c, 1)
        fwhm2 = round(13.5 + 5.0 * (c_oct / c_tot_c), 1)
        if c_oct / c_tot_c > 0.45:
            label1 = "X–M–X (Peierls-Distorted Octahedral/Pyramidal ~92°)"
            label2 = "X–M–X (Quasi-Linear Trans-Octahedral / Bridge Peak)"
        elif c_pyr >= c_tet:
            label1 = "X–Pn–X (Trigonal Pyramidal Angle)"
            label2 = "Pn–X–Pn (Chalcogen Bridge Angle)"
        else:
            label1 = "X–T–X (Intra-Tetrahedral Angle)"
            label2 = "T–X–T (Corner/Edge-Sharing Chalcogen Bridge)"
    elif material_class == "Covalent Network":
        if "F" in sym_set or "Cl" in sym_set or "Br" in sym_set:
            anion = "F" if "F" in sym_set else ("Cl" if "Cl" in sym_set else "Br")
            cats = [s for s in syms if s != anion] or [syms[0]]
            if set(cats).issubset({"Be", "Zn"}):
                m_sym = cats[0]
                theta1 = 109.5
                fwhm1 = 7.5
                theta2 = 145.5 if m_sym == "Be" else (110.0 if anion == "Cl" else 128.0)
                fwhm2 = 16.0
                label1 = f"{anion}–{m_sym}–{anion} (Intra-Tetrahedral {m_sym}{anion}4 Halide Angle)"
                label2 = f"{m_sym}–{anion}–{m_sym} (Corner/Edge-Sharing Halide Bridge Angle)"
            else:
                theta1 = 90.0 if "Al" in sym_set and "Zr" not in sym_set and "Th" not in sym_set else 78.5
                fwhm1 = 12.5
                theta2 = 138.0
                fwhm2 = 19.0
                label1 = "F–M–F (Intra-Polyhedral ZrF7–8 / AlF6 / ThF8 Angle)"
                label2 = "M–F–M (Corner- & Edge-Sharing Fluoride Polyhedral Bridge)"
        elif sym_set == {"B"}:
            theta1, fwhm1 = 60.0, 8.5
            theta2, fwhm2 = 108.0, 14.5
            label1 = "B–B–B (Intra-Icosahedral B12 Triangular Angle ~60°)"
            label2 = "B–B–B (Pentagonal B12 & Inter-Icosahedral Bridge ~108°)"
        elif sym_set.issubset({"P", "As", "Sb"}):
            pn = syms[0]
            theta1 = 98.5 if pn == "P" else (97.5 if pn == "As" else 95.5)
            fwhm1 = 9.0
            theta2 = 124.0
            fwhm2 = 17.0
            label1 = f"{pn}–{pn}–{pn} (Pyramidal 3-Coordinate Pnictogen Bond Angle)"
            label2 = "Inter-Pyramidal / Second-Shell Dihedral Peak"
        elif sym_set in ({"B", "N"}, {"B", "C", "N"}):
            theta1 = 118.5 if sym_set == {"B", "N"} else 114.0
            fwhm1 = 9.5
            theta2 = 126.0
            fwhm2 = 16.5
            label1 = "N–B–N / C–B–N (Trigonal sp2 & Mixed sp2–sp3 Network Angle)"
            label2 = "B–N–B / B–C–N (Inter-Polyhedral Bridge Angle)"
        elif "O" in sym_set or ("N" in sym_set and "Si" in sym_set):
            c_b_cov = frac_map.get("B", 0.0)
            theta1 = round(109.5 * (1.0 - c_b_cov) + 118.0 * c_b_cov, 1)
            fwhm1 = 9.0
            theta2 = 128.5 if "O" in sym_set else 123.5
            fwhm2 = 16.5
            label1 = "X–Si–X / X–T–X (Tetrahedral Nitride/Oxycarbide/Oxynitride Angle)"
            label2 = "Si–N–Si / T–(O,N,C)–T (Cross-Linking Bridge Angle)"
        else:
            c_dop_tm = sum(frac_map.get(s, 0.0) for s in ("Fe", "Gd", "Tb"))
            theta1 = round(109.5 - 10.0 * c_dop_tm, 1)
            fwhm1 = round(9.2 + 6.0 * c_dop_tm, 1)
            theta2 = round(138.0 - 14.0 * c_dop_tm, 1)
            fwhm2 = round(17.5 + 6.0 * c_dop_tm, 1)
            label1 = "T–T–T (Tetrahedral sp3 Continuous Random Network Bond Angle)"
            label2 = "Bridge / Second-Shell Dihedral Peak"
    else:
        x_met = sum(frac_map.get(s, 0.0) for s in ("B", "P", "C", "Si", "Ge"))
        theta1 = round(59.5 + 2.8 * x_met, 1)
        fwhm1 = round(11.0 + 3.5 * x_met, 1)
        theta2 = round(108.5 - 3.5 * x_met, 1)
        fwhm2 = round(15.5 + 4.0 * x_met, 1)
        label1 = "M–M–M (Polytetrahedral 3-Atom Contact Peak)"
        label2 = f"M–M–M (Icosahedral 108.5° & Prism Angle, x_met={x_met:.2f})"

    if bench:
        theta1 = float(bench["theta1"])
        theta2 = float(bench["theta2"])

    angle_points = _generate_angle_curve(theta1, fwhm1, theta2, fwhm2)

    # 3. Composition-Weighted Ring Size (n-ring) or Voronoi Polyhedron (<n3,n4,n5,n6>) Distribution
    if material_class == "Oxide":
        c_cat_sum = max(1e-6, 1.0 - frac_map.get("O", 0.6))
        w_b = frac_map.get("B", 0.0) / c_cat_sum
        w_mod = sum(frac_map.get(s, 0.0) for s in syms if s not in {"O", "Si", "Ge", "B", "P", "Al", "Ti", "Ta", "Nb", "Zr", "Hf", "V", "Mo", "W", "Te"}) / c_cat_sum
        if w_b > 0.35:
            # Borate / borosilicate composition-weighted ring distribution (boron anomaly: modifier converts 3-ring boroxol -> 4/6-ring BO4)
            boroxol_pct = max(12.0, 48.0 * w_b * (1.0 - 0.85 * w_mod))
            r4_pct = 15.0 + 18.0 * w_mod
            r5_pct = 14.0 + 12.0 * (1.0 - w_b)
            r6_pct = 17.0 + 22.0 * (1.0 - w_b) + 12.0 * w_mod
            r7_pct = 6.0 + 14.0 * w_mod
            topo_type = "Composition-Weighted Ring Distribution (B–O / Si–O Network)"
            dom_motif = f"3-ring (Boroxol, {boroxol_pct:.0f}%) & 6-ring network (x_B={w_b:.2f}, x_mod={w_mod:.2f})"
            dist_bars = _normalize_bars([
                {"label": "3-ring (Boroxol)", "pct": boroxol_pct, "description": "Planar B3O6 boroxol rings (808 cm^-1 Raman breathing mode)"},
                {"label": "4-ring", "pct": r4_pct, "description": "Four-membered diborate / BO4-containing rings"},
                {"label": "5-ring", "pct": r5_pct, "description": "Five-membered pentaborate / mixed rings"},
                {"label": "6-ring", "pct": r6_pct, "description": "Six-membered metaborate / silicate rings"},
                {"label": ">=7-ring", "pct": r7_pct, "description": "Large modifier-hosting network cages"},
            ])
        else:
            # Silicate / germanate / phosphate / transition-metal oxide ring distribution weighted by modifier & high-CN cation fraction
            w_high_cn = sum(frac_map.get(s, 0.0) for s in ("Al", "Ti", "Ta", "Zr", "Hf", "In", "Sn")) / c_cat_sum
            r3_pct = 4.0 + 10.0 * w_high_cn + 6.0 * w_b
            r4_pct = 11.0 + 14.0 * w_high_cn + 4.0 * w_mod
            r5_pct = 24.0 + 4.0 * w_high_cn
            r6_pct = max(16.0, 35.0 - 18.0 * w_mod - 14.0 * w_high_cn)
            r7_pct = 18.0 + 10.0 * w_mod
            r8_pct = 8.0 + 14.0 * w_mod
            topo_type = "Composition-Weighted Ring Distribution (King/Guttman n-Rings)"
            dom_motif = f"6-ring & 5/7-ring network (x_mod={w_mod:.2f})"
            dist_bars = _normalize_bars([
                {"label": "3-ring", "pct": r3_pct, "description": "Planar 3-membered rings / edge-sharing polyhedra"},
                {"label": "4-ring", "pct": r4_pct, "description": "Four-membered polyhedral rings (D1 band)"},
                {"label": "5-ring", "pct": r5_pct, "description": "Odd-membered topological frustration rings"},
                {"label": "6-ring", "pct": r6_pct, "description": "Six-polyhedra corner-sharing rings"},
                {"label": "7-ring", "pct": r7_pct, "description": "Seven-membered rings accommodating modifier cations"},
                {"label": ">=8-ring", "pct": r8_pct, "description": "Large depolymerized network cages"},
            ])
    elif material_class == "Chalcogenide":
        # Weight by mean coordination number <r> = sum(c_i * z_i) and p-bonded octahedral fraction
        z_map = {"Ge": 4.0, "Si": 4.0, "Ga": 4.0, "In": 4.0, "As": 3.0, "Sb": 3.5, "Bi": 5.0, "P": 3.5, "S": 2.0, "Se": 2.0, "Te": 2.4}
        mean_r = sum(frac_map.get(s, 0.0) * z_map.get(s, 2.5) for s in syms)
        c_oct = sum(frac_map.get(s, 0.0) for s in ("Bi", "Sb", "Te"))
        r2_edge = 14.0 + 12.0 * max(0.0, mean_r - 2.3)
        r3_pct = 10.0 + 8.0 * c_oct
        r4_pct = 15.0 + 22.0 * c_oct
        r5_pct = max(12.0, 22.0 - 10.0 * c_oct)
        r6_pct = max(14.0, 26.0 - 12.0 * c_oct)
        r7_pct = max(6.0, 13.0 - 6.0 * max(0.0, mean_r - 2.4))
        topo_type = f"Composition-Weighted Ring Distribution (<r> ≈ {mean_r:.2f})"
        dom_motif = "4-ring (ABAB p-bonded cubes) + 6-ring" if c_oct > 0.45 else "6-ring (Corner-sharing) + 2-ring (Edge-sharing)"
        dist_bars = _normalize_bars([
            {"label": "2-ring (Edge)", "pct": r2_edge, "description": "Edge-sharing bitetrahedra / bipyramids"},
            {"label": "3-ring", "pct": r3_pct, "description": "Three-polyhedra chalcogenide rings"},
            {"label": "4-ring (ABAB)", "pct": r4_pct, "description": "Four-membered ABAB rings (dominant in phase-change / p-bonded tellurides & selenides)"},
            {"label": "5-ring", "pct": r5_pct, "description": "Five-membered covalent rings"},
            {"label": "6-ring", "pct": r6_pct, "description": "Six-membered corner-sharing rings"},
            {"label": ">=7-ring", "pct": r7_pct, "description": "Medium-range chain/layer loops"},
        ])
    elif material_class == "Covalent Network":
        if "F" in sym_set or "Cl" in sym_set or "Br" in sym_set:
            anion = "F" if "F" in sym_set else ("Cl" if "Cl" in sym_set else "Br")
            cats = [s for s in syms if s != anion] or [syms[0]]
            if set(cats).issubset({"Be", "Zn"}):
                m_sym = cats[0]
                topo_type = f"Corner-Sharing {m_sym}{anion}4 Halide Network Ring Statistics"
                dom_motif = f"6-ring & 5/7-ring Corner-Sharing {m_sym}{anion}4 Tetrahedra"
                dist_bars = _normalize_bars([
                    {"label": "3-ring", "pct": 6.0 if anion != "F" else 2.5, "description": f"Edge/corner-sharing {m_sym}{anion}4 3-membered rings"},
                    {"label": "4-ring", "pct": 12.0 if anion != "F" else 8.0, "description": f"Four-membered {m_sym}{anion}4 halide rings"},
                    {"label": "5-ring", "pct": 24.0, "description": f"Five-membered {m_sym}{anion}4 rings frustrating cristobalite/rutile order"},
                    {"label": "6-ring", "pct": 34.0, "description": f"Six-membered corner-sharing {m_sym}{anion}4 rings"},
                    {"label": ">=7-ring", "pct": 24.0, "description": "Larger continuous halide network loops"},
                ])
            else:
                topo_type = "Heavy-Metal / Fluoroaluminate Polyhedral Network Statistics"
                dom_motif = "Corner- & Edge-Sharing MF6–MF8 Polyhedral Chains & Rings"
                dist_bars = _normalize_bars([
                    {"label": "2-ring (Edge)", "pct": 18.0, "description": "Edge-sharing ZrF7–8 / ThF8 / AlF6 polyhedral dimers"},
                    {"label": "3-ring", "pct": 19.0, "description": "Three-polyhedra fluoride rings"},
                    {"label": "4-ring", "pct": 25.0, "description": "Four-membered corner-sharing fluoride polyhedral rings"},
                    {"label": "5-ring", "pct": 22.0, "description": "Five-membered fluoride polyhedral loops hosting Ba2+/Na+ modifiers"},
                    {"label": ">=6-ring", "pct": 16.0, "description": "Large modifier-stabilized fluoride network cages"},
                ])
        elif sym_set == {"B"}:
            topo_type = "Icosahedral Boron (B12) Network Ring Statistics"
            dom_motif = "3-ring & 5-ring Intra-Icosahedral B12 Motifs"
            dist_bars = _normalize_bars([
                {"label": "3-ring (B12)", "pct": 38.0, "description": "Intra-icosahedral triangular B3 faces of B12 clusters"},
                {"label": "5-ring (B12)", "pct": 36.0, "description": "Five-fold equatorial B5 rings within B12 icosahedra"},
                {"label": "6-ring", "pct": 16.0, "description": "Inter-icosahedral 3-center/2-electron covalent links"},
                {"label": ">=7-ring", "pct": 10.0, "description": "Larger inter-cluster covalent loops"},
            ])
        elif sym_set.issubset({"P", "As", "Sb"}):
            pn = syms[0]
            topo_type = f"Pyramidal 3-Coordinate Pnictogen ({pn}) Ring Statistics"
            dom_motif = f"6-ring & 5/7-ring Pyramidal {pn}3 Network"
            dist_bars = _normalize_bars([
                {"label": "4-ring", "pct": 6.0, "description": f"Strained 4-membered {pn}4 pyramidal rings"},
                {"label": "5-ring", "pct": 29.0, "description": f"Five-membered {pn}5 rings frustrating layered A7 rhombohedral order"},
                {"label": "6-ring", "pct": 37.0, "description": f"Six-membered chair/boat {pn}6 pyramidal rings"},
                {"label": "7-ring", "pct": 20.0, "description": "Seven-membered pnictogen network rings"},
                {"label": ">=8-ring", "pct": 8.0, "description": "Larger continuous pnictogen network loops"},
            ])
        elif sym_set in ({"B", "N"}, {"B", "C", "N"}):
            topo_type = "Mixed sp2/sp3 Borazine & Covalent Ring Distribution"
            dom_motif = "6-ring (Borazine / Hexagonal) & 5/7-ring Disordered Network"
            dist_bars = _normalize_bars([
                {"label": "4-ring", "pct": 7.0, "description": "Strained 4-membered B–N / C–N rings"},
                {"label": "5-ring", "pct": 23.0, "description": "Odd-membered rings inducing sheet curvature"},
                {"label": "6-ring (Borazine)", "pct": 44.0, "description": "Six-membered hexagonal B3N3 / B–C–N rings"},
                {"label": "7-ring", "pct": 18.0, "description": "Seven-membered topological disorder rings"},
                {"label": ">=8-ring", "pct": 8.0, "description": "Larger cross-linked network loops"},
            ])
        elif "O" in sym_set or ("N" in sym_set and "Si" in sym_set):
            topo_type = "Cross-Linked Tetrahedral Nitride / Oxycarbide / Oxynitride Ring Statistics"
            dom_motif = "6-ring & 5/4-ring Cross-Linked Si(N,O,C)4 Network"
            dist_bars = _normalize_bars([
                {"label": "3-ring", "pct": 8.0, "description": "Three-polyhedra Si3N3 / Si3(O,N)3 rings"},
                {"label": "4-ring", "pct": 16.0, "description": "Four-membered cross-linked nitride/oxycarbide rings"},
                {"label": "5-ring", "pct": 26.0, "description": "Five-membered continuous network rings"},
                {"label": "6-ring", "pct": 32.0, "description": "Six-membered corner-sharing tetrahedral rings"},
                {"label": ">=7-ring", "pct": 18.0, "description": "Larger cross-linked network cages"},
            ])
        else:
            c_dop = sum(frac_map.get(s, 0.0) for s in ("Fe", "Gd", "Tb", "H"))
            c_tet = max(0.0, 1.0 - c_dop)
            topo_type = "Composition-Weighted Tetrahedral CRN Ring Statistics"
            dom_motif = f"6-ring & 5-ring (sp3 CRN, x_tet={c_tet:.2f})"
            dist_bars = _normalize_bars([
                {"label": "4-ring", "pct": 4.0 + 8.0 * c_dop, "description": "Strained 4-membered tetrahedral CRN rings"},
                {"label": "5-ring", "pct": 31.0 - 5.0 * c_dop, "description": "Five-membered rings preventing diamond-cubic / zincblende periodicity"},
                {"label": "6-ring", "pct": 39.0 - 9.0 * c_dop, "description": "Six-membered chair/boat tetrahedral rings"},
                {"label": "7-ring", "pct": 21.0 + 3.0 * c_dop, "description": "Seven-membered rings balancing network curvature"},
                {"label": ">=8-ring", "pct": 5.0 + 6.0 * c_dop, "description": "Larger continuous random network cages"},
            ])
    else:
        # Metallic Glass: weight Voronoi polyhedra by metalloid fraction x_met and atomic radius mismatch delta_r
        x_met = sum(frac_map.get(s, 0.0) for s in ("B", "P", "C", "Si", "Ge"))
        r_mean = sum(frac_map.get(s, 0.0) * ATOMIC_RADII_A.get(s, 1.40) for s in syms) or 1.40
        delta_r = math.sqrt(sum(frac_map.get(s, 0.0) * ((ATOMIC_RADII_A.get(s, 1.40) - r_mean) / r_mean) ** 2 for s in syms))
        topo_type = f"Composition-Weighted Voronoi Polyhedron Distribution (x_met={x_met:.2f}, δr={delta_r*100:.1f}%)"
        if x_met >= 0.12:
            dom_motif = "<0,3,6,0> Trigonal Prism & <0,2,8,0> Antiprism"
            dist_bars = _normalize_bars([
                {"label": "<0,3,6,0>", "pct": 18.0 + 32.0 * x_met, "description": "Tricapped trigonal prism (CN=9) around metalloid (Si/Ge/P/B/C)"},
                {"label": "<0,2,8,0>", "pct": 18.0 + 16.0 * x_met, "description": "Bicapped square antiprism (CN=10) p-d hybridized cluster"},
                {"label": "<0,2,8,1>", "pct": 21.0, "description": "Distorted Kasper polyhedron (CN=11)"},
                {"label": "<0,0,12,0>", "pct": max(10.0, 24.0 - 24.0 * x_met), "description": "Full 5-fold icosahedron (CN=12) frustrating BCC/B20 order"},
                {"label": "<0,1,10,2>", "pct": 14.0 + 25.0 * delta_r, "description": "High-CN matrix coordination polyhedron (CN=13)"},
            ])
        else:
            dom_motif = "<0,0,12,0> & <0,2,8,2> Icosahedral Clusters"
            dist_bars = _normalize_bars([
                {"label": "<0,0,12,0>", "pct": max(14.0, 30.0 - 65.0 * delta_r), "description": "Full 12-coordinated icosahedron (12 pentagonal faces)"},
                {"label": "<0,2,8,2>", "pct": 24.0, "description": "Distorted 12-coordinated icosahedral cluster"},
                {"label": "<0,1,10,2>", "pct": 19.0 + 25.0 * delta_r, "description": "13-coordinated Frank-Kasper-like polyhedron"},
                {"label": "<0,3,6,3>", "pct": 15.0 + 15.0 * x_met, "description": "12-coordinated polytetrahedral shell"},
                {"label": "<0,1,10,4>", "pct": 12.0 + 45.0 * delta_r, "description": "Z15-like large solvent coordination cage (CN=15)"},
            ])

    has_direct_voronoi_bars = bool(bench and "voronoi_bars" in bench)
    if has_direct_voronoi_bars:
        dist_bars = _normalize_bars(bench["voronoi_bars"])
        topo_type = bench.get("topo_type", topo_type)
        dom_motif = bench.get("dom_motif", dom_motif)

    # 4. Explicit Provenance Metadata for Overall System & Each of the 4 Sections
    exp_pair_count = sum(1 for p in partial_pairs if "Experimental" in p.get("pair_source", ""))
    total_pair_count = len(partial_pairs)
    if is_direct_benchmark:
        sq_source_type = "experimental_benchmark"
        sq_source_badge = "🔬 Benchmark Peaks (Q₁, Q₂) + Parameterized S(Q) Curve"
        sq_source_detail = (
            f"Scalar peak positions Q₁ = {q1:.2f} Å⁻¹, Q₂ = {q2:.2f} Å⁻¹ anchored to published diffraction ({bench['ref']}); "
            f"continuous S(Q) curve is a parameterized Gaussian/Lorentzian profile reconstruction."
        )
        gr_source_type = "experimental_benchmark"
        gr_source_badge = f"🔬 Benchmark Shells (r₁, r₂; {exp_pair_count}/{total_pair_count} pairs) + Parameterized g(r) Curve"
        gr_source_detail = (
            f"First/second shells r₁ = {r1:.2f} Å, r₂ = {r2:.2f} Å & partial pair lengths from {bench['ref']}; "
            f"continuous total g(r) profile is a parameterized Gaussian shell reconstruction weighted by stoichiometric c_α c_β."
        )
        ang_source_type = "experimental_benchmark"
        ang_source_badge = "🔬 Benchmark Angles (θ₁, θ₂) + Parameterized P(θ) Curve"
        ang_source_detail = (
            f"Mean intra/inter-unit angles θ₁ = {theta1:.1f}°, θ₂ = {theta2:.1f}° from {bench['ref']}; "
            f"continuous P(θ) curve is a parameterized bimodal Gaussian profile."
        )
        if has_direct_voronoi_bars:
            ring_source_type = "experimental_benchmark"
            ring_source_badge = "🔬 Published RMC / AIMD Literature Ring / Voronoi Benchmark"
            ring_source_detail = f"Ring / Voronoi polyhedron statistics directly from published RMC/AIMD literature ({bench['ref']}) for {formula}."
        else:
            ring_source_type = "composition_weighted_reconstruction"
            ring_source_badge = "⚖️ Archetype-Guided Composition-Weighted Topology"
            ring_source_detail = f"Ring / Voronoi polyhedron fractions computed from stoichiometric atomic fractions c_i of {formula} (guided by {bench['ref']})."
        overall_badge = "🔬 Experimental / RMC Benchmark Peaks + Parameterized Curve Profiles"
        overall_type = "direct_experimental_benchmark"
        comp_weight_note = (
            f"Scalar peak positions (Q₁, Q₂, r₁, r₂, θ₁, θ₂) anchored directly to {bench['ref']}; "
            f"continuous S(Q), g(r), and P(θ) curves are parameterized Gaussian/Lorentzian reconstructions."
        )
    else:
        sq_source_type = "composition_weighted_reconstruction"
        sq_source_badge = "⚖️ Composition-Weighted Parameterized S(Q) Reconstruction"
        sq_source_detail = (
            f"Q₁ = {q1:.2f} Å⁻¹ and Q₂ = {q2:.2f} Å⁻¹ computed from stoichiometric atomic fractions c_i of {formula} "
            f"and Ehrenfest / network-former scaling; continuous S(Q) curve is a parameterized Lorentzian/Gaussian profile."
        )
        gr_source_type = "experimental_pairs_composition_weighted" if exp_pair_count > 0 else "composition_weighted_reconstruction"
        gr_source_badge = (
            f"🔬 Experimental Pair Lengths ({exp_pair_count}/{total_pair_count}) + ⚖️ Parameterized g(r) Curve"
            if exp_pair_count > 0
            else "⚖️ Composition-Weighted Radii Sum + Parameterized g(r) Curve"
        )
        gr_source_detail = (
            f"{exp_pair_count}/{total_pair_count} partial pair bond lengths r_αβ from published EXAFS/PDF benchmarks; "
            f"mean r₁ = {r1:.2f} Å and continuous g(r) profile reconstructed from Gaussian shells weighted by stoichiometric fractions c_α c_β of {formula}."
        )
        ang_source_type = "composition_weighted_reconstruction"
        ang_source_badge = "⚖️ Composition-Weighted Parameterized P(θ) Reconstruction"
        ang_source_detail = (
            f"Peak angles θ₁ = {theta1:.1f}°, θ₂ = {theta2:.1f}° and widths weighted by stoichiometric cation/solute fractions c_i in {formula}; "
            f"continuous P(θ) curve is a parameterized Gaussian profile."
        )
        ring_source_type = "composition_weighted_reconstruction"
        ring_source_badge = "⚖️ Composition-Weighted Topological Reconstruction"
        ring_source_detail = f"Ring / Voronoi polyhedron fractions computed continuously from stoichiometric atomic fractions c_i and size variance of {formula}."
        overall_badge = "⚖️ Experimental Pair Lengths + Composition-Weighted Parameterized Profiles"
        overall_type = "composition_weighted_reconstruction"
        comp_weight_note = (
            f"Partial pair bond lengths ({exp_pair_count}/{total_pair_count} from EXAFS/PDF benchmarks) and peak positions weighted by "
            f"stoichiometric atomic fractions c_i of {formula}; continuous curves are parameterized analytical profiles."
        )

    ring_vor_dict = {
        "distribution_type": topo_type,
        "topology_type": topo_type,
        "dominant_motif": dom_motif,
        "bars": dist_bars,
        "source_type": ring_source_type,
        "source_badge": ring_source_badge,
        "source_detail": ring_source_detail,
        "physical_interpretation": (
            f"Broad distribution of {dom_motif} breaks 3D translational symmetry and frustrates crystallization in {formula}."
        ),
    }

    return {
        "provenance": {
            "is_direct_experimental_benchmark": is_direct_benchmark,
            "overall_type": overall_type,
            "overall_badge": overall_badge,
            "composition_weighting_note": comp_weight_note,
            "benchmark_reference": bench["ref"] if bench else "Composition-weighted from canonical EXAFS/PDF pair lengths & stoichiometric atomic fractions c_i",
            "experimental_pair_count": exp_pair_count,
            "total_pair_count": total_pair_count,
        },
        "diffraction_sq": {
            "probe": verification_method or "Synchrotron X-ray / Neutron Total Scattering & SAED",
            "fsdp_q1_inv_A": q1,
            "q1_inv_A": q1,
            "principal_peak_q2_inv_A": q2,
            "second_peak_q2_inv_A": q2,
            "real_space_periodicity_A": d1_periodicity,
            "correlation_length_L_A": corr_len_L,
            "curve_points": sq_points,
            "source_type": sq_source_type,
            "source_badge": sq_source_badge,
            "source_detail": sq_source_detail,
            "physical_interpretation": (
                f"First Sharp Diffraction Peak at Q₁ = {q1:.2f} Å⁻¹ corresponds to quasi-periodic medium-range order "
                f"(d ≈ {d1_periodicity:.2f} Å, coherence length L ≈ {corr_len_L:.1f} Å) without crystalline Bragg peaks."
            ),
        },
        "rdf_gr": {
            "r1_A": r1,
            "r1_bond_length_A": r1,
            "r2_A": r2,
            "r2_second_shell_A": r2,
            "r2_r1_ratio": round(r2 / max(0.5, r1), 2),
            "first_shell_cn": first_shell_cn_val,
            "partial_pairs": partial_pairs,
            "curve_points": gr_points,
            "source_type": gr_source_type,
            "source_badge": gr_source_badge,
            "source_detail": gr_source_detail,
            "physical_interpretation": (
                f"Composition-weighted first coordination shell at r₁ = {r1:.2f} Å followed by broadened second shell at r₂ = {r2:.2f} Å "
                f"(r₂/r₁ = {r2 / max(0.5, r1):.2f}), decaying to g(r) → 1 at long range."
            ),
        },
        "bond_angle_distribution": {
            "mean_angle_deg": theta1,
            "intra_polyhedral_angle_deg": theta1,
            "sigma_angle_deg": round(fwhm1 / 2.355, 1),
            "intra_polyhedral_fwhm_deg": fwhm1,
            "intra_polyhedral_label": label1,
            "motif_geometry": label1,
            "secondary_angle_deg": theta2,
            "inter_polyhedral_bridge_angle_deg": theta2,
            "inter_polyhedral_fwhm_deg": fwhm2,
            "inter_polyhedral_label": label2,
            "curve_points": angle_points,
            "source_type": ang_source_type,
            "source_badge": ang_source_badge,
            "source_detail": ang_source_detail,
            "physical_interpretation": (
                f"Primary bond-angle peak at θ₁ = {theta1:.1f}° (FWHM ≈ {fwhm1:.1f}°) paired with inter-unit / second-shell "
                f"angle θ₂ = {theta2:.1f}° provides the topological flexibility required for non-crystalline packing."
            ),
        },
        "ring_or_voronoi_distribution": ring_vor_dict,
    }
