"""LABOT deck floor plan, portrait SBS orientation, anchors measured from the customer's plate drawing.

Scale (0.4555 mm/px) is derived assuming the 3x2 main slots are exactly SBS-sized and touching:
pitch 187 px x 281 px  <->  85.48 x 127.76 mm.  Slot position relative to the anchor triangles
and the front/back direction are INFERRED - see notes drawn in panel A.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Circle

S = 0.4555                       # mm per source pixel
CX, CY = 429.0, 407.0            # deck centre in the source image


def mm(px, py):
    return (px - CX) * S, (CY - py) * S     # y up = towards the top of the drawing (row B / C)


# --- measured anchors (px) ------------------------------------------------------------------
TRI_BACK_APEX = [(242, 256), (429, 256), (616, 256)]
TRI_BACK_BASE = [(195, 445), (287, 445), (382, 444), (475, 445), (569, 444), (664, 445)]
TRI_FRONT_APEX = [(242, 537), (428, 538), (616, 537)]
TRI_FRONT_BASE = [(195, 724), (289, 725), (382, 724), (476, 724), (569, 724), (664, 724)]
RAIL_TOP = [(148, 40), (428, 40), (711, 39)]
RAIL_BOTTOM = [(148, 772), (428, 772), (710, 773)]
RAIL_LEFT = [(35, 125), (35, 407), (33, 687)]
RAIL_RIGHT = [(823, 125), (823, 407), (823, 687)]

OUTLINE_PX = [(68, 9), (789, 9), (789, 75), (849, 75), (849, 740), (789, 740), (789, 799), (68, 799), (68, 740), (8, 740), (8, 75), (68, 75)]

# --- slots (px ranges, inferred) ------------------------------------------------------------
COLS = [(148.5, 335.5), (335.5, 522.5), (522.5, 709.5)]
ROW_B = (164, 444)               # back main row
ROW_A = (444, 724)               # front main row
ROW_C = (9, 75)                  # back narrow row (missing in the customer's table -> C1-C3)
ROW_0 = (740, 799)               # front narrow row (table: 1, 2, 3)
SIDE_L = (8, 148)
SIDE_R = (709.5, 849)
SIDE_Y = (75, 740)

COL = dict(tips="#cfd4da", samples="#9ec5fe", plate="#a3cfbb", reagent="#ffd29c", waste="#e5b8b8",
           res="#d9c2f0", none="#ffffff", mod="#a3cfbb")


def rect_px(ax, xr, yr, fc="#fff", ec="#333", lw=1.1, ls="-", z=2):
    x0, y1 = mm(xr[0], yr[0])
    x1, y0 = mm(xr[1], yr[1])
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=2.5", fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))
    return x0, y0, x1 - x0, y1 - y0


def label(ax, xr, yr, text, fs=6.3, sid=None, color="#111"):
    x, y, w, h = rect_px_dims(xr, yr)
    if sid:
        ax.text(x + 2, y + h - 2, sid, fontsize=6.5, va="top", color="#555", zorder=5, fontweight="bold")
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, zorder=5, linespacing=1.15, color=color)


def rect_px_dims(xr, yr):
    x0, y1 = mm(xr[0], yr[0])
    x1, y0 = mm(xr[1], yr[1])
    return x0, y0, x1 - x0, y1 - y0


def frame(ax, title, anchors=False):
    ax.set_title(title, fontsize=10.5, loc="left", fontweight="bold")
    ax.add_patch(Polygon([mm(*p) for p in OUTLINE_PX], closed=True, fc="#f6e7c8", ec="#c78a1a", lw=1.5, zorder=0))
    if anchors:
        for pts, c in ((TRI_BACK_APEX + TRI_BACK_BASE + TRI_FRONT_APEX + TRI_FRONT_BASE, "#2b6cb0"),
                       (RAIL_TOP + RAIL_BOTTOM, "#c05621"), (RAIL_LEFT + RAIL_RIGHT, "#2f855a")):
            for p in pts:
                ax.add_patch(Circle(mm(*p), 4.2, fc="white", ec=c, lw=1.4, zorder=6))
    x, y = mm(849, 799)
    ax.set_xlim(-200, 200)
    ax.set_ylim(-285, 205)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.annotate("", xy=(0, -200), xytext=(0, -186), arrowprops=dict(arrowstyle="->", lw=1.5, color="#444"))
    ax.text(8, -193, "předpoklad: obsluha dole (řada 1–3)", fontsize=7, va="center", color="#444")


def base_slots(ax, items=None, sid_names=True):
    items = items or {}
    names = {("B", 0): "B1", ("B", 1): "B2", ("B", 2): "B3", ("A", 0): "A1", ("A", 1): "A2", ("A", 2): "A3",
             ("C", 0): "C1", ("C", 1): "C2", ("C", 2): "C3", ("N", 0): "1", ("N", 1): "2", ("N", 2): "3"}
    rows = {"B": ROW_B, "A": ROW_A, "C": ROW_C, "N": ROW_0}
    skip = set()
    for key, (text, kind, *span) in items.items():
        pass
    for r, yr in rows.items():
        for c, xr in enumerate(COLS):
            sid = names[(r, c)]
            if sid in skip:
                continue
            it = items.get(sid)
            ls = "--" if r in "CN" else "-"
            if it and it[2:] == ("span_up",):          # two-slot item drawn from the A slot up through B
                continue
            if it and it[2:] == ("span",):
                continue
            fc = COL[it[1]] if it else "#fff"
            yr_draw = yr
            if it and it[2:] == ("tall",):             # A + B column
                yr_draw = (ROW_B[0], ROW_A[1])
            rect_px(ax, xr, yr_draw, fc=fc, ls=ls)
            label(ax, xr, yr_draw, it[0] if it else ("volné" if items else ""), sid=sid)
    # side zones
    for sid, xr in (("L", SIDE_L), ("R", SIDE_R)):
        it = items.get(sid)
        rect_px(ax, xr, SIDE_Y, fc=COL[it[1]] if it else "#fff", ls=":", lw=1.0)
        label(ax, xr, SIDE_Y, it[0] if it else "boční pozice\n(vakutejnery, 15/50 mL,\nEppendorf)\n\njen krajní kanál\n(levý / pravý)", sid=sid, fs=5.8)


fig, axes = plt.subplots(1, 3, figsize=(24.5, 8.8))

# ---- A: geometry
ax = axes[0]
frame(ax, "A) Půdorys decku – SBS na výšku, kotvy změřené z výkresu (mm)", anchors=True)
base_slots(ax)
ax.text(-198, -212, "● modré: 3 šrouby do trojúhelníku (hlavní sloty A1–B3, 85,5 × 127,8 mm)\n"
        "● oranžové: 3 šrouby v řadě – úzké řady C1–C3 (vzadu) a 1–3 (vpředu), ≤ 2 řady hloubky\n"
        "● zelené: 3 šrouby v řadě – boční pozice L/R (osa Y, rozteč 128 mm)\n"
        "Měřítko 0,455 mm/px odvozeno z rozteče slotů; poloha slotu vůči kotvám, vpředu/vzadu = ODHAD",
        fontsize=7, va="top", color="#222", linespacing=1.35)

# ---- B: customer table, 12.5 uL pipette
cfg125 = {
    "B1": ("IN_TUBES – VZORKY\n96× Eppendorf 1,5 mL\nnebo QIAGEN 2,0 mL\n(2 holdery: A1 + B1)", "samples", "tall"),
    "A1": ("", "samples", "span"),
    "A2": ("96 TIPS\npro vzorky", "tips"),
    "B2": ("96 TIPS\nR-primery\nnebo pufry", "tips"),
    "A3": ("OUT_PLATE\n/ MAGNETIC PLATE\n/ IN_PLATE\n(PCR 200 µL, chlazení)", "plate"),
    "B3": ("96_R-PRIMERS\n(PCR 200 µL, chlazení)\nnebo OUT_PLATE", "plate"),
    "1": ("WASTE", "waste"),
    "2": ("8 F-PRIMERS\n+ MM mix\n(pro 1 plate)", "reagent"),
    "3": ("alkalický /\nneutralizační pufr\n(pro 1 plate)", "reagent"),
}
ax = axes[1]
frame(ax, "B) Konfigurace s pipetou 12,5 µL (podle tabulky zákazníka)")
base_slots(ax, cfg125)
ax.text(-198, -212, "Rack 96 zkumavek = dva holdery ve sloupci 1 (A1+B1): dvouslotová dvojice je SVISLÁ.\n"
        "C1–C3 (zadní úzká řada) v tabulce chybí → doplnit využití.", fontsize=7, va="top", linespacing=1.35)

# ---- C: 300 uL
cfg300 = dict(cfg125)
cfg300["A3"] = ("RESERVOIRS\n(pro pipetu 300 µL)", "res")
cfg300["B3"] = ("RESERVOIRS\n(pro pipetu 300 µL)", "res")
ax = axes[2]
frame(ax, "C) Konfigurace s pipetou 300 µL (A3/B3 = zásobníky)")
base_slots(ax, cfg300)
ax.text(-198, -212, "Ostatní sloty beze změny; výměna pipety mezi konfiguracemi = zásah obsluhy / změna nástroje.", fontsize=7, va="top")

plt.tight_layout()
for ext in ("svg", "png"):
    fig.savefig(f"docs/deck_floorplan.{ext}", dpi=125)
print("ok")
