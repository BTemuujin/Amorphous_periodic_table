"""End-to-End Orchestrator for the Amorphous Periodic Table Pipeline.

Executes Steps 1 through 5 sequentially and updates Beads (`bd`) issue tracking
states at each stage transition.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.step1_retrieve_literature import build_raw_amorphous_dataset
from src.step2_parse_normalize import run_step2_normalization
from src.step3_ingest_sqlite import ingest_amorphous_systems_to_sqlite
from src.step4_statistical_analysis import run_step4_analysis
from src.step5_generate_report import generate_markdown_report
from src.step6_build_periodic_table_data import build_periodic_table_118
from generate_amorphous_table import render_periodic_table
from build_interactive_table import build_interactive_html

EPIC_ID = "Amorphous_periodic_table-3k9"
STEP_IDS = {
    1: "Amorphous_periodic_table-3k9.1",
    2: "Amorphous_periodic_table-3k9.2",
    3: "Amorphous_periodic_table-3k9.3",
    4: "Amorphous_periodic_table-3k9.4",
    5: "Amorphous_periodic_table-3k9.5",
    6: "Amorphous_periodic_table-wzy",
}


def run_bd_cmd(args: list[str], cwd: Path) -> None:
    """Run a `bd` CLI command to keep Beads issue status synchronized."""
    try:
        res = subprocess.run(
            ["bd"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout.strip():
            print(f"  [bd] {res.stdout.strip()}")
    except Exception as exc:
        print(f"  [bd warning] {exc}")


def main() -> None:
    root = Path(__file__).resolve().parent
    raw_json = root / "data" / "raw_amorphous_records.json"
    norm_json = root / "amorphous_systems.json"
    sqlite_db = root / "amorphous_materials.db"
    stats_json = root / "data" / "statistical_analysis_results.json"
    report_md = root / "amorphous_periodic_table_report.md"
    ptable_118_json = root / "data" / "amorphous_periodic_table_118.json"
    interactive_html = root / "index.html"
    run_live = "--skip-online" not in sys.argv

    print("=== Step 1: Literature and Database Retrieval ===")
    run_bd_cmd(["reopen", STEP_IDS[1]], root)
    s1 = build_raw_amorphous_dataset(raw_json, run_live_queries=run_live)
    print(f"  Retrieved {s1['metadata']['total_records']} raw experimental records -> {raw_json}")
    run_bd_cmd(
        ["close", STEP_IDS[1], "--reason", f"Completed Step 1: retrieved {s1['metadata']['total_records']} records into data/raw_amorphous_records.json"],
        root,
    )

    print("\n=== Step 2: Data Parsing and Normalization ===")
    run_bd_cmd(["reopen", STEP_IDS[2]], root)
    s2 = run_step2_normalization(raw_json, norm_json)
    print(
        f"  Normalized {s2['metadata']['total_normalized_inorganic_systems']} inorganic amorphous systems "
        f"(filtered {s2['metadata']['filtered_organic_records_count']} organic controls) -> {norm_json}"
    )
    run_bd_cmd(
        ["close", STEP_IDS[2], "--reason", f"Completed Step 2: exported {s2['metadata']['total_normalized_inorganic_systems']} normalized inorganic systems to amorphous_systems.json"],
        root,
    )

    print("\n=== Step 3: Local Database Ingestion ===")
    run_bd_cmd(["reopen", STEP_IDS[3]], root)
    s3 = ingest_amorphous_systems_to_sqlite(norm_json, sqlite_db)
    print(
        f"  Ingested {s3['materials_count']} materials and {s3['material_elements_count']} "
        f"material_elements rows into {sqlite_db}"
    )
    print(f"  Formula index plan: {s3['formula_query_plan']}")
    print(f"  Element index plan: {s3['element_symbol_query_plan']}")
    run_bd_cmd(
        ["close", STEP_IDS[3], "--reason", f"Completed Step 3: ingested {s3['materials_count']} systems and {s3['material_elements_count']} element rows into amorphous_materials.db with indexes"],
        root,
    )

    print("\n=== Step 4: Statistical and Elemental Attribution Analysis ===")
    run_bd_cmd(["reopen", STEP_IDS[4]], root)
    s4 = run_step4_analysis(sqlite_db, stats_json)
    print(
        f"  Analyzed {s4['metadata']['total_unique_elements']} unique elements across "
        f"{s4['metadata']['total_amorphous_materials']} systems -> {stats_json}"
    )
    run_bd_cmd(
        ["close", STEP_IDS[4], "--reason", f"Completed Step 4: computed frequencies, co-occurrence matrix, Pearson/MI correlations, and tetrahedral network former sub-analysis"],
        root,
    )

    print("\n=== Step 5: Final Classification and Export ===")
    run_bd_cmd(["reopen", STEP_IDS[5]], root)
    generate_markdown_report(stats_json, report_md)
    print(f"  Generated Markdown report -> {report_md}")
    run_bd_cmd(
        ["close", STEP_IDS[5], "--reason", "Completed Step 5: generated amorphous_periodic_table_report.md"],
        root,
    )

    print("\n=== Step 6: Interactive Amorphous Periodic Table & 300 DPI Poster ===")
    run_bd_cmd(["reopen", STEP_IDS[6]], root)
    build_periodic_table_118()
    render_periodic_table()
    build_interactive_html(ptable_118_json, interactive_html)
    run_bd_cmd(
        ["close", STEP_IDS[6], "--reason", "Completed Step 6: built data/amorphous_periodic_table_118.json, amorphous_periodic_table.png (300 DPI), and index.html"],
        root,
    )

    run_bd_cmd(["reopen", EPIC_ID], root)
    run_bd_cmd(
        ["close", EPIC_ID, "--reason", "All 6 pipeline steps completed and verified."],
        root,
    )
    run_bd_cmd(["export", "-o", ".beads/issues.jsonl"], root)


if __name__ == "__main__":
    main()
