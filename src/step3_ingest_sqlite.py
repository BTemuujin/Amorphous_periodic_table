"""Step 3: Local Database Ingestion.

Ingests `amorphous_systems.json` into a local SQLite database named
`amorphous_materials.db` with two tables:
- `materials (id, formula, class, verification_method, reference_doi, ...)`
- `material_elements (material_id, element_symbol, atomic_fraction, tetrahedral_coordination_flag, ...)`

Indexes `element_symbol` and `formula` to optimize lookup efficiency.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS material_elements;
DROP TABLE IF EXISTS materials;

CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    formula TEXT NOT NULL,
    raw_formula TEXT,
    class TEXT NOT NULL,
    synthesis_regime TEXT,
    synthesis_regime_label TEXT,
    verification_method TEXT NOT NULL,
    reference_doi TEXT NOT NULL,
    source_reference TEXT,
    paper_title TEXT,
    system_tetrahedral_flag INTEGER NOT NULL DEFAULT 0,
    crystalline_conversion_note TEXT,
    fsdp_q1_inv_A REAL,
    r1_bond_length_A REAL,
    mean_bond_angle_deg REAL,
    dominant_ring_or_voronoi TEXT,
    structural_characterization_json TEXT
);

CREATE TABLE material_elements (
    material_id INTEGER NOT NULL,
    element_symbol TEXT NOT NULL,
    atomic_fraction REAL NOT NULL,
    tetrahedral_coordination_flag INTEGER NOT NULL DEFAULT 0,
    coordination_environment TEXT,
    element_role TEXT,
    PRIMARY KEY (material_id, element_symbol),
    FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX idx_materials_formula ON materials(formula);
CREATE INDEX idx_material_elements_symbol ON material_elements(element_symbol);
CREATE INDEX idx_material_elements_tet_flag ON material_elements(tetrahedral_coordination_flag);
"""


def ingest_amorphous_systems_to_sqlite(
    json_path: Path, db_path: Path
) -> Dict[str, Any]:
    """Load `amorphous_systems.json` and populate `amorphous_materials.db`."""
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    systems: List[Dict[str, Any]] = payload.get("systems", [])

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.executescript(SCHEMA_DDL)

        materials_inserted = 0
        elements_inserted = 0

        for sys_entry in systems:
            formula = sys_entry["formula"]
            raw_formula = sys_entry.get("raw_formula", formula)
            sc = sys_entry.get("structural_characterization") or {}
            diff_sq = sc.get("diffraction_sq") or {}
            rdf = sc.get("rdf_gr") or {}
            bad = sc.get("bond_angle_distribution") or {}
            ring_vor = sc.get("ring_or_voronoi_distribution") or {}

            cur.execute(
                """
                INSERT INTO materials (
                    formula, raw_formula, class, synthesis_regime, synthesis_regime_label,
                    verification_method, reference_doi, source_reference, paper_title,
                    system_tetrahedral_flag, crystalline_conversion_note,
                    fsdp_q1_inv_A, r1_bond_length_A, mean_bond_angle_deg,
                    dominant_ring_or_voronoi, structural_characterization_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    formula,
                    raw_formula,
                    sys_entry["material_class"],
                    sys_entry.get("synthesis_regime", "bulk_melt_quenched"),
                    sys_entry.get("synthesis_regime_label", "Bulk Melt-Quenched Glass"),
                    sys_entry["verification_method"],
                    sys_entry["reference_doi"],
                    sys_entry.get("source_reference", ""),
                    sys_entry.get("paper_title", ""),
                    int(sys_entry.get("system_tetrahedral_flag", 0)),
                    sys_entry.get("crystalline_conversion_note", ""),
                    float(diff_sq["q1_inv_A"]) if "q1_inv_A" in diff_sq else None,
                    float(rdf["r1_A"]) if "r1_A" in rdf else None,
                    float(bad["intra_polyhedral_angle_deg"]) if "intra_polyhedral_angle_deg" in bad else None,
                    ring_vor.get("dominant_motif", ""),
                    json.dumps(sc, ensure_ascii=False) if sc else "",
                ),
            )
            material_id = cur.lastrowid
            materials_inserted += 1

            for el_entry in sys_entry.get("elements", []):
                cur.execute(
                    """
                    INSERT INTO material_elements (
                        material_id, element_symbol, atomic_fraction,
                        tetrahedral_coordination_flag, coordination_environment,
                        element_role
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        material_id,
                        el_entry["element_symbol"],
                        float(el_entry["atomic_fraction"]),
                        int(el_entry["tetrahedral_coordination_flag"]),
                        el_entry.get("coordination_environment", ""),
                        el_entry.get("element_role", ""),
                    ),
                )
                elements_inserted += 1

        conn.commit()

        # Verify indexes via EXPLAIN QUERY PLAN
        cur.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM materials WHERE formula = 'SiO2'"
        )
        formula_plan = [row[-1] for row in cur.fetchall()]

        cur.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM material_elements WHERE element_symbol = 'Si'"
        )
        element_plan = [row[-1] for row in cur.fetchall()]

        return {
            "db_path": str(db_path),
            "materials_count": materials_inserted,
            "material_elements_count": elements_inserted,
            "formula_query_plan": formula_plan,
            "element_symbol_query_plan": element_plan,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    json_file = root / "amorphous_systems.json"
    db_file = root / "amorphous_materials.db"
    stats = ingest_amorphous_systems_to_sqlite(json_file, db_file)
    print(
        f"[Step 3] Ingested {stats['materials_count']} materials and "
        f"{stats['material_elements_count']} constituent rows into {db_file}"
    )
