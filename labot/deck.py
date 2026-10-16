"""Deck model: 3x2 main SBS slots + 3 front + 3 back narrow single-row slots.

Main slots   M1..M3 (front row), M4..M6 (back row)
Narrow slots F1..F3 (front), B1..B3 (back)
A two-slot item (Eppendorf rack) occupies two neighbouring main slots.
"""
from dataclasses import dataclass
from itertools import product


@dataclass
class DeckLayout:
    main_cols: int = 3
    main_rows: int = 2
    small_front: int = 3
    small_back: int = 3
    two_slot_orientation: str = "horizontal"   # horizontal | vertical | any

    @property
    def main(self):
        return [f"M{i + 1}" for i in range(self.main_cols * self.main_rows)]

    @property
    def small(self):
        return ([f"F{i + 1}" for i in range(self.small_front)]
                + [f"B{i + 1}" for i in range(self.small_back)])

    def pairs(self):
        cols, rows = self.main_cols, self.main_rows
        idx = lambda c, r: f"M{r * cols + c + 1}"
        out = []
        if self.two_slot_orientation in ("horizontal", "any"):
            out += [(idx(c, r), idx(c + 1, r)) for r in range(rows) for c in range(cols - 1)]
        if self.two_slot_orientation in ("vertical", "any"):
            out += [(idx(c, r), idx(c, r + 1)) for c in range(cols) for r in range(rows - 1)]
        return out

    def describe(self):
        return {"main": self.main, "small": self.small, "two_slot_pairs": self.pairs()}


def place(items, layout: DeckLayout):
    """items: list of (id, footprint, pinned_slot|None).

    Returns (assignment {id: [slots]}, free_main [..], free_small [..]) maximising
    the number of free main slots (they are used for tip racks) or (None, msg).
    """
    pinned = {i: p for i, _, p in items if p}
    fp = {i: f for i, f, _ in items}
    twos = [i for i, f, _ in items if f == "sbs2"]
    ones = [i for i, f, _ in items if f == "sbs"]
    smalls = [i for i, f, _ in items if f == "small"]
    pairs = layout.pairs()
    best = None

    def finish(assign, used):
        nonlocal best
        assign = dict(assign)
        used = set(used)
        free_main = [s for s in layout.main if s not in used]
        free_small = [s for s in layout.small if s not in used]
        for i in ones:
            if i in assign:
                continue
            if not free_main:
                return
            assign[i] = [free_main.pop(0)]
        for i in smalls:
            if i in assign:
                continue
            if free_small:
                assign[i] = [free_small.pop(0)]
            elif free_main:
                assign[i] = [free_main.pop()]   # narrow item on a big slot: take from the far end
            else:
                return
        if best is None or len(free_main) > len(best[1]):
            best = (assign, free_main, free_small)

    pre, pre_used = {}, set()
    for i, slot in pinned.items():
        if fp[i] == "sbs2":
            pr = next((p for p in pairs if p[0] == slot), None)
            if not pr:
                return None, f"{i}: no two-slot pair starts at pinned slot {slot}"
            slots = list(pr)
        else:
            slots = [slot]
        if any(s in pre_used or s not in layout.main + layout.small for s in slots):
            return None, f"{i}: pinned slot {slot} invalid or already used"
        pre[i] = slots
        pre_used.update(slots)

    free_twos = [i for i in twos if i not in pre]
    for combo in product(pairs, repeat=len(free_twos)):
        used = set(pre_used)
        ok = True
        for pr in combo:
            if used & set(pr):
                ok = False
                break
            used.update(pr)
        if ok:
            finish({**pre, **dict(zip(free_twos, map(list, combo)))}, used)
    if best is None:
        need = len(twos) * 2 + len(ones)
        return None, (f"cannot place {len(twos)} two-slot, {len(ones)} one-slot and {len(smalls)} "
                      f"narrow items on {len(layout.main)} main + {len(layout.small)} narrow slots "
                      f"(main slots needed >= {need})")
    return best
