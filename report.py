"""
report.py

This file builds the outputs for a portfolio or steering meeting:
- the value vs feasibility matrix as a PNG
- an Excel workbook with the ranked portfolio, obligations and method
- a one-page PDF for the steering committee
"""
import textwrap
from collections import Counter
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Font, PatternFill

from portfolio import COMPLIANCE_OVERHEAD, DPIA_OVERHEAD, FRIA_OVERHEAD, QUADRANT_SPLIT
from scoring import CATEGORY_WEIGHTS

# Risk tiers use status colours (critical to good) plus a marker shape,
# so the tier never depends on colour alone
TIER_STYLE = {
    "Prohibited": {"color": "#d03b3b", "marker": "X", "fill": "F6D4D4"},
    "High-risk": {"color": "#ec835a", "marker": "^", "fill": "FBE2D7"},
    "Limited": {"color": "#fab219", "marker": "D", "fill": "FEEFC6"},
    "Minimal": {"color": "#0ca30c", "marker": "o", "fill": "D3EDD3"},
    "Out of scope": {"color": "#8a8985", "marker": "s", "fill": "E8E8E6"},
    "Not assessed": {"color": "#8a8985", "marker": "P", "fill": "E8E8E6"},
}
GATE_FILL = {"Go": "D3EDD3", "Go with conditions": "FEEFC6", "Stop": "F6D4D4", "Assess first": "E8E8E6"}

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#d9d8d4"

# Corner of the matrix where each quadrant label sits
QUADRANT_LABELS = {
    "Quick win": ("right", "top"),
    "Strategic bet": ("left", "top"),
    "Fill-in": ("right", "bottom"),
    "Deprioritise": ("left", "bottom"),
}

DISCLAIMER = ("Screening aid based on Regulation (EU) 2024/1689 (AI Act) and GDPR Art. 35. "
              "Not legal advice: confirm classifications with legal and data protection.")


def draw_matrix(rows, ax):
    """Draw the value vs feasibility matrix on a matplotlib axis."""
    ax.set_facecolor(SURFACE)
    ax.set_xlim(0.8, 5.2)
    ax.set_ylim(0.8, 5.2)
    ax.axvline(QUADRANT_SPLIT, color=GRID, lw=1, zorder=1)
    ax.axhline(QUADRANT_SPLIT, color=GRID, lw=1, zorder=1)

    for label, (ha, va) in QUADRANT_LABELS.items():
        x = 5.15 if ha == "right" else 0.85
        y = 5.15 if va == "top" else 0.85
        ax.text(x, y, label, ha=ha, va=va, fontsize=8, color=INK_SECONDARY, style="italic")

    placed = []   # label positions already used, to avoid overlapping labels
    for row in rows:
        style = TIER_STYLE[row["ai_act_tier"]]
        x_raw, x, y = row["feasibility"], row["adjusted_feasibility"], row["value"]
        # Compliance work moves a use case to the left: show where it started.
        # Not shown for stopped use cases, which will not be built at all.
        if row["compliance_overhead"] > 0 and row["gate"] != "Stop":
            ax.scatter(x_raw, y, s=60, marker=style["marker"], facecolors="none",
                       edgecolors=style["color"], linewidths=1, zorder=2)
            if x_raw - x >= 0.2:
                ax.annotate("", xy=(x, y), xytext=(x_raw, y), zorder=2,
                            arrowprops={"arrowstyle": "->", "color": INK_SECONDARY, "lw": 1,
                                        "shrinkA": 5, "shrinkB": 6})
        ax.scatter(x, y, s=90, marker=style["marker"], color=style["color"],
                   edgecolors=SURFACE, linewidths=2, zorder=3)

        # Use cases on the same spot share one label; close neighbours get
        # their label below the marker instead of above
        same = [p for p in placed if abs(p["x"] - x) < 0.01 and abs(p["y"] - y) < 0.01]
        if same:
            same[0]["text"].set_text(same[0]["text"].get_text() + " / " + row["use_case_id"])
            continue
        crowded = any(abs(p["x"] - x) < 0.35 and abs(p["y"] - y) < 0.15 and p["above"] for p in placed)
        text = ax.annotate(row["use_case_id"], (x, y), xytext=(0, -14 if crowded else 8),
                           textcoords="offset points", ha="center", fontsize=7.5, color=INK, zorder=4)
        placed.append({"x": x, "y": y, "text": text, "above": not crowded})

    ax.set_xlabel("Feasibility after compliance overhead (data, technology, cost)", fontsize=8.5, color=INK)
    ax.set_ylabel("Business value", fontsize=8.5, color=INK)
    ax.tick_params(labelsize=8, colors=INK_SECONDARY)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)

    tiers_present = [t for t in TIER_STYLE if any(r["ai_act_tier"] == t for r in rows)]
    handles = [plt.Line2D([], [], ls="", marker=TIER_STYLE[t]["marker"], color=TIER_STYLE[t]["color"],
                          markersize=7, label=t) for t in tiers_present]
    handles.append(plt.Line2D([], [], ls="", marker="o", markerfacecolor="none",
                              markeredgecolor=INK_SECONDARY, markersize=7, label="Before compliance overhead"))
    ax.legend(handles=handles, title="EU AI Act tier", fontsize=7.5, title_fontsize=8,
              loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)


def save_matrix(rows, path):
    """Save the matrix as a PNG and return the path."""
    fig, ax = plt.subplots(figsize=(7, 6.2), facecolor=SURFACE)
    draw_matrix(rows, ax)
    ax.set_title("AI use case portfolio: value vs feasibility", fontsize=11, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def _write_table(sheet, headers, rows, widths):
    """Write a header row and data rows with simple formatting."""
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for values in rows:
        sheet.append(values)
    for column, width in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", widths):
        sheet.column_dimensions[column].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"


def write_excel(rows, path, matrix_png):
    """Write the portfolio workbook and return the path."""
    wb = Workbook()

    portfolio = wb.active
    portfolio.title = "Portfolio"
    headers = ["Rank", "ID", "Use case", "Business area", "Value", "Feasibility", "Compliance overhead",
               "Adjusted feasibility", "Original score", "Adjusted score", "Priority", "Quadrant",
               "AI Act tier", "AI Act basis", "Role", "DPIA", "FRIA", "Gate", "Conditions"]
    table = [[i, r["use_case_id"], r["name"], r["business_area"], r["value"], r["feasibility"],
              r["compliance_overhead"], r["adjusted_feasibility"], r["final_score"], r["adjusted_score"],
              r["priority"], r["quadrant"], r["ai_act_tier"], r["ai_act_basis"], r["role"], r["dpia"],
              "Yes" if r["fria"] else "No", r["gate"], "; ".join(r["conditions"])]
             for i, r in enumerate(rows, start=1)]
    _write_table(portfolio, headers, table,
                 [6, 7, 30, 16, 8, 11, 12, 12, 10, 10, 11, 13, 13, 38, 10, 20, 7, 18, 45])
    for row_cells, r in zip(portfolio.iter_rows(min_row=2), rows):
        row_cells[12].fill = PatternFill("solid", fgColor=TIER_STYLE[r["ai_act_tier"]]["fill"])
        row_cells[17].fill = PatternFill("solid", fgColor=GATE_FILL[r["gate"]])

    matrix = wb.create_sheet("Matrix")
    image = Image(matrix_png)
    image.width, image.height = 700, 620
    matrix.add_image(image, "A1")

    duties = wb.create_sheet("Obligations")
    duty_rows = []
    for r in rows:
        for item in r["obligations"]:
            duty_rows.append([r["use_case_id"], r["name"], r["ai_act_tier"], "EU AI Act", item, "Open", ""])
        if r["dpia"] not in ("Required", "Screening recommended"):
            continue
        for reason in r["dpia_reasons"]:
            duty_rows.append([r["use_case_id"], r["name"], r["ai_act_tier"], f"GDPR DPIA: {r['dpia']}", reason, "Open", ""])
    _write_table(duties, ["ID", "Use case", "AI Act tier", "Source", "Obligation or reason", "Status", "Owner"],
                 duty_rows, [7, 30, 13, 26, 75, 10, 16])

    method = wb.create_sheet("Method")
    method_rows = [["Category weight: " + c, w] for c, w in CATEGORY_WEIGHTS.items()]
    method_rows += [[f"Compliance overhead: {tier} {role}", points] for (tier, role), points in COMPLIANCE_OVERHEAD.items()]
    method_rows += [["Compliance overhead: DPIA required", DPIA_OVERHEAD],
                    ["Compliance overhead: FRIA required", FRIA_OVERHEAD],
                    ["Quadrant split (value and feasibility)", QUADRANT_SPLIT],
                    ["Scale", "1 to 5; for cost and time, 5 means cheap or fast"],
                    ["Note", DISCLAIMER]]
    _write_table(method, ["Setting", "Value"], method_rows, [45, 70])

    wb.save(path)
    return path


def write_pdf(rows, path, today=None):
    """Write a one-page A4 landscape steering committee summary and return the path."""
    today = today or date.today()
    fig = plt.figure(figsize=(11.69, 8.27), facecolor=SURFACE)
    fig.text(0.04, 0.95, "AI Use Case Portfolio Review", fontsize=17, weight="bold", color=INK)
    gates = Counter(r["gate"] for r in rows)
    fig.text(0.04, 0.915, f"{today:%d %B %Y}  |  {len(rows)} use cases  |  "
             f"Go: {gates['Go']}   Go with conditions: {gates['Go with conditions']}   "
             f"Stop: {gates['Stop']}   Assess first: {gates['Assess first']}",
             fontsize=9.5, color=INK_SECONDARY)

    ax = fig.add_axes([0.07, 0.3, 0.36, 0.57])
    draw_matrix(rows, ax)

    # Ranked table on the right
    table_ax = fig.add_axes([0.47, 0.51, 0.5, 0.37])
    table_ax.axis("off")
    columns = ["#", "Use case", "Score", "AI Act tier", "DPIA", "Gate"]
    cells = [[str(i), f"{r['use_case_id']} {r['name']}", f"{r['adjusted_score']:.2f}",
              r["ai_act_tier"], r["dpia"].replace("Screening recommended", "Screening"), r["gate"]]
             for i, r in enumerate(rows, start=1)]
    table = table_ax.table(cellText=cells, colLabels=columns, cellLoc="left", bbox=[0, 0, 1, 1],
                           colWidths=[0.04, 0.42, 0.07, 0.13, 0.15, 0.19])
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    for (row_index, col_index), cell in table.get_celld().items():
        cell.set_edgecolor(GRID)
        if row_index == 0:
            cell.set_facecolor("#1F3864")
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
            continue
        r = rows[row_index - 1]
        if col_index == 3:
            cell.set_facecolor("#" + TIER_STYLE[r["ai_act_tier"]]["fill"])
        elif col_index == 5:
            cell.set_facecolor("#" + GATE_FILL[r["gate"]])
        else:
            cell.set_facecolor(SURFACE)

    # Actions the committee has to decide on, below the table
    fig.text(0.47, 0.465, "Compliance actions before go-live", fontsize=10.5, weight="bold", color=INK)
    y = 0.435
    for r in [r for r in rows if r["conditions"]]:
        if y < 0.13:
            fig.text(0.47, y, "More in the Excel workbook (Obligations sheet).", fontsize=7.8, color=INK_SECONDARY)
            break
        detail = "; ".join(r["conditions"])
        if r["ai_act_tier"] == "High-risk":
            detail += f" ({len(r['obligations'])} AI Act obligations)"
        line = textwrap.fill(f"{r['use_case_id']} {r['name']}: {detail}", 100, subsequent_indent="    ")
        fig.text(0.47, y, line, fontsize=7.8, color=INK, va="top", linespacing=1.4)
        y -= 0.022 * (line.count("\n") + 1) + 0.008

    tiers = Counter(r["ai_act_tier"] for r in rows)
    dpias = sum(r["dpia"] == "Required" for r in rows)
    notes = [f"{tiers['High-risk']} high-risk and {tiers['Prohibited']} prohibited use case(s) under the EU AI Act; "
             f"{dpias} need a DPIA before processing personal data.",
             "Score = 35% business value + 65% feasibility after compliance overhead. Arrows show how much "
             "compliance work moves a use case.",
             DISCLAIMER]
    for i, note in enumerate(notes):
        fig.text(0.04, 0.075 - i * 0.022, note, fontsize=7.8, color=INK_SECONDARY if i else INK)

    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path
