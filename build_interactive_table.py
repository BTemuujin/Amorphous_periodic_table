#!/usr/bin/env python3
"""
build_interactive_table.py

Reads `data/amorphous_periodic_table_118.json` and compiles a self-contained,
publication-grade interactive web application (`index.html`) modeled after
`mag_periodic_table/build_interactive_table.py`.

Visual & Scientific Features:
- Full Cell Coloring (49 elements): Elements that make amorphous phase formation possible
  (Network Formers & Intermediates across Oxide, Chalcogenide, Covalent, and Metallic glasses).
- Diagonal 50/50 Half-Split Cell Coloring (28 elements): Elements that participate in
  reported amorphous systems as Network Modifiers, Charge Compensators, or BMG Cages.
- Uncolored / White Cells (41 elements): Elements with zero verified inorganic amorphous
  systems in `amorphous_materials.db`.
- Interactive Box 1 (How to Read Each Element Cell + Full/Half/White Fill Key) and
  Box 2 (Clickable Structural Role Legend).
- Filter & Search Toolbar (Filter by Full/Half/Unreported, Structural Category, Glass Class,
  Synthesis Regime [Bulk Melt-Quenched, Rapid-Quenched Ribbon/Splat, Vapor/Thin-Film],
  Tetrahedral Motif ◆, Heatmap Coloring Mode, or search by Symbol/Name/Z/Chemical Formula).
- Slide-Out Element Inspection Drawer with 5 tabs:
  1. Overview & Interactive Three.js 3D WebGL Local Coordination Viewer
  2. Verified Amorphous Systems (`amorphous_materials.db`) with clickable DOIs & synthesis regimes
  3. Co-Occurrence & Correlation Metrics (Pearson phi, stoichiometric r, NMI)
  4. Glass-Forming Mechanism, Conversion Benchmarks & Atomic/Crystalline Reference
  5. Diffraction S(Q), Radial/Partial Distribution g(r), Bond Angles & Ring/Voronoi Topology
"""

import argparse
import copy
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_JSON = SCRIPT_DIR / "data" / "amorphous_periodic_table_118.json"
DEFAULT_HTML = SCRIPT_DIR / "index.html"


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Interactive Amorphous Periodic Table — 118 Elements &amp; __TOTAL_SYS__ Verified Systems</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<style>
  :root {
    --bg-main: #F8FAFC;
    --card-bg: #FFFFFF;
    --text-dark: #0F172A;
    --text-muted: #475569;
    --text-light: #94A3B8;
    --border-subtle: #CBD5E1;
    --accent-blue: #0284C7;
    --accent-indigo: #4F46E5;
    --tet-diamond: #0369A1;

    /* Category Palette */
    --cat-tet-former: #7EC8E3;
    --cat-tet-former-b: #0284C7;
    --cat-anion-former: #A7F3D0;
    --cat-anion-former-b: #059669;
    --cat-cond-tet: #C4B5FD;
    --cat-cond-tet-b: #7C3AED;
    --cat-poly-interm: #FDE68A;
    --cat-poly-interm-b: #D97706;
    --cat-bmg-interm: #FDBA74;
    --cat-bmg-interm-b: #EA580C;
    --cat-modifier: #F9A8D4;
    --cat-modifier-b: #DB2777;
    --cat-unreported: #FFFFFF;
    --cat-unreported-b: #CBD5E1;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  body {
    background-color: var(--bg-main);
    color: var(--text-dark);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    padding: 16px 22px 32px;
    min-height: 100vh;
    overflow-x: auto;
  }

  .app-container {
    min-width: 1320px;
    max-width: 1760px;
    margin: 0 auto;
    position: relative;
  }

  /* HEADER & KPI BAR */
  .top-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 14px;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid #E2E8F0;
  }

  .title-group h1 {
    font-size: 30px;
    font-weight: 900;
    letter-spacing: -0.6px;
    color: var(--text-dark);
    line-height: 1.1;
  }

  .title-group p {
    font-size: 13.5px;
    font-weight: 600;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .kpi-strip {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .kpi-pill {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 11px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  }
  .kpi-pill:hover {
    border-color: var(--accent-blue);
    transform: translateY(-1px);
  }
  .kpi-pill.active-filter {
    border-color: var(--accent-blue);
    background: #F0F9FF;
    box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.18);
  }
  .kpi-pill .kpi-val {
    font-size: 15px;
    font-weight: 900;
    color: var(--text-dark);
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .kpi-pill .kpi-lbl {
    font-size: 10.5px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  /* TOOLBAR: SEARCH, FILTERS & HEATMAP MODE */
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    padding: 9px 13px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .toolbar-label {
    font-size: 11px;
    font-weight: 800;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-right: 2px;
  }

  .filter-btn {
    border: 1px solid #CBD5E1;
    background: #F8FAFC;
    color: var(--text-dark);
    font-size: 11.5px;
    font-weight: 700;
    padding: 5px 10px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.14s ease;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .filter-btn:hover {
    background: #E2E8F0;
  }
  .filter-btn.active {
    background: #0F172A;
    color: #FFFFFF;
    border-color: #0F172A;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .mode-select {
    font-size: 12px;
    font-weight: 700;
    color: var(--text-dark);
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 9px;
    cursor: pointer;
  }

  .search-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }
  .search-input {
    width: 265px;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 26px 6px 10px;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    background: #F8FAFC;
    color: var(--text-dark);
    outline: none;
    transition: border-color 0.15s;
  }
  .search-input:focus {
    border-color: var(--accent-blue);
    background: #FFFFFF;
  }
  .search-clear {
    position: absolute;
    right: 7px;
    font-size: 13px;
    color: var(--text-muted);
    cursor: pointer;
    display: none;
    background: none;
    border: none;
    font-weight: 800;
  }

  /* PERIODIC TABLE 18-COLUMN GRID */
  .ptable-grid {
    display: grid;
    grid-template-columns: 32px repeat(18, minmax(66px, 1fr));
    grid-template-rows: 22px repeat(7, 74px) 18px repeat(2, 74px);
    gap: 5px;
    position: relative;
    user-select: none;
  }

  .group-label {
    display: flex;
    align-items: flex-end;
    justify-content: center;
    font-size: 12.5px;
    font-weight: 800;
    color: #64748B;
    padding-bottom: 3px;
  }

  .period-label {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 800;
    color: #64748B;
  }

  .series-row-label {
    grid-column: 2 / 4;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-end;
    padding-right: 8px;
    font-size: 11.5px;
    font-weight: 800;
    color: var(--text-dark);
    text-align: right;
    line-height: 1.2;
  }

  /* ELEMENT CELL */
  .el-cell {
    position: relative;
    border-width: 1.8px;
    border-style: solid;
    border-radius: 5px;
    padding: 3px 4px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    cursor: pointer;
    transition: transform 0.14s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.14s ease, opacity 0.18s ease;
    overflow: hidden;
    background: #FFFFFF;
  }

  /* FULL FILL: Makes amorphous phase possible */
  .el-cell.fill-full {
    background: var(--cell-bg);
    border-color: var(--cell-border);
  }

  /* DIAGONAL 50/50 HALF FILL: Part of reported amorphous systems */
  .el-cell.fill-half {
    background: linear-gradient(
      135deg,
      var(--cell-bg) 0%,
      var(--cell-bg) 49.0%,
      var(--cell-border) 49.3%,
      var(--cell-border) 50.7%,
      #FFFFFF 51.0%,
      #FFFFFF 100%
    );
    border-color: var(--cell-border);
  }

  /* UNCOLORED: Unreported in inorganic amorphous catalog */
  .el-cell.fill-none {
    background: #FFFFFF;
    border-color: #CBD5E1;
    color: #94A3B8;
  }

  /* Radioactive Diagonal Hatching Overlay */
  .el-cell.radioactive::before {
    content: "";
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      -45deg,
      rgba(71, 85, 105, 0.16),
      rgba(71, 85, 105, 0.16) 2px,
      transparent 2px,
      transparent 6px
    );
    pointer-events: none;
    z-index: 1;
  }

  .el-cell:hover {
    transform: scale(1.13);
    z-index: 30;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.20);
  }

  .el-cell.selected {
    outline: 3px solid #0F172A;
    outline-offset: 1px;
    z-index: 25;
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.24);
  }

  .el-cell.dimmed {
    opacity: 0.16;
    filter: grayscale(70%);
  }

  .el-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    font-size: 10.5px;
    font-weight: 800;
    line-height: 1;
    z-index: 2;
  }

  .el-z {
    color: inherit;
  }

  .el-tet-badge {
    color: var(--tet-diamond);
    font-size: 11px;
    line-height: 1;
    text-shadow: 0 0 2px #FFFFFF, 0 0 3px #FFFFFF;
  }

  .el-sym {
    font-size: 20px;
    font-weight: 900;
    text-align: center;
    line-height: 1.05;
    letter-spacing: -0.4px;
    z-index: 2;
    text-shadow: 0 0 3px rgba(255, 255, 255, 0.85);
  }

  .el-role {
    font-size: 8.8px;
    font-weight: 700;
    text-align: center;
    color: #334155;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.05;
    z-index: 2;
    text-shadow: 0 0 3px rgba(255, 255, 255, 0.9);
  }
  .el-cell.fill-none .el-role {
    color: #94A3B8;
    font-weight: 600;
  }

  .el-metric {
    font-size: 9px;
    font-weight: 800;
    text-align: center;
    color: #0F172A;
    white-space: nowrap;
    line-height: 1.05;
    z-index: 2;
    text-shadow: 0 0 3px rgba(255, 255, 255, 0.95);
  }
  .el-cell.fill-none .el-metric {
    color: #CBD5E1;
    font-weight: 600;
  }

  /* PLACEHOLDER CELLS (57-71 & 89-103) */
  .placeholder-cell {
    border: 1.5px dashed #94A3B8;
    border-radius: 5px;
    background: #F1F5F9;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 800;
    color: #475569;
    line-height: 1.25;
  }
  .placeholder-cell span {
    font-size: 10px;
    font-weight: 600;
    color: #64748B;
  }

  /* BOX 1 & BOX 2 IN THE TOP PERIODIC TABLE GAP (COLS 4..13, ROWS 2..4) */
  .info-box {
    background: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 9px;
    padding: 8px 11px;
    box-shadow: 0 2px 5px rgba(15, 23, 42, 0.04);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
    z-index: 5;
  }

  .box1-container {
    grid-column: 4 / 9;
    grid-row: 2 / 5;
  }

  .box2-container {
    grid-column: 9 / 14;
    grid-row: 2 / 5;
  }

  .box-header {
    font-size: 11px;
    font-weight: 900;
    color: var(--text-dark);
    letter-spacing: 0.3px;
    text-transform: uppercase;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 3px;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .box1-top {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .sample-cell {
    width: 86px;
    height: 94px;
    background: var(--cat-tet-former);
    border: 2px solid var(--cat-tet-former-b);
    border-radius: 6px;
    padding: 5px 6px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex-shrink: 0;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(2, 132, 199, 0.16);
    transition: transform 0.15s ease;
  }
  .sample-cell:hover {
    transform: scale(1.04);
  }

  .sample-cell .sc-top {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 800;
  }
  .sample-cell .sc-sym {
    font-size: 26px;
    font-weight: 900;
    text-align: center;
    line-height: 1;
  }
  .sample-cell .sc-role {
    font-size: 10px;
    font-weight: 700;
    text-align: center;
    color: #334155;
  }
  .sample-cell .sc-metric {
    font-size: 10.5px;
    font-weight: 800;
    text-align: center;
  }

  .sample-callouts {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 10.5px;
    font-weight: 700;
    color: var(--text-dark);
  }
  .sample-callouts div {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .callout-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-blue);
    flex-shrink: 0;
  }

  .fill-mode-key {
    display: flex;
    flex-direction: column;
    gap: 4px;
    border-top: 1px solid #E2E8F0;
    padding-top: 5px;
    margin-top: 4px;
  }

  .fm-row {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 10px;
    font-weight: 700;
    color: var(--text-dark);
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 4px;
    transition: background 0.12s;
  }
  .fm-row:hover {
    background: #F1F5F9;
  }

  .fm-swatch {
    width: 22px;
    height: 14px;
    border-radius: 3px;
    flex-shrink: 0;
    border: 1.5px solid #0284C7;
  }
  .fm-swatch.full {
    background: #7EC8E3;
    border-color: #0284C7;
  }
  .fm-swatch.half {
    background: linear-gradient(135deg, #F9A8D4 0%, #F9A8D4 49%, #DB2777 50%, #FFFFFF 51%, #FFFFFF 100%);
    border-color: #DB2777;
  }
  .fm-swatch.none {
    background: #FFFFFF;
    border-color: #CBD5E1;
  }

  /* BOX 2: LEGEND */
  .legend-grid {
    display: flex;
    flex-direction: column;
    gap: 3.5px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 2px 5px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.12s ease;
  }
  .legend-item:hover {
    background: #F1F5F9;
  }
  .legend-item.active {
    background: #E0F2FE;
    outline: 1px solid #0284C7;
  }

  .legend-swatch {
    width: 22px;
    height: 15px;
    border-radius: 3px;
    border-width: 1.5px;
    border-style: solid;
    flex-shrink: 0;
  }
  .legend-swatch.half-swatch {
    background: linear-gradient(135deg, #F9A8D4 0%, #F9A8D4 49%, #DB2777 50%, #FFFFFF 51%, #FFFFFF 100%) !important;
  }

  .legend-text {
    display: flex;
    flex-direction: column;
    line-height: 1.15;
    overflow: hidden;
  }
  .legend-title {
    font-size: 10.2px;
    font-weight: 800;
    color: var(--text-dark);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .legend-desc {
    font-size: 8.9px;
    font-weight: 600;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .legend-footer {
    border-top: 1px solid #E2E8F0;
    padding-top: 3px;
    font-size: 9.6px;
    font-weight: 800;
    color: var(--text-dark);
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
  }
  .legend-footer:hover {
    color: var(--accent-blue);
  }

  /* FOOTNOTE */
  .footer-notes {
    margin-top: 16px;
    padding: 12px 16px;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    font-size: 11.5px;
    color: var(--text-muted);
    line-height: 1.5;
  }
  .footer-notes strong {
    color: var(--text-dark);
  }

  /* SLIDE-OUT INSPECTION DRAWER */
  .drawer-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.35);
    backdrop-filter: blur(2px);
    z-index: 100;
    display: none;
    opacity: 0;
    transition: opacity 0.2s ease;
  }
  .drawer-backdrop.open {
    display: block;
    opacity: 1;
  }

  .inspection-drawer {
    position: fixed;
    top: 0;
    right: -700px;
    width: 660px;
    max-width: 94vw;
    height: 100vh;
    background: #FFFFFF;
    box-shadow: -8px 0 30px rgba(15, 23, 42, 0.22);
    z-index: 110;
    display: flex;
    flex-direction: column;
    transition: right 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    border-left: 1px solid #CBD5E1;
  }
  .inspection-drawer.open {
    right: 0;
  }

  .drawer-header {
    padding: 16px 20px;
    border-bottom: 1px solid #E2E8F0;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 14px;
    background: #F8FAFC;
  }

  .drawer-el-head {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .drawer-el-badge {
    width: 68px;
    height: 74px;
    border-radius: 8px;
    border: 2.5px solid #0284C7;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 4px 6px;
    flex-shrink: 0;
    box-shadow: 0 3px 8px rgba(15, 23, 42, 0.12);
  }
  .drawer-el-badge.fill-half {
    background: linear-gradient(
      135deg,
      var(--cell-bg) 0%,
      var(--cell-bg) 49%,
      var(--cell-border) 50%,
      #FFFFFF 51%,
      #FFFFFF 100%
    );
  }
  .drawer-el-badge .db-top {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    font-weight: 800;
  }
  .drawer-el-badge .db-sym {
    font-size: 25px;
    font-weight: 900;
    text-align: center;
    line-height: 1;
  }
  .drawer-el-badge .db-mass {
    font-size: 9.5px;
    font-weight: 700;
    text-align: center;
    color: #334155;
  }

  .drawer-title-meta h2 {
    font-size: 22px;
    font-weight: 900;
    color: var(--text-dark);
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .fill-mode-tag {
    font-size: 10.5px;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .fill-mode-tag.full {
    background: #E0F2FE;
    color: #0369A1;
    border: 1px solid #7DD3FC;
  }
  .fill-mode-tag.half {
    background: #FCE7F3;
    color: #BE185D;
    border: 1px solid #F9A8D4;
  }
  .fill-mode-tag.none {
    background: #F1F5F9;
    color: #64748B;
    border: 1px solid #CBD5E1;
  }

  .drawer-subtitle {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text-muted);
    margin-top: 3px;
  }

  .drawer-close-btn {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    width: 32px;
    height: 32px;
    font-size: 18px;
    font-weight: 800;
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .drawer-close-btn:hover {
    background: #F1F5F9;
    color: var(--text-dark);
  }

  /* DRAWER TABS */
  .drawer-tabs {
    display: flex;
    border-bottom: 1px solid #E2E8F0;
    background: #FFFFFF;
    padding: 0 16px;
    gap: 4px;
  }

  .drawer-tab {
    padding: 10px 12px;
    font-size: 12px;
    font-weight: 800;
    color: var(--text-muted);
    background: none;
    border: none;
    border-bottom: 2.5px solid transparent;
    cursor: pointer;
    transition: all 0.14s;
  }
  .drawer-tab:hover {
    color: var(--text-dark);
  }
  .drawer-tab.active {
    color: var(--accent-blue);
    border-bottom-color: var(--accent-blue);
  }

  .drawer-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px 28px;
  }

  .tab-pane {
    display: none;
  }
  .tab-pane.active {
    display: block;
  }

  /* 3D VIEWER CARD */
  .viewer-card {
    background: #0F172A;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 16px;
    border: 1px solid #334155;
    color: #F8FAFC;
  }

  .viewer-header {
    padding: 10px 14px;
    background: rgba(30, 41, 59, 0.9);
    border-bottom: 1px solid #334155;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .viewer-title-block h3 {
    font-size: 13.5px;
    font-weight: 800;
    color: #38BDF8;
  }
  .viewer-title-block p {
    font-size: 11px;
    color: #CBD5E1;
    margin-top: 1px;
  }

  .viewer-controls {
    display: flex;
    gap: 5px;
  }

  .v-btn {
    background: #1E293B;
    border: 1px solid #475569;
    color: #E2E8F0;
    font-size: 10.5px;
    font-weight: 700;
    padding: 4px 8px;
    border-radius: 5px;
    cursor: pointer;
  }
  .v-btn:hover, .v-btn.active {
    background: #0284C7;
    border-color: #38BDF8;
    color: #FFFFFF;
  }

  .canvas-holder {
    width: 100%;
    height: 270px;
    position: relative;
    background: radial-gradient(circle at center, #1E293B 0%, #0F172A 100%);
  }

  .viewer-caption {
    padding: 9px 14px;
    font-size: 11.5px;
    color: #CBD5E1;
    background: rgba(15, 23, 42, 0.95);
    border-top: 1px solid #334155;
    line-height: 1.45;
  }
  .viewer-caption strong {
    color: #F8FAFC;
  }

  /* SCORECARD METRICS */
  .section-title {
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: var(--text-muted);
    margin: 14px 0 8px;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 4px;
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }

  .metric-box {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 7px;
    padding: 8px 10px;
  }
  .metric-box .m-lbl {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
  }
  .metric-box .m-val {
    font-size: 16px;
    font-weight: 900;
    color: var(--text-dark);
    margin-top: 2px;
  }
  .metric-box .m-sub {
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 1px;
  }

  /* SYSTEMS TABLE */
  .sys-filter-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  .sys-search {
    flex: 1;
    padding: 6px 10px;
    font-size: 12px;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
  }

  .sys-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .sys-card {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 10px 12px;
    transition: border-color 0.14s;
  }
  .sys-card:hover {
    border-color: var(--accent-blue);
    background: #FFFFFF;
  }

  .sys-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 5px;
  }

  .sys-formula {
    font-size: 14px;
    font-weight: 900;
    color: var(--text-dark);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .class-badge {
    font-size: 10px;
    font-weight: 800;
    padding: 2px 7px;
    border-radius: 4px;
    background: #E2E8F0;
    color: #1E293B;
  }
  .class-badge.Oxide { background: #DBEAFE; color: #1E40AF; }
  .class-badge.Chalcogenide { background: #D1FAE5; color: #065F46; }
  .class-badge.Metallic { background: #FFEDD5; color: #9A3412; }
  .class-badge.Covalent { background: #EDE9FE; color: #5B21B6; }

  .sys-meta {
    font-size: 11.5px;
    color: var(--text-muted);
    line-height: 1.45;
  }
  .sys-meta strong {
    color: var(--text-dark);
  }

  .doi-link {
    display: inline-block;
    margin-top: 4px;
    font-size: 11px;
    font-weight: 700;
    color: var(--accent-blue);
    text-decoration: none;
  }
  .doi-link:hover {
    text-decoration: underline;
  }

  /* CO-OCCURRENCE CHIPS & TABLE */
  .partner-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 12px;
  }
  .partner-chip {
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 800;
    color: var(--text-dark);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.14s;
  }
  .partner-chip:hover {
    border-color: var(--accent-blue);
    background: #E0F2FE;
  }

  .corr-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  .corr-table th, .corr-table td {
    padding: 7px 9px;
    border-bottom: 1px solid #E2E8F0;
    text-align: left;
  }
  .corr-table th {
    background: #F8FAFC;
    font-weight: 800;
    color: var(--text-muted);
    font-size: 10.5px;
    text-transform: uppercase;
  }

  .prose-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 12.5px;
    line-height: 1.55;
    color: var(--text-dark);
    margin-bottom: 12px;
  }

  /* FULLSCREEN 3D MODAL */
  .modal-3d {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.92);
    z-index: 200;
    display: none;
    flex-direction: column;
  }
  .modal-3d.open {
    display: flex;
  }
  .modal-3d-top {
    padding: 14px 22px;
    background: #0F172A;
    border-bottom: 1px solid #334155;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #F8FAFC;
  }
  .modal-3d-canvas {
    flex: 1;
    width: 100%;
    position: relative;
  }

  /* AMORPHOUS PHYSICS & GLASS THEORY GUIDE MODAL */
  .guide-btn {
    background: linear-gradient(135deg, #0284C7 0%, #4F46E5 100%);
    color: #FFFFFF;
    font-weight: 800;
    font-size: 11.5px;
    border: none;
    border-radius: 7px;
    padding: 7px 12px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 2px 6px rgba(2, 132, 199, 0.28);
    transition: transform 0.14s, box-shadow 0.14s;
    white-space: nowrap;
  }
  .guide-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(79, 70, 229, 0.36);
  }

  .modal-guide {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.78);
    backdrop-filter: blur(3px);
    z-index: 220;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 18px;
  }
  .modal-guide.open {
    display: flex;
  }
  .guide-dialog {
    background: #FFFFFF;
    width: min(1080px, 96vw);
    max-height: 90vh;
    border-radius: 12px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.42);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #CBD5E1;
  }
  .guide-header {
    padding: 16px 22px;
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    color: #F8FAFC;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #334155;
  }
  .guide-header h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 900;
    color: #38BDF8;
    letter-spacing: -0.2px;
  }
  .guide-header p {
    margin: 3px 0 0;
    font-size: 12px;
    color: #CBD5E1;
  }
  .guide-body {
    padding: 18px 22px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: #F8FAFC;
  }
  .guide-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
    gap: 12px;
  }
  .guide-card {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 9px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  }
  .guide-card h3 {
    margin: 0 0 6px;
    font-size: 13.5px;
    font-weight: 900;
    color: #0F172A;
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .guide-card p, .guide-card li {
    font-size: 12px;
    line-height: 1.55;
    color: #334155;
    margin: 4px 0;
  }
  .guide-card ul {
    margin: 6px 0 0 18px;
    padding: 0;
  }
  .guide-tag {
    font-size: 10px;
    font-weight: 800;
    padding: 2px 7px;
    border-radius: 4px;
    text-transform: uppercase;
  }

  /* SRO & MRO STRUCTURAL CHARTS (TAB 5) */
  .sro-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 6px;
    align-items: center;
  }
  .sro-pill, .sro-badge {
    font-size: 10.5px;
    font-weight: 700;
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    color: #1E293B;
    padding: 2px 7px;
    border-radius: 4px;
    white-space: nowrap;
  }
  .sro-jump-btn {
    font-size: 10.5px;
    font-weight: 800;
    background: #E0F2FE;
    border: 1px solid #7DD3FC;
    color: #0369A1;
    padding: 2px 8px;
    border-radius: 4px;
    cursor: pointer;
    margin-left: auto;
  }
  .sro-jump-btn:hover {
    background: #0284C7;
    color: #FFFFFF;
  }
  .sro-chart-card, .sro-plot-card {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 9px;
    padding: 12px 14px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  }
  .sro-chart-title, .sro-plot-card h4 {
    font-size: 12.5px;
    font-weight: 900;
    color: #0F172A;
    margin-bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
  }
  .sro-chart-sub, .sro-caption {
    font-size: 11px;
    color: #475569;
    margin-top: 6px;
    line-height: 1.45;
  }
  .sro-svg {
    width: 100%;
    height: auto;
    display: block;
    background: #FAFCFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin: 4px 0;
  }
  .partial-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    margin-top: 8px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    overflow: hidden;
  }
  .partial-table th {
    background: #F1F5F9;
    color: #334155;
    font-weight: 800;
    text-align: left;
    padding: 5px 8px;
    border-bottom: 1px solid #CBD5E1;
  }
  .partial-table td {
    padding: 5px 8px;
    border-bottom: 1px solid #E2E8F0;
    color: #1E293B;
  }
  .partial-table tr:last-child td {
    border-bottom: none;
  }
  .ring-bar-row {
    display: grid;
    grid-template-columns: 165px 1fr 48px;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    margin-bottom: 5px;
  }
  .ring-bar-lbl {
    font-weight: 700;
    color: #1E293B;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .ring-bar-track {
    height: 11px;
    background: #F1F5F9;
    border-radius: 5px;
    overflow: hidden;
    border: 1px solid #E2E8F0;
  }
  .ring-bar-fill {
    height: 100%;
    border-radius: 4px;
  }
  .ring-bar-val {
    font-weight: 800;
    color: #334155;
    text-align: right;
  }
  .cooc-sys-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .cooc-sys-pill {
    display: inline-block;
    font-size: 10.5px;
    font-weight: 700;
    background: #F0F9FF;
    border: 1px solid #BAE6FD;
    color: #0369A1;
    padding: 1.5px 6px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.12s ease;
  }
  .cooc-sys-pill:hover {
    background: #0284C7;
    border-color: #0284C7;
    color: #FFFFFF;
  }
  .prov-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    font-weight: 800;
    padding: 2px 7px;
    border-radius: 4px;
    white-space: nowrap;
  }
  .prov-exp {
    background: #ECFDF5;
    border: 1px solid #6EE7B7;
    color: #047857;
  }
  .prov-recon {
    background: #EEF2FF;
    border: 1px solid #C7D2FE;
    color: #3730A3;
  }
  .prov-banner {
    border-radius: 8px;
    padding: 9px 12px;
    margin-bottom: 10px;
    font-size: 11.5px;
    line-height: 1.45;
  }
  .prov-banner.exp {
    background: #F0FDF4;
    border: 1.5px solid #86EFAC;
    color: #14532D;
  }
  .prov-banner.recon {
    background: #F8FAFC;
    border: 1.5px solid #CBD5E1;
    color: #1E293B;
  }
</style>
</head>
<body>
<div class="app-container">
  <!-- HEADER -->
  <header class="top-header">
    <div class="title-group">
      <h1>AMORPHOUS PERIODIC TABLE</h1>
      <p>Full-Color Amorphous Phase Formers &amp; Intermediates (__COUNT_FULL__) &bull; Diagonal Half-Color Network Modifiers (__COUNT_HALF__) &bull; __TOTAL_SYS__ Crossref/OpenAlex-Verified Systems</p>
    </div>
    <div class="kpi-strip">
      <button class="guide-btn" onclick="openGuideModal()" title="Read the interactive guide to amorphous solid-state physics, glass roles, BMGs, Hellman &amp; major group thin films, and diffraction/RDF provenance">
        &#128214; Amorphous Physics &amp; Glass Theory Guide
      </button>
      <div class="kpi-pill" onclick="setQuickFilter('all')" id="kpi-all">
        <span class="kpi-val">118 Elements</span>
        <span class="kpi-lbl" id="kpiTotalSysLbl">__TOTAL_SYS__ Verified Systems</span>
      </div>
      <div class="kpi-pill" onclick="setQuickFilter('full')" id="kpi-full">
        <span class="kpi-val" style="color:#0284C7;">__COUNT_FULL__ Full Color</span>
        <span class="kpi-lbl">Makes Amorphous Possible</span>
      </div>
      <div class="kpi-pill" onclick="setQuickFilter('half')" id="kpi-half">
        <span class="kpi-val" style="color:#DB2777;">__COUNT_HALF__ Half Color</span>
        <span class="kpi-lbl">In Reported Systems (Modifiers)</span>
      </div>
      <div class="kpi-pill" onclick="setQuickFilter('tet')" id="kpi-tet">
        <span class="kpi-val" style="color:#0369A1;">&#9670; __COUNT_TET__ Tetrahedral</span>
        <span class="kpi-lbl">Verified CN=4 Network Motif</span>
      </div>
      <div class="kpi-pill" onclick="setQuickFilter('none')" id="kpi-none">
        <span class="kpi-val" style="color:#64748B;">__COUNT_NONE__ White</span>
        <span class="kpi-lbl">Unreported in Catalog</span>
      </div>
    </div>
  </header>

  <!-- TOOLBAR -->
  <div class="toolbar">
    <div class="filter-group">
      <span class="toolbar-label">Filter:</span>
      <button class="filter-btn active" data-filter="all" onclick="setQuickFilter('all')">All (118)</button>
      <button class="filter-btn" data-filter="full" onclick="setQuickFilter('full')">Full Color: Backbone/Cluster (__COUNT_FULL__)</button>
      <button class="filter-btn" data-filter="half" onclick="setQuickFilter('half')">Half Color: Modifiers (__COUNT_HALF__)</button>
      <button class="filter-btn" data-filter="tet" onclick="setQuickFilter('tet')">&#9670; Tetrahedral CN=4 (__COUNT_TET__)</button>
      <button class="filter-btn" data-filter="class:Oxide" onclick="setQuickFilter('class:Oxide')">Oxides (__COUNT_OXIDE__ sys)</button>
      <button class="filter-btn" data-filter="class:Chalcogenide" onclick="setQuickFilter('class:Chalcogenide')">Chalcogenides (__COUNT_CHALC__ sys)</button>
      <button class="filter-btn" data-filter="class:Metallic Glass" onclick="setQuickFilter('class:Metallic Glass')">Metallic Glasses (__COUNT_MG__ sys)</button>
      <button class="filter-btn" data-filter="class:Covalent Network" onclick="setQuickFilter('class:Covalent Network')">Covalent (__COUNT_COV__ sys)</button>
      <span class="toolbar-label" style="margin-left:4px;">Regime:</span>
      <button class="filter-btn" data-filter="regime:bulk_melt_quenched" onclick="setQuickFilter('regime:bulk_melt_quenched')" title="Conventional melt-quenched bulk glasses &amp; bulk metallic glasses (Rc ~ 10^-2 to 10^3 K/s)">Bulk Melt-Quenched (__COUNT_BULK__)</button>
      <button class="filter-btn" data-filter="regime:rapid_quenched_ribbon" onclick="setQuickFilter('regime:rapid_quenched_ribbon')" title="Melt-spun ribbons, splat-quenched, or containerless levitation-quenched glasses (Rc ~ 10^4 to 10^6 K/s)">Rapid-Quenched Ribbon (__COUNT_RIBBON__)</button>
      <button class="filter-btn" data-filter="regime:vapor_thin_film" onclick="setQuickFilter('regime:vapor_thin_film')" title="Vapor-deposited, sputtered, MBE, PECVD, ALD, or ion-beam amorphized thin films (Rc > 10^8 K/s)">Vapor / Thin-Film (__COUNT_VAPOR__)</button>
    </div>

    <div class="toolbar-right">
      <label class="toolbar-label" for="colorModeSelect">Color Mode:</label>
      <select id="colorModeSelect" class="mode-select" onchange="setColorMode(this.value)">
        <option value="role">Structural Role (Full vs. Half Split)</option>
        <option value="systems">System Frequency Heatmap (N = 0–__MAX_OCC__ sys)</option>
        <option value="tet_frac">Tetrahedral CN=4 Fraction Heatmap</option>
      </select>

      <div class="search-wrap">
        <input
          type="text"
          id="searchInput"
          class="search-input"
          placeholder="Search symbol, name, Z, or formula (e.g. Bi2Se3, FeGe, CoSi, Pd40Ni40P20, SiO2)..."
          oninput="handleSearch(this.value)"
        >
        <button class="search-clear" id="searchClearBtn" onclick="clearSearch()">&times;</button>
      </div>
    </div>
  </div>

  <!-- 18-COLUMN PERIODIC TABLE GRID -->
  <div class="ptable-grid" id="ptableGrid">
    <!-- Injected dynamically by JS -->
  </div>

  <!-- SCIENTIFIC METHODOLOGY FOOTER -->
  <div class="footer-notes">
    <strong>Scientific Methodology, Crossref/OpenAlex DOI Audit &amp; Visual Encoding (<code>amorphous_materials.db</code> — __TOTAL_SYS__ Experimentally Verified Systems, __COUNT_ACTIVE__ Active Elements):</strong><br>
    &bull; <strong>100% Crossref &amp; OpenAlex Verified Citations:</strong> Every cataloged amorphous system is verified against live Crossref REST and OpenAlex APIs (HTTP 200 OK, exact author/year/journal/title match) and experimentally confirmed by diffuse X-ray/neutron diffraction (<i>S</i>(<i>Q</i>) FSDP), pair distribution function <i>g</i>(<i>r</i>), TEM SAED, and/or DSC glass transition (<i>T<sub>g</sub></i> / <i>T<sub>x</sub></i>). Spans three distinct synthesis regimes: <strong>Bulk Melt-Quenched Glasses &amp; BMGs</strong> (__COUNT_BULK__ systems; Inoue, Johnson, Sheng/Ma), <strong>Rapid-Quenched Melt-Spun Ribbons &amp; Levitated Melts</strong> (__COUNT_RIBBON__ systems; Lamparter/Steeb, Benmore/Weber), and <strong>Vapor-Deposited / Thin-Film Amorphous Solids</strong> (__COUNT_VAPOR__ systems; Frances Hellman Group UC Berkeley <i>a</i>-Bi<sub>2</sub>Se<sub>3</sub>, <i>a</i>-Fe<sub>x</sub>Ge<sub>1&minus;x</sub>, <i>a</i>-Fe<sub>x</sub>Si<sub>1&minus;x</sub>, <i>a</i>-Co<sub>x</sub>Ge<sub>1&minus;x</sub>, <i>a</i>-Mn<sub>x</sub>Si<sub>1&minus;x</sub>, <i>a</i>-Gd<sub>x</sub>Si<sub>1&minus;x</sub>, ultrastable <i>a</i>-Si; Wuttig/Salinga phase-change chalcogenides; Bassiri/Fejer LIGO coatings; Hosono/Wager oxide semiconductors; Kortright/Bienenstock/Beasley/Dynes superconducting &amp; catalytic films).<br>
    &bull; <strong>Full Cell Coloring (__COUNT_FULL__ Elements — &ldquo;Makes Amorphous Phase Possible&rdquo;):</strong> Primary Tetrahedral Network Formers (__COUNT_CAT_1A__), Bridging Anion Formers (__COUNT_CAT_1B__), Conditional Tetrahedral Intermediates (__COUNT_CAT_2A__), Oxide/Chalcogenide/BMG Polyhedral Intermediates (__COUNT_CAT_2B__), and Metallic Cluster / BMG Host Intermediates (__COUNT_CAT_2C__) that construct the continuous random network (CRN) or icosahedral/polytetrahedral cluster backbone.<br>
    &bull; <strong>Diagonal 50/50 Half-Split Cell Coloring (__COUNT_HALF__ Elements — &ldquo;Part of Reported Amorphous Systems&rdquo;):</strong> Network Modifiers, Charge Compensators, and Large/Small Topological Cages (Li–Cs, Mg–Ba, Ag, Y, La–Lu, U, I, H) that participate within multicomponent amorphous matrices. Each active element cell displays its primary local coordination motif and raw verified system count (<code>CN &middot; N</code>).
  </div>
</div>

<!-- SLIDE-OUT ELEMENT INSPECTION DRAWER -->
<div class="drawer-backdrop" id="drawerBackdrop" onclick="closeDrawer()"></div>
<aside class="inspection-drawer" id="inspectionDrawer">
  <div class="drawer-header">
    <div class="drawer-el-head">
      <div class="drawer-el-badge" id="drawerBadge">
        <div class="db-top">
          <span id="drawerZ">14</span>
          <span id="drawerTet" style="color:#0369A1;">&#9670;</span>
        </div>
        <div class="db-sym" id="drawerSym">Si</div>
        <div class="db-mass" id="drawerMass">28.085</div>
      </div>
      <div class="drawer-title-meta">
        <h2>
          <span id="drawerName">Silicon</span>
          <span class="fill-mode-tag full" id="drawerFillTag">FULL COLOR</span>
        </h2>
        <div class="drawer-subtitle" id="drawerRoleSub">Primary Tetrahedral Network Former &bull; CN=4 &middot; N=__SI_COUNT__</div>
      </div>
    </div>
    <button class="drawer-close-btn" onclick="closeDrawer()" title="Close (Esc)">&times;</button>
  </div>

  <div class="drawer-tabs">
    <button class="drawer-tab active" onclick="switchTab('overview')" data-tab="overview">1. Overview &amp; 3D</button>
    <button class="drawer-tab" onclick="switchTab('systems')" data-tab="systems" id="tabBtnSystems">2. Verified Systems (__SI_COUNT__)</button>
    <button class="drawer-tab" onclick="switchTab('correlations')" data-tab="correlations">3. Co-Occurrence</button>
    <button class="drawer-tab" onclick="switchTab('mechanism')" data-tab="mechanism">4. Mechanism &amp; Ref</button>
    <button class="drawer-tab" onclick="switchTab('structure')" data-tab="structure" id="tabBtnStructure">5. Diffraction, RDF &amp; Rings (__SI_COUNT__)</button>
  </div>

  <div class="drawer-body">
    <!-- TAB 1: OVERVIEW & 3D COORDINATION MOTIF -->
    <div class="tab-pane active" id="pane-overview">
      <div class="viewer-card">
        <div class="viewer-header">
          <div class="viewer-title-block">
            <h3 id="motifTitle">Corner-Sharing Tetrahedral Network (MX4)</h3>
            <p id="motifCoord">CN = 4 (sp3 covalent / mixed ionic-covalent)</p>
          </div>
          <div class="viewer-controls">
            <button class="v-btn active" id="btnAutoRotate" onclick="toggleAutoRotate()">Auto-Rotate</button>
            <button class="v-btn active" id="btnPolyCage" onclick="togglePolyCage()">Polyhedra</button>
            <button class="v-btn" onclick="resetCamera()">Reset</button>
            <button class="v-btn" onclick="openFullscreen3D()">&#x26F6; Expand</button>
          </div>
        </div>
        <div class="canvas-holder" id="canvasHolder"></div>
        <div class="viewer-caption" id="motifCaption"></div>
      </div>

      <div class="section-title">Amorphous Coordination &amp; System Scorecard</div>
      <div class="metric-grid" id="overviewScorecard"></div>

      <div class="section-title">Amorphous Class, Synthesis Regime &amp; Structural Role Breakdown</div>
      <div class="prose-card" id="overviewBreakdown"></div>
    </div>

    <!-- TAB 2: VERIFIED AMORPHOUS SYSTEMS -->
    <div class="tab-pane" id="pane-systems">
      <div class="sys-filter-bar">
        <input
          type="text"
          id="sysSearchInput"
          class="sys-search"
          placeholder="Filter this element's verified systems by formula, paper title, class, synthesis regime, coordination, or DOI..."
          oninput="renderElementSystems()"
        >
      </div>
      <div class="sys-list" id="drawerSystemsList"></div>
    </div>

    <!-- TAB 3: CO-OCCURRENCE & CORRELATIONS -->
    <div class="tab-pane" id="pane-correlations">
      <div class="section-title">All Co-Occurring Partner Elements (Click Partner to Inspect)</div>
      <div class="partner-chips" id="drawerPartnerChips"></div>

      <div class="section-title">All Co-Occurring Element Pairs, Shared Amorphous Systems &amp; Correlation Metrics</div>
      <div id="drawerCorrTableWrap"></div>
    </div>

    <!-- TAB 4: MECHANISM, CONVERSION BENCHMARKS & ATOMIC REFERENCE -->
    <div class="tab-pane" id="pane-mechanism">
      <div class="section-title">Glass-Forming Structural Mechanism</div>
      <div class="prose-card" id="drawerMechanism"></div>

      <div class="section-title">Crystalline-to-Amorphous Conversion Benchmarks</div>
      <div id="drawerConversions"></div>

      <div class="section-title">Baseline Atomic, Electronic &amp; Crystalline Reference</div>
      <div class="metric-grid" id="drawerAtomicGrid"></div>
    </div>

    <!-- TAB 5: DIFFRACTION S(Q), RADIAL DISTRIBUTION FUNCTION g(r), BOND ANGLES & RINGS/VORONOI -->
    <div class="tab-pane" id="pane-structure">
      <div class="sys-filter-bar" style="background:#F1F5F9;padding:8px 10px;border-radius:7px;border:1px solid #CBD5E1;">
        <label for="structSysSelect" style="font-size:11.5px;font-weight:800;color:#0F172A;white-space:nowrap;">Verified System:</label>
        <select id="structSysSelect" class="mode-select" style="flex:1;" onchange="renderElementStructurePlots(this.value)"></select>
      </div>
      <div id="structElementSummary" style="margin-bottom:10px;"></div>
      <div id="structPlotsContainer"></div>
    </div>
  </div>
</aside>

<!-- AMORPHOUS PHYSICS & GLASS THEORY GUIDE MODAL -->
<div class="modal-guide" id="modalGuide" onclick="if(event.target===this)closeGuideModal()">
  <div class="guide-dialog">
    <div class="guide-header">
      <div>
        <h2>&#128214; Amorphous Solid-State Physics &amp; Structural Glass Theory Guide</h2>
        <p>Why certain elements make the amorphous phase possible (Full Color) while others participate as modifiers/cages (Half Color)</p>
      </div>
      <button class="v-btn" onclick="closeGuideModal()" style="font-size:13px;padding:6px 14px;">Close Guide (Esc)</button>
    </div>
    <div class="guide-body">
      <div class="guide-grid">
        <div class="guide-card" style="border-left:4px solid #0284C7;">
          <h3>
            <span class="guide-tag" style="background:#E0F2FE;color:#0369A1;">1a. Primary Network Formers</span>
            Continuous Random Networks (CRN: Si, Ge, P, B, As)
          </h3>
          <p>
            By <strong>Zachariasen&rsquo;s Rules (1932)</strong> and <strong>Phillips&ndash;Thorpe Topological Constraint Theory (1979)</strong>, a covalent/oxide melt avoids crystallization when polyhedra of low coordination (<i>z</i> = 3 or 4, e.g., SiO<sub>4</sub>, GeSe<sub>4</sub>, BO<sub>3</sub>/BO<sub>4</sub>, PO<sub>4</sub>) share <strong>corners rather than edges or faces</strong>.
          </p>
          <ul>
            <li><strong>Isostatic Window (&lang;<i>r</i>&rang; &approx; 2.40):</strong> When the number of bond-stretching (<i>r</i>/2) and bond-bending (2<i>r</i> &minus; 3) constraints per atom equals the 3D degrees of freedom (<i>n<sub>c</sub></i> = 3 at mean coordination &lang;<i>r</i>&rang; = 2.40, as in As<sub>2</sub>Se<sub>3</sub> or GeSe<sub>4</sub>), the network forms a stress-free, non-periodic 3D graph without paying a macroscopic enthalpy penalty relative to the crystal.</li>
            <li><strong>Dual Role in BMGs:</strong> Metalloids (B, P, Si, Ge) also form solute-centered trigonal prisms (M<sub>9</sub>B, Pd<sub>6</sub>Ni<sub>3</sub>P) that stabilize bulk metallic glasses.</li>
          </ul>
        </div>

        <div class="guide-card" style="border-left:4px solid #059669;">
          <h3>
            <span class="guide-tag" style="background:#D1FAE5;color:#065F46;">1b. Bridging Anion Formers</span>
            Flexible Low-CN Hinges (O, S, Se, N, F, Cl, Br)
          </h3>
          <p>
            Why can&rsquo;t rigid tetrahedra alone easily pack into a strain-free glass without defects? Because a purely 4-coordinated network (<i>a</i>-Si, &lang;<i>r</i>&rang; = 4.0) is <strong>over-constrained</strong> (<i>n<sub>c</sub></i> = 7 &gt; 3).
          </p>
          <ul>
            <li><strong>2-Coordinate Rotational Hinges:</strong> Bridging anions (&ndash;O&ndash;, &ndash;S&ndash;, &ndash;Se&ndash;, &ndash;F&ndash;, &ndash;Cl&ndash;, &ndash;Br&ndash; with CN=2, or planar &ndash;N&lt; with CN=3) sit between rigid MX<sub>4</sub> tetrahedra (including halide glasses BeF<sub>2</sub>, ZnCl<sub>2</sub>, ZnBr<sub>2</sub>). Because a 2-coordinate bridge has <strong>soft inter-tetrahedral bond-bending</strong> (e.g., Si&ndash;O&ndash;Si varies continuously from 125&deg; to 165&deg;, mean &sim;144&deg;) and free dihedral torsion, it absorbs topological disorder while maintaining 100% covalent connectivity.</li>
          </ul>
        </div>

        <div class="guide-card" style="border-left:4px solid #7C3AED;">
          <h3>
            <span class="guide-tag" style="background:#EDE9FE;color:#5B21B6;">2a. Conditional Tetrahedral</span>
            Compensated Intermediates (Al, Ga, Zn, Be, C, V, Mo, W, Ti, Sn, In, Cd)
          </h3>
          <p>
            <strong>Conditional glass formers (intermediates)</strong> cannot form a single-component oxide glass by simple melt quenching (Al<sub>2</sub>O<sub>3</sub> or TiO<sub>2</sub> crystallize unless levitation-quenched or sputtered), <em>or</em> require specific chemical/energetic conditions to adopt 4-coordinate tetrahedral geometry:
          </p>
          <ul>
            <li><strong>Charge-Compensated Tetrahedra &amp; Amorphous Oxides:</strong> Trivalent Al<sup>3+</sup> and Ga<sup>3+</sup> form [AlO<sub>4</sub>]<sup>&minus;</sup> and [GaO<sub>4</sub>]<sup>&minus;</sup> when paired with modifiers, or mixed AlO<sub>4</sub>/AlO<sub>5</sub>/AlO<sub>6</sub> networks in containerless/ALD <i>a</i>-Al<sub>2</sub>O<sub>3</sub> (Benmore/Weber), high-<i>k</i> <i>a</i>-HfO<sub>2</sub>/<i>a</i>-ZrO<sub>2</sub>, LIGO <i>a</i>-Ta<sub>2</sub>O<sub>5</sub> coatings (Bassiri/Fejer), and amorphous oxide semiconductors (IGZO, ZTO, IZO — Hosono/Wager).</li>
            <li><strong>Halide / Pnictide / Ion-Beam Tetrahedra:</strong> BeF<sub>2</sub>, ZnCl<sub>2</sub>, and ZnBr<sub>2</sub> are exact tetrahedral structural analogues of SiO<sub>2</sub>; CdGeAs<sub>2</sub> and InP form tetrahedral chalcopyrite/III-V glasses; carbon forms <i>sp</i><sup>3</sup> tetrahedral amorphous carbon (<i>ta</i>-C) under energetic ion deposition.</li>
          </ul>
        </div>

        <div class="guide-card" style="border-left:4px solid #EA580C;">
          <h3>
            <span class="guide-tag" style="background:#FFEDD5;color:#9A3412;">2b &amp; 2c. BMGs &amp; Clusters</span>
            Bulk Metallic Glasses &amp; Icosahedral Frustration
          </h3>
          <p>
            Unlike covalent glasses, metallic bonds are non-directional and dense (CN=11&ndash;14). Pure liquid metals crystallize in nanoseconds because periodic FCC/BCC nuclei form effortlessly. <strong>Bulk Metallic Glasses (BMGs)</strong> defeat crystallization via <strong>Geometric &amp; Topological Frustration</strong> (Inoue&rsquo;s Rules, Johnson, Sheng/Ma &amp; Egami&rsquo;s Atomic-Level Stress Theory):
          </p>
          <ul>
            <li><strong>Five-Fold Icosahedral Short-Range Order:</strong> Solute-centered &lang;0,0,12,0&rang; icosahedra and Frank-Kasper polytetrahedra are locally denser and lower in energy than FCC/BCC, but <strong>five-fold rotational symmetry cannot tile 3D Euclidean space periodically</strong>.</li>
            <li><strong>Multi-Component Size Mismatch (&Delta;<i>r</i> / <i>r</i> &gt; 12%):</strong> Combining large (Zr, Hf, Pd, La, Gd), medium (Cu, Ni, Co, Fe, Ti), and small (Be, B, P, Si, Al) atoms creates dense cluster packing (Vitreloy-1, Zr<sub>50</sub>Cu<sub>40</sub>Al<sub>10</sub>, Pd<sub>40</sub>Cu<sub>30</sub>Ni<sub>10</sub>P<sub>20</sub>, Ni<sub>62</sub>Nb<sub>38</sub>, Fe<sub>80</sub>B<sub>20</sub>, Co<sub>80</sub>B<sub>20</sub>).</li>
          </ul>
        </div>

        <div class="guide-card" style="border-left:4px solid #0F766E;">
          <h3>
            <span class="guide-tag" style="background:#CCFBF1;color:#115E59;">Synthesis Regimes (Filterable)</span>
            Bulk Melt-Quenched vs. Rapid-Quenched Ribbons vs. Vapor Thin Films
          </h3>
          <p>
            Glass-forming ability depends critically on the <strong>effective cooling rate</strong> and synthesis pathway. Use the toolbar buttons to filter elements by synthesis regime:
          </p>
          <ul>
            <li><strong>Bulk Melt-Quenched Glasses &amp; BMGs (__COUNT_BULK__ sys, <i>R<sub>c</sub></i> ~ 10<sup>&minus;2</sup>&ndash;10<sup>3</sup> K/s):</strong> Canonical oxide, chalcogenide, halide, and bulk metallic glasses cooled from the equilibrium liquid.</li>
            <li><strong>Rapid-Quenched Melt-Spun Ribbons &amp; Levitated Melts (__COUNT_RIBBON__ sys, <i>R<sub>c</sub></i> ~ 10<sup>4</sup>&ndash;10<sup>6</sup> K/s):</strong> Marginal binary metallic glasses (Cu<sub>64</sub>Zr<sub>36</sub>, Fe<sub>80</sub>B<sub>20</sub>, Ni<sub>81</sub>B<sub>19</sub>) and containerless aerodynamic-levitation oxides (<i>a</i>-Al<sub>2</sub>O<sub>3</sub>, <i>a</i>-TiO<sub>2</sub>).</li>
            <li><strong>Vapor-Deposited / Thin-Film Amorphous Solids (__COUNT_VAPOR__ sys, <i>R<sub>c,eff</sub></i> ~ 10<sup>8</sup>&ndash;10<sup>12</sup> K/s):</strong> E-beam co-evaporated, sputtered, ALD, or ion-implanted films including Hellman Group quantum films (<i>a</i>-Bi<sub>2</sub>Se<sub>3</sub>, <i>a</i>-FeGe, <i>a</i>-FeSi, <i>a</i>-CoSi, <i>a</i>-MnSi, <i>a</i>-GdSi, e-beam <i>a</i>-Si), Wuttig phase-change chalcogenides (Ge<sub>2</sub>Sb<sub>2</sub>Te<sub>5</sub>), and Hosono oxide semiconductors (IGZO).</li>
          </ul>
        </div>

        <div class="guide-card" style="border-left:4px solid #DB2777;">
          <h3>
            <span class="guide-tag" style="background:#FCE7F3;color:#9D174D;">Tab 5 Provenance &amp; Weighting</span>
            Scalar Peak Anchors vs. Parameterized Profile Reconstructions
          </h3>
          <p>
            Every system in <strong>Tab 5</strong> displays an explicit <strong>Data Provenance Badge</strong> distinguishing literature scalar peak anchors from parameterized continuous curves:
          </p>
          <ul>
            <li><strong>&#128300; Lit. Benchmark Peak Anchors + Parameterized Curve (__COUNT_BENCH__ Canonical Systems):</strong> Scalar peak positions (<i>Q</i><sub>1</sub>, <i>Q</i><sub>2</sub>, <i>r</i><sub>1</sub>, <i>r</i><sub>2</sub>, &theta;&#772;) and partial pair distances <i>r<sub>&alpha;&beta;</sub></i> are anchored directly to published X-ray/neutron diffraction, EXAFS, RMC, or AIMD benchmarks (Wright, Salmon, Greaves, Benmore, Sheng/Ma, Wuttig, Hellman, Kortright, Lamparter/Steeb, Sv&aacute;b); continuous <i>S</i>(<i>Q</i>), <i>g</i>(<i>r</i>), and <i>P</i>(&theta;) curves are parameterized Gaussian/Lorentzian reconstructions centered on those experimental anchors.</li>
            <li><strong>&#9878;&#65039; Composition-Weighted Analytical Reconstruction:</strong> For multicomponent alloys and solid-solution series without digitized curve tables, peak anchors and partial pair Gaussians <i>g<sub>&alpha;&beta;</sub></i>(<i>r</i>) (weighted by <i>w<sub>&alpha;&beta;</sub></i> = 2<i>c<sub>&alpha;</sub>c<sub>&beta;</sub></i> or <i>c<sub>&alpha;</sub></i><sup>2</sup>) are reconstructed continuously from the exact atomic fractions <i>c<sub>i</sub></i>.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- FULLSCREEN 3D MODAL -->
<div class="modal-3d" id="modal3D">
  <div class="modal-3d-top">
    <div>
      <strong id="modal3DTitle" style="font-size:16px;color:#38BDF8;">3D Local Coordination Motif</strong>
      <span id="modal3DSub" style="font-size:13px;color:#CBD5E1;margin-left:12px;"></span>
    </div>
    <button class="v-btn" onclick="closeFullscreen3D()" style="font-size:13px;padding:6px 14px;">Close Fullscreen (Esc)</button>
  </div>
  <div class="modal-3d-canvas" id="modal3DCanvas"></div>
</div>

<script>
window.AMORPHOUS_DATA = __AMORPHOUS_DATA_JSON__;

(function() {
  const DATA = window.AMORPHOUS_DATA;
  const ELEMENTS = DATA.elements;
  const SRO_BY_FORMULA = DATA.systems_sro_by_formula || {};
  const ELEM_BY_Z = {};
  const ELEM_BY_SYM = {};
  ELEMENTS.forEach(el => {
    ELEM_BY_Z[el.atomic_number] = el;
    ELEM_BY_SYM[el.symbol.toLowerCase()] = el;
    (el.verified_systems || []).forEach(s => {
      if (!s.structural_characterization && SRO_BY_FORMULA[s.formula]) {
        s.structural_characterization = SRO_BY_FORMULA[s.formula];
      }
    });
  });

  let activeFilter = 'all';
  let activeColorMode = 'role';
  let searchQuery = '';
  let currentElement = ELEM_BY_Z[14]; // Default Silicon

  // Build Periodic Table Grid
  function buildGrid() {
    const grid = document.getElementById('ptableGrid');
    grid.innerHTML = '';

    // Group headers (1..18)
    for (let g = 1; g <= 18; g++) {
      const gl = document.createElement('div');
      gl.className = 'group-label';
      gl.style.gridColumn = (g + 1);
      gl.style.gridRow = (g >= 3 && g <= 12) ? 4 : 1;
      gl.textContent = g;
      grid.appendChild(gl);
    }

    // Period labels (1..7)
    for (let p = 1; p <= 7; p++) {
      const pl = document.createElement('div');
      pl.className = 'period-label';
      pl.style.gridColumn = 1;
      pl.style.gridRow = p + 1;
      pl.textContent = p;
      grid.appendChild(pl);
    }

    // Box 1: How to Read Each Element Cell + Fill-Mode Key
    const box1 = document.createElement('div');
    box1.className = 'info-box box1-container';
    box1.innerHTML = `
      <div class="box-header">
        <span>BOX 1: HOW TO READ EACH ELEMENT CELL</span>
        <span style="font-size:9.5px;color:#0284C7;cursor:pointer;" onclick="openDrawer(14)">Inspect Si &rarr;</span>
      </div>
      <div class="box1-top">
        <div class="sample-cell" onclick="openDrawer(14)" title="Click to inspect Silicon (Z=14)">
          <div class="sc-top">
            <span>14</span>
            <span style="color:#0369A1;">&#9670;</span>
          </div>
          <div class="sc-sym">Si</div>
          <div class="sc-role">Tet Former</div>
          <div class="sc-metric">CN=4 &middot; N=__SI_COUNT__</div>
        </div>
        <div class="sample-callouts">
          <div><span class="callout-dot"></span><span><strong>Z=14:</strong> Atomic Number</span></div>
          <div><span class="callout-dot"></span><span><strong style="color:#0369A1;">&#9670;:</strong> Verified CN=4 Tetrahedral Motif</span></div>
          <div><span class="callout-dot"></span><span><strong>Si:</strong> Chemical Symbol</span></div>
          <div><span class="callout-dot"></span><span><strong>Tet Former:</strong> Structural Glass Role</span></div>
          <div><span class="callout-dot"></span><span><strong>CN=4 &middot; N=__SI_COUNT__:</strong> Coordination &amp; Systems</span></div>
        </div>
      </div>
      <div class="fill-mode-key">
        <div class="fm-row" onclick="setQuickFilter('full')" title="Click to filter __COUNT_FULL__ Full-Color elements">
          <span class="fm-swatch full"></span>
          <span><strong>FULL COLOR (__COUNT_FULL__ el):</strong> Makes amorphous phase possible (Backbone/Cluster)</span>
        </div>
        <div class="fm-row" onclick="setQuickFilter('half')" title="Click to filter __COUNT_HALF__ Half-Color modifier elements">
          <span class="fm-swatch half"></span>
          <span><strong>HALF COLOR (__COUNT_HALF__ el):</strong> Part of reported amorphous systems (Modifiers)</span>
        </div>
        <div class="fm-row" onclick="setQuickFilter('none')" title="Click to filter __COUNT_NONE__ Unreported elements">
          <span class="fm-swatch none"></span>
          <span><strong>WHITE (__COUNT_NONE__ el):</strong> Unreported in catalog &nbsp;|&nbsp; <strong>///:</strong> Radioactive</span>
        </div>
      </div>
    `;
    grid.appendChild(box1);

    // Box 2: Interactive Legend & Amorphous Structural Roles
    const box2 = document.createElement('div');
    box2.className = 'info-box box2-container';
    const legendItems = [
      {
        code: 'primary_tetrahedral_former',
        fill: 'full',
        bg: '#7EC8E3',
        border: '#0284C7',
        title: '1a. Primary Tetrahedral Formers (Full, __COUNT_CAT_1A__ el)',
        desc: 'Si, Ge, P, B, As — Continuous random network (CRN) backbones'
      },
      {
        code: 'bridging_anion_former',
        fill: 'full',
        bg: '#A7F3D0',
        border: '#059669',
        title: '1b. Bridging Anion Formers (Full, __COUNT_CAT_1B__ el)',
        desc: 'O, S, Se, N, F, Cl, Br — Flexible CN=2–3 bridging ligands'
      },
      {
        code: 'conditional_tetrahedral_intermediate',
        fill: 'full',
        bg: '#C4B5FD',
        border: '#7C3AED',
        title: '2a. Conditional Tetrahedral Intermediates (Full, __COUNT_CAT_2A__ el)',
        desc: 'Al, Ga, Zn, Be, C, V, Mo, W, Ti, Sn, In, Cd — Compensated MX4'
      },
      {
        code: 'oxide_chalcogenide_intermediate',
        fill: 'full',
        bg: '#FDE68A',
        border: '#D97706',
        title: '2b. Oxide / Chalcogenide / BMG Intermediates (Full, __COUNT_CAT_2B__ el)',
        desc: 'Te, Sb, Bi, Pb, Fe, Zr, Hf, Nb, Ta, Sc, Tl, Os, Th — Polyhedral / early-TM'
      },
      {
        code: 'metallic_cluster_intermediate',
        fill: 'full',
        bg: '#FDBA74',
        border: '#EA580C',
        title: '2c. Metallic Cluster / BMG Intermediates (Full, __COUNT_CAT_2C__ el)',
        desc: 'Cu, Ni, Co, Pd, Pt, Au, Cr, Mn, Ru, Rh, Re, Ir — <0,0,12,0> BMG'
      },
      {
        code: 'network_modifier',
        fill: 'half',
        bg: '#F9A8D4',
        border: '#DB2777',
        title: '3. Network Modifiers & Cages (Half-Split, __COUNT_HALF__ el)',
        desc: 'Li–Cs, Mg–Ba, Ag, Y, La–Lu, U, I, H — Depolymerize NBOs / cages'
      }
    ];

    let legHtml = `<div class="box-header"><span>BOX 2: LEGEND &amp; AMORPHOUS STRUCTURAL ROLES</span><span style="font-size:9px;color:#64748B;">Click role to filter</span></div><div class="legend-grid">`;
    legendItems.forEach(item => {
      const swClass = item.fill === 'half' ? 'legend-swatch half-swatch' : 'legend-swatch';
      legHtml += `
        <div class="legend-item" data-cat="${item.code}" onclick="setQuickFilter('cat:${item.code}')">
          <span class="${swClass}" style="background:${item.bg};border-color:${item.border};"></span>
          <div class="legend-text">
            <span class="legend-title">${item.title}</span>
            <span class="legend-desc">${item.desc}</span>
          </div>
        </div>
      `;
    });
    legHtml += `</div>
      <div class="legend-footer" onclick="setQuickFilter('tet')">
        <span><strong style="color:#0369A1;">&#9670;</strong> = Verified 4-Coordinate Tetrahedral Motif (__COUNT_TET__ el: Si, Ge, P, B, As, Al..Cd)</span>
        <span style="color:#0284C7;">Filter &#9670;</span>
      </div>
    `;
    box2.innerHTML = legHtml;
    grid.appendChild(box2);

    // Placeholders for Lanthanides (57-71) and Actinides (89-103)
    const phLan = document.createElement('div');
    phLan.className = 'placeholder-cell';
    phLan.style.gridColumn = 4;
    phLan.style.gridRow = 7;
    phLan.innerHTML = `57–71<span>* La–Lu</span>`;
    grid.appendChild(phLan);

    const phAct = document.createElement('div');
    phAct.className = 'placeholder-cell';
    phAct.style.gridColumn = 4;
    phAct.style.gridRow = 8;
    phAct.innerHTML = `89–103<span>** Ac–Lr</span>`;
    grid.appendChild(phAct);

    // Row labels for Lanthanides & Actinides
    const lblLan = document.createElement('div');
    lblLan.className = 'series-row-label';
    lblLan.style.gridRow = 10;
    lblLan.innerHTML = `* Lanthanides<span style="font-size:10px;color:#64748B;">(57–71)</span>`;
    grid.appendChild(lblLan);

    const lblAct = document.createElement('div');
    lblAct.className = 'series-row-label';
    lblAct.style.gridRow = 11;
    lblAct.innerHTML = `** Actinides<span style="font-size:10px;color:#64748B;">(89–103)</span>`;
    grid.appendChild(lblAct);

    // Render all 118 Element Cells
    ELEMENTS.forEach(el => {
      const cell = document.createElement('div');
      const z = el.atomic_number;
      let col, row;
      if (z >= 57 && z <= 71) {
        col = 4 + (z - 57);
        row = 10;
      } else if (z >= 89 && z <= 103) {
        col = 4 + (z - 89);
        row = 11;
      } else {
        col = el.group + 1;
        row = el.period + 1;
      }

      cell.id = `el-cell-${z}`;
      cell.dataset.z = z;
      cell.style.gridColumn = col;
      cell.style.gridRow = row;
      cell.onclick = () => openDrawer(z);

      updateCellAppearance(cell, el);
      grid.appendChild(cell);
    });
  }

  function heatColor(ratio, rgbLow, rgbHigh) {
    const r = Math.round(rgbLow[0] + (rgbHigh[0] - rgbLow[0]) * ratio);
    const g = Math.round(rgbLow[1] + (rgbHigh[1] - rgbLow[1]) * ratio);
    const b = Math.round(rgbLow[2] + (rgbHigh[2] - rgbLow[2]) * ratio);
    return `rgb(${r}, ${g}, ${b})`;
  }

  function updateCellAppearance(cell, el) {
    const isRad = el.radioactive ? ' radioactive' : '';
    let fillClass = `fill-${el.fill_mode}`;
    let bgHex = el.color_hex;
    let borderHex = el.border_hex;
    let metricText = '';
    const sysFreq = el.system_frequency ?? el.frequency ?? 0;
    const tetFrac = el.tetrahedral_fraction ?? el.tetrahedral_ratio ?? 0;
    const shortCn = el.short_cn_label || 'CN=4';

    if (el.occurrence_count > 0) {
      metricText = `${shortCn} \u00b7 N=${el.occurrence_count}`;
    } else {
      metricText = String(el.atomic_mass);
    }

    if (activeColorMode === 'systems') {
      if (el.occurrence_count > 0) {
        const ratio = Math.min(1, Math.sqrt(el.occurrence_count / __MAX_OCC__.0));
        bgHex = heatColor(ratio, [254, 243, 199], [217, 119, 6]);
        borderHex = '#B45309';
        fillClass = 'fill-full';
        metricText = `${el.occurrence_count} sys (${(sysFreq * 100).toFixed(1)}%)`;
      } else {
        fillClass = 'fill-none';
      }
    } else if (activeColorMode === 'tet_frac') {
      if (el.has_tetrahedral_motif && el.tetrahedral_count > 0) {
        const ratio = Math.min(1, tetFrac);
        bgHex = heatColor(ratio, [224, 231, 255], [79, 70, 229]);
        borderHex = '#4338CA';
        fillClass = 'fill-full';
        metricText = `CN4: ${el.tetrahedral_count}/${el.occurrence_count}`;
      } else {
        fillClass = 'fill-none';
      }
    }

    cell.className = `el-cell ${fillClass}${isRad}`;
    cell.style.setProperty('--cell-bg', bgHex);
    cell.style.setProperty('--cell-border', borderHex);

    const tetBadge = el.has_tetrahedral_motif ? `<span class="el-tet-badge" title="Verified 4-Coordinate Tetrahedral Network Motif (CN=4)">&#9670;</span>` : `<span></span>`;
    cell.innerHTML = `
      <div class="el-top">
        <span class="el-z">${el.atomic_number}</span>
        ${tetBadge}
      </div>
      <div class="el-sym">${el.symbol}</div>
      <div class="el-role">${el.short_role_label}</div>
      <div class="el-metric">${metricText}</div>
    `;
  }

  function applyFilters() {
    const q = searchQuery.trim().toLowerCase();

    ELEMENTS.forEach(el => {
      const cell = document.getElementById(`el-cell-${el.atomic_number}`);
      if (!cell) return;

      const catCodeVal = el.category_code || el.amorphous_category_key || '';
      const catTitleVal = el.category_title || el.amorphous_category_label || '';

      let passFilter = true;
      if (activeFilter === 'full') {
        passFilter = el.fill_mode === 'full';
      } else if (activeFilter === 'half') {
        passFilter = el.fill_mode === 'half';
      } else if (activeFilter === 'none') {
        passFilter = el.fill_mode === 'none';
      } else if (activeFilter === 'tet') {
        passFilter = el.has_tetrahedral_motif;
      } else if (activeFilter.startsWith('cat:')) {
        const catCode = activeFilter.slice(4);
        passFilter = catCodeVal === catCode;
      } else if (activeFilter.startsWith('class:')) {
        const clsName = activeFilter.slice(6);
        passFilter = (el.class_breakdown && (el.class_breakdown[clsName] || 0) > 0);
      } else if (activeFilter.startsWith('regime:')) {
        const regKey = activeFilter.slice(7);
        passFilter = (el.synthesis_regime_breakdown && (el.synthesis_regime_breakdown[regKey] || 0) > 0);
      }

      let passSearch = true;
      if (q) {
        const matchBasic =
          el.symbol.toLowerCase() === q ||
          el.symbol.toLowerCase().includes(q) ||
          el.name.toLowerCase().includes(q) ||
          String(el.atomic_number) === q ||
          catTitleVal.toLowerCase().includes(q) ||
          (el.short_role_label && el.short_role_label.toLowerCase().includes(q));

        const matchSystem = (el.verified_systems || []).some(
          s => {
            const coordEnv = s.coordination_environment || s.local_coordination || '';
            const regLbl = s.synthesis_regime_label || '';
            return (
              s.formula.toLowerCase().includes(q) ||
              (s.raw_formula && s.raw_formula.toLowerCase().includes(q)) ||
              coordEnv.toLowerCase().includes(q) ||
              regLbl.toLowerCase().includes(q)
            );
          }
        );
        passSearch = matchBasic || matchSystem;
      }

      if (passFilter && passSearch) {
        cell.classList.remove('dimmed');
      } else {
        cell.classList.add('dimmed');
      }
    });

    // Update active state on toolbar buttons & legend items
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === activeFilter);
    });
    document.querySelectorAll('.legend-item').forEach(item => {
      item.classList.toggle('active', `cat:${item.dataset.cat}` === activeFilter);
    });
    ['all', 'full', 'half', 'tet', 'none'].forEach(k => {
      const pill = document.getElementById(`kpi-${k}`);
      if (pill) pill.classList.toggle('active-filter', activeFilter === k);
    });
  }

  window.setQuickFilter = function(f) {
    if (activeFilter === f && f !== 'all') {
      activeFilter = 'all';
    } else {
      activeFilter = f;
    }
    applyFilters();
  };

  window.setColorMode = function(mode) {
    activeColorMode = mode;
    ELEMENTS.forEach(el => {
      const cell = document.getElementById(`el-cell-${el.atomic_number}`);
      if (cell) updateCellAppearance(cell, el);
    });
    applyFilters();
  };

  window.handleSearch = function(val) {
    searchQuery = val || '';
    const clearBtn = document.getElementById('searchClearBtn');
    if (clearBtn) clearBtn.style.display = searchQuery ? 'block' : 'none';
    applyFilters();
  };

  window.clearSearch = function() {
    const inp = document.getElementById('searchInput');
    if (inp) inp.value = '';
    handleSearch('');
  };

  // =========================================================================
  // SLIDE-OUT INSPECTION DRAWER
  // =========================================================================
  window.openDrawer = function(zOrSym) {
    let el = typeof zOrSym === 'number' ? ELEM_BY_Z[zOrSym] : ELEM_BY_SYM[String(zOrSym).toLowerCase()];
    if (!el) return;
    currentElement = el;

    document.querySelectorAll('.el-cell.selected').forEach(c => c.classList.remove('selected'));
    const activeCell = document.getElementById(`el-cell-${el.atomic_number}`);
    if (activeCell) activeCell.classList.add('selected');

    // Header Badge
    const badge = document.getElementById('drawerBadge');
    badge.className = `drawer-el-badge fill-${el.fill_mode}`;
    badge.style.setProperty('--cell-bg', el.color_hex);
    badge.style.setProperty('--cell-border', el.border_hex);
    if (el.fill_mode === 'full') {
      badge.style.background = el.color_hex;
    } else if (el.fill_mode === 'none') {
      badge.style.background = '#FFFFFF';
    } else {
      badge.style.background = '';
    }
    badge.style.borderColor = el.border_hex;

    document.getElementById('drawerZ').textContent = el.atomic_number;
    document.getElementById('drawerTet').style.display = el.has_tetrahedral_motif ? 'inline' : 'none';
    document.getElementById('drawerSym').textContent = el.symbol;
    document.getElementById('drawerMass').textContent = el.atomic_mass;
    document.getElementById('drawerName').textContent = `${el.name} (${el.symbol})`;

    const fillTag = document.getElementById('drawerFillTag');
    fillTag.className = `fill-mode-tag ${el.fill_mode}`;
    if (el.fill_mode === 'full') {
      fillTag.textContent = 'FULL COLOR • Makes Amorphous Phase Possible';
    } else if (el.fill_mode === 'half') {
      fillTag.textContent = 'HALF COLOR • In Reported Amorphous Systems';
    } else {
      fillTag.textContent = 'WHITE • Unreported in Amorphous Catalog';
    }

    const catTitleVal = el.category_title || el.amorphous_category_label || '';
    const shortCn = el.short_cn_label || 'CN=4';
    const subMetricStr = el.occurrence_count > 0 ? `${shortCn} \u00b7 N=${el.occurrence_count} Verified Systems` : '0 Verified Systems in Catalog';
    document.getElementById('drawerRoleSub').textContent = `${catTitleVal} \u2022 ${subMetricStr}`;
    document.getElementById('tabBtnSystems').textContent = `2. Verified Systems (${el.occurrence_count})`;
    const tabBtnStruct = document.getElementById('tabBtnStructure');
    if (tabBtnStruct) {
      tabBtnStruct.textContent = `5. Diffraction, RDF & Rings (${el.occurrence_count})`;
    }

    // Tab 1: Overview & 3D Motif
    const m3d = el.motif_3d || {};
    const motifLabel = m3d.motif_label || m3d.title || 'Local Coordination Motif';
    const motifCoord = m3d.typical_coordination || m3d.coordination_number || '';
    const motifProto = m3d.prototype_unit || m3d.bond_angle || '';
    const motifDesc = m3d.description || m3d.geometry_summary || '';
    document.getElementById('motifTitle').textContent = motifLabel;
    document.getElementById('motifCoord').textContent = `${motifCoord} \u2022 Angles: ${motifProto}`;
    document.getElementById('motifCaption').innerHTML = `<strong>${el.symbol} Local Structure:</strong> ${motifDesc}`;

    const sc = document.getElementById('overviewScorecard');
    const st = el.stoichiometry_stats || {
      min: el.min_atomic_fraction ?? 0,
      mean: el.mean_atomic_fraction ?? 0,
      max: el.max_atomic_fraction ?? 0
    };
    const sysFreq = el.system_frequency ?? el.frequency ?? 0;
    const tetFrac = el.tetrahedral_fraction ?? el.tetrahedral_ratio ?? 0;
    const partnerDiv = el.partner_diversity ?? el.unique_partner_elements ?? 0;

    sc.innerHTML = `
      <div class="metric-box">
        <div class="m-lbl">Primary Coordination</div>
        <div class="m-val" style="color:#0284C7;">${el.occurrence_count > 0 ? shortCn : '—'}</div>
        <div class="m-sub">${motifCoord || el.short_role_label}</div>
      </div>
      <div class="metric-box">
        <div class="m-lbl">Verified Systems (N)</div>
        <div class="m-val">${el.occurrence_count} <span style="font-size:12px;font-weight:700;color:#64748B;">/ ${(DATA.metadata && DATA.metadata.total_verified_amorphous_systems) || __TOTAL_SYS__}</span></div>
        <div class="m-sub">${(sysFreq * 100).toFixed(1)}% of catalog</div>
      </div>
      <div class="metric-box">
        <div class="m-lbl">&#9670; Tetrahedral (CN=4)</div>
        <div class="m-val" style="color:#0369A1;">${el.tetrahedral_count} <span style="font-size:12px;font-weight:700;color:#64748B;">(${(tetFrac * 100).toFixed(0)}%)</span></div>
        <div class="m-sub">${el.has_tetrahedral_motif ? 'Verified CN=4 Motif' : 'Non-tetrahedral'}</div>
      </div>
      <div class="metric-box">
        <div class="m-lbl">Stoichiometric Mean</div>
        <div class="m-val">${(st.mean * 100).toFixed(1)} at.%</div>
        <div class="m-sub">Range: ${(st.min * 100).toFixed(1)}–${(st.max * 100).toFixed(1)} at.%</div>
      </div>
      <div class="metric-box">
        <div class="m-lbl">Co-Occurring Elements</div>
        <div class="m-val">${partnerDiv} <span style="font-size:12px;font-weight:700;color:#64748B;">/ 76</span></div>
        <div class="m-sub">Chemical partner breadth</div>
      </div>
      <div class="metric-box">
        <div class="m-lbl">Cell Fill Mode</div>
        <div class="m-val" style="text-transform:uppercase;">${el.fill_mode}</div>
        <div class="m-sub">${el.short_role_label}</div>
      </div>
    `;

    const cb = el.class_breakdown || {};
    const srb = el.synthesis_regime_breakdown || {};
    const rb = el.role_counts || {};
    document.getElementById('overviewBreakdown').innerHTML = `
      <div style="margin-bottom:8px;">
        <strong>Glass Class Distribution:</strong>
        Oxide: <strong>${cb['Oxide'] || 0}</strong> &bull;
        Chalcogenide: <strong>${cb['Chalcogenide'] || 0}</strong> &bull;
        Metallic Glass: <strong>${cb['Metallic Glass'] || 0}</strong> &bull;
        Covalent Network: <strong>${cb['Covalent Network'] || 0}</strong>
      </div>
      <div style="margin-bottom:8px;">
        <strong>Synthesis Regime Breakdown:</strong>
        Bulk Melt-Quenched: <strong>${srb.bulk_melt_quenched || 0}</strong> &bull;
        Rapid-Quenched Ribbon / Levitated: <strong>${srb.rapid_quenched_ribbon || 0}</strong> &bull;
        Vapor / Thin-Film: <strong>${srb.vapor_thin_film || 0}</strong>
      </div>
      <div style="margin-bottom:8px;">
        <strong>Crystal-Chemical Role Counts (` + "`material_elements`" + `):</strong>
        Network Former: <strong>${rb.network_former || 0}</strong> &bull;
        Intermediate: <strong>${rb.intermediate || 0}</strong> &bull;
        Modifier: <strong>${rb.modifier || 0}</strong> &bull;
        BMG Matrix/Cluster: <strong>${rb.metallic_glass_matrix || 0}</strong> &bull;
        Bridging Anion: <strong>${rb.bridging_anion || 0}</strong>
      </div>
      <div style="color:#475569;font-size:11.5px;">
        <strong>Structural Role Rationale:</strong> ${el.category_derivation_rule || 'Unreported in verified inorganic amorphous catalog.'}
      </div>
    `;

    // Tab 2: Verified Systems
    const sysInput = document.getElementById('sysSearchInput');
    if (sysInput) sysInput.value = '';
    renderElementSystems();

    // Tab 3: Co-Occurrence & Correlations
    renderElementCorrelations(el);

    // Tab 4: Mechanism & Reference
    renderElementMechanism(el);

    // Tab 5: Diffraction, RDF & Rings
    renderElementStructureTab(el);

    // Open Drawer & Render 3D Scene
    document.getElementById('drawerBackdrop').classList.add('open');
    document.getElementById('inspectionDrawer').classList.add('open');
    initOrUpdate3DScene(el, 'canvasHolder');
  };

  window.closeDrawer = function() {
    document.getElementById('drawerBackdrop').classList.remove('open');
    document.getElementById('inspectionDrawer').classList.remove('open');
  };

  window.openGuideModal = function() {
    const m = document.getElementById('modalGuide');
    if (m) m.classList.add('open');
  };

  window.closeGuideModal = function() {
    const m = document.getElementById('modalGuide');
    if (m) m.classList.remove('open');
  };

  window.switchTab = function(tabId) {
    document.querySelectorAll('.drawer-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    document.querySelectorAll('.tab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === `pane-${tabId}`);
    });
    if (tabId === 'overview' && currentElement) {
      setTimeout(() => initOrUpdate3DScene(currentElement, 'canvasHolder'), 30);
    }
  };

  window.inspectSystemStructure = function(sysIdxOrFormula) {
    switchTab('structure');
    const systems = (currentElement && currentElement.verified_systems) || [];
    let idx = 0;
    if (typeof sysIdxOrFormula === 'string' && isNaN(Number(sysIdxOrFormula))) {
      const found = systems.findIndex(s => s.formula === sysIdxOrFormula || s.raw_formula === sysIdxOrFormula);
      idx = found >= 0 ? found : 0;
    } else {
      idx = Number(sysIdxOrFormula) || 0;
    }
    const sel = document.getElementById('structSysSelect');
    if (sel) {
      sel.value = String(idx);
    }
    renderElementStructurePlots(idx);
  };

  window.renderElementSystems = function() {
    const el = currentElement;
    const container = document.getElementById('drawerSystemsList');
    if (!el || !container) return;

    const q = (document.getElementById('sysSearchInput')?.value || '').trim().toLowerCase();
    const allSys = (el.verified_systems || []).map((s, idx) => ({ s, origIdx: idx }));
    const systems = allSys.filter(({ s }) => {
      if (!q) return true;
      const coordEnv = s.coordination_environment || s.local_coordination || '';
      const pTitle = s.paper_title || '';
      const srcRef = s.source_reference || s.reference_citation || '';
      const regLbl = s.synthesis_regime_label || '';
      return (
        s.formula.toLowerCase().includes(q) ||
        (s.raw_formula && s.raw_formula.toLowerCase().includes(q)) ||
        s.material_class.toLowerCase().includes(q) ||
        regLbl.toLowerCase().includes(q) ||
        coordEnv.toLowerCase().includes(q) ||
        pTitle.toLowerCase().includes(q) ||
        srcRef.toLowerCase().includes(q) ||
        (s.verification_method && s.verification_method.toLowerCase().includes(q)) ||
        (s.reference_doi && s.reference_doi.toLowerCase().includes(q))
      );
    });

    if (systems.length === 0) {
      container.innerHTML = `<div class="prose-card">No verified inorganic amorphous systems matching filter for <strong>${el.name} (${el.symbol})</strong>.</div>`;
      return;
    }

    container.innerHTML = systems.map(({ s, origIdx }) => {
      const clsKey = s.material_class.split(' ')[0];
      const isTet = (s.tetrahedral_coordination_flag ?? s.tetrahedral_flag ?? 0) > 0;
      const tetTag = isTet
        ? `<span style="color:#0369A1;font-size:11px;font-weight:800;">&#9670; CN=4</span>`
        : '';
      const rawNote = (s.raw_formula && s.raw_formula !== s.formula)
        ? `<span style="font-size:11px;font-weight:600;color:#64748B;">(${s.raw_formula})</span>`
        : '';
      const convNote = s.crystalline_conversion_note || s.notes || '';
      const convHtml = convNote
        ? `<div style="margin-top:4px;font-size:11px;color:#0F766E;background:#F0FDFA;padding:4px 7px;border-radius:4px;border:1px solid #99F6E4;"><strong>Amorphization Benchmark:</strong> ${convNote}</div>`
        : '';
      const elRole = s.element_role || s.structural_role || '';
      const coordEnv = s.coordination_environment || s.local_coordination || '';
      const regLabel = s.synthesis_regime_label || 'Bulk Melt-Quenched Glass / BMG';
      const srcRef = s.source_reference || s.reference_citation || '';
      const doiUrl = s.doi_url || (s.reference_doi && s.reference_doi.startsWith('http') ? s.reference_doi : `https://doi.org/${s.reference_doi}`);
      const q1 = s.fsdp_q1_inv_A ? `Q₁=${Number(s.fsdp_q1_inv_A).toFixed(2)} Å⁻¹` : '';
      const r1 = s.r1_bond_length_A ? `r₁=${Number(s.r1_bond_length_A).toFixed(2)} Å` : '';
      const th = s.mean_bond_angle_deg ? `θ=${Number(s.mean_bond_angle_deg).toFixed(1)}°` : '';
      const ring = s.dominant_ring_or_voronoi || '';
      const provObj = (s.structural_characterization && s.structural_characterization.provenance) || {};
      const isExpBench = provObj.overall_type === 'direct_experimental_benchmark';
      const provPill = isExpBench
        ? `<span class="prov-badge prov-exp" title="Scalar peak positions anchored to published experimental diffraction / EXAFS / RMC benchmark; continuous curves parameterized">&#128300; Lit. Peak Anchors + Parameterized Curve</span>`
        : `<span class="prov-badge prov-recon" title="Composition-weighted analytical reconstruction from constituent atomic fractions">&#9878;&#65039; Composition-Weighted Reconstruction</span>`;
      const sroBadges = (q1 || r1 || th || ring) ? `
        <div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:6px;align-items:center;">
          ${provPill}
          ${q1 ? `<span style="background:#EFF6FF;border:1px solid #BFDBFE;color:#1D4ED8;font-size:10.5px;font-weight:800;padding:2px 6px;border-radius:4px;">${q1}</span>` : ''}
          ${r1 ? `<span style="background:#F0FDF4;border:1px solid #BBF7D0;color:#15803D;font-size:10.5px;font-weight:800;padding:2px 6px;border-radius:4px;">${r1}</span>` : ''}
          ${th ? `<span style="background:#FEF3C7;border:1px solid #FDE68A;color:#B45309;font-size:10.5px;font-weight:800;padding:2px 6px;border-radius:4px;">${th}</span>` : ''}
          ${ring ? `<span style="background:#F3E8FF;border:1px solid #E9D5FF;color:#6D28D9;font-size:10.5px;font-weight:800;padding:2px 6px;border-radius:4px;">${ring}</span>` : ''}
        </div>
      ` : '';
      return `
        <div class="sys-card">
          <div class="sys-card-top">
            <div class="sys-formula">
              <span>${s.formula}</span>
              ${rawNote}
              ${tetTag}
            </div>
            <span class="class-badge ${clsKey}">${s.material_class}</span>
          </div>
          <div class="sys-meta">
            <div><strong>${el.symbol} Atomic Fraction:</strong> ${(s.atomic_fraction * 100).toFixed(1)} at.% &bull; <strong>Role:</strong> ${elRole}</div>
            <div><strong>Synthesis Regime:</strong> ${regLabel}</div>
            <div><strong>Local Coordination:</strong> ${coordEnv}</div>
            <div><strong>Verification:</strong> ${s.verification_method}</div>
          </div>
          ${sroBadges}
          ${convHtml}
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;margin-top:6px;">
            <a class="doi-link" style="margin-top:0;" href="${doiUrl}" target="_blank" rel="noopener noreferrer">
              Verified DOI: ${s.reference_doi} — ${srcRef} &nearr;
            </a>
            <button onclick="inspectSystemStructure(${origIdx})" style="padding:3px 8px;font-size:10.5px;font-weight:800;color:#0F766E;background:#F0FDFA;border:1.5px solid #14B8A6;border-radius:5px;cursor:pointer;white-space:nowrap;">
              &#128200; S(Q), g(r) &amp; Rings &rarr;
            </button>
          </div>
        </div>
      `;
    }).join('');
  };

  function buildLinePlotSvg(points, xMin, xMax, yMin, yMax, xLabel, yLabel, strokeColor, fillColor, vMarkers, hBaseline) {
    const W = 540, H = 195;
    const padL = 44, padR = 18, padT = 18, padB = 34;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;
    const tx = x => padL + ((x - xMin) / Math.max(1e-6, xMax - xMin)) * plotW;
    const ty = y => padT + plotH - ((y - yMin) / Math.max(1e-6, yMax - yMin)) * plotH;

    let gridHtml = '';
    const yTicks = 4;
    for (let i = 0; i <= yTicks; i++) {
      const yVal = yMin + (i / yTicks) * (yMax - yMin);
      const py = ty(yVal);
      gridHtml += `<line x1="${padL}" y1="${py.toFixed(1)}" x2="${W - padR}" y2="${py.toFixed(1)}" stroke="#E2E8F0" stroke-width="1"/>`;
      gridHtml += `<text x="${padL - 6}" y="${(py + 3.5).toFixed(1)}" text-anchor="end" font-size="9.5" font-weight="600" fill="#64748B">${yVal.toFixed(1)}</text>`;
    }

    const xTicks = 5;
    for (let i = 0; i <= xTicks; i++) {
      const xVal = xMin + (i / xTicks) * (xMax - xMin);
      const px = tx(xVal);
      gridHtml += `<line x1="${px.toFixed(1)}" y1="${padT}" x2="${px.toFixed(1)}" y2="${padT + plotH}" stroke="#F1F5F9" stroke-width="1"/>`;
      gridHtml += `<text x="${px.toFixed(1)}" y="${padT + plotH + 13}" text-anchor="middle" font-size="9.5" font-weight="600" fill="#64748B">${xVal.toFixed(xMax > 30 ? 0 : 1)}</text>`;
    }

    let baseHtml = '';
    if (hBaseline !== null && hBaseline !== undefined && hBaseline >= yMin && hBaseline <= yMax) {
      const by = ty(hBaseline);
      baseHtml = `<line x1="${padL}" y1="${by.toFixed(1)}" x2="${W - padR}" y2="${by.toFixed(1)}" stroke="#94A3B8" stroke-width="1.2" stroke-dasharray="4,3"/>`;
    }

    let polyPts = points.map(p => `${tx(p[0]).toFixed(1)},${ty(p[1]).toFixed(1)}`).join(' ');
    let areaPts = `${tx(points[0][0]).toFixed(1)},${ty(yMin).toFixed(1)} ` + polyPts + ` ${tx(points[points.length - 1][0]).toFixed(1)},${ty(yMin).toFixed(1)}`;

    let markersHtml = '';
    (vMarkers || []).forEach(m => {
      if (m.x >= xMin && m.x <= xMax) {
        const mx = tx(m.x);
        markersHtml += `<line x1="${mx.toFixed(1)}" y1="${padT}" x2="${mx.toFixed(1)}" y2="${padT + plotH}" stroke="${m.color || '#EF4444'}" stroke-width="1.4" stroke-dasharray="3,2"/>`;
        markersHtml += `<rect x="${(mx - 28).toFixed(1)}" y="${padT + 2}" width="56" height="14" rx="3" fill="#FFFFFF" stroke="${m.color || '#EF4444'}" stroke-width="1"/>`;
        markersHtml += `<text x="${mx.toFixed(1)}" y="${padT + 12}" text-anchor="middle" font-size="8.5" font-weight="800" fill="${m.color || '#EF4444'}">${m.label}</text>`;
      }
    });

    return `
      <svg class="sro-svg" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
        ${gridHtml}
        ${baseHtml}
        <polygon points="${areaPts}" fill="${fillColor}" opacity="0.22"/>
        <polyline points="${polyPts}" fill="none" stroke="${strokeColor}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        ${markersHtml}
        <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" stroke="#475569" stroke-width="1.3"/>
        <line x1="${padL}" y1="${padT + plotH}" x2="${W - padR}" y2="${padT + plotH}" stroke="#475569" stroke-width="1.3"/>
        <text x="${padL + plotW / 2}" y="${H - 4}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#1E293B">${xLabel}</text>
        <text x="12" y="${padT + plotH / 2}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#1E293B" transform="rotate(-90 12 ${padT + plotH / 2})">${yLabel}</text>
      </svg>
    `;
  }

  window.renderElementStructureTab = function(el) {
    const sel = document.getElementById('structSysSelect');
    const sumWrap = document.getElementById('structElementSummary');
    const plotsWrap = document.getElementById('structPlotsContainer');
    if (!sel || !sumWrap || !plotsWrap) return;

    const systems = el.verified_systems || [];
    const sroSum = el.structural_characterization_summary || {};
    if (!systems.length) {
      sel.innerHTML = `<option value="">No verified amorphous systems for ${el.symbol}</option>`;
      sumWrap.innerHTML = `<strong>${el.name} (${el.symbol})</strong> has 0 verified inorganic amorphous systems in the catalog.`;
      plotsWrap.innerHTML = `<div class="prose-card">Select an active amorphous element (full or half colored cell) to inspect its Diffraction Structure Factor <em>S(Q)</em>, Radial &amp; Partial Pair Distribution Functions <em>g(r)</em>, Bond-Angle Distribution <em>P(&theta;)</em>, and Ring / Voronoi Topology.</div>`;
      return;
    }

    sel.innerHTML = systems.map((s, idx) => {
      const rawTag = (s.raw_formula && s.raw_formula !== s.formula) ? ` (${s.raw_formula})` : '';
      const pType = (s.structural_characterization && s.structural_characterization.provenance && s.structural_characterization.provenance.overall_type) || '';
      const srcTag = pType === 'direct_experimental_benchmark' ? '🔬 Exp. Benchmark' : '⚖️ Comp.-Weighted';
      return `<option value="${idx}">${s.formula}${rawTag} — ${s.material_class} [${srcTag}] (${s.reference_doi})</option>`;
    }).join('');

    const q1Range = sroSum.fsdp_q1_range_inv_A ? `${sroSum.fsdp_q1_range_inv_A.min.toFixed(2)}–${sroSum.fsdp_q1_range_inv_A.max.toFixed(2)} Å⁻¹ (mean ${sroSum.fsdp_q1_range_inv_A.mean.toFixed(2)} Å⁻¹)` : '—';
    const r1Range = sroSum.r1_bond_length_range_A ? `${sroSum.r1_bond_length_range_A.min.toFixed(2)}–${sroSum.r1_bond_length_range_A.max.toFixed(2)} Å (mean ${sroSum.r1_bond_length_range_A.mean.toFixed(2)} Å)` : '—';
    const thRange = sroSum.mean_bond_angle_range_deg ? `${sroSum.mean_bond_angle_range_deg.min.toFixed(1)}°–${sroSum.mean_bond_angle_range_deg.max.toFixed(1)}° (mean ${sroSum.mean_bond_angle_range_deg.mean.toFixed(1)}°)` : '—';
    const expCnt = sroSum.direct_experimental_benchmark_count ?? systems.filter(s => (s.structural_characterization?.provenance?.overall_type === 'direct_experimental_benchmark')).length;
    const reconCnt = systems.length - expCnt;

    sumWrap.innerHTML = `
      <div class="prose-card" style="padding:8px 11px;font-size:11.5px;background:#F8FAFC;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
          <strong>${el.name} (${el.symbol}) Ensemble SRO/MRO Summary (${systems.length} Systems):</strong>
          <span style="display:inline-flex;gap:6px;flex-wrap:wrap;">
            <span class="prov-badge prov-exp">&#128300; ${expCnt} Direct Exp./Lit. Benchmark</span>
            <span class="prov-badge prov-recon">&#9878;&#65039; ${reconCnt} Composition-Weighted</span>
          </span>
        </div>
        <div style="margin-top:4px;">
          &bull; <strong>Diffraction <em>Q</em>₁ Range:</strong> ${q1Range} &nbsp;|&nbsp;
          &bull; <strong>1st-Shell Bond <em>r</em>₁ Range:</strong> ${r1Range} &nbsp;|&nbsp;
          &bull; <strong>Bond Angle <em>&theta;</em> Range:</strong> ${thRange}
        </div>
      </div>
    `;

    renderElementStructurePlots(0);
  };

  window.renderElementStructurePlots = function(sysIdx) {
    const el = currentElement;
    const plotsWrap = document.getElementById('structPlotsContainer');
    if (!el || !plotsWrap) return;
    const systems = el.verified_systems || [];
    const idx = Number(sysIdx) || 0;
    const sys = systems[idx];
    if (!sys || !sys.structural_characterization) {
      plotsWrap.innerHTML = `<div class="prose-card">No structural characterization profile available for this system.</div>`;
      return;
    }

    const sc = sys.structural_characterization;
    const prov = sc.provenance || {};
    const isExp = prov.overall_type === 'direct_experimental_benchmark';
    const sq = sc.diffraction_sq || {};
    const gr = sc.rdf_gr || {};
    const ba = sc.bond_angle_distribution || {};
    const rv = sc.ring_or_voronoi_distribution || {};
    const doiUrl = sys.doi_url || `https://doi.org/${sys.reference_doi}`;

    const makeSourceBadge = (sec) => {
      const st = sec.source_type || prov.overall_type || 'composition_weighted_reconstruction';
      const isExpSec = st === 'direct_experimental_benchmark' || st === 'experimental_benchmark';
      const rawLbl = sec.source_badge || (isExpSec ? 'Experiment / Literature Benchmark' : 'Composition-Weighted Reconstruction');
      const cleanLbl = rawLbl.replace(/^(\uD83D\uDD2C|\u2696\uFE0F|\u2696)\s*/, '');
      if (isExpSec) {
        return `<span class="prov-badge prov-exp">&#128300; ${cleanLbl}</span>`;
      }
      return `<span class="prov-badge prov-recon">&#9878;&#65039; ${cleanLbl}</span>`;
    };

    // 1. S(Q) SVG
    const sqPts = sq.curve_points || [[0.5, 0.1], [2.0, 2.0], [8.0, 1.0]];
    const sqYMax = Math.max(3.2, ...sqPts.map(p => p[1]) ) * 1.08;
    const sqMarkers = [
      { x: sq.fsdp_q1_inv_A, label: `Q₁=${Number(sq.fsdp_q1_inv_A).toFixed(2)}`, color: '#1D4ED8' }
    ];
    if (sq.principal_peak_q2_inv_A && Math.abs(sq.principal_peak_q2_inv_A - sq.fsdp_q1_inv_A) > 0.35) {
      sqMarkers.push({ x: sq.principal_peak_q2_inv_A, label: `Q₂=${Number(sq.principal_peak_q2_inv_A).toFixed(2)}`, color: '#0F766E' });
    }
    const sqSvg = buildLinePlotSvg(sqPts, 0.4, 9.0, 0.0, sqYMax, 'Scattering Vector Q (Å⁻¹)', 'S(Q)', '#2563EB', '#60A5FA', sqMarkers, 1.0);

    // 2. g(r) SVG + Partial Pairs Table
    const grPts = gr.curve_points || [[1.0, 0.0], [2.0, 2.5], [6.5, 1.0]];
    const grYMax = Math.max(3.2, ...grPts.map(p => p[1])) * 1.08;
    const grMarkers = [
      { x: gr.r1_A, label: `r₁=${Number(gr.r1_A).toFixed(2)}Å`, color: '#15803D' },
      { x: gr.r2_A, label: `r₂=${Number(gr.r2_A).toFixed(2)}Å`, color: '#0369A1' }
    ];
    const grSvg = buildLinePlotSvg(grPts, 0.8, 6.8, 0.0, grYMax, 'Interatomic Distance r (Å)', 'g(r)', '#16A34A', '#4ADE80', grMarkers, 1.0);

    const partials = gr.partial_pairs || [];
    const partialsHtml = partials.length ? `
      <table class="partial-table">
        <thead>
          <tr>
            <th>Partial Pair &alpha;&ndash;&beta;</th>
            <th>1st-Shell <em>r<sub>&alpha;&beta;</sub></em> (Å)</th>
            <th>Weight <em>w<sub>&alpha;&beta;</sub></em></th>
            <th>Coord. <em>N<sub>&alpha;&beta;</sub></em></th>
            <th>Bonding Character</th>
            <th>Pair Provenance</th>
          </tr>
        </thead>
        <tbody>
          ${partials.map(p => {
            const wStr = p.composition_weight !== undefined ? `${(Number(p.composition_weight) * 100).toFixed(1)}%` : '—';
            const pSrc = p.pair_source || '';
            const isLitPair = pSrc.includes('Experiment') || pSrc.includes('Literature');
            const pBadge = isLitPair
              ? `<span class="prov-badge prov-exp" style="font-size:9.5px;padding:1px 5px;">&#128300; ${pSrc}</span>`
              : `<span class="prov-badge prov-recon" style="font-size:9.5px;padding:1px 5px;">&#9878;&#65039; ${pSrc || 'Covalent/Metallic Sum'}</span>`;
            return `
              <tr>
                <td><strong>${p.pair}</strong></td>
                <td>${Number(p.r_ij_A).toFixed(2)} Å</td>
                <td><strong>${wStr}</strong></td>
                <td>${p.coordination_number}</td>
                <td>${p.bond_type}</td>
                <td>${pBadge}</td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    ` : '';

    // 3. Bond-Angle Distribution P(theta) SVG
    const baPts = ba.curve_points || [[50, 0], [109.5, 1.0], [175, 0]];
    const baMarkers = [
      { x: ba.mean_angle_deg, label: `θ₁=${Number(ba.mean_angle_deg).toFixed(1)}°`, color: '#D97706' }
    ];
    if (ba.secondary_angle_deg) {
      baMarkers.push({ x: ba.secondary_angle_deg, label: `θ₂=${Number(ba.secondary_angle_deg).toFixed(0)}°`, color: '#7C3AED' });
    }
    const baSvg = buildLinePlotSvg(baPts, 45, 175, 0.0, 1.15, 'Intrapolyhedral / Interpolyhedral Angle θ (deg)', 'P(θ) (norm.)', '#D97706', '#FBBF24', baMarkers, null);

    // 4. Ring / Voronoi Bar Chart
    const bars = rv.bars || [];
    const maxPct = Math.max(40, ...bars.map(b => b.pct));
    const barsHtml = bars.map(b => {
      const wPct = Math.min(100, (b.pct / maxPct) * 100);
      const isDom = rv.dominant_motif && rv.dominant_motif.includes(b.label);
      const fillBg = isDom ? 'linear-gradient(90deg,#7C3AED,#6D28D9)' : 'linear-gradient(90deg,#38BDF8,#0284C7)';
      return `
        <div class="ring-bar-row">
          <div class="ring-bar-lbl">${b.label}</div>
          <div class="ring-bar-track">
            <div class="ring-bar-fill" style="width:${wPct.toFixed(1)}%;background:${fillBg};"></div>
          </div>
          <div class="ring-bar-val">${Number(b.pct).toFixed(1)}%</div>
        </div>
      `;
    }).join('');

    const rawOverallBadge = prov.overall_badge || (isExp ? 'Experiment / Literature Benchmark' : 'Composition-Weighted Reconstruction');
    const overallBadgeText = rawOverallBadge.replace(/^(\uD83D\uDD2C|\u2696\uFE0F|\u2696)\s*/, '');
    const benchRefText = prov.benchmark_reference || '';
    const compNoteText = prov.composition_weighting_note || '';

    plotsWrap.innerHTML = `
      <div class="sro-plot-card" style="background:#F8FAFC;border-left:4px solid #0284C7;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;">
          <div>
            <div style="font-size:14px;font-weight:800;color:#0F172A;display:flex;align-items:center;gap:7px;flex-wrap:wrap;">
              <span>${sys.formula}</span>
              <span style="font-size:12px;font-weight:600;color:#475569;">(${sys.material_class})</span>
              <span class="prov-badge ${isExp ? 'prov-exp' : 'prov-recon'}">${isExp ? '&#128300;' : '&#9878;&#65039;'} ${overallBadgeText}</span>
            </div>
            <div style="font-size:11.5px;color:#334155;margin-top:3px;"><strong>Local Coordination:</strong> ${sys.coordination_environment || sys.local_coordination}</div>
          </div>
          <a class="doi-link" style="margin-top:0;" href="${doiUrl}" target="_blank" rel="noopener noreferrer">DOI: ${sys.reference_doi} &nearr;</a>
        </div>
        <div style="font-size:11px;color:#475569;margin-top:6px;">
          <strong>Verified Reference:</strong> ${sys.source_reference || sys.reference_citation}
        </div>
        <div class="prov-banner ${isExp ? 'exp' : 'recon'}" style="margin-top:8px;margin-bottom:0;">
          <div><strong>Data Provenance:</strong> ${benchRefText}</div>
          <div style="margin-top:2px;font-size:11px;opacity:0.92;"><strong>Stoichiometric Composition Weighting:</strong> ${compNoteText}</div>
        </div>
      </div>

      <div class="sro-plot-card">
        <h4>
          <span>1. Diffraction Structure Factor <em>S(Q)</em></span>
          <span style="display:inline-flex;gap:5px;align-items:center;flex-wrap:wrap;">
            ${makeSourceBadge(sq)}
            <span class="sro-badge">Q₁ = ${Number(sq.fsdp_q1_inv_A).toFixed(2)} Å⁻¹ &bull; L<sub>MRO</sub> = ${Number(sq.correlation_length_L_A).toFixed(1)} Å</span>
          </span>
        </h4>
        ${sqSvg}
        <div class="sro-caption">
          <div><strong>Probe:</strong> ${sq.probe || 'X-ray / Neutron Total Scattering'} &bull; <strong>Source:</strong> ${sq.source_detail || ''}</div>
          <div style="margin-top:2px;"><strong>Interpretation:</strong> ${sq.physical_interpretation || ''}</div>
        </div>
      </div>

      <div class="sro-plot-card">
        <h4>
          <span>2. Radial &amp; Partial Pair Distribution Functions <em>g(r), g<sub>&alpha;&beta;</sub>(r)</em></span>
          <span style="display:inline-flex;gap:5px;align-items:center;flex-wrap:wrap;">
            ${makeSourceBadge(gr)}
            <span class="sro-badge">r₁ = ${Number(gr.r1_A).toFixed(2)} Å &bull; r₂/r₁ = ${Number(gr.r2_r1_ratio).toFixed(2)}</span>
          </span>
        </h4>
        ${grSvg}
        ${partialsHtml}
        <div class="sro-caption">
          <div><strong>Source &amp; Weighting:</strong> ${gr.source_detail || ''}</div>
          <div style="margin-top:2px;"><strong>Interpretation:</strong> ${gr.physical_interpretation || ''}</div>
        </div>
      </div>

      <div class="sro-plot-card">
        <h4>
          <span>3. Bond-Angle Distribution <em>P(&theta;)</em></span>
          <span style="display:inline-flex;gap:5px;align-items:center;flex-wrap:wrap;">
            ${makeSourceBadge(ba)}
            <span class="sro-badge">&theta;&#772; = ${Number(ba.mean_angle_deg).toFixed(1)}° &plusmn; ${Number(ba.sigma_angle_deg).toFixed(1)}°</span>
          </span>
        </h4>
        ${baSvg}
        <div class="sro-caption">
          <div><strong>Source &amp; Weighting:</strong> ${ba.source_detail || ''}</div>
          <div style="margin-top:2px;"><strong>Motif Geometry:</strong> ${ba.motif_geometry || ''} &bull; ${ba.physical_interpretation || ''}</div>
        </div>
      </div>

      <div class="sro-plot-card">
        <h4>
          <span>4. ${rv.distribution_type || 'Ring Size / Voronoi Topology Distribution'}</span>
          <span style="display:inline-flex;gap:5px;align-items:center;flex-wrap:wrap;">
            ${makeSourceBadge(rv)}
            <span class="sro-badge">Dominant: ${rv.dominant_motif || ''}</span>
          </span>
        </h4>
        <div style="margin-top:6px;">
          ${barsHtml}
        </div>
        <div class="sro-caption">
          <div><strong>Source &amp; Weighting:</strong> ${rv.source_detail || ''}</div>
          <div style="margin-top:2px;"><strong>Topological Signature:</strong> ${rv.physical_interpretation || ''}</div>
        </div>
      </div>
    `;
  };

  function renderElementCorrelations(el) {
    const chipsWrap = document.getElementById('drawerPartnerChips');
    const tableWrap = document.getElementById('drawerCorrTableWrap');

    const partners = el.top_cooccurring_partners || el.top_co_occurring_partners || [];
    if (partners.length === 0) {
      chipsWrap.innerHTML = `<span style="font-size:12px;color:#64748B;">No co-occurring partners in catalog.</span>`;
      tableWrap.innerHTML = `<div class="prose-card">This element has 0 recorded systems in <code>amorphous_materials.db</code>.</div>`;
      return;
    }

    chipsWrap.innerHTML = partners.map(p => {
      const pEl = ELEM_BY_SYM[p.partner.toLowerCase()];
      const bg = pEl ? pEl.color_hex : '#E2E8F0';
      const coCnt = p.cooccurrence_count ?? p.count ?? 0;
      return `
        <div class="partner-chip" onclick="openDrawer('${p.partner}')" title="Click to inspect ${p.partner}">
          <span style="width:10px;height:10px;border-radius:50%;background:${bg};border:1px solid #475569;"></span>
          <span>${p.partner}</span>
          <span style="font-size:11px;color:#475569;">(${coCnt} sys)</span>
        </div>
      `;
    }).join('');

    const corrs = el.top_correlations || el.pair_correlations || [];
    const corrByPartner = {};
    corrs.forEach(c => { corrByPartner[c.partner] = c; });

    let rowsHtml = partners.map(p => {
      const c = corrByPartner[p.partner] || {};
      const coCnt = p.cooccurrence_count ?? p.count ?? c.co_occurrences ?? 0;
      const phiVal = c.pearson_phi ?? c.pearson_phi_binary;
      const rVal = c.stoichiometric_r ?? c.pearson_r_union_fraction;
      const nmiVal = c.normalized_mutual_info ?? c.normalized_mi;
      const phi = phiVal !== undefined ? phiVal.toFixed(3) : '—';
      const r = rVal !== undefined ? rVal.toFixed(3) : '—';
      const nmi = nmiVal !== undefined ? nmiVal.toFixed(3) : '—';

      const sharedSys = p.shared_systems || c.shared_systems || [];
      const sysPillsHtml = sharedSys.length
        ? `<div class="cooc-sys-list">` + sharedSys.map(s => {
            const safeFormula = String(s.formula).replace(/'/g, "\\'");
            const tip = `${s.formula} (${s.material_class || ''}) — DOI: ${s.reference_doi || ''} — Click to view S(Q), g(r) & Rings`;
            return `<span class="cooc-sys-pill" onclick="inspectSystemStructure('${safeFormula}')" title="${tip}">${s.formula}</span>`;
          }).join('') + `</div>`
        : '—';

      return `
        <tr>
          <td style="white-space:nowrap;"><strong style="cursor:pointer;color:#0284C7;" onclick="openDrawer('${p.partner}')">${el.symbol}–${p.partner}</strong></td>
          <td style="text-align:center;"><strong>${coCnt}</strong></td>
          <td>${sysPillsHtml}</td>
          <td>${phi}</td>
          <td>${r}</td>
          <td>${nmi}</td>
        </tr>
      `;
    }).join('');

    tableWrap.innerHTML = `
      <table class="corr-table">
        <thead>
          <tr>
            <th>Pair</th>
            <th>Count</th>
            <th>All Shared Amorphous Systems (Click System for S(Q), g(r) &amp; Rings)</th>
            <th>&phi;<sub>ij</sub></th>
            <th>r<sub>ij</sub></th>
            <th>NMI</th>
          </tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    `;
  }

  function renderElementMechanism(el) {
    const catTitleVal = el.category_title || el.amorphous_category_label || '';
    document.getElementById('drawerMechanism').innerHTML = `
      <p style="margin-bottom:8px;"><strong>Structural Role:</strong> ${catTitleVal} (<code>fill_mode = "${el.fill_mode}"</code>)</p>
      <p>${el.mechanism_summary || ''}</p>
    `;

    const convWrap = document.getElementById('drawerConversions');
    const convs = el.conversion_examples || el.conversion_benchmarks || [];
    if (convs.length === 0) {
      convWrap.innerHTML = `<div class="prose-card" style="font-size:12px;color:#64748B;">See Verified Systems tab for full stoichiometric compositions and experimental verification references.</div>`;
    } else {
      convWrap.innerHTML = convs.map(c => {
        const parentSys = c.parent_crystalline_system || c.crystalline_parent || '';
        const inducedSys = c.amorphous_system_induced || c.amorphous_system || '';
        const promoter = c.promoting_element || c.added_element || '';
        const mech = c.structural_mechanism || c.mechanism || '';
        const refDoi = c.reference_doi || c.doi || '';
        return `
          <div class="prose-card" style="border-left:3.5px solid #0284C7;">
            <div style="font-weight:800;color:#0F172A;margin-bottom:4px;">
              ${parentSys} &rarr; <span style="color:#0284C7;">${inducedSys}</span>
              <span style="font-size:11px;color:#475569;">(Promoter: ${promoter})</span>
            </div>
            <div style="font-size:11.5px;color:#334155;margin-bottom:4px;">${mech}</div>
            <div style="font-size:11px;color:#64748B;">Verification: ${c.verification} &bull; DOI: ${refDoi}</div>
          </div>
        `;
      }).join('');
    }

    const ref = el.crystalline_reference || {};
    const cryst = el.crystallography || {};
    const elecCfgObj = el.electronic_configuration || {};
    const chemBondObj = el.chemical_bonding || {};
    const lat = ref.lattice_constants || cryst.lattice_parameters || {};
    const latStr = lat.a ? `a=${lat.a} Å${lat.c ? ', c=' + lat.c + ' Å' : ''}` : '—';
    const elecCfgStr = el.electron_configuration || elecCfgObj.abbreviated || elecCfgObj.full || '—';
    const chemSeriesStr = el.chemical_series || el.chemical_family || '';
    const paulingEN = el.electronegativity_pauling ?? chemBondObj.electronegativity_pauling ?? '—';
    const radiusPm = el.atomic_radius_pm ?? chemBondObj.atomic_radius_pm;
    const crystStruct = ref.crystal_structure || cryst.crystal_system || '—';
    const spaceGrp = ref.space_group || cryst.space_group_symbol || '';

    document.getElementById('drawerAtomicGrid').innerHTML = `
      <div class="metric-box">
        <div class="m-lbl">Electron Config</div>
        <div class="m-val" style="font-size:13px;">${elecCfgStr}</div>
        <div class="m-sub">${chemSeriesStr}</div>
      </div>
      <div class="metric-box">
        <div class="m-lbl">Pauling Electronegativity</div>
        <div class="m-val">${paulingEN}</div>
        <div class="m-sub">Radius: ${radiusPm ? radiusPm + ' pm' : '—'}</div>
      </div>
      <div class="metric-box">
        <div class="m-lbl">Reference Crystal</div>
        <div class="m-val" style="font-size:13px;">${crystStruct}</div>
        <div class="m-sub">${spaceGrp} (${latStr})</div>
      </div>
    `;
  }

  // =========================================================================
  // INTERACTIVE THREE.JS 3D COORDINATION MOTIF VIEWER
  // =========================================================================
  let threeState = {
    renderer: null,
    scene: null,
    camera: null,
    controls: null,
    animId: null,
    autoRotate: true,
    showPolyCage: true,
    cageMeshes: [],
    containerId: 'canvasHolder'
  };

  function clearThreeScene() {
    if (threeState.animId) cancelAnimationFrame(threeState.animId);
    if (threeState.renderer && threeState.renderer.domElement) {
      threeState.renderer.domElement.remove();
    }
    threeState.cageMeshes = [];
  }

  function createSphere(radius, colorHex, pos) {
    const geom = new THREE.SphereGeometry(radius, 28, 28);
    const mat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      roughness: 0.25,
      metalness: 0.15,
      clearcoat: 0.3
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(pos[0], pos[1], pos[2]);
    return mesh;
  }

  function createBond(p1, p2, radius, colorHex) {
    const v1 = new THREE.Vector3(...p1);
    const v2 = new THREE.Vector3(...p2);
    const dir = new THREE.Vector3().subVectors(v2, v1);
    const len = dir.length();
    const geom = new THREE.CylinderGeometry(radius, radius, len, 16);
    const mat = new THREE.MeshStandardMaterial({ color: colorHex, roughness: 0.4, metalness: 0.2 });
    const cyl = new THREE.Mesh(geom, mat);
    const mid = new THREE.Vector3().addVectors(v1, v2).multiplyScalar(0.5);
    cyl.position.copy(mid);
    cyl.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
    return cyl;
  }

  function addTetrahedronCage(group, center, vertices, colorHex) {
    const geom = new THREE.BufferGeometry();
    const v = vertices;
    const indices = [
      0, 1, 2,
      0, 2, 3,
      0, 3, 1,
      1, 3, 2
    ];
    const positions = [];
    v.forEach(pt => positions.push(pt[0], pt[1], pt[2]));
    geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geom.setIndex(indices);
    geom.computeVertexNormals();

    const mat = new THREE.MeshPhysicalMaterial({
      color: colorHex,
      transparent: true,
      opacity: 0.24,
      side: THREE.DoubleSide,
      roughness: 0.2
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.visible = threeState.showPolyCage;
    group.add(mesh);
    threeState.cageMeshes.push(mesh);

    // Wireframe edges
    const edges = [[0,1],[0,2],[0,3],[1,2],[2,3],[3,1]];
    edges.forEach(([i, j]) => {
      const edgeLine = createBond(v[i], v[j], 0.025, 0x94A3B8);
      edgeLine.visible = threeState.showPolyCage;
      group.add(edgeLine);
      threeState.cageMeshes.push(edgeLine);
    });
  }

  function buildMotifGeometry(group, el) {
    const motifId = (el.motif_3d && el.motif_3d.motif_id) || 'corner_sharing_tetrahedra';
    const primaryColor = el.color_hex || '#38BDF8';
    const anionColor = '#10B981';
    const modColor = '#F472B6';

    if (motifId === 'corner_sharing_tetrahedra' || motifId === 'conditional_tetrahedron' || motifId === 'hydrogen_passivated_tetrahedron') {
      // Two corner-sharing MX4 tetrahedra bridged at [0, 0, 0]
      const c1 = [-1.25, 0.0, 0.0];
      const v1 = [
        [0.0, 0.0, 0.0],
        [-1.75, 1.12, 0.0],
        [-1.75, -0.56, 0.97],
        [-1.75, -0.56, -0.97]
      ];
      group.add(createSphere(0.36, primaryColor, c1));
      v1.forEach((pt, idx) => {
        const col = (motifId === 'hydrogen_passivated_tetrahedron' && idx === 1) ? '#F8FAFC' : anionColor;
        const rad = (motifId === 'hydrogen_passivated_tetrahedron' && idx === 1) ? 0.20 : 0.25;
        group.add(createSphere(rad, col, pt));
        group.add(createBond(c1, pt, 0.07, 0xE2E8F0));
      });
      addTetrahedronCage(group, c1, v1, primaryColor);

      // Second corner-sharing tetrahedron
      const c2 = [1.22, 0.22, 0.0];
      const v2 = [
        [0.0, 0.0, 0.0],
        [1.82, 1.24, 0.15],
        [1.68, -0.42, 1.02],
        [1.68, -0.42, -0.98]
      ];
      group.add(createSphere(0.36, primaryColor, c2));
      v2.slice(1).forEach(pt => {
        group.add(createSphere(0.25, anionColor, pt));
        group.add(createBond(c2, pt, 0.07, 0xE2E8F0));
      });
      group.add(createBond(c2, v2[0], 0.07, 0xE2E8F0));
      addTetrahedronCage(group, c2, v2, primaryColor);

      if (motifId === 'conditional_tetrahedron') {
        // Charge-compensating modifier cation near bridging oxygen
        const modPos = [0.0, -1.35, 0.65];
        group.add(createSphere(0.38, modColor, modPos));
        group.add(createBond(modPos, [0.0, 0.0, 0.0], 0.04, 0xF472B6));
      }
    } else if (motifId === 'mixed_trigonal_tetrahedral') {
      // Left: Planar BX3 triangle; Right: Corner-sharing BX4 tetrahedron
      const c1 = [-1.3, 0.0, 0.0];
      const tri = [
        [0.0, 0.0, 0.0],
        [-1.95, 1.1, 0.0],
        [-1.95, -1.1, 0.0]
      ];
      group.add(createSphere(0.34, primaryColor, c1));
      tri.forEach(pt => {
        group.add(createSphere(0.24, anionColor, pt));
        group.add(createBond(c1, pt, 0.07, 0xE2E8F0));
      });
      const c2 = [1.25, 0.0, 0.0];
      const tet = [
        [0.0, 0.0, 0.0],
        [1.75, 1.1, 0.0],
        [1.75, -0.55, 0.95],
        [1.75, -0.55, -0.95]
      ];
      group.add(createSphere(0.36, primaryColor, c2));
      tet.slice(1).forEach(pt => {
        group.add(createSphere(0.24, anionColor, pt));
        group.add(createBond(c2, pt, 0.07, 0xE2E8F0));
      });
      group.add(createBond(c2, tet[0], 0.07, 0xE2E8F0));
      addTetrahedronCage(group, c2, tet, primaryColor);
    } else if (motifId === 'bridging_anion_dimer' || motifId === 'trigonal_bridging_anion') {
      // Central bridging anion X at origin + 2 or 3 tetrahedral cations around it
      const center = [0.0, 0.25, 0.0];
      group.add(createSphere(0.38, primaryColor, center));
      const mPositions = motifId === 'trigonal_bridging_anion'
        ? [[-1.35, -0.45, 0.0], [1.35, -0.45, 0.0], [0.0, 1.65, 0.0]]
        : [[-1.35, -0.35, 0.0], [1.35, -0.35, 0.0]];

      mPositions.forEach((mPos, idx) => {
        group.add(createSphere(0.34, '#38BDF8', mPos));
        group.add(createBond(center, mPos, 0.08, 0xE2E8F0));
        // Outer ligands on each cation
        const sign = idx === 0 ? -1 : 1;
        const extras = [
          [mPos[0] + sign * 0.65, mPos[1] + 0.95, 0.55],
          [mPos[0] + sign * 0.65, mPos[1] - 0.85, 0.65],
          [mPos[0] + sign * 0.65, mPos[1] + 0.05, -0.95]
        ];
        extras.forEach(ep => {
          group.add(createSphere(0.22, primaryColor, ep));
          group.add(createBond(mPos, ep, 0.055, 0x94A3B8));
        });
      });
    } else if (motifId === 'octahedral_polyhedral_intermediate') {
      // Central cation + 6 octahedral ligands
      const c = [0.0, 0.0, 0.0];
      group.add(createSphere(0.42, primaryColor, c));
      const oct = [
        [1.45, 0, 0], [-1.45, 0, 0],
        [0, 1.45, 0], [0, -1.45, 0],
        [0, 0, 1.45], [0, 0, -1.45]
      ];
      oct.forEach(pt => {
        group.add(createSphere(0.25, anionColor, pt));
        group.add(createBond(c, pt, 0.07, 0xE2E8F0));
      });
      const edges = [
        [0,2],[0,3],[0,4],[0,5],[1,2],[1,3],[1,4],[1,5],[2,4],[4,3],[3,5],[5,2]
      ];
      edges.forEach(([i, j]) => {
        const b = createBond(oct[i], oct[j], 0.025, 0xF59E0B);
        b.visible = threeState.showPolyCage;
        group.add(b);
        threeState.cageMeshes.push(b);
      });
    } else if (motifId === 'icosahedral_cluster_cn12') {
      // 13-atom <0,0,12,0> icosahedral short-range order cluster
      const c = [0.0, 0.0, 0.0];
      group.add(createSphere(0.42, primaryColor, c));
      const phi = (1 + Math.sqrt(5)) / 2;
      const rawVerts = [
        [-1,  phi, 0], [ 1,  phi, 0], [-1, -phi, 0], [ 1, -phi, 0],
        [ 0, -1,  phi], [ 0,  1,  phi], [ 0, -1, -phi], [ 0,  1, -phi],
        [ phi, 0, -1], [ phi, 0,  1], [-phi, 0, -1], [-phi, 0,  1]
      ];
      const scale = 0.88;
      const verts = rawVerts.map(v => [v[0]*scale, v[1]*scale, v[2]*scale]);
      verts.forEach((pt, i) => {
        const col = i % 3 === 0 ? '#38BDF8' : '#FB923C';
        group.add(createSphere(0.28, col, pt));
        group.add(createBond(c, pt, 0.055, 0xE2E8F0));
      });
      // Outer icosahedral cage edges
      for (let i = 0; i < verts.length; i++) {
        for (let j = i + 1; j < verts.length; j++) {
          const dx = verts[i][0] - verts[j][0];
          const dy = verts[i][1] - verts[j][1];
          const dz = verts[i][2] - verts[j][2];
          const d = Math.sqrt(dx*dx + dy*dy + dz*dz);
          if (d < 1.85) {
            const edge = createBond(verts[i], verts[j], 0.025, 0xF97316);
            edge.visible = threeState.showPolyCage;
            group.add(edge);
            threeState.cageMeshes.push(edge);
          }
        }
      }
    } else if (motifId === 'modifier_nbo_cage') {
      // Large modifier cation coordinated by non-bridging oxygens attached to depolymerized SiO4 tetrahedra
      const modPos = [0.0, 0.0, 0.0];
      group.add(createSphere(0.46, primaryColor, modPos));
      const nboCoords = [
        [-1.15, 0.65, 0.35],
        [1.15, 0.65, -0.35],
        [0.0, -1.18, 0.55],
        [-0.85, -0.75, -0.85],
        [0.95, -0.55, 0.85],
        [0.0, 1.15, -0.75]
      ];
      nboCoords.forEach((pt, idx) => {
        group.add(createSphere(0.24, anionColor, pt));
        const ionicBond = createBond(modPos, pt, 0.038, 0xF472B6);
        group.add(ionicBond);
        if (idx < 2) {
          const siPos = [pt[0] * 1.65, pt[1] * 1.25, pt[2]];
          group.add(createSphere(0.32, '#38BDF8', siPos));
          group.add(createBond(pt, siPos, 0.07, 0xE2E8F0));
        }
      });
    } else {
      // Crystalline periodic reference cell (2x2x2 cube) for unreported elements
      const pts = [];
      for (let ix = -1; ix <= 1; ix += 2) {
        for (let iy = -1; iy <= 1; iy += 2) {
          for (let iz = -1; iz <= 1; iz += 2) {
            const p = [ix * 0.95, iy * 0.95, iz * 0.95];
            pts.push(p);
            group.add(createSphere(0.28, '#94A3B8', p));
          }
        }
      }
      group.add(createSphere(0.32, '#CBD5E1', [0, 0, 0]));
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const d = Math.hypot(pts[i][0]-pts[j][0], pts[i][1]-pts[j][1], pts[i][2]-pts[j][2]);
          if (Math.abs(d - 1.9) < 0.1) {
            group.add(createBond(pts[i], pts[j], 0.03, 0x64748B));
          }
        }
      }
    }
  }

  function initOrUpdate3DScene(el, holderId) {
    const holder = document.getElementById(holderId);
    if (!holder || typeof THREE === 'undefined') return;
    clearThreeScene();
    threeState.containerId = holderId;

    const w = holder.clientWidth || 580;
    const h = holder.clientHeight || 270;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 100);
    camera.position.set(0, 1.4, 5.2);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    holder.innerHTML = '';
    holder.appendChild(renderer.domElement);

    const ambient = new THREE.AmbientLight(0xFFFFFF, 0.75);
    scene.add(ambient);
    const dirLight1 = new THREE.DirectionalLight(0xFFFFFF, 0.85);
    dirLight1.position.set(5, 8, 6);
    scene.add(dirLight1);
    const dirLight2 = new THREE.DirectionalLight(0x38BDF8, 0.35);
    dirLight2.position.set(-5, -4, -4);
    scene.add(dirLight2);

    const motifGroup = new THREE.Group();
    buildMotifGeometry(motifGroup, el);
    scene.add(motifGroup);

    let controls = null;
    if (THREE.OrbitControls) {
      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.06;
    }

    threeState.renderer = renderer;
    threeState.scene = scene;
    threeState.camera = camera;
    threeState.controls = controls;
    threeState.motifGroup = motifGroup;

    function animate() {
      threeState.animId = requestAnimationFrame(animate);
      if (threeState.autoRotate && threeState.motifGroup) {
        threeState.motifGroup.rotation.y += 0.0065;
      }
      if (threeState.controls) threeState.controls.update();
      renderer.render(scene, camera);
    }
    animate();
  }

  window.toggleAutoRotate = function() {
    threeState.autoRotate = !threeState.autoRotate;
    const btn = document.getElementById('btnAutoRotate');
    if (btn) btn.classList.toggle('active', threeState.autoRotate);
  };

  window.togglePolyCage = function() {
    threeState.showPolyCage = !threeState.showPolyCage;
    const btn = document.getElementById('btnPolyCage');
    if (btn) btn.classList.toggle('active', threeState.showPolyCage);
    threeState.cageMeshes.forEach(m => { m.visible = threeState.showPolyCage; });
  };

  window.resetCamera = function() {
    if (threeState.camera) {
      threeState.camera.position.set(0, 1.4, 5.2);
      if (threeState.controls) threeState.controls.reset();
    }
    if (threeState.motifGroup) {
      threeState.motifGroup.rotation.set(0, 0, 0);
    }
  };

  window.openFullscreen3D = function() {
    const modal = document.getElementById('modal3D');
    modal.classList.add('open');
    const m3d = (currentElement && currentElement.motif_3d) || {};
    const mLabel = m3d.motif_label || m3d.title || '';
    const mCoord = m3d.typical_coordination || m3d.coordination_number || '';
    document.getElementById('modal3DTitle').textContent = `${currentElement.name} (${currentElement.symbol}) — ${mLabel}`;
    document.getElementById('modal3DSub').textContent = mCoord;
    setTimeout(() => initOrUpdate3DScene(currentElement, 'modal3DCanvas'), 40);
  };

  window.closeFullscreen3D = function() {
    const modal = document.getElementById('modal3D');
    modal.classList.remove('open');
    setTimeout(() => initOrUpdate3DScene(currentElement, 'canvasHolder'), 40);
  };

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const guideModal = document.getElementById('modalGuide');
      const modal = document.getElementById('modal3D');
      if (guideModal && guideModal.classList.contains('open')) {
        closeGuideModal();
      } else if (modal && modal.classList.contains('open')) {
        closeFullscreen3D();
      } else {
        closeDrawer();
      }
    }
  });

  // Dynamically synchronize toolbar class & synthesis regime counts with DATA.metadata
  const classSummaryRaw = (DATA.metadata && DATA.metadata.class_summary) || [];
  const classSummary = {};
  if (Array.isArray(classSummaryRaw)) {
    classSummaryRaw.forEach(item => {
      if (item && item.class) classSummary[item.class] = item.cnt ?? item.total_systems;
    });
  } else {
    Object.keys(classSummaryRaw).forEach(k => {
      classSummary[k] = classSummaryRaw[k]?.cnt ?? classSummaryRaw[k]?.total_systems ?? classSummaryRaw[k];
    });
  }
  const classLabels = {
    'Oxide': 'Oxides',
    'Chalcogenide': 'Chalcogenides',
    'Metallic Glass': 'Metallic Glasses',
    'Covalent Network': 'Covalent'
  };
  Object.keys(classLabels).forEach(clsKey => {
    const btn = document.querySelector(`.filter-btn[data-filter="class:${clsKey}"]`);
    if (btn && classSummary[clsKey] !== undefined) {
      btn.textContent = `${classLabels[clsKey]} (${classSummary[clsKey]} sys)`;
    }
  });

  const regimeSummaryRaw = (DATA.metadata && DATA.metadata.synthesis_regime_summary) || [];
  const regimeSummary = {};
  if (Array.isArray(regimeSummaryRaw)) {
    regimeSummaryRaw.forEach(item => {
      if (item && item.synthesis_regime) regimeSummary[item.synthesis_regime] = item.cnt ?? item.total_systems;
    });
  } else {
    Object.keys(regimeSummaryRaw).forEach(k => {
      regimeSummary[k] = regimeSummaryRaw[k]?.cnt ?? regimeSummaryRaw[k]?.total_systems ?? regimeSummaryRaw[k];
    });
  }
  const regimeLabels = {
    'bulk_melt_quenched': 'Bulk Melt-Quenched',
    'rapid_quenched_ribbon': 'Rapid-Quenched Ribbon',
    'vapor_thin_film': 'Vapor / Thin-Film'
  };
  Object.keys(regimeLabels).forEach(regKey => {
    const btn = document.querySelector(`.filter-btn[data-filter="regime:${regKey}"]`);
    if (btn && regimeSummary[regKey] !== undefined) {
      btn.textContent = `${regimeLabels[regKey]} (${regimeSummary[regKey]})`;
    }
  });

  // Initialize on load
  buildGrid();
  applyFilters();
})();
</script>
</body>
</html>
"""


def build_interactive_html(json_path: Path = DEFAULT_JSON, output_html: Path = DEFAULT_HTML) -> None:
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Deduplicate per-system structural_characterization curves into a top-level map
    # keyed by formula so each system's 100-point S(Q)/g(r)/P(theta) curves are stored
    # once in index.html instead of once per constituent element (~60% smaller HTML).
    systems_sro_by_formula = {}
    max_occ = 1
    si_count = 0
    count_full = 0
    count_half = 0
    count_none = 0
    count_tet = 0
    cat_counts: dict[str, int] = {}
    for el in payload.get("elements", []):
        occ = int(el.get("occurrence_count", 0))
        if occ > max_occ:
            max_occ = occ
        if el.get("symbol") == "Si":
            si_count = occ
        fm = el.get("fill_mode")
        if fm == "full":
            count_full += 1
        elif fm == "half":
            count_half += 1
        else:
            count_none += 1
        if el.get("has_tetrahedral_motif"):
            count_tet += 1
        cat_code = el.get("category_code", "")
        if cat_code:
            cat_counts[cat_code] = cat_counts.get(cat_code, 0) + 1
        sro_sum = el.get("structural_characterization_summary")
        if isinstance(sro_sum, dict):
            sro_sum.pop("prototype_characterization", None)
        for s in el.get("verified_systems", []):
            sc = s.pop("structural_characterization", None)
            if sc is not None and s.get("formula") not in systems_sro_by_formula:
                systems_sro_by_formula[s["formula"]] = sc
    payload["systems_sro_by_formula"] = systems_sro_by_formula

    meta = payload.get("metadata", {})
    total_sys = int(meta.get("total_verified_amorphous_systems", len(systems_sro_by_formula)))
    count_active = count_full + count_half

    cls_counts = {}
    for item in meta.get("class_summary", []):
        if isinstance(item, dict) and "class" in item:
            cls_counts[item["class"]] = int(item.get("cnt", 0))

    reg_counts = {}
    for item in meta.get("synthesis_regime_summary", []):
        if isinstance(item, dict) and "synthesis_regime" in item:
            reg_counts[item["synthesis_regime"]] = int(item.get("cnt", 0))

    bench_count = sum(
        1
        for sc in systems_sro_by_formula.values()
        if isinstance(sc, dict)
        and (sc.get("provenance") or {}).get("overall_type") == "direct_experimental_benchmark"
    )

    compact_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    html_content = (
        HTML_TEMPLATE.replace("__TOTAL_SYS__", str(total_sys))
        .replace("__COUNT_FULL__", str(count_full))
        .replace("__COUNT_HALF__", str(count_half))
        .replace("__COUNT_NONE__", str(count_none))
        .replace("__COUNT_ACTIVE__", str(count_active))
        .replace("__COUNT_TET__", str(count_tet))
        .replace("__COUNT_CAT_1A__", str(cat_counts.get("primary_tetrahedral_former", 0)))
        .replace("__COUNT_CAT_1B__", str(cat_counts.get("bridging_anion_former", 0)))
        .replace("__COUNT_CAT_2A__", str(cat_counts.get("conditional_tetrahedral_intermediate", 0)))
        .replace("__COUNT_CAT_2B__", str(cat_counts.get("oxide_chalcogenide_intermediate", 0)))
        .replace("__COUNT_CAT_2C__", str(cat_counts.get("metallic_cluster_intermediate", 0)))
        .replace("__COUNT_OXIDE__", str(cls_counts.get("Oxide", 0)))
        .replace("__COUNT_CHALC__", str(cls_counts.get("Chalcogenide", 0)))
        .replace("__COUNT_MG__", str(cls_counts.get("Metallic Glass", 0)))
        .replace("__COUNT_COV__", str(cls_counts.get("Covalent Network", 0)))
        .replace("__COUNT_BULK__", str(reg_counts.get("bulk_melt_quenched", 0)))
        .replace("__COUNT_RIBBON__", str(reg_counts.get("rapid_quenched_ribbon", 0)))
        .replace("__COUNT_VAPOR__", str(reg_counts.get("vapor_thin_film", 0)))
        .replace("__COUNT_BENCH__", str(bench_count))
        .replace("__MAX_OCC__", str(max_occ))
        .replace("__SI_COUNT__", str(si_count))
        .replace("__AMORPHOUS_DATA_JSON__", compact_json)
    )

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    size_kb = output_html.stat().st_size / 1024.0
    print(f"[Step 6C] Built interactive application: {output_html} ({size_kb:.1f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile self-contained interactive Amorphous Periodic Table HTML.")
    parser.add_argument("-i", "--input", default=str(DEFAULT_JSON), help="Path to 118-element JSON")
    parser.add_argument("-o", "--output", default=str(DEFAULT_HTML), help="Output HTML path")
    args = parser.parse_args()
    build_interactive_html(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
