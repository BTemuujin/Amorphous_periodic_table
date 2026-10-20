#!/usr/bin/env python3
"""
generate_amorphous_table.py

Loads `data/amorphous_periodic_table_118.json` and renders a 300 DPI
publication-grade static periodic table poster (`amorphous_periodic_table.png`),
modeled after `mag_periodic_table/generate_magnetic_table.py`.

Visual Encoding:
- FULL CELL COLOR (49 elements): Elements that make amorphous phase formation possible
  (Primary Tetrahedral Formers, Bridging Anion Formers, Conditional Tetrahedral
  Intermediates, Oxide/Chalcogenide Intermediates, and Metallic Cluster Formers).
- DIAGONAL 50/50 HALF CELL COLOR (28 elements): Elements that are part of reported
  amorphous systems as Network Modifiers / Charge Compensators / Topological Cages.
- UNCOLORED / WHITE (41 elements): Elements with zero verified inorganic amorphous
  systems in `amorphous_materials.db`.
"""

import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as patheffects
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB = SCRIPT_DIR / "data" / "amorphous_periodic_table_118.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "amorphous_periodic_table.png"

CONFIG = {
    "canvas": {
        "fig_width_inches": 28.0,
        "fig_height_inches": 18.0,
        "dpi": 300,
        "bg_color": "#F8FAFC",
        "xlim": (-0.2, 19.8),
        "ylim": (-0.75, 14.75),
        "db_path": str(DEFAULT_DB),
        "output_path": str(DEFAULT_OUTPUT),
    },
    "fonts": {
        "family": "sans-serif",
    },
    "font_sizes": {
        "cell_symbol": 19.5,
        "cell_symbol_small": 17.5,
        "cell_number": 13.5,
        "cell_role": 10.5,
        "cell_metric": 10.5,
        "cell_badge": 13.5,
        "group_numbers": 15.5,
        "period_numbers": 15.5,
        "series_labels": 13.5,
        "placeholder_numbers": 13.5,
        "placeholder_symbols": 11.5,
        "main_title": 40.0,
        "subtitle": 18.0,
        "box_header": 13.0,
        "sample_cell_symbol": 25.0,
        "sample_cell_number": 13.5,
        "sample_cell_role": 11.5,
        "sample_cell_metric": 11.5,
        "sample_cell_badge": 14.0,
        "callout_text": 10.8,
        "legend_item_title": 10.8,
        "legend_item_desc": 9.3,
        "footnote": 12.0,
    },
    "colors": {
        "text_dark": "#0F172A",
        "text_muted": "#475569",
        "text_unreported": "#94A3B8",
        "header_color": "#0F172A",
        "axis_number_color": "#64748B",
        "tet_badge": "#0369A1",
        "tet_badge_halo": "#FFFFFF",
        "metric_color": "#0F172A",
        "radioactive_hatch": "#64748B",
        "callout_arrow": "#0284C7",
        "box_border": "#CBD5E1",
        "box_bg": "#FFFFFF",
    },
    "geometry": {
        "cell_width": 0.90,
        "cell_height": 0.94,
        "cell_border_width": 1.5,
        "hatch_pattern": "///",
        "hatch_alpha": 0.30,
        "row_y": {
            1: 11.20,
            2: 10.12,
            3: 9.04,
            4: 7.96,
            5: 6.88,
            6: 5.80,
            7: 4.72,
            8: 3.25,   # Lanthanides (57-71)
            9: 2.15,   # Actinides (89-103)
        },
        "boxes_bottom_y": 9.30,
        "boxes_height": 3.74,
        "box1_x": 3.04,
        "box1_width": 4.30,
        "box2_x": 7.54,
        "box2_width": 5.26,
    },
}


def draw_element_cell_background(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    fill_mode: str,
    face_col: str,
    border_col: str,
    border_lw: float,
    is_radioactive: bool,
    hatch_col: str,
    hatch_pattern: str,
    hatch_alpha: float,
) -> None:
    """Render full-colored, diagonal 50/50 half-colored, or white cell background."""
    if fill_mode == "full":
        base_patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="square,pad=0",
            facecolor=face_col,
            edgecolor=border_col,
            linewidth=border_lw,
            zorder=2,
        )
        ax.add_patch(base_patch)
    elif fill_mode == "half":
        # White base + upper-left diagonal triangle in category color + outer border
        white_base = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="square,pad=0",
            facecolor="#FFFFFF",
            edgecolor="none",
            linewidth=0.0,
            zorder=2,
        )
        ax.add_patch(white_base)

        upper_left_tri = Polygon(
            [(x, y), (x, y + h), (x + w, y + h)],
            closed=True,
            facecolor=face_col,
            edgecolor="none",
            zorder=2.4,
        )
        ax.add_patch(upper_left_tri)

        # Subtle diagonal divider line from bottom-left to top-right
        ax.plot(
            [x, x + w],
            [y, y + h],
            color=border_col,
            linewidth=0.9,
            linestyle="-",
            alpha=0.65,
            zorder=2.6,
        )

        border_patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="square,pad=0",
            facecolor="none",
            edgecolor=border_col,
            linewidth=border_lw,
            zorder=2.8,
        )
        ax.add_patch(border_patch)
    else:
        uncolored_patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="square,pad=0",
            facecolor="#FFFFFF",
            edgecolor=border_col,
            linewidth=1.1,
            zorder=2,
        )
        ax.add_patch(uncolored_patch)

    if is_radioactive:
        hatch_box = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="square,pad=0",
            facecolor="none",
            edgecolor=hatch_col,
            linewidth=0.0,
            hatch=hatch_pattern,
            alpha=hatch_alpha,
            zorder=3.0,
        )
        ax.add_patch(hatch_box)


def render_periodic_table() -> None:
    canvas_cfg = CONFIG["canvas"]
    fonts_cfg = CONFIG["fonts"]
    fs = CONFIG["font_sizes"]
    col = CONFIG["colors"]
    geom = CONFIG["geometry"]

    with open(canvas_cfg["db_path"], "r", encoding="utf-8") as f:
        payload = json.load(f)

    elements = payload["elements"]
    elem_by_z = {int(e["atomic_number"]): e for e in elements}

    fig = plt.figure(
        figsize=(canvas_cfg["fig_width_inches"], canvas_cfg["fig_height_inches"]),
        dpi=canvas_cfg["dpi"],
    )
    ax = fig.add_subplot(111)
    ax.set_xlim(*canvas_cfg["xlim"])
    ax.set_ylim(*canvas_cfg["ylim"])
    ax.axis("off")

    fig.patch.set_facecolor(canvas_cfg["bg_color"])
    ax.set_facecolor(canvas_cfg["bg_color"])

    cell_w = geom["cell_width"]
    cell_h = geom["cell_height"]
    row_y = geom["row_y"]

    def get_pos(period: int, col_idx: int):
        return float(col_idx), row_y[period]

    def get_f_pos(series_idx: int, col_offset: int):
        return 3.0 + col_offset, row_y[8 if series_idx == 0 else 9]

    # Group Numbers (1-18)
    for g in range(1, 19):
        gx = g + cell_w / 2.0
        gy = (row_y[4] + cell_h + 0.18) if (3 <= g <= 12) else (row_y[1] + cell_h + 0.18)
        ax.text(
            gx,
            gy,
            f"{g}",
            ha="center",
            va="center",
            fontsize=fs["group_numbers"],
            fontweight="bold",
            color=col["axis_number_color"],
            family=fonts_cfg["family"],
        )

    # Period Numbers (1-7)
    for p in range(1, 8):
        px = 0.55
        py = row_y[p] + cell_h / 2.0
        ax.text(
            px,
            py,
            f"{p}",
            ha="center",
            va="center",
            fontsize=fs["period_numbers"],
            fontweight="bold",
            color=col["axis_number_color"],
            family=fonts_cfg["family"],
        )

    badge_stroke = [patheffects.withStroke(linewidth=2.2, foreground=col["tet_badge_halo"])]
    text_halo = [patheffects.withStroke(linewidth=1.8, foreground="#FFFFFF")]

    # Render all 118 Element Cells
    for z in range(1, 119):
        elem = elem_by_z[z]
        sym = elem["symbol"]
        period = elem["period"]
        fill_mode = elem["fill_mode"]
        face_col = elem["color_hex"]
        border_col = elem["border_hex"]
        text_col = elem["text_hex"]
        has_tet = bool(elem["has_tetrahedral_motif"])
        is_rad = bool(elem["radioactive"])
        occ = int(elem["occurrence_count"])
        score = float(elem["amorphous_induction_score"])
        short_role = elem["short_role_label"]

        if 57 <= z <= 71:
            x, y = get_f_pos(0, z - 57)
        elif 89 <= z <= 103:
            x, y = get_f_pos(1, z - 89)
        else:
            x, y = get_pos(period, elem["group"])

        draw_element_cell_background(
            ax=ax,
            x=x,
            y=y,
            w=cell_w,
            h=cell_h,
            fill_mode=fill_mode,
            face_col=face_col,
            border_col=border_col,
            border_lw=geom["cell_border_width"],
            is_radioactive=is_rad,
            hatch_col=col["radioactive_hatch"],
            hatch_pattern=geom["hatch_pattern"],
            hatch_alpha=geom["hatch_alpha"],
        )

        # Atomic Number (top-left)
        num_color = col["text_unreported"] if fill_mode == "none" else col["text_dark"]
        ax.text(
            x + 0.07,
            y + cell_h - 0.14,
            str(z),
            ha="left",
            va="center",
            fontsize=fs["cell_number"],
            fontweight="bold",
            color=num_color,
            family=fonts_cfg["family"],
            zorder=4,
        )

        # Tetrahedral Network Motif Diamond Badge (top-right)
        if has_tet:
            ax.text(
                x + cell_w - 0.07,
                y + cell_h - 0.14,
                "◆",
                ha="right",
                va="center",
                fontsize=fs["cell_badge"],
                fontweight="bold",
                color=col["tet_badge"],
                path_effects=badge_stroke,
                family=fonts_cfg["family"],
                zorder=5,
            )

        # Chemical Symbol (center)
        sym_y = y + cell_h * 0.57 if occ > 0 else y + cell_h * 0.52
        sym_size = fs["cell_symbol"] if len(sym) <= 2 else fs["cell_symbol_small"]
        sym_color = "#64748B" if fill_mode == "none" else text_col
        ax.text(
            x + cell_w / 2.0,
            sym_y,
            sym,
            ha="center",
            va="center",
            fontsize=sym_size,
            fontweight="heavy",
            color=sym_color,
            path_effects=text_halo if fill_mode == "half" else None,
            family=fonts_cfg["family"],
            zorder=4,
        )

        if occ > 0:
            # Role subtitle line
            ax.text(
                x + cell_w / 2.0,
                y + cell_h * 0.33,
                short_role,
                ha="center",
                va="center",
                fontsize=fs["cell_role"],
                fontweight="semibold",
                color=col["text_muted"],
                path_effects=text_halo if fill_mode == "half" else None,
                family=fonts_cfg["family"],
                zorder=4,
            )
            # Bottom quantitative metric: Primary Coordination Motif + Raw System Count
            short_cn = elem.get("short_cn_label", "CN=4")
            metric_str = f"{short_cn} · N={occ}"
            ax.text(
                x + cell_w / 2.0,
                y + 0.12,
                metric_str,
                ha="center",
                va="center",
                fontsize=fs["cell_metric"],
                fontweight="bold",
                color=col["metric_color"],
                family=fonts_cfg["family"],
                zorder=4,
            )
        else:
            ax.text(
                x + cell_w / 2.0,
                y + cell_h * 0.25,
                str(elem["atomic_mass"]),
                ha="center",
                va="center",
                fontsize=fs["cell_role"],
                color=col["text_unreported"],
                family=fonts_cfg["family"],
                zorder=4,
            )

    # Placeholders for Lanthanides & Actinides in Main Table
    lx, ly = get_pos(6, 3)
    l_ph = FancyBboxPatch(
        (lx, ly),
        cell_w,
        cell_h,
        boxstyle="square,pad=0",
        facecolor="#F1F5F9",
        edgecolor="#94A3B8",
        linewidth=1.2,
        linestyle="--",
        zorder=2,
    )
    ax.add_patch(l_ph)
    ax.text(
        lx + cell_w / 2.0,
        ly + cell_h * 0.62,
        "57–71",
        ha="center",
        va="center",
        fontsize=fs["placeholder_numbers"],
        fontweight="bold",
        color=col["text_dark"],
        family=fonts_cfg["family"],
        zorder=4,
    )
    ax.text(
        lx + cell_w / 2.0,
        ly + cell_h * 0.35,
        "La–Lu",
        ha="center",
        va="center",
        fontsize=fs["placeholder_symbols"],
        fontweight="semibold",
        color=col["axis_number_color"],
        family=fonts_cfg["family"],
        zorder=4,
    )

    ax_p, ay_p = get_pos(7, 3)
    a_ph = FancyBboxPatch(
        (ax_p, ay_p),
        cell_w,
        cell_h,
        boxstyle="square,pad=0",
        facecolor="#F1F5F9",
        edgecolor="#94A3B8",
        linewidth=1.2,
        linestyle="--",
        zorder=2,
    )
    ax.add_patch(a_ph)
    ax.text(
        ax_p + cell_w / 2.0,
        ay_p + cell_h * 0.62,
        "89–103",
        ha="center",
        va="center",
        fontsize=fs["placeholder_numbers"],
        fontweight="bold",
        color=col["text_dark"],
        family=fonts_cfg["family"],
        zorder=4,
    )
    ax.text(
        ax_p + cell_w / 2.0,
        ay_p + cell_h * 0.35,
        "Ac–Lr",
        ha="center",
        va="center",
        fontsize=fs["placeholder_symbols"],
        fontweight="semibold",
        color=col["axis_number_color"],
        family=fonts_cfg["family"],
        zorder=4,
    )

    # Labels for pulled-out f-block rows
    lx_lbl, ly_lbl = get_f_pos(0, 0)
    ax.text(
        lx_lbl - 0.25,
        ly_lbl + cell_h / 2.0,
        "* Lanthanides\n   (57–71)",
        ha="right",
        va="center",
        fontsize=fs["series_labels"],
        fontweight="bold",
        color=col["text_dark"],
        family=fonts_cfg["family"],
    )

    ax_lbl, ay_lbl = get_f_pos(1, 0)
    ax.text(
        ax_lbl - 0.25,
        ay_lbl + cell_h / 2.0,
        "** Actinides\n   (89–103)",
        ha="right",
        va="center",
        fontsize=fs["series_labels"],
        fontweight="bold",
        color=col["text_dark"],
        family=fonts_cfg["family"],
    )

    ax.annotate(
        "",
        xy=(lx_lbl - 0.05, ly_lbl + cell_h * 0.6),
        xytext=(lx + cell_w * 0.25, ly),
        arrowprops=dict(arrowstyle="->", color="#94A3B8", lw=1.2, linestyle=":"),
    )
    ax.annotate(
        "",
        xy=(ax_lbl - 0.05, ay_lbl + cell_h * 0.6),
        xytext=(ax_p + cell_w * 0.25, ay_p),
        arrowprops=dict(arrowstyle="->", color="#94A3B8", lw=1.2, linestyle=":"),
    )

    # -------------------------------------------------------------------------
    # HEADER: TITLE & SUBTITLE
    # -------------------------------------------------------------------------
    title_x = 3.0
    title_y = 14.22
    ax.text(
        title_x,
        title_y,
        "AMORPHOUS PERIODIC TABLE",
        ha="left",
        va="top",
        fontsize=fs["main_title"],
        fontweight="heavy",
        color=col["header_color"],
        family=fonts_cfg["family"],
    )
    total_sys = payload.get("metadata", {}).get("total_verified_amorphous_systems", 241)
    ax.text(
        title_x,
        title_y - 0.54,
        f"Full-Color Amorphous Phase Formers & Intermediates (49) • Half-Color Network Modifiers (28) • {total_sys} Verified Systems",
        ha="left",
        va="top",
        fontsize=fs["subtitle"],
        fontweight="semibold",
        color=col["text_muted"],
        family=fonts_cfg["family"],
    )

    # -------------------------------------------------------------------------
    # BOX 1: "HOW TO READ EACH ELEMENT CELL"
    # -------------------------------------------------------------------------
    b1_x = geom["box1_x"]
    b1_y = geom["boxes_bottom_y"]
    b1_w = geom["box1_width"]
    b1_h = geom["boxes_height"]

    box1 = FancyBboxPatch(
        (b1_x, b1_y),
        b1_w,
        b1_h,
        boxstyle="round,pad=0.08,rounding_size=0.14",
        facecolor=col["box_bg"],
        edgecolor=col["box_border"],
        linewidth=1.5,
        zorder=2,
    )
    ax.add_patch(box1)

    ax.text(
        b1_x + 0.16,
        b1_y + b1_h - 0.28,
        "BOX 1: HOW TO READ EACH ELEMENT CELL",
        fontsize=fs["box_header"],
        fontweight="heavy",
        color=col["header_color"],
        family=fonts_cfg["family"],
        zorder=4,
    )

    # Magnified Sample Cell (Silicon, Si)
    sc_w = 1.44
    sc_h = 1.72
    sc_x = b1_x + 0.18
    sc_y = b1_y + 1.44

    sc_rect = FancyBboxPatch(
        (sc_x, sc_y),
        sc_w,
        sc_h,
        boxstyle="square,pad=0",
        facecolor="#7EC8E3",
        edgecolor="#0284C7",
        linewidth=2.0,
        zorder=3,
    )
    ax.add_patch(sc_rect)

    ax.text(
        sc_x + 0.11,
        sc_y + sc_h - 0.22,
        "14",
        fontsize=fs["sample_cell_number"],
        fontweight="bold",
        color=col["text_dark"],
        family=fonts_cfg["family"],
        zorder=4,
    )
    ax.text(
        sc_x + sc_w - 0.11,
        sc_y + sc_h - 0.22,
        "◆",
        fontsize=fs["sample_cell_badge"],
        fontweight="bold",
        color=col["tet_badge"],
        path_effects=badge_stroke,
        ha="right",
        family=fonts_cfg["family"],
        zorder=5,
    )
    ax.text(
        sc_x + sc_w / 2.0,
        sc_y + sc_h * 0.57,
        "Si",
        fontsize=fs["sample_cell_symbol"],
        fontweight="heavy",
        color=col["text_dark"],
        ha="center",
        va="center",
        family=fonts_cfg["family"],
        zorder=4,
    )
    ax.text(
        sc_x + sc_w / 2.0,
        sc_y + sc_h * 0.34,
        "Tet Former",
        fontsize=fs["sample_cell_role"],
        fontweight="semibold",
        color=col["text_muted"],
        ha="center",
        va="center",
        family=fonts_cfg["family"],
        zorder=4,
    )
    si_el = elem_by_z.get(14, {})
    si_occ = int(si_el.get("occurrence_count", 65))
    ax.text(
        sc_x + sc_w / 2.0,
        sc_y + 0.16,
        f"CN=4 · N={si_occ}",
        fontsize=fs["sample_cell_metric"],
        fontweight="bold",
        color=col["text_dark"],
        ha="center",
        va="center",
        family=fonts_cfg["family"],
        zorder=4,
    )

    callouts = [
        ("Atomic Number (Z=14)", (sc_x + 0.16, sc_y + sc_h - 0.14), (b1_x + 1.84, sc_y + sc_h - 0.12)),
        ("◆ Tetrahedral Motif (CN=4)", (sc_x + sc_w - 0.08, sc_y + sc_h - 0.18), (b1_x + 1.84, sc_y + sc_h - 0.52)),
        ("Element Symbol (Si)", (sc_x + sc_w - 0.16, sc_y + sc_h * 0.57), (b1_x + 1.84, sc_y + sc_h - 0.92)),
        ("Structural Glass Role", (sc_x + sc_w - 0.14, sc_y + sc_h * 0.34), (b1_x + 1.84, sc_y + sc_h - 1.32)),
        ("Coordination & System Count (N)", (sc_x + sc_w - 0.14, sc_y + 0.16), (b1_x + 1.84, sc_y + sc_h - 1.66)),
    ]
    for label, target, text_pos in callouts:
        ax.annotate(
            label,
            xy=target,
            xytext=text_pos,
            textcoords="data",
            fontsize=fs["callout_text"],
            fontweight="semibold",
            color=col["text_dark"],
            family=fonts_cfg["family"],
            arrowprops=dict(arrowstyle="->", color=col["callout_arrow"], lw=1.2, shrinkA=2, shrinkB=4),
            va="center",
            zorder=5,
        )

    # Fill-Mode Key at bottom of Box 1 (Full vs Half vs Uncolored)
    fm_y1 = b1_y + 0.84
    fm_y2 = b1_y + 0.45
    fm_y3 = b1_y + 0.08
    sw_w = 0.38
    sw_h = 0.25

    # Full fill mini swatch
    draw_element_cell_background(
        ax, b1_x + 0.18, fm_y1, sw_w, sw_h, "full", "#7EC8E3", "#0284C7", 1.3, False, "", "", 0.0
    )
    ax.text(
        b1_x + 0.66,
        fm_y1 + sw_h / 2.0,
        "FULL COLOR (49 el): Makes amorphous phase possible",
        fontsize=9.6,
        fontweight="bold",
        color=col["text_dark"],
        va="center",
        family=fonts_cfg["family"],
        zorder=4,
    )

    # Half fill mini swatch (diagonal 50/50 split)
    draw_element_cell_background(
        ax, b1_x + 0.18, fm_y2, sw_w, sw_h, "half", "#F9A8D4", "#DB2777", 1.3, False, "", "", 0.0
    )
    ax.text(
        b1_x + 0.66,
        fm_y2 + sw_h / 2.0,
        "HALF COLOR (28 el): Part of reported amorphous systems",
        fontsize=9.6,
        fontweight="bold",
        color=col["text_dark"],
        va="center",
        family=fonts_cfg["family"],
        zorder=4,
    )

    # White mini swatch
    draw_element_cell_background(
        ax, b1_x + 0.18, fm_y3, sw_w, sw_h, "none", "#FFFFFF", "#CBD5E1", 1.1, False, "", "", 0.0
    )
    ax.text(
        b1_x + 0.66,
        fm_y3 + sw_h / 2.0,
        "WHITE (41 el): Unreported  |  /// = Radioactive",
        fontsize=9.5,
        fontweight="semibold",
        color=col["text_muted"],
        va="center",
        family=fonts_cfg["family"],
        zorder=4,
    )

    # -------------------------------------------------------------------------
    # BOX 2: "LEGEND & AMORPHOUS STRUCTURAL CLASSIFICATION"
    # -------------------------------------------------------------------------
    b2_x = geom["box2_x"]
    b2_y = geom["boxes_bottom_y"]
    b2_w = geom["box2_width"]
    b2_h = geom["boxes_height"]

    box2 = FancyBboxPatch(
        (b2_x, b2_y),
        b2_w,
        b2_h,
        boxstyle="round,pad=0.08,rounding_size=0.14",
        facecolor=col["box_bg"],
        edgecolor=col["box_border"],
        linewidth=1.5,
        zorder=2,
    )
    ax.add_patch(box2)

    ax.text(
        b2_x + 0.16,
        b2_y + b2_h - 0.28,
        "BOX 2: LEGEND & AMORPHOUS STRUCTURAL ROLES",
        fontsize=fs["box_header"],
        fontweight="heavy",
        color=col["header_color"],
        family=fonts_cfg["family"],
        zorder=4,
    )

    legend_rows = [
        (
            "full",
            "#7EC8E3",
            "#0284C7",
            "1a. Primary Tetrahedral Formers (Full, 5 el)",
            "Si, Ge, P, B, As — Continuous random network (CRN) backbones",
        ),
        (
            "full",
            "#A7F3D0",
            "#059669",
            "1b. Bridging Anion Formers (Full, 7 el)",
            "O, S, Se, N, F, Cl, Br — Flexible CN=2–3 bridging ligands",
        ),
        (
            "full",
            "#C4B5FD",
            "#7C3AED",
            "2a. Conditional Tetrahedral Intermediates (Full, 12 el)",
            "Al, Ga, Zn, Be, C, V, Mo, W, Ti, Sn, In, Cd — Compensated MX4",
        ),
        (
            "full",
            "#FDE68A",
            "#D97706",
            "2b. Oxide / Chalcogenide / BMG Intermediates (Full, 13 el)",
            "Te, Sb, Bi, Pb, Fe, Zr, Hf, Nb, Ta, Sc, Tl, Os, Th — Polyhedral / early-TM",
        ),
        (
            "full",
            "#FDBA74",
            "#EA580C",
            "2c. Metallic Cluster / BMG Intermediates (Full, 12 el)",
            "Cu, Ni, Co, Pd, Pt, Au, Cr, Mn, Ru, Rh, Re, Ir — <0,0,12,0> BMG",
        ),
        (
            "half",
            "#F9A8D4",
            "#DB2777",
            "3. Network Modifiers & Cages (Half-Split, 28 el)",
            "Li–Cs, Mg–Ba, Ag, Y, La–Lu, U, I, H — Depolymerize NBOs / cages",
        ),
    ]

    l_sw_w = 0.40
    l_sw_h = 0.28
    l_sw_x = b2_x + 0.16

    for idx, (fmode, fcol, bcol, title_str, desc_str) in enumerate(legend_rows):
        iy = b2_y + b2_h - 0.76 - idx * 0.52
        draw_element_cell_background(
            ax, l_sw_x, iy, l_sw_w, l_sw_h, fmode, fcol, bcol, 1.3, False, "", "", 0.0
        )
        ax.text(
            l_sw_x + l_sw_w + 0.12,
            iy + l_sw_h * 0.73,
            title_str,
            fontsize=fs["legend_item_title"],
            fontweight="bold",
            color=col["text_dark"],
            va="center",
            family=fonts_cfg["family"],
            zorder=4,
        )
        ax.text(
            l_sw_x + l_sw_w + 0.12,
            iy + l_sw_h * 0.12,
            desc_str,
            fontsize=fs["legend_item_desc"],
            fontweight="normal",
            color=col["text_muted"],
            va="center",
            family=fonts_cfg["family"],
            zorder=4,
        )

    # Bottom indicator bar in Box 2
    ind_y = b2_y + 0.16
    ax.text(
        b2_x + 0.24,
        ind_y,
        "◆",
        fontsize=13.0,
        fontweight="bold",
        color=col["tet_badge"],
        path_effects=badge_stroke,
        ha="center",
        va="center",
        family=fonts_cfg["family"],
        zorder=5,
    )
    ax.text(
        b2_x + 0.42,
        ind_y,
        "= Verified 4-Coordinate Tetrahedral Motif (17 el: Si, Ge, P, B, As, Al..Cd)",
        fontsize=9.4,
        fontweight="bold",
        color=col["text_dark"],
        va="center",
        family=fonts_cfg["family"],
        zorder=4,
    )

    # -------------------------------------------------------------------------
    # FOOTNOTE ATTRIBUTION
    # -------------------------------------------------------------------------
    foot_x = 0.55
    foot_y = -0.10
    footnote_text = (
        f"Scientific Methodology & Verification Criteria (amorphous_materials.db — {total_sys} Experimental Systems, 77 Elements, 100% Crossref-Verified DOIs):\n"
        "• Strictly filtered for peer-reviewed inorganic amorphous systems verified by diffuse X-ray/neutron scattering halos (FSDP), TEM selected area electron diffraction (SAED), and/or DSC glass transition (Tg/Tx).\n"
        "• Full Cell Coloring (49 elements): Network Formers & Intermediates that construct the amorphous continuous random network (Zachariasen–Phillips–Thorpe CRN) or icosahedral/polytetrahedral metallic glass backbone (Inoue Rules).\n"
        "• Diagonal 50/50 Half Cell Coloring (28 elements): Network Modifiers, Charge Compensators, and Topological Cages that participate exclusively within multicomponent amorphous systems."
    )
    ax.text(
        foot_x,
        foot_y,
        footnote_text,
        ha="left",
        va="top",
        fontsize=fs["footnote"],
        fontweight="normal",
        color=col["text_muted"],
        family=fonts_cfg["family"],
        linespacing=1.38,
    )

    plt.tight_layout()
    plt.savefig(
        canvas_cfg["output_path"],
        dpi=canvas_cfg["dpi"],
        facecolor=fig.get_facecolor(),
        edgecolor="none",
        bbox_inches="tight",
    )
    plt.close()
    print(f"[Step 6B] Generated 300 DPI static poster: {canvas_cfg['output_path']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render 300 DPI static Amorphous Periodic Table poster PNG."
    )
    parser.add_argument("-i", "--input", "--db", dest="db", default=None, help="Input 118-element JSON path")
    parser.add_argument("-o", "--output", default=None, help="Output PNG path")
    parser.add_argument("--dpi", type=int, default=None, help="Rendering DPI (default: 300)")
    args = parser.parse_args()

    if args.db:
        CONFIG["canvas"]["db_path"] = os.path.abspath(args.db)
    if args.output:
        CONFIG["canvas"]["output_path"] = os.path.abspath(args.output)
    if args.dpi:
        CONFIG["canvas"]["dpi"] = args.dpi

    render_periodic_table()


if __name__ == "__main__":
    main()
