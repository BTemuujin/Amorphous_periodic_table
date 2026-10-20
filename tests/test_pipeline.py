"""Unit and Integration Tests for the Amorphous Periodic Table Pipeline (Steps 1-5)."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

from src.step2_parse_normalize import (
    format_iupac_formula,
    is_element_tetrahedral_former,
    is_purely_organic,
    parse_chemical_formula,
)


ROOT = Path(__file__).resolve().parent.parent


class TestAmorphousPeriodicTablePipeline(unittest.TestCase):
    """End-to-end verification of Steps 1 through 5."""

    def test_step1_raw_records(self) -> None:
        raw_path = ROOT / "data" / "raw_amorphous_records.json"
        self.assertTrue(raw_path.exists(), "data/raw_amorphous_records.json must exist")
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        records = payload["records"]
        self.assertGreaterEqual(len(records), 150)

        classes = {r["material_class"] for r in records}
        for expected_cls in ("Oxide", "Chalcogenide", "Metallic Glass", "Covalent Network"):
            self.assertIn(expected_cls, classes)

        for r in records:
            self.assertTrue(r["chemical_formula"])
            self.assertGreater(len(r["constituents"]), 0)
            self.assertTrue(r["amorphous_verification_technique"])
            self.assertTrue(r["doi"])

    def test_step2_parser_and_organic_filter_unit(self) -> None:
        # Stoichiometric normalization test
        fracs = parse_chemical_formula("Na2O-CaO-5SiO2")
        self.assertAlmostEqual(sum(fracs.values()), 1.0, places=5)
        self.assertAlmostEqual(fracs["Na"], 2 / 20, places=4)
        self.assertAlmostEqual(fracs["Ca"], 1 / 20, places=4)
        self.assertAlmostEqual(fracs["Si"], 5 / 20, places=4)
        self.assertAlmostEqual(fracs["O"], 12 / 20, places=4)

        # Parenthesized & bracketed formula expansion (Section 4.4 / 5.4)
        ca_po3_2 = parse_chemical_formula("Ca(PO3)2")
        cao_p2o5 = parse_chemical_formula("CaO-P2O5")
        for el in ("Ca", "P", "O"):
            self.assertAlmostEqual(ca_po3_2[el], cao_p2o5[el], places=5)
        self.assertEqual(
            format_iupac_formula("Ca(PO3)2", ca_po3_2),
            format_iupac_formula("CaO-P2O5", cao_p2o5),
        )

        b_ca_p = parse_chemical_formula("B2O3-Ca(PO3)2")
        self.assertAlmostEqual(b_ca_p["B"], 2 / 14, places=5)
        self.assertAlmostEqual(b_ca_p["Ca"], 1 / 14, places=5)
        self.assertAlmostEqual(b_ca_p["P"], 2 / 14, places=5)
        self.assertAlmostEqual(b_ca_p["O"], 9 / 14, places=5)

        bmg_parens = parse_chemical_formula("(Zr0.5Cu0.5)90Al10")
        self.assertAlmostEqual(bmg_parens["Zr"], 0.45, places=5)
        self.assertAlmostEqual(bmg_parens["Cu"], 0.45, places=5)
        self.assertAlmostEqual(bmg_parens["Al"], 0.10, places=5)

        # Fraction + LCM/GCD empirical reduction (Section 4.4 / 5.4)
        f_libs1 = parse_chemical_formula("Li2B2S4")
        f_libs2 = parse_chemical_formula("Li2S-B2S3")
        self.assertEqual(format_iupac_formula("Li2B2S4", f_libs1), "LiBS2")
        self.assertEqual(format_iupac_formula("Li2S-B2S3", f_libs2), "LiBS2")

        f_cord1 = parse_chemical_formula("2MgO-2Al2O3-5SiO2")
        f_cord2 = parse_chemical_formula("Mg2Al4Si5O18")
        self.assertEqual(format_iupac_formula("2MgO-2Al2O3-5SiO2", f_cord1), "Mg2Al4Si5O18")
        self.assertEqual(format_iupac_formula("Mg2Al4Si5O18", f_cord2), "Mg2Al4Si5O18")

        # Organic filter positive & negative tests
        self.assertTrue(is_purely_organic(["C", "H", "O"], "Organic Glass"))
        self.assertTrue(is_purely_organic(["C", "H"], "Covalent Network"))
        self.assertFalse(is_purely_organic(["C"], "Covalent Network"))  # ta-C
        self.assertFalse(is_purely_organic(["Si", "C"], "Covalent Network"))  # a-SiC
        self.assertFalse(is_purely_organic(["Si", "O", "C"], "Covalent Network"))  # SiOC
        self.assertFalse(is_purely_organic(["Fe", "P", "C"], "Metallic Glass"))

        # Central tetrahedral flag unit test (Resolution A3 & Section 4.1 / 5.1)
        self.assertTrue(is_element_tetrahedral_former("Si", "SiO4 tetrahedra (CN=4)", "Oxide"))
        self.assertFalse(is_element_tetrahedral_former("O", "Bridging oxygen Si-O-Si (CN=2)", "Oxide"))
        self.assertFalse(is_element_tetrahedral_former("Na", "Modifier cation (CN=6)", "Oxide"))
        # Regression test: 'polytetrahedral', 'quasi-tetrahedral', and 'tetrahedral interstices' must never be flagged as CN=4
        self.assertFalse(
            is_element_tetrahedral_former("Al", "Polytetrahedral cluster (CN=12)", "Metallic Glass")
        )
        self.assertFalse(
            is_element_tetrahedral_former("Si", "Quasi-tetrahedral p-d bonding (CN=8-9)", "Metallic Glass")
        )
        self.assertFalse(
            is_element_tetrahedral_former(
                "Be",
                "Tightly packed small-atom icosahedral/tetrahedral interstices (CN=9-10)",
                "Oxide",
            )
        )
        self.assertFalse(
            is_element_tetrahedral_former("B", "Planar BS3 triangles and borthiin rings (CN=3)", "Chalcogenide")
        )
        self.assertTrue(
            is_element_tetrahedral_former("B", "BS4 tetrahedra (CN=4)", "Chalcogenide")
        )

    def test_step2_amorphous_systems_json(self) -> None:
        norm_path = ROOT / "amorphous_systems.json"
        self.assertTrue(norm_path.exists(), "amorphous_systems.json must exist")
        payload = json.loads(norm_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["metadata"]["filtered_organic_records_count"], 5)

        systems = payload["systems"]
        self.assertGreaterEqual(len(systems), 150)

        # Ensure 100% unique IUPAC formulas
        formulas = [s["formula"] for s in systems]
        self.assertEqual(len(formulas), len(set(formulas)), "All normalized IUPAC formulas must be unique")

        for sys_entry in systems:
            self.assertNotEqual(sys_entry["material_class"], "Organic Glass")
            els = sys_entry["elements"]
            total_frac = sum(e["atomic_fraction"] for e in els)
            self.assertAlmostEqual(total_frac, 1.0, places=4)
            if sys_entry["material_class"] == "Metallic Glass":
                self.assertEqual(
                    sys_entry["system_tetrahedral_flag"],
                    0,
                    f"Metallic glass {sys_entry['formula']} must have system_tetrahedral_flag=0",
                )
            for e in els:
                if e["element_symbol"] in {"O", "S", "Se", "Te", "F", "Cl", "Br", "I", "Na", "K", "Rb", "Cs", "Ca", "Sr", "Ba"}:
                    self.assertEqual(
                        e["tetrahedral_coordination_flag"],
                        0,
                        f"Anion/modifier {e['element_symbol']} must have tetrahedral_coordination_flag=0 per Resolution A3",
                    )
            self.assertIn(
                sys_entry.get("synthesis_regime"),
                {"bulk_melt_quenched", "rapid_quenched_ribbon", "vapor_thin_film"},
                f"System {sys_entry['formula']} must have a valid synthesis_regime",
            )
            self.assertTrue(sys_entry.get("synthesis_regime_label"))

    def test_step3_sqlite_database_and_indexes(self) -> None:
        db_path = ROOT / "amorphous_materials.db"
        self.assertTrue(db_path.exists(), "amorphous_materials.db must exist")

        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM materials")
            mat_count = cur.fetchone()[0]
            self.assertGreaterEqual(mat_count, 150)

            cur.execute("SELECT COUNT(*) FROM material_elements")
            el_count = cur.fetchone()[0]
            self.assertGreater(el_count, 400)

            # Verify no parenthetical disambiguation needed in formula column
            cur.execute("SELECT COUNT(*) FROM materials WHERE formula LIKE '%(%'")
            self.assertEqual(cur.fetchone()[0], 0)

            # Verify 0 tetrahedral flags in Metallic Glasses
            cur.execute(
                """
                SELECT COUNT(*)
                FROM material_elements me
                JOIN materials m ON m.id = me.material_id
                WHERE m.class = 'Metallic Glass' AND me.tetrahedral_coordination_flag = 1
                """
            )
            self.assertEqual(cur.fetchone()[0], 0)

            # Verify required columns in materials
            cur.execute("PRAGMA table_info(materials)")
            mat_cols = {row[1] for row in cur.fetchall()}
            for col in ("id", "formula", "class", "verification_method", "reference_doi", "synthesis_regime", "synthesis_regime_label"):
                self.assertIn(col, mat_cols)

            # Verify required columns in material_elements
            cur.execute("PRAGMA table_info(material_elements)")
            me_cols = {row[1] for row in cur.fetchall()}
            for col in ("material_id", "element_symbol", "atomic_fraction", "tetrahedral_coordination_flag"):
                self.assertIn(col, me_cols)

            # Verify explicit named index usage
            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM materials WHERE formula = 'SiO2'")
            plan_f = " ".join(str(r) for r in cur.fetchall())
            self.assertIn("idx_materials_formula", plan_f)

            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM material_elements WHERE element_symbol = 'Si'")
            plan_e = " ".join(str(r) for r in cur.fetchall())
            self.assertIn("idx_material_elements_symbol", plan_e)
        finally:
            conn.close()

    def test_step4_statistical_analysis(self) -> None:
        stats_path = ROOT / "data" / "statistical_analysis_results.json"
        self.assertTrue(stats_path.exists())
        data = json.loads(stats_path.read_text(encoding="utf-8"))

        self.assertEqual(data["metadata"]["total_unique_elements"], 77)
        ranked = data["element_ranking_by_induction_score"]
        self.assertEqual(len(ranked), data["metadata"]["total_unique_elements"])

        # Verify co-occurrence symmetry on top15 matrix
        rows = data["top15_co_occurrence_matrix"]["rows"]
        n = len(rows)
        for i in range(n):
            for j in range(n):
                self.assertEqual(rows[i]["counts"][j], rows[j]["counts"][i])

        # Verify primary tetrahedral network formers sub-analysis
        prim_list = data["tetrahedral_sub_analysis"]["primary_tetrahedral_network_formers"]
        prim_els = {e["element_symbol"] for e in prim_list}
        self.assertEqual(prim_els, {"Si", "Ge", "P", "B", "As"})

        prim_by_sym = {e["element_symbol"]: e for e in prim_list}
        self.assertAlmostEqual(prim_by_sym["Si"]["non_metallic_tetrahedral_ratio"], 1.0, places=5)
        self.assertAlmostEqual(prim_by_sym["Ge"]["non_metallic_tetrahedral_ratio"], 1.0, places=5)
        # P is tetrahedral in 21/22 non-metallic systems (all 19 oxide/chalcogenide + 2 covalent pnictides; elemental a-P is pyramidal CN=3)
        self.assertAlmostEqual(prim_by_sym["P"]["non_metallic_tetrahedral_ratio"], 21 / 22, places=5)

        # Verify complete 6-group partition across all 77 unique elements
        partition_counts = data["tetrahedral_sub_analysis"]["partition_counts"]
        self.assertEqual(partition_counts["primary_tetrahedral_network_formers"], 5)
        self.assertEqual(partition_counts["bridging_anion_network_formers"], 7)
        self.assertEqual(partition_counts["secondary_conditional_tetrahedral_elements"], 12)
        self.assertEqual(partition_counts["non_tetrahedral_oxide_chalcogenide_intermediates"], 13)
        self.assertEqual(partition_counts["metallic_cluster_host_intermediates"], 12)
        self.assertEqual(partition_counts["network_modifiers"], 28)
        self.assertEqual(
            partition_counts["total_partitioned_elements"],
            data["metadata"]["total_unique_elements"],
        )

        # Verify multicomponent_mean_atomic_fraction is tracked separately from monatomic films (Section 4.5)
        ranked_by_sym = {e["element_symbol"]: e for e in ranked}
        self.assertLess(
            ranked_by_sym["Sb"]["multicomponent_mean_atomic_fraction"],
            ranked_by_sym["Sb"]["mean_atomic_fraction"],
        )

        # Verify every element's category_derivation_rule is strictly positive-evidence-backed and crystal-chemically transparent
        for e in ranked:
            self.assertNotIn(
                ": 0 modifier",
                e["category_derivation_rule"],
                f"Element {e['element_symbol']} should not have a ': 0 modifier' fallback rule",
            )
            self.assertNotIn(
                "Derived from SQLite",
                e["category_derivation_rule"],
                f"Element {e['element_symbol']} should have a crystal-chemical explanation rather than circular 'Derived from SQLite'",
            )
            if e["structural_category"] == "Modifier":
                self.assertGreaterEqual(
                    e["role_breakdown"].get("Network Modifier / Charge Compensator", 0),
                    1,
                    f"Modifier {e['element_symbol']} must have >= 1 Network Modifier / Charge Compensator role in SQLite",
                )

    def test_step5_markdown_report(self) -> None:
        from src.step5_generate_report import CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES

        report_path = ROOT / "amorphous_periodic_table_report.md"
        self.assertTrue(report_path.exists())
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("Ranked List of Elements by Capability to Induce Amorphous Phase Formation", content)
        self.assertIn("Classification Table: Network Formers, Intermediates, and Modifiers", content)
        self.assertIn("Specific System Examples: Conversion of Crystalline-Prone Alloys", content)
        self.assertIn("Aluminosilicate / SiAlON Tetrahedral Co-Network", content)
        self.assertIn("Au75Si25", content)
        self.assertIn("Pd40Ni40P20", content)
        self.assertIn("$5 + 7 + 12 + 13 + 12 + 28 = 77$", content)
        self.assertIn("All Intermediates Combined, $N=37$", content)
        self.assertIn("14 peer-reviewed experimental benchmark conversions", content)

        # Step 8.1 verification gate: Every conversion example DOI in step5_generate_report.py must exist in verified_doi_registry.json
        registry_path = ROOT / "data" / "verified_doi_registry.json"
        registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
        registry_by_doi = {k.lower(): v for k, v in registry_payload["verified_dois"].items()}
        for ex in CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES:
            doi = ex["doi"].strip().lower()
            self.assertIn(doi, registry_by_doi, f"Conversion example DOI {doi} ({ex['amorphous_system']}) must be in verified_doi_registry.json")
            reg = registry_by_doi[doi]
            self.assertEqual(reg.get("http_status"), 200)
            self.assertTrue(reg.get("title"))

    def test_step6_interactive_and_static_periodic_table(self) -> None:
        # Bug 1 & Bug 4 checks: run_pipeline import, zero-arg build_periodic_table_118(), and local baseline_elements_118.json
        from run_pipeline import main as run_pipeline_main
        from src.step6_build_periodic_table_data import (
            DEFAULT_REFERENCE_JSON_PATH,
            build_periodic_table_118,
            build_periodic_table_118_dataset,
        )

        self.assertTrue(callable(run_pipeline_main))
        self.assertIs(build_periodic_table_118, build_periodic_table_118_dataset)

        step6_src = (ROOT / "src" / "step6_build_periodic_table_data.py").read_text(encoding="utf-8")
        self.assertNotIn("mag_periodic_table", step6_src, "No external repo path should remain in step6_build_periodic_table_data.py")

        built_payload = build_periodic_table_118()
        self.assertEqual(len(built_payload["elements"]), 118)
        self.assertTrue(DEFAULT_REFERENCE_JSON_PATH.exists(), "Local data/baseline_elements_118.json must exist inside repo")

        ptable_json = ROOT / "data" / "amorphous_periodic_table_118.json"
        poster_png = ROOT / "amorphous_periodic_table.png"
        index_html = ROOT / "index.html"

        self.assertTrue(ptable_json.exists(), "118-element periodic table JSON must exist")
        self.assertTrue(poster_png.exists(), "Static 300 DPI PNG poster must exist")
        self.assertTrue(index_html.exists(), "Interactive index.html must exist")

        payload = json.loads(ptable_json.read_text(encoding="utf-8"))
        elements = payload["elements"]
        self.assertEqual(len(elements), 118, "All 118 elements (Z=1..118) must be present")

        full_els = [e for e in elements if e["fill_mode"] == "full"]
        half_els = [e for e in elements if e["fill_mode"] == "half"]
        none_els = [e for e in elements if e["fill_mode"] == "none"]
        tet_els = [e for e in elements if e["has_tetrahedral_motif"]]

        self.assertEqual(len(full_els), 49, "Exactly 49 elements must have full cell fill (make amorphous phase possible)")
        self.assertEqual(len(half_els), 28, "Exactly 28 elements must have diagonal half cell fill (part of reported systems)")
        self.assertEqual(len(none_els), 41, "Exactly 41 elements must have none/white fill (unreported)")
        self.assertEqual(len(tet_els), 17, "Exactly 17 elements must have verified 4-coordinate tetrahedral motifs")

        # Bug 2 check: Verify every JS-accessed property exists on all 118 elements
        required_el_keys = {
            "category_code",
            "category_title",
            "system_frequency",
            "tetrahedral_fraction",
            "stoichiometry_stats",
            "partner_diversity",
            "role_counts",
            "top_cooccurring_partners",
            "top_correlations",
            "conversion_examples",
            "electron_configuration",
            "chemical_series",
            "electronegativity_pauling",
            "atomic_radius_pm",
            "crystalline_reference",
        }
        required_motif_keys = {
            "motif_id",
            "motif_label",
            "typical_coordination",
            "prototype_unit",
            "description",
        }
        required_sys_keys = {
            "formula",
            "raw_formula",
            "material_class",
            "synthesis_regime",
            "synthesis_regime_label",
            "atomic_fraction",
            "tetrahedral_coordination_flag",
            "element_role",
            "coordination_environment",
            "verification_method",
            "reference_doi",
            "doi_url",
            "source_reference",
            "crystalline_conversion_note",
        }

        for e in elements:
            self.assertTrue(required_el_keys.issubset(e.keys()), f"Missing JS keys on {e['symbol']}")
            self.assertTrue(required_motif_keys.issubset(e["motif_3d"].keys()), f"Missing motif_3d JS keys on {e['symbol']}")

        # Verify every active element (full or half) has >= 1 verified system and non-empty correlations when partners > 0
        for e in full_els + half_els:
            self.assertGreaterEqual(e["occurrence_count"], 1, f"{e['symbol']} must have >= 1 verified system")
            self.assertEqual(len(e["verified_systems"]), e["occurrence_count"])
            for s in e["verified_systems"]:
                self.assertTrue(required_sys_keys.issubset(s.keys()), f"Missing system JS keys on {e['symbol']}")
                self.assertTrue(s["doi_url"].startswith("https://doi.org/") or s["doi_url"].startswith("http"))
            if e["partner_diversity"] > 0:
                self.assertGreaterEqual(len(e["top_cooccurring_partners"]), 1)
                self.assertIn("cooccurrence_count", e["top_cooccurring_partners"][0])
                self.assertGreaterEqual(len(e["top_correlations"]), 1, f"{e['symbol']} must have populated top_correlations")
                c0 = e["top_correlations"][0]
                self.assertIn("pearson_phi", c0)
                self.assertIn("stoichiometric_r", c0)
                self.assertIn("normalized_mutual_info", c0)

        # Verify PNG poster size and non-trivial dimensions
        self.assertGreater(poster_png.stat().st_size, 500_000, "300 DPI poster PNG should be > 500 KB")

        # Bug 3 check: Verify interactive HTML embeds 118-element dataset, dynamic class & synthesis regime counts, and deduplicated SRO map
        html_text = index_html.read_text(encoding="utf-8")
        self.assertIn("window.AMORPHOUS_DATA =", html_text)
        self.assertIn(".el-cell.fill-full", html_text)
        self.assertIn(".el-cell.fill-half", html_text)
        self.assertIn("linear-gradient", html_text)
        self.assertIn("THREE.WebGLRenderer", html_text)
        self.assertIn("corner_sharing_tetrahedra", html_text)
        self.assertIn("icosahedral_cluster_cn12", html_text)
        self.assertIn("Oxides (84 sys)", html_text)
        self.assertIn("Chalcogenides (42 sys)", html_text)
        self.assertIn("Metallic Glasses (81 sys)", html_text)
        self.assertIn("Covalent (34 sys)", html_text)
        self.assertIn("regime:bulk_melt_quenched", html_text)
        self.assertIn("regime:rapid_quenched_ribbon", html_text)
        self.assertIn("regime:vapor_thin_film", html_text)
        self.assertIn("systems_sro_by_formula", html_text)

    def test_step7_doi_verification_and_sro_mro_characterization(self) -> None:
        """Verify 100% Crossref/OpenAlex DOI audit, Hellman & major research group systems, provenance indicators, and composition-weighted SRO/MRO characterization."""
        from src.structural_characterization_data import compute_system_structural_characterization

        registry_path = ROOT / "data" / "verified_doi_registry.json"
        self.assertTrue(registry_path.exists(), "data/verified_doi_registry.json must exist")
        registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
        registry_by_doi = {k.lower(): v for k, v in registry_payload["verified_dois"].items()}
        self.assertGreaterEqual(len(registry_by_doi), 225)

        systems_path = ROOT / "amorphous_systems.json"
        systems_payload = json.loads(systems_path.read_text(encoding="utf-8"))
        systems = systems_payload["systems"]
        self.assertEqual(len(systems), 241, "Must have 241 normalized inorganic amorphous systems")

        # 1. Verify Frances Hellman Group, major research group, and newly added 6 element amorphous systems
        formulas_set = {s["formula"] for s in systems}
        expected_landmark_systems = {
            # Hellman Group & topological amorphous solids
            "Bi2Se3",
            "FeGe",
            "FeGe3",
            "FeSi",
            "Fe3Si7",
            "CoSi",
            "CoGe",
            "MnSi",
            "Cr3Si7",
            "Gd7Si43",
            "Tb3Si17",
            "Gd3Ge17",
            "Si",
            # Phase-change & chalcogenide networks (Wuttig/Salinga, Sen, Massobrio)
            "Bi2Te3",
            "Sb2Te3",
            "Sb2S3",
            "Ag5In5Sb60Te30",
            "GeSe3",
            # Binary & transparent oxide thin films (Benmore, Petkov, Bassiri/LIGO, Hosono/Wager)
            "Al2O3",
            "TiO2",
            "Ta2O5",
            "HfO2",
            "ZrO2",
            "ZnSnO3",
            "In2O3",
            # Transition-metal sulfides & superconducting metal-metalloid films (Kortright/Bienenstock, Hertel/Dynes)
            "MoS3",
            "MoS2",
            "MoGe",
            "NbSi",
            # Landmark BMG & isotopic neutron diffraction benchmarks (Inoue, Ma/Sheng, Sváb, Lamparter/Steeb)
            "Zr50Cu40Al10",
            "Pd40Ni10Cu30P20",
            "Nb38Ni62",
            "Hf50Cu50",
            "Co80B20",
            "Mg70Zn30",
            # Step 8.2 newly added 6 element glasses (Eu, Br, Tl, Os, Th, U)
            "Eu2B4PbO10",
            "ZnBr2",
            "TlAsSe2",
            "OsO2",
            "BaYbThF9",
            "Na2USi2O8",
        }
        for exp_formula in expected_landmark_systems:
            self.assertIn(exp_formula, formulas_set, f"Landmark amorphous system {exp_formula} must be in amorphous_systems.json")

        # 2. Verify every single system in amorphous_systems.json has a verified DOI in the registry
        #    with HTTP 200 status, non-empty verified paper title, and matching publication year & author surname
        exp_bench_count = 0
        comp_recon_count = 0
        for sys_entry in systems:
            doi = sys_entry["reference_doi"].strip().lower()
            self.assertIn(doi, registry_by_doi, f"DOI {doi} for {sys_entry['formula']} must be in verified_doi_registry.json")
            reg = registry_by_doi[doi]
            self.assertEqual(reg.get("http_status"), 200, f"DOI {doi} must have HTTP 200 status in Crossref/OpenAlex")
            self.assertTrue(reg.get("title"), f"DOI {doi} must have a verified paper title")
            self.assertTrue(sys_entry.get("paper_title"), f"System {sys_entry['formula']} must have paper_title populated")
            year_str = str(reg.get("year", ""))
            if year_str and year_str != "None":
                self.assertIn(
                    year_str,
                    sys_entry["source_reference"],
                    f"System {sys_entry['formula']} source_reference '{sys_entry['source_reference']}' must contain verified year {year_str}",
                )

            # 3. Verify SRO/MRO structural characterization, explicit provenance indicators, and schema deduplication
            sc = sys_entry.get("structural_characterization")
            self.assertIsInstance(sc, dict, f"System {sys_entry['formula']} must have structural_characterization dict")
            self.assertIn("provenance", sc, f"Missing provenance block in structural_characterization for {sys_entry['formula']}")
            prov = sc["provenance"]
            self.assertIsInstance(prov.get("is_direct_experimental_benchmark"), bool)
            self.assertIn(
                prov.get("overall_type"),
                {"direct_experimental_benchmark", "composition_weighted_reconstruction"},
            )
            self.assertTrue(prov.get("composition_weighting_note"))
            if prov["is_direct_experimental_benchmark"]:
                exp_bench_count += 1
            else:
                comp_recon_count += 1
            self.assertTrue(prov.get("overall_badge"))
            self.assertTrue(prov.get("benchmark_reference"))
            self.assertGreaterEqual(prov.get("total_pair_count", 0), 1)
            self.assertGreaterEqual(prov.get("experimental_pair_count", 0), 0)

            # Verify duplicate alias arrays were removed
            self.assertNotIn("ring_voronoi_topology", sc)
            self.assertNotIn("sq_curve_points", sc["diffraction_sq"])
            self.assertNotIn("gr_curve_points", sc["rdf_gr"])
            self.assertNotIn("angle_distribution_points", sc["bond_angle_distribution"])
            self.assertNotIn("distribution", sc["ring_or_voronoi_distribution"])

            for req_sc_key in (
                "diffraction_sq",
                "rdf_gr",
                "bond_angle_distribution",
                "ring_or_voronoi_distribution",
            ):
                self.assertIn(req_sc_key, sc, f"Missing {req_sc_key} in structural_characterization for {sys_entry['formula']}")
                sec = sc[req_sc_key]
                self.assertIn("source_type", sec)
                self.assertIn("source_badge", sec)
                self.assertIn("source_detail", sec)
            self.assertGreater(sc["diffraction_sq"]["q1_inv_A"], 0.5)
            self.assertGreater(sc["rdf_gr"]["r1_A"], 1.0)
            self.assertGreater(len(sc["diffraction_sq"]["curve_points"]), 10)
            self.assertGreater(len(sc["rdf_gr"]["curve_points"]), 10)
            self.assertGreater(len(sc["bond_angle_distribution"]["curve_points"]), 10)
            self.assertGreaterEqual(len(sc["ring_or_voronoi_distribution"]["bars"]), 3)
            for pair_entry in sc["rdf_gr"].get("partial_pairs", []):
                self.assertIn("pair_source", pair_entry)
                self.assertIn("composition_weight", pair_entry)
                self.assertGreater(pair_entry["composition_weight"], 0.0)

        self.assertGreaterEqual(exp_bench_count, 35, "At least 35 systems must have direct experimental SRO/MRO benchmarks")
        self.assertGreaterEqual(comp_recon_count, 150, "Remaining systems must be flagged as composition-weighted reconstructions")

        # 3b. Verify genuine composition-sensitivity of S(Q), g(r), P(theta), and ring distribution
        sc_high_na = compute_system_structural_characterization(
            "Na4SiO4",
            "2Na2O-SiO2",
            "Oxide",
            atomic_fractions={"Na": 4 / 9, "Si": 1 / 9, "O": 4 / 9},
            coord_map={"Na": "Modifier cation (CN=6)", "Si": "SiO4 tetrahedra (CN=4)", "O": "Non-bridging oxygen"},
        )
        sc_low_na = compute_system_structural_characterization(
            "Na2Si4O9",
            "Na2O-4SiO2",
            "Oxide",
            atomic_fractions={"Na": 2 / 15, "Si": 4 / 15, "O": 9 / 15},
            coord_map={"Na": "Modifier cation (CN=6)", "Si": "SiO4 tetrahedra (CN=4)", "O": "Bridging oxygen"},
        )
        self.assertNotEqual(
            sc_high_na["diffraction_sq"]["q1_inv_A"],
            sc_low_na["diffraction_sq"]["q1_inv_A"],
            "S(Q) FSDP Q1 must shift with Na/Si stoichiometric ratio",
        )
        self.assertNotEqual(
            sc_high_na["rdf_gr"]["curve_points"],
            sc_low_na["rdf_gr"]["curve_points"],
            "g(r) curve points must vary with stoichiometric pair weights",
        )
        self.assertNotEqual(
            sc_high_na["ring_or_voronoi_distribution"]["bars"],
            sc_low_na["ring_or_voronoi_distribution"]["bars"],
            "Ring size distribution must shift with modifier-to-former ratio",
        )

        # 4. Verify zero off-topic / banned DOI prefixes exist anywhere in amorphous_systems.json or verified_doi_registry.json
        banned_doi_prefixes = (
            "10.1520/",  # ASTM industrial specifications
            "10.4271/",  # SAE aerospace specifications
            "10.22541/", # Authorea preprints
            "10.32657/", # Institutional repository theses
            "10.1016/b978-0-408-70932-3", # Smithells Metals Reference Book chapters
            "10.1007/10717201", # Landolt-Börnstein chapters
            "10.1021/bk-", # ACS Symposium Series
            "10.1149/ma", # ECS Meeting Abstracts
            "10.1093/clinchem/", # Clinical chemistry
            "10.1016/j.Watres.", # Water research
        )
        for sys_entry in systems:
            doi_low = sys_entry["reference_doi"].strip().lower()
            for bad_prefix in banned_doi_prefixes:
                self.assertFalse(
                    doi_low.startswith(bad_prefix.lower()),
                    f"System {sys_entry['formula']} has banned off-topic DOI {doi_low}",
                )

        # 5. Verify data/amorphous_periodic_table_118.json embeds verified paper_title,
        #    structural_characterization_summary provenance counts, and full shared_systems on co-occurrences
        ptable_payload = json.loads((ROOT / "data" / "amorphous_periodic_table_118.json").read_text(encoding="utf-8"))
        el_by_sym = {e["symbol"]: e for e in ptable_payload["elements"]}
        for new_sym in ("Eu", "Br", "Tl", "Os", "Th", "U"):
            self.assertTrue(el_by_sym[new_sym]["in_amorphous_dataset"], f"Element {new_sym} must be active in amorphous_periodic_table_118.json")
            self.assertGreaterEqual(el_by_sym[new_sym]["occurrence_count"], 1)

        for el in ptable_payload["elements"]:
            if el["occurrence_count"] > 0:
                self.assertIn("structural_characterization_summary", el)
                sro_sum = el["structural_characterization_summary"]
                self.assertTrue(
                    sro_sum.get("has_structural_data"),
                    f"Active element {el['symbol']} must have structural_characterization_summary.has_structural_data=True",
                )
                self.assertEqual(sro_sum.get("systems_with_sro_mro_count"), el["occurrence_count"])
                self.assertEqual(
                    sro_sum.get("direct_experimental_benchmark_count", 0)
                    + sro_sum.get("composition_weighted_reconstruction_count", 0),
                    el["occurrence_count"],
                )
                for vs in el["verified_systems"]:
                    v_doi = vs["reference_doi"].strip().lower()
                    self.assertIn(v_doi, registry_by_doi)
                    self.assertTrue(vs.get("paper_title"))
                    self.assertIn("structural_characterization", vs)
                    self.assertIn("provenance", vs["structural_characterization"])
                # Verify co-occurrences include all partners and shared_systems
                self.assertEqual(len(el["top_cooccurring_partners"]), el["partner_diversity"])
                for p_entry in el["top_cooccurring_partners"]:
                    self.assertIn("shared_systems", p_entry)
                    self.assertEqual(
                        len(p_entry["shared_systems"]),
                        p_entry["cooccurrence_count"],
                        f"shared_systems length must equal cooccurrence_count for {el['symbol']}-{p_entry['partner']}",
                    )
                for c_entry in el["top_correlations"]:
                    self.assertIn("shared_systems", c_entry)
                    self.assertEqual(
                        len(c_entry["shared_systems"]),
                        c_entry["co_occurrences"],
                        f"shared_systems length must equal co_occurrences for {el['symbol']}-{c_entry['partner']}",
                    )

        # 6. Verify interactive index.html contains the Amorphous Physics Guide Modal, Tab 5 SRO/MRO SVG plots, and provenance CSS classes
        html_text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("modalGuide", html_text)
        self.assertIn("openGuideModal", html_text)
        self.assertIn("pane-structure", html_text)
        self.assertIn("renderElementStructurePlots", html_text)
        self.assertIn("inspectSystemStructure", html_text)
        for css_cls in (
            ".sro-plot-card",
            ".sro-badge",
            ".sro-caption",
            ".partial-table",
            ".sro-svg",
            ".ring-bar-lbl",
            ".ring-bar-val",
            ".cooc-sys-list",
            ".cooc-sys-pill",
            ".prov-badge",
            ".prov-exp",
            ".prov-recon",
            ".prov-banner",
        ):
            self.assertIn(css_cls, html_text, f"Missing CSS rule {css_cls} in index.html")
        self.assertNotIn("201 Verified Inorganic", html_text)
        self.assertNotIn("S = 0–79", html_text)

    def test_step8_second_audit_remediations(self) -> None:
        """Verify all 7 remediation steps from the second ground-up audit."""
        from src.step2_parse_normalize import classify_synthesis_regime
        from src.structural_characterization_data import (
            DIRECT_EXPERIMENTAL_SRO_BENCHMARKS,
            _parse_cn_from_coord_map,
        )

        systems_payload = json.loads((ROOT / "amorphous_systems.json").read_text(encoding="utf-8"))
        systems = systems_payload["systems"]
        sys_by_formula = {s["formula"]: s for s in systems}
        sys_by_raw = {s["raw_formula"]: s for s in systems}

        # Step 1: Verify the 21 remediated DOIs match their exact compositions/papers
        expected_remediated_dois = {
            "BaSi2O5": "10.2138/am-2021-7910",
            "KAlSi3O8": "10.1016/0016-7037(79)90196-8",
            "Na2Mo2P2O12": "10.1016/s0167-577x(01)00245-2",
            "CoSiO3": "10.1016/s0022-3093(01)00660-0",
            "Ge2Sb2Se5": "10.1155/2018/7158079",
            "InGe3Se7": "10.3390/met5010102",
            "Fe40Ni40P14B6": "10.1007/bf00551801",
            "Fe76Si9B10P5": "10.2320/matertrans.mrp2007198",
            "Ce70Al10Cu20": "10.1016/j.actamat.2006.02.044",
            "Al86Ni8Ce6": "10.2320/matertrans1989.36.883",
            "Hf55Cu30Ni5Al10": "10.2320/matertrans.43.2357",
            "Mo52Cr14Fe14P12B8": "10.5006/0010-9312-36.10.577",
            "Cs2O-3B2O3": "10.1016/0022-3093(89)90425-0",
            "Ir45Ta55": "10.1007/bf00659342",
            "Li10GeP2S12": "10.1016/j.jnoncrysol.2010.05.016",
            "Ge20Sb5Se75": "10.1016/j.ceramint.2023.12.189",
            "Ag5In5Sb60Te30": "10.1063/1.2184428",
            "GeSe3": "10.3389/fmats.2019.00133",
            "ZrO2": "10.1039/c9ra01865d",
            "Pd40Cu30Ni10P20": "10.2320/matertrans1989.37.181",
            "MoS2": "10.1016/j.tsf.2020.138209",
        }
        for raw_f, exp_doi in expected_remediated_dois.items():
            self.assertTrue(raw_f in sys_by_raw, f"Raw formula {raw_f} must exist in amorphous_systems.json")
            self.assertEqual(
                sys_by_raw[raw_f]["reference_doi"].lower(),
                exp_doi.lower(),
                f"Expected DOI {exp_doi} for {raw_f}, got {sys_by_raw[raw_f]['reference_doi']}",
            )

        # Step 2: Verify 100% of DIRECT_EXPERIMENTAL_SRO_BENCHMARKS keys match a system in amorphous_systems.json
        for bench_key in DIRECT_EXPERIMENTAL_SRO_BENCHMARKS:
            matched = (bench_key in sys_by_formula) or (bench_key in sys_by_raw)
            self.assertTrue(
                matched,
                f"Benchmark key {bench_key} in DIRECT_EXPERIMENTAL_SRO_BENCHMARKS must match a system in amorphous_systems.json",
            )
        exp_benchmarks = [
            s for s in systems
            if s["structural_characterization"]["provenance"]["is_direct_experimental_benchmark"]
        ]
        self.assertEqual(len(exp_benchmarks), 44, "All 44 experimental SRO/MRO benchmarks must match")
        self.assertTrue(
            sys_by_formula["Pd40Ni10Cu30P20"]["structural_characterization"]["provenance"]["is_direct_experimental_benchmark"]
        )
        self.assertTrue(
            sys_by_formula["Pd42.5Ni7.5Cu30P20"]["structural_characterization"]["provenance"]["is_direct_experimental_benchmark"]
        )
        self.assertTrue(
            sys_by_formula["Zr50Cu50"]["structural_characterization"]["provenance"]["is_direct_experimental_benchmark"]
        )

        # Step 3: Verify synthesis regime classifier does not match 'mm' inside 'Commercial'
        self.assertEqual(
            classify_synthesis_regime(
                "Fe40Ni40P14B6",
                "Fe40Ni40B6P14",
                "Metallic Glass",
                "Diffuse XRD halo; TEM SAED; DSC Tg=668 K (Metglas 2826)",
                "Commercial Metglas 2826 ribbon where 20 at.% (P+B) metalloids vitrify Fe-Ni Permalloy.",
            )[0],
            "rapid_quenched_ribbon",
        )
        self.assertEqual(sys_by_raw["Fe40Ni40P14B6"]["synthesis_regime"], "rapid_quenched_ribbon")
        self.assertEqual(sys_by_raw["Fe48Cr15Mo14C15B6Y2"]["synthesis_regime"], "bulk_melt_quenched")

        # Step 4: Verify index.html dynamically injects exact synthesis regime and benchmark counts
        html_text = (ROOT / "index.html").read_text(encoding="utf-8")
        for expected_sub in (
            "Bulk Melt-Quenched (152)",
            "Rapid-Quenched Ribbon (31)",
            "Vapor / Thin-Film (58)",
            "Lit. Benchmark Peak Anchors + Parameterized Curve (44 Canonical Systems)",
        ):
            self.assertTrue(expected_sub in html_text, f"Expected '{expected_sub}' in index.html")
        for forbidden_sub in (
            "Bulk Melt-Quenched (151)",
            "Rapid-Quenched Ribbon (48)",
            "Vapor / Thin-Film (42)",
            "Lit. Benchmark Peak Anchors + Parameterized Curve (36 Canonical Systems)",
        ):
            self.assertFalse(forbidden_sub in html_text, f"Did not expect '{forbidden_sub}' in index.html")

        # Step 5: Verify _parse_cn_from_coord_map and heavy-metal fluoride / halide coordination numbers
        self.assertEqual(_parse_cn_from_coord_map("Zr", {"Zr": "ZrF7/ZrF8 polyhedra (CN=7-8)"}, 4.0), 7.5)
        self.assertEqual(_parse_cn_from_coord_map("Th", {"Th": "ThF8/ThF9 polyhedra (CN=8-9)"}, 6.0), 8.5)
        self.assertEqual(
            _parse_cn_from_coord_map(
                "Al",
                {"Al": "Tetrahedral AlO4 (CN=4, ~55%), pentahedral AlO5 (CN=5, ~35%), octahedral AlO6 (CN=6, ~10%)"},
                4.0,
            ),
            4.5,
        )
        zblan_pairs = {
            p["pair"]: p["cn_ij"]
            for p in sys_by_raw["Zr0.53Ba0.20La0.04Al0.03Na0.20F2.83"]["structural_characterization"]["rdf_gr"]["partial_pairs"]
        }
        self.assertEqual(zblan_pairs["Zr–F"], 7.5)
        self.assertEqual(zblan_pairs["Ba–F"], 9.0)
        self.assertEqual(zblan_pairs["Al–F"], 6.0)

        znbr2_pairs = {
            p["pair"]: p["cn_ij"]
            for p in sys_by_raw["ZnBr2"]["structural_characterization"]["rdf_gr"]["partial_pairs"]
        }
        self.assertEqual(znbr2_pairs["Zn–Br"], 4.0)

        # Step 6: Verify honest ring/Voronoi provenance badges and literature Voronoi bars
        allowed_topo_badges = {
            "🔬 Published RMC / AIMD Literature Ring / Voronoi Benchmark",
            "⚖️ Archetype-Guided Composition-Weighted Topology",
            "⚖️ Composition-Weighted Topological Reconstruction",
        }
        for s in systems:
            topo_sec = s["structural_characterization"]["ring_or_voronoi_distribution"]
            self.assertIn(topo_sec["source_badge"], allowed_topo_badges)
            self.assertNotEqual(topo_sec["source_badge"], "🔬 Literature RMC / AIMD Topology Benchmark")
        for bmg_f in ("Zr50Cu50", "Zr36Cu64", "Ni80P20", "Fe80B20"):
            self.assertEqual(
                sys_by_formula[bmg_f]["structural_characterization"]["ring_or_voronoi_distribution"]["source_badge"],
                "🔬 Published RMC / AIMD Literature Ring / Voronoi Benchmark",
            )

        # Step 7: Verify specific metallic glass sub-categories are preserved in statistical_analysis_results.json
        stats_data = json.loads((ROOT / "data" / "statistical_analysis_results.json").read_text(encoding="utf-8"))
        el_cat_by_sym = {
            e["element_symbol"]: e["structural_category"]
            for e in stats_data["element_statistics_by_frequency"]
        }
        self.assertEqual(el_cat_by_sym["Cu"], "Intermediate (Metallic Icosahedral Cluster Former)")
        self.assertEqual(el_cat_by_sym["Ni"], "Intermediate (Metallic Cluster Former)")
        self.assertEqual(el_cat_by_sym["Pd"], "Intermediate (Metallic Glass Host)")
        self.assertEqual(el_cat_by_sym["Cr"], "Intermediate (Metallic Passivator)")
        self.assertIn("metallic_glass_subcategories", stats_data["tetrahedral_sub_analysis"])

    def test_step9_third_audit_remediations(self) -> None:
        from src.catalog_oxides_chalcogenides import OXIDE_AND_CHALCOGENIDE_SYSTEMS
        from src.catalog_metals_covalent import METALS_COVALENT_AND_CONTROL_SYSTEMS
        from src.catalog_extended_systems import EXTENDED_AMORPHOUS_SYSTEMS
        from src.step2_parse_normalize import parse_molar_counts
        from src.step5_generate_report import CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES
        from src.structural_characterization_data import compute_system_structural_characterization

        systems_payload = json.loads((ROOT / "amorphous_systems.json").read_text(encoding="utf-8"))
        systems = systems_payload["systems"]
        sys_by_raw = {s["raw_formula"]: s for s in systems}

        # 1. Verify multi-anion and mixed-network systems have zero unphysical anion-anion pairs
        forbidden_anion_pairs = {"I–O", "O–I", "I–Te", "Te–I", "I–Se", "Se–I", "C–O", "O–C", "N–O", "O–N"}
        for s in systems:
            pairs = {p["pair"] for p in s["structural_characterization"]["rdf_gr"]["partial_pairs"]}
            overlap = pairs & forbidden_anion_pairs
            self.assertFalse(
                overlap,
                f"System {s['raw_formula']} ({s['formula']}) contains unphysical anion-anion pairs: {overlap}",
            )

        expected_secondary_pairs = {
            "AgI-AgPO3": {"Ag–I", "P–O", "Ag–O"},
            "CuI-Cu2O-MoO3": {"Cu–I", "Mo–O", "Cu–O"},
            "GeTe4I": {"Ge–I", "Ge–Te"},
            "SiOC0.4": {"Si–O", "Si–C"},
            "Ca0.5Si0.5O0.5C0.5": {"Si–O", "Si–C", "Ca–O"},
            "Y0.12Al0.22Si0.66O1.46N0.36": {"Si–O", "Si–N", "Al–O", "Al–N", "Y–O", "Y–N"},
            "SiB0.5C0.5N1.5": {"Si–N", "Si–C", "B–N", "C–N"},
            "BC2N": {"B–N", "B–C", "C–N"},
        }
        for raw_f, req_pairs in expected_secondary_pairs.items():
            actual_pairs = {
                p["pair"] for p in sys_by_raw[raw_f]["structural_characterization"]["rdf_gr"]["partial_pairs"]
            }
            self.assertTrue(
                req_pairs.issubset(actual_pairs),
                f"System {raw_f} missing expected pairs {req_pairs - actual_pairs} (got {actual_pairs})",
            )

        # Also unit-test multi-cation halochalcogenide GeAsSeI directly
        geassei_sc = compute_system_structural_characterization(
            "GeAsSeI", "GeAsSeI", "Chalcogenide", atomic_fractions={"Ge": 0.25, "As": 0.25, "Se": 0.25, "I": 0.25}
        )
        geassei_pairs = {p["pair"] for p in geassei_sc["rdf_gr"]["partial_pairs"]}
        self.assertTrue({"Ge–I", "As–I", "Ge–Se", "As–Se"}.issubset(geassei_pairs))
        self.assertFalse(geassei_pairs & forbidden_anion_pairs)

        # 2. Verify all 17 remediated catalog citations and 100% DOI registry synchronization
        expected_remediated_dois = {
            "Te4V2O13": "10.1016/j.molstruc.2008.02.009",
            "BaTi2O5": "10.1021/acs.jpcc.6b08248",
            "GeS2": "10.1016/s0022-3093(01)00667-6",
            "GeAsSe3": "10.1103/physrevb.66.134204",
            "GeTe4I": "10.1088/0953-8984/22/40/404207",
            "Fe78Si9B13": "10.1007/bf00445998",
            "Zr55Cu30Al10Ni5": "10.2320/matertrans1989.37.185",
            "Ti40Zr25Ni8Cu9Be18": "10.4028/www.scientific.net/msf.343-346.146",
            "Ti50Cu25Ni15Sn5Be5": "10.1007/978-3-662-64978-7_66",
            "Mo52Cr14Fe14P12B8": "10.5006/0010-9312-36.10.577",
            "Zn40Mg11Ca31Yb18": "10.1016/j.jnoncrysol.2018.02.028",
            "AlN": "10.1016/j.tsf.2011.09.079",
            "Ca0.5Si0.5O0.5C0.5": "10.3390/ma17246159",
            "Cs2O-3B2O3": "10.1016/0022-3093(89)90425-0",
            "BaO-4B2O3": "10.1007/s12633-016-9492-y",
            "Li10GeP2S12": "10.1016/j.jnoncrysol.2010.05.016",
            "Zr55Al10Ni5Cu29Nb1": "10.1016/j.msea.2015.11.063",
        }
        for raw_f, exp_doi in expected_remediated_dois.items():
            self.assertEqual(sys_by_raw[raw_f]["reference_doi"].lower(), exp_doi.lower())

        all_catalog_entries = (
            list(OXIDE_AND_CHALCOGENIDE_SYSTEMS)
            + list(METALS_COVALENT_AND_CONTROL_SYSTEMS)
            + list(EXTENDED_AMORPHOUS_SYSTEMS)
        )
        active_dois = {e[3].strip() for e in all_catalog_entries} | {
            ex["doi"].strip() for ex in CRYSTALLINE_TO_AMORPHOUS_CONVERSION_EXAMPLES
        }
        reg_payload = json.loads((ROOT / "data" / "verified_doi_registry.json").read_text(encoding="utf-8"))
        reg_dois = set(reg_payload["verified_dois"].keys())
        self.assertEqual(active_dois, reg_dois, "verified_doi_registry.json keys must match active catalog DOIs with 0 missing and 0 orphaned")

        # 3. Verify dynamic Silicon occurrence count in index.html and template tokens in build_interactive_table.py
        builder_src = (ROOT / "build_interactive_table.py").read_text(encoding="utf-8")
        self.assertIn("__SI_COUNT__", builder_src)
        self.assertNotIn("|| 241", builder_src)

        html_text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertTrue("CN=4 &middot; N=66" in html_text, "Expected CN=4 &middot; N=66 in index.html")
        self.assertTrue("2. Verified Systems (66)" in html_text, "Expected 2. Verified Systems (66) in index.html")
        self.assertFalse("CN=4 &middot; N=65" in html_text, "Unexpected stale CN=4 &middot; N=65 in index.html")
        self.assertFalse("2. Verified Systems (65)" in html_text, "Unexpected stale 2. Verified Systems (65) in index.html")

        # 4. Verify WO3-4TeO2 stoichiometry and molar-ratio docstring
        self.assertIn("WO3-4TeO2", sys_by_raw)
        self.assertNotIn("WO3-TeO2", sys_by_raw)
        self.assertEqual(sys_by_raw["WO3-4TeO2"]["formula"], "WTe4O11")
        self.assertIn("molar ratios", parse_molar_counts.__doc__ or "")

    def test_step10_fourth_audit_remediations(self) -> None:
        """Verify all 5 remediation steps from the fourth ground-up audit."""
        systems_payload = json.loads((ROOT / "amorphous_systems.json").read_text(encoding="utf-8"))
        systems = systems_payload["systems"]
        sys_by_raw = {s["formula"]: s for s in systems}
        sys_by_raw.update({s["raw_formula"]: s for s in systems})

        # Step 1: Verify SiH0.12 (a-Si:H) includes Si-Si (2.35 A) + Si-H (1.48 A) and Si0.5Ge0.5 includes Si-Ge, Si-Si, Ge-Ge
        sih_gr = sys_by_raw["SiH0.12"]["structural_characterization"]["rdf_gr"]
        sih_pairs = {p["pair"]: p["r_ij_A"] for p in sih_gr["partial_pairs"]}
        self.assertIn("Si–Si", sih_pairs)
        self.assertIn("Si–H", sih_pairs)
        self.assertEqual(sih_pairs["Si–Si"], 2.35)
        self.assertEqual(sih_pairs["Si–H"], 1.48)
        self.assertEqual(sih_gr["r1_A"], 2.35)

        sige_gr = sys_by_raw["Si0.5Ge0.5"]["structural_characterization"]["rdf_gr"]
        sige_pairs = {p["pair"]: p["r_ij_A"] for p in sige_gr["partial_pairs"]}
        self.assertEqual(set(sige_pairs.keys()), {"Si–Ge", "Si–Si", "Ge–Ge"})
        self.assertEqual(sige_pairs["Si–Ge"], 2.38)
        self.assertEqual(sige_pairs["Si–Si"], 2.35)
        self.assertEqual(sige_pairs["Ge–Ge"], 2.45)

        # Step 2: Verify first_shell_cn in modified oxides/oxynitrides/halides reports network-former CN (<= 7.5), not modifier cage CN
        for raw_f, max_cn in (
            ("Cs2O-3B2O3", 4.0),
            ("BaSi2O5", 4.0),
            ("KAlSi3O8", 4.0),
            ("Na2Si2O5", 4.0),
            ("Y0.12Al0.22Si0.66O1.46N0.36", 4.5),
            ("Al0.35Ca0.25Sr0.15Ba0.15Mg0.10F2.35", 6.0),
        ):
            gr_sec = sys_by_raw[raw_f]["structural_characterization"]["rdf_gr"]
            self.assertLessEqual(
                gr_sec["first_shell_cn"],
                max_cn,
                f"Expected network-former first_shell_cn <= {max_cn} for {raw_f}, got {gr_sec['first_shell_cn']}",
            )
            first_pair = gr_sec["partial_pairs"][0]["pair"]
            self.assertFalse(
                first_pair.startswith(("Cs–", "Ba–", "K–", "Na–", "Y–")),
                f"First partial pair of {raw_f} must be a network-former pair, got {first_pair}",
            )

        # Step 3: Verify Covalent Network bond angles and ring/polyhedral topologies differentiate halide, B12, pnictogen, sp2 BN, and nitride subclasses
        baalf_sc = sys_by_raw["Al0.35Ca0.25Sr0.15Ba0.15Mg0.10F2.35"]["structural_characterization"]
        self.assertAlmostEqual(baalf_sc["bond_angle_distribution"]["intra_polyhedral_angle_deg"], 90.0, delta=2.0)
        self.assertIn("MF6–MF8", baalf_sc["ring_or_voronoi_distribution"]["dominant_motif"])
        self.assertIn("Fluoroaluminate", baalf_sc["ring_or_voronoi_distribution"]["topology_type"])

        b_sc = sys_by_raw["B"]["structural_characterization"]
        self.assertAlmostEqual(b_sc["bond_angle_distribution"]["intra_polyhedral_angle_deg"], 60.0, delta=2.0)
        self.assertIn("B12", b_sc["ring_or_voronoi_distribution"]["dominant_motif"])

        for pnic in ("P", "Sb"):
            p_sc = sys_by_raw[pnic]["structural_characterization"]
            self.assertLess(p_sc["bond_angle_distribution"]["intra_polyhedral_angle_deg"], 103.0)
            self.assertIn("Pyramidal", p_sc["ring_or_voronoi_distribution"]["dominant_motif"])

        for sp2_f in ("BN", "BC2N"):
            sp2_sc = sys_by_raw[sp2_f]["structural_characterization"]
            self.assertGreaterEqual(sp2_sc["bond_angle_distribution"]["intra_polyhedral_angle_deg"], 114.0)
            self.assertIn("sp2", sp2_sc["ring_or_voronoi_distribution"]["topology_type"])
            self.assertIn("Borazine", sp2_sc["ring_or_voronoi_distribution"]["dominant_motif"])

        # Step 4: Verify modified thio-chalcogenides report covalent network-former r1_A and order network-former pairs first
        expected_chalc_r1 = {
            "Li3PS4": (2.04, "P–S"),
            "Na3PS4": (2.04, "P–S"),
            "Li7P3S11": (2.04, "P–S"),
            "Li10GeP2S12": (2.10, "Ge–S"),
            "Na2S-GeS2": (2.22, "Ge–S"),
            "Li2B2S4": (1.86, "B–S"),
            "3Li2S-B2S3": (1.86, "B–S"),
            "AgAsS2": (2.26, "As–S"),
            "Cu2GeSe3": (2.37, "Ge–Se"),
            "Tl2Se-As2Se3": (2.41, "As–Se"),
        }
        for raw_f, (exp_r1, exp_first_pair) in expected_chalc_r1.items():
            gr_sec = sys_by_raw[raw_f]["structural_characterization"]["rdf_gr"]
            self.assertAlmostEqual(
                gr_sec["r1_A"],
                exp_r1,
                delta=0.03,
                msg=f"Expected r1_A ~ {exp_r1} A for {raw_f}, got {gr_sec['r1_A']}",
            )
            self.assertEqual(
                gr_sec["partial_pairs"][0]["pair"],
                exp_first_pair,
                f"Expected first pair {exp_first_pair} for {raw_f}, got {gr_sec['partial_pairs'][0]['pair']}",
            )
            self.assertLessEqual(gr_sec["first_shell_cn"], 4.0)

        # Step 5: Verify build_interactive_table.py uses dynamic role/category tokens and CLAUDE.md documents 6 steps
        builder_src = (ROOT / "build_interactive_table.py").read_text(encoding="utf-8")
        for token in (
            "__COUNT_FULL__",
            "__COUNT_HALF__",
            "__COUNT_NONE__",
            "__COUNT_ACTIVE__",
            "__COUNT_TET__",
            "__COUNT_CAT_1A__",
            "__COUNT_CAT_1B__",
            "__COUNT_CAT_2A__",
            "__COUNT_CAT_2B__",
            "__COUNT_CAT_2C__",
        ):
            self.assertIn(token, builder_src, f"Expected dynamic token {token} in build_interactive_table.py")
        claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Step 6", claude_md)
        self.assertIn("structural_characterization_data.py", claude_md)

    def test_step11_vpn_fulltext_sro_mro_extraction(self) -> None:
        """Verify full-text VPN paper extraction artifacts and audited direct experimental SRO/MRO benchmarks."""
        vpn_summary_path = ROOT / "data" / "vpn_extracted_sro_mro.json"
        vpn_tables_path = ROOT / "data" / "vpn_extracted_structural_tables.json"
        self.assertTrue(vpn_summary_path.exists(), "data/vpn_extracted_sro_mro.json must exist")
        self.assertTrue(vpn_tables_path.exists(), "data/vpn_extracted_structural_tables.json must exist")

        vpn_summary = json.loads(vpn_summary_path.read_text(encoding="utf-8"))
        meta = vpn_summary["metadata"]
        self.assertEqual(meta["pdf_files_downloaded"], 72)
        self.assertEqual(meta["pdf_files_with_extractable_text"], 61)
        self.assertEqual(meta["scanned_image_pdfs_without_ocr"], 11)
        self.assertEqual(meta["elsevier_xml_metadata_stubs"], 72)
        self.assertEqual(meta["fulltext_files_downloaded"], 61)

        systems_payload = json.loads((ROOT / "amorphous_systems.json").read_text(encoding="utf-8"))
        sys_by_formula = {s["formula"]: s for s in systems_payload["systems"]}
        sys_by_raw = {s["raw_formula"]: s for s in systems_payload["systems"]}

        expected_replaced_catalog_dois = {
            "As2O3": "10.1016/0022-3093(89)90274-3",
            "LaAl3Si3O12": "10.1016/j.jnoncrysol.2010.01.017",
            "BaB4O7": "10.1063/5.0153282",
            "CaGa2O4": "10.1016/s0022-3093(87)80110-2",
            "LaTaB4O10": "10.1016/j.jallcom.2025.178622",
            "MnSiO3": "10.1016/j.jallcom.2019.07.012",
            "CdP2O6": "10.1016/s0022-3093(01)01049-3",
            "Al2O3-3P2O5": "10.1007/bf01197650",
        }
        for raw_f, exp_doi in expected_replaced_catalog_dois.items():
            self.assertEqual(sys_by_raw[raw_f]["reference_doi"].lower(), exp_doi.lower())

        expected_vpn_benchmarks = {
            "Al2O3": (2.11, 1.80, 2.90, "10.3389/fmats.2019.00038"),
            "Ta2O5": (2.04, 1.97, 3.74, "10.1063/1.4913586"),
            "As2S3": (1.24, 2.28, 3.52, "10.1103/physrevb.39.10342"),
            "As2Se3": (1.22, 2.42, 3.68, "10.1103/physrevb.78.064207"),
            "GeSe3": (1.06, 2.37, 3.85, "10.3389/fmats.2019.00133"),
            "GaN": (2.18, 1.95, 3.18, "10.1103/physrevlett.79.677"),
            "MoGe": (2.78, 2.65, 4.45, "10.1103/physrevb.37.2979"),
            "Zr50Cu40Al10": (2.71, 2.86, 4.78, "10.2320/matertrans.mbw200833"),
        }
        for formula, (exp_q1, exp_r1, exp_r2, exp_doi) in expected_vpn_benchmarks.items():
            self.assertIn(formula, sys_by_formula)
            sc = sys_by_formula[formula]["structural_characterization"]
            self.assertTrue(sc["provenance"]["is_direct_experimental_benchmark"])
            self.assertEqual(sc["diffraction_sq"]["q1_inv_A"], exp_q1)
            self.assertEqual(sc["rdf_gr"]["r1_A"], exp_r1)
            self.assertEqual(sc["rdf_gr"]["r2_A"], exp_r2)
            self.assertIn(exp_doi, sc["provenance"]["benchmark_reference"])

        # Ensure EXAFS/TEM-RDF-only papers (BN, GeAsSe3, GeSi) and non-diffraction papers (As2O3, BaB4O7)
        # are NOT falsely flagged as full diffraction+RDF+angle experimental benchmarks
        for non_full_bench in ("BN", "GeAsSe3", "GeSi", "As2O3", "BaB4O7"):
            sc = sys_by_formula[non_full_bench]["structural_characterization"]
            self.assertFalse(
                sc["provenance"]["is_direct_experimental_benchmark"],
                f"{non_full_bench} must not be marked as a full diffraction/RDF/angle benchmark",
            )
            self.assertEqual(sc["diffraction_sq"]["source_type"], "composition_weighted_reconstruction")
        # Verify GaN does not claim an experimental ring percentage breakdown
        self.assertEqual(
            sys_by_formula["GaN"]["structural_characterization"]["ring_or_voronoi_distribution"]["source_type"],
            "composition_weighted_reconstruction",
        )


if __name__ == "__main__":
    unittest.main()

