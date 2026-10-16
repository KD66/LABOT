"""Draw the assumed LABOT deck floor plan + two reference layouts (SVG + PNG).

All geometry is an ASSUMPTION built from the customer's description - edit the
constants below once the real dimensions are confirmed.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

SBS_W, SBS_D = 127.76, 85.48          # SBS footprint (mm)
PITCH_X, PITCH_Y = 135.0, 95.0        # assumed slot pitch
NARROW_D = 22.0                       # assumed depth of narrow slot (max 2 rows @ 9 mm)
GAP = 8.0
FRONT_EXTRA = 12.0                    # "predsazena rada": front narrow row protrudes forward

SLOTS = {}
for i in range(6):
    c, r = i % 3, i // 3              # M1-M3 front row (r=0), M4-M6 back row (r=1)
    SLOTS[f"M{i + 1}"] = (c * PITCH_X, r * PITCH_Y, SBS_W, SBS_D, "main")
for c in range(3):
    SLOTS[f"F{c + 1}"] = (c * PITCH_X, -GAP - FRONT_EXTRA - NARROW_D, SBS_W, NARROW_D, "narrow")
    SLOTS[f"B{c + 1}"] = (c * PITCH_X, PITCH_Y + SBS_D + GAP, SBS_W, NARROW_D, "narrow")

COL = dict(tips="#cfd4da", samples="#9ec5fe", plate="#a3cfbb", reagent="#ffd29c", spare="#ffffff",
           waste="#e5b8b8")


def box(ax, x, y, w, h, fc, ec="#333", lw=1.0, ls="-", r=3.0, z=1, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, alpha=alpha))


def deck(ax, title, layout=None, notes=None):
    ax.set_title(title, fontsize=11, loc="left", fontweight="bold")
    box(ax, -12, -GAP - FRONT_EXTRA - NARROW_D - 10, 3 * PITCH_X + 10, 2 * PITCH_Y + 2 * NARROW_D + 2 * GAP + FRONT_EXTRA + 30,
        "#f4f5f7", ec="#888", r=6, z=0)
    layout = layout or {}
    drawn = set()
    for sid, (x, y, w, h, kind) in SLOTS.items():
        item = layout.get(sid)
        if item and len(item) == 3 and item[2] == "span":     # second half of a two-slot item is drawn with the first
            continue
        fc, label = ("#fff", "") if not item else (COL[item[1]], item[0])
        ls = "--" if kind == "narrow" else "-"
        if item and len(item) > 3:          # two-slot item: item[3] = partner slot
            px, py, pw, ph, _ = SLOTS[item[3]]
            w = max(x, px) + pw - min(x, px)
        box(ax, x, y, w, h, fc, ls=ls, lw=1.2 if kind == "main" else 1.0, z=1)
        ax.text(x + 4, y + h - 3, sid, fontsize=7, va="top", color="#555", zorder=3)
        if label:
            ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=8, zorder=3, linespacing=1.15)
        elif not item:
            ax.text(x + w / 2, y + h / 2, "volné" if layout else "", ha="center", va="center", fontsize=7, color="#999", zorder=3)
    ax.annotate("", xy=(190, -78), xytext=(190, -52), arrowprops=dict(arrowstyle="->", lw=1.6, color="#444"))
    ax.text(200, -66, "OPERÁTOR (obsluha zepředu)", fontsize=8, va="center", color="#444")
    ax.annotate("", xy=(-6, -GAP - FRONT_EXTRA - NARROW_D - 6), xytext=(-6 + 35, -GAP - FRONT_EXTRA - NARROW_D - 6),
                arrowprops=dict(arrowstyle="->", color="#a00"))
    ax.text(-4, -GAP - FRONT_EXTRA - NARROW_D - 14, "X", color="#a00", fontsize=8)
    ax.set_xlim(-18, 3 * PITCH_X + 4)
    ax.set_ylim(-95, 2 * PITCH_Y + 2 * NARROW_D + 2 * GAP + 24)
    ax.set_aspect("equal")
    ax.axis("off")
    if notes:
        ax.text(-12, -92, notes, fontsize=7.5, va="top", color="#222", linespacing=1.3)


def legend(ax):
    y = 2 * PITCH_Y + 2 * NARROW_D + 2 * GAP + 18
    for i, (k, t) in enumerate([("tips", "špičky ClipTip"), ("samples", "vzorky (2 sloty)"), ("plate", "cílová/jiná destička"),
                                ("reagent", "reagencie (úzký slot)")]):
        box(ax, i * 100 - 10, y, 14, 8, COL[k], r=1)
        ax.text(i * 100 + 8, y + 4, t, fontsize=7, va="center")


fig, axes = plt.subplots(1, 3, figsize=(24, 9.2))

# A: geometry
deck(axes[0], "A) Předpokládaný půdorys decku (mm, pohled shora)",
     notes=("M1–M3 přední řada, M4–M6 zadní řada hlavních SBS slotů (127,76 × 85,48 mm)\n"
            "F1–F3 přední úzká řada (předsazená, max. 2 řady, hloubka ≈ 22 mm)\n"
            "B1–B3 zadní úzká řada (max. 2 řady)\n"
            "Rack 96× Eppendorf = 2 sousední hlavní sloty (vodorovně)\n"
            "!! rozteče, hloubka úzkých slotů, poloha odpadu špiček a osa kanálů = k potvrzení"))
for sid, (x, y, w, h, kind) in SLOTS.items():
    if kind == "narrow":
        ax = axes[0]
        ax.text(x + w / 2, y + h / 2, "max. 2 řady", ha="center", va="center", fontsize=7, color="#777")
    else:
        axes[0].text(x + w / 2, y + h / 2 - 8, "SBS", ha="center", va="center", fontsize=8, color="#777")

# B: NGS 8ch reference
ngs = {
    "M1": ("špičky\nClipTip 300 / 1250", "tips"),
    "M2": ("lib_plate\n(cíl, nejčastěji\nnavštěvovaná)", "plate"),
    "M3": ("2. rack špiček\n/ odkládání", "tips"),
    "M4": ("vzorky\n96× 1,5 mL Eppendorf", "samples", "x", "M5"),
    "M5": ("", "samples", "span"),
    "M6": ("index plate\n(1× za run)", "plate"),
    "F1": ("MM-1\nfrag/ligace", "reagent"),
    "F2": ("MM-2\nPCR", "reagent"),
    "F3": ("odpad /\nzbytky", "waste"),
}
deck(axes[1], "B) NGS 96 vzorků – referenční rozložení (reuse špiček pro MM)", ngs,
     notes=("• cíl + špičky + reagencie tvoří „trojúhelník“ M1–M2–F1/F2 → nejkratší dráhy hlavy\n"
            "• vzorky a indexy (1× za run, nové špičky/kolonu) jsou vzadu = dlouhá dráha jen 12×\n"
            "• MM: 1 špička / reagencii, multi-dispense, bezkontaktně → 2 špičky místo 24"))
legend(axes[1])

# C: LC-MS
lcms = {
    "M1": ("špičky\nClipTip 300", "tips"),
    "M2": ("prep_plate\n(deepwell, cíl)", "plate"),
    "M3": ("vial_plate\n(výstup)", "plate"),
    "M4": ("vzorky\n96× 2 mL Eppendorf", "samples", "x", "M5"),
    "M5": ("", "samples", "span"),
    "M6": ("2. rack špiček", "tips"),
    "F1": ("IS\n(int. standard)", "reagent"),
    "F2": ("ACN\n(srážedlo)", "reagent"),
    "F3": ("odpad", "waste"),
}
deck(axes[2], "C) LC-MS 96 vzorků – referenční rozložení", lcms,
     notes=("• ACN je těkavé a řídké → nové špičky + mix, jen mírně přesné; IS = reuse špičky\n"
            "• supernatant → vialky: nové špičky po sloupcích (kritické přesnost + carry-over)\n"
            "• vzorky vzadu: 1× čtení, dlouhá dráha nevadí"))
legend(axes[2])

plt.tight_layout()
for ext in ("svg", "png"):
    fig.savefig(f"docs/deck_floorplan.{ext}", dpi=130)
print("ok")
