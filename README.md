# Interactive Amorphous Periodic Table

![Amorphous Periodic Table (300 DPI)](amorphous_periodic_table.png)

A literature-verified periodic table and interactive web application cataloging **241 experimentally verified inorganic amorphous systems** across **77 active elements** (out of 118 elements, $Z = 1\text{--}118$), spanning **Oxides** (91), **Chalcogenides** (47), **Metallic Glasses** (73), and **Covalent Networks / Halide Glasses** (30).

---

## Key Features

- **100% Crossref & OpenAlex Verified Citations (`data/verified_doi_registry.json`)**:
  Every cataloged amorphous system and crystalline-to-amorphous conversion benchmark resolves to a live peer-reviewed DOI (`HTTP 200 OK`, verified author/year/journal/title match) and is experimentally confirmed by diffuse X-ray/neutron scattering ($S(Q)$ First Sharp Diffraction Peak), pair distribution function $g(r)$, TEM selected-area electron diffraction (SAED), and/or differential scanning calorimetry ($T_g$ / $T_x$).
- **Mutually Exclusive 6-Group Structural Partition**:
  - **Full Cell Coloring (49 Elements — *"Makes Amorphous Phase Possible"*)**:
    - **1a. Primary Tetrahedral Network Formers (5 el)**: `Si`, `Ge`, `P`, `B`, `As`
    - **1b. Bridging Anion Network Formers (7 el)**: `O`, `S`, `Se`, `N`, `F`, `Cl`, `Br`
    - **2a. Conditional Tetrahedral Intermediates (12 el)**: `Al`, `Ga`, `Zn`, `Be`, `C`, `V`, `Mo`, `W`, `Ti`, `Sn`, `In`, `Cd`
    - **2b. Oxide / Chalcogenide / BMG Polyhedral Intermediates (13 el)**: `Te`, `Sb`, `Bi`, `Pb`, `Fe`, `Zr`, `Hf`, `Nb`, `Ta`, `Sc`, `Tl`, `Os`, `Th`
    - **2c. Metallic Cluster / BMG Host Intermediates (12 el)**: `Cu`, `Ni`, `Co`, `Pd`, `Pt`, `Au`, `Cr`, `Mn`, `Ru`, `Rh`, `Re`, `Ir`
  - **Diagonal 50/50 Half-Split Cell Coloring (28 Elements — *"Part of Reported Amorphous Systems"*)**:
    - **3. Network Modifiers, Charge Compensators & Topological Cages (28 el)**: `Li`–`Cs`, `Mg`–`Ba`, `Ag`, `Y`, `La`–`Lu`, `U`, `I`, `H`
  - **Uncolored / White Cells (41 Elements)**: Elements with zero verified inorganic amorphous systems in `amorphous_materials.db`.
- **Three Filterable Synthesis Regimes**:
  - **Bulk Melt-Quenched Glasses & BMGs** (152 systems; $R_c \sim 10^{-2}\text{--}10^3\text{ K/s}$)
  - **Rapid-Quenched Melt-Spun Ribbons & Levitated Melts** (31 systems; $R_c \sim 10^4\text{--}10^6\text{ K/s}$)
  - **Vapor-Deposited / Thin-Film Amorphous Solids** (58 systems; $R_{c,\text{eff}} > 10^8\text{ K/s}$, including Frances Hellman Group quantum thin films, Wuttig phase-change chalcogenides, Hosono oxide semiconductors, and LIGO coatings)
- **Self-Contained Interactive Web Application (`index.html`)**:
  Open `index.html` directly in any modern browser to explore:
  1. **Overview & Interactive Three.js 3D WebGL Local Coordination Viewer**
  2. **Verified Amorphous Systems (`amorphous_materials.db`)** with clickable DOIs, paper titles, and synthesis regimes
  3. **Co-Occurrence & Correlation Metrics** (Pearson $\phi$, stoichiometric $r$, Normalized Mutual Information, and shared systems)
  4. **Glass-Forming Mechanism, Conversion Benchmarks & Atomic/Crystalline Reference**
  5. **Diffraction $S(Q)$, Radial/Partial Distribution $g(r)$, Bond Angles $P(\theta)$ & Ring/Voronoi Topology** with explicit provenance badges distinguishing literature benchmark peak anchors (43 canonical systems) from composition-weighted analytical reconstructions (198 systems)

---

## Quick Start

### 1. Run the 6-Step Pipeline

```bash
python3 run_pipeline.py --skip-online
```

This executes all six deterministic stages:
1. **`src/step1_retrieve_literature.py`** — Compiles curated amorphous material records (`data/raw_amorphous_records.json`).
2. **`src/step2_parse_normalize.py`** — Normalizes formulas to canonical IUPAC stoichiometry, filters out organic control glasses, flags 4-coordinate tetrahedral network formers, and computes SRO/MRO structural characterizations (`amorphous_systems.json`).
3. **`src/step3_ingest_sqlite.py`** — Ingests normalized records into `amorphous_materials.db` with indexed `materials` and `material_elements` tables.
4. **`src/step4_statistical_analysis.py`** — Computes elemental frequencies, co-occurrence matrix $C_{ij}$, Pearson $\phi$/$r$, Mutual Information, Shannon partner entropy $H_i$, and the Composite Amorphous Induction Score $S_i$ (`data/statistical_analysis_results.json`).
5. **`src/step5_generate_report.py`** — Exports the comprehensive analytical report (`amorphous_periodic_table_report.md`).
6. **`generate_amorphous_table.py` & `build_interactive_table.py`** — Builds the 118-element dataset (`data/amorphous_periodic_table_118.json`), renders the 300 DPI publication poster (`amorphous_periodic_table.png`), and compiles the interactive web application (`index.html`).

### 2. Run the Test Suite

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## Repository Structure

```text
├── amorphous_materials.db              # Indexed SQLite database (241 systems, 705 element rows)
├── amorphous_periodic_table.png        # 300 DPI publication-grade periodic table poster
├── amorphous_periodic_table_report.md  # Full statistical & structural classification report
├── amorphous_systems.json              # Normalized 241-system catalog with SRO/MRO profiles
├── build_interactive_table.py          # Self-contained interactive HTML compiler
├── generate_amorphous_table.py         # 118-element JSON & 300 DPI Matplotlib poster generator
├── index.html                          # Standalone interactive web application
├── pyproject.toml                      # Python package & dependency metadata
├── run_pipeline.py                     # End-to-end 6-step pipeline orchestrator
├── data/
│   ├── amorphous_periodic_table_118.json
│   ├── baseline_elements_118.json
│   ├── raw_amorphous_records.json
│   ├── statistical_analysis_results.json
│   └── verified_doi_registry.json      # 100% Crossref & OpenAlex verified DOI audit registry
├── src/
│   ├── catalog_oxides_chalcogenides.py
│   ├── catalog_metals_covalent.py
│   ├── catalog_extended_systems.py
│   ├── step1_retrieve_literature.py
│   ├── step2_parse_normalize.py
│   ├── step3_ingest_sqlite.py
│   ├── step4_statistical_analysis.py
│   ├── step5_generate_report.py
│   ├── step6_build_periodic_table_data.py
│   ├── structural_characterization_data.py
│   ├── verify_and_resolve_dois.py
│   └── vpn_fulltext_extractor.py
└── tests/
    └── test_pipeline.py                # 11-test unit & end-to-end verification suite
```
