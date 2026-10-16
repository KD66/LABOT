"""Single-tip pickup with the end channel of an 8-channel head (channel row along X)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

P = 9.0   # channel / tip pitch, mm


def draw(ax, title, pos_of_active_tip, channel, taken):
    """channel: 0 = leftmost (K1) ... 7 = rightmost (K8); pos_of_active_tip: rack position 0..7 under that channel."""
    rack_x0 = 0
    ax.set_title(title, fontsize=9.5, loc="left", fontweight="bold")
    ax.add_patch(Rectangle((-8, -11), 7 * P + 16, 22, fc="#cfd4da", ec="#333", hatch="////", zorder=1))
    ax.add_patch(Rectangle((-8 - 75, -11), 75, 22, fc="#e8f1ff", ec="#888", zorder=1))
    ax.add_patch(Rectangle((7 * P + 8, -11), 75, 22, fc="#e8f1ff", ec="#888", zorder=1))
    ax.text(-8 - 37, 0, "soused vlevo\n(nižší než rack)", ha="center", va="center", fontsize=7, color="#456")
    ax.text(7 * P + 8 + 37, 0, "soused vpravo\n(nižší než rack)", ha="center", va="center", fontsize=7, color="#456")
    for i in range(8):
        ax.add_patch(plt.Circle((i * P, 0), 3.3, fc="white" if i in taken else "#7a98a8", ec="#333", lw=0.8, zorder=2))
        ax.text(i * P, -15.5, str(i + 1), ha="center", fontsize=6.5, color="#555")
    head0 = pos_of_active_tip - channel          # x position index of K1
    for k in range(8):
        x = (head0 + k) * P
        act = k == channel
        ax.plot([x], [17], marker="v", ms=10 if act else 7, color="#c53030" if act else "#999", zorder=4)
        ax.text(x, 23, f"K{k + 1}", ha="center", fontsize=6.5, color="#c53030" if act else "#777")
    ax.set_xlim(-95, 7 * P + 95)
    ax.set_ylim(-22, 30)
    ax.set_aspect("equal")
    ax.axis("off")


fig, axes = plt.subplots(3, 1, figsize=(11, 8.4))
draw(axes[0], "1) Levý kanál K1 bere tip 8 (kraj racku) – K2…K8 přečnívají doprava nad souseda", 7, 0, set())
draw(axes[1], "2) Pravý kanál K8 bere tip 1 (kraj racku) – K1…K7 přečnívají doleva nad souseda", 0, 7, set())
draw(axes[2], "3) Později: K8 bere tip 4, tipy 1–3 už chybí → K1…K7 jsou nad prázdnými pozicemi (odběr jde od kraje dovnitř)", 3, 7, {0, 1, 2})
fig.text(0.02, 0.01, "Pohled shora, osa X vodorovně; rack se může odebírat po sloupcích (osa Y, 12 sloupců). Přečnívající kanály nemají špičku – jejich kužely "
         "musí být nad sousedním labware → rack se špičkami je ZVÝŠEN v Z. Plný sloupec (8 špiček) se bere všemi kanály bez omezení.",
         fontsize=7.5, wrap=True)
plt.tight_layout(rect=(0, 0.04, 1, 1))
for ext in ("png", "svg"):
    fig.savefig(f"docs/tip_pickup_geometry.{ext}", dpi=130)
print("ok")
