"""Build docs/labot_zadani_parametry.xlsx - the sheet the customer fills in."""
import glob
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

SRC = glob.glob("/root/.claude/uploads/*/*ClipTip*.xlsx")
HDR = PatternFill("solid", fgColor="1F4E78")
FILL = PatternFill("solid", fgColor="FFF2CC")     # to be filled
ASSUME = PatternFill("solid", fgColor="E2EFDA")   # prefilled assumption - confirm
thin = Side(style="thin", color="BBBBBB")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = openpyxl.Workbook()


def sheet(name, headers, rows, widths, fill_cols=(), assume_cols=(), validations=None, nrows_extra=0):
    ws = wb.create_sheet(name)
    ws.append(headers)
    for c in ws[1]:
        c.fill, c.font = HDR, Font(bold=True, color="FFFFFF")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append(list(r))
    for _ in range(nrows_extra):
        ws.append([None] * len(headers))
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = BORDER
            if c.column in fill_cols:
                c.fill = FILL
            if c.column in assume_cols and c.value not in (None, ""):
                c.fill = ASSUME
    ws.freeze_panes = "A2"
    for col, items in (validations or {}).items():
        dv = DataValidation(type="list", formula1='"' + ",".join(items) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}{ws.max_row + 200}")
    return ws


# ---------------------------------------------------------------- README
ws = wb.active
ws.title = "0_Jak_vyplnit"
for line in [
    "LABOT – zadání pro plánování decku a generování kódu runu",
    "",
    "Žlutá buňka = vyplní zákazník.   Zelená buňka = náš předpoklad z popisu, prosím potvrdit/opravit.",
    "Prázdné pole = použije se výchozí hodnota ve sloupci 'Výchozí', pokud je uvedena.",
    "",
    "Listy:",
    "1_Robot      – hlava, pipety, pohyby, režimy dávkování, špičky",
    "2_Deck       – sloty (3×2 SBS + 3 přední + 3 zadní úzké, předsazená řada), rozměry a omezení",
    "3_Plasticware – použité nádoby/destičky/racky/špičky",
    "4_Kapaliny   – každá kapalina: chování, riziko kontaminace, povolené znovupoužití špičky",
    "5_Kroky      – jeden řádek = jeden pipetovací krok (z–do, objem, režim, špička, dispense)",
    "6_Kvalita    – definice přesnosti a správnosti (třídy A/B/C) a způsob ověření",
    "7_Run        – počty vzorků a runů, směny, priority optimalizace",
    "8_Pipety     – seznam ClipTip pipet (ze zaslané tabulky) – zaškrtněte, které robot reálně má",
    "",
    "Pojmy: správnost (trueness) = systematická odchylka od nominálního objemu v % nebo µL;",
    "přesnost (precision) = náhodná odchylka, CV v %. Vyplňte pro každou třídu kroku (list 6).",
]:
    ws.append([line])
ws.column_dimensions["A"].width = 120
ws["A1"].font = Font(bold=True, size=14)

# ---------------------------------------------------------------- 1 Robot
robot = [
    ("Pipetovací hlava – typ", "", "1 kanál / 8 / 12 / 16 / Equalizer (nastavitelná rozteč) / jiné", "volí počet jednotek na pohyb a dosah do úzkých slotů", ""),
    ("Počet pipet/hlav současně na gantry", "", "1 / 2 / výměna nástroje", "určuje, zda lze střídat rozsahy bez zásahu", "1"),
    ("Osa řady kanálů vůči decku", "", "podél X (zleva doprava) / podél Y (zepředu dozadu)", "KLÍČOVÉ: úzký slot max. 2 řady – 8 kanálů se tam vejde jen při ose podél X", ""),
    ("Rozteč kanálů (min / max)", "", "mm (9 / 4,5 / 9–19,8 …)", "zarovnání na 96/384 formát", "9"),
    ("Rozsah pipety / pipet (viz list 8)", "", "µL min–max", "horní mez = max. nasátý objem na špičku (ne jmenovitý objem špičky)", ""),
    ("Pracovní okno přesnosti", "", "např. ≥ 10 % max. objemu pipety", "pod tím se krok nesmí dělat touto pipetou", "≥10 % max."),
    ("Dispense režimy podporované hlavou", "", "forward / reverse / multi-dispense (repeat) / blow-out / mix / touch-off / air-gap / pre-wet", "řídí, co smí plánovač použít", "forward, reverse, multi, mix"),
    ("Multi-dispense: minimální/typický přebytek", "", "µL na kanál", "ztráty a počet dávek na 1 nasátí", "5"),
    ("Prime/zahozená první dávka", "", "ano / ne", "zpřesňuje první dávku při multi-dispense", "ne"),
    ("Detekce hladiny (LLD)", "", "ano / ne / kapacitní / tlaková", "bezkontaktní dávkování a nasávání z nízkých objemů", "ne"),
    ("Dispense: kontakt se stěnou/hladinou", "", "air / wall-touch / liquid-contact – které jsou řiditelné", "pravidla znovupoužití špičky", "air, wall-touch"),
    ("Vrácení špičky do racku (tip return)", "", "ano / ne", "umožní znovupoužití špiček mezi runy a úsporu špiček", ""),
    ("Odpad špiček – poloha", "", "souřadnice nebo slot", "dráha eject", ""),
    ("Rychlosti pohybu X / Y / Z", "", "mm/s", "model času a minimalizace pohybů", ""),
    ("Doba nasazení / vyhození špičky", "", "s", "model času", "3 / 2"),
    ("Průtoky nasátí / dávkování (min–max)", "", "µL/s", "model času, vazkost", "100"),
    ("Maximální výška labware na decku", "", "mm", "kolize hlavy", ""),
    ("Moduly na decku (třepačka, ohřev, chlazení, magnet)", "", "seznam + sloty", "zabírají sloty", "žádné"),
    ("Vzorkové racky 96× Eppendorf – zabírají 2 sloty", "2 sousední hlavní sloty, vodorovně?", "vodorovně / svisle", "povolená poloha", "vodorovně"),
    ("Typ špiček (ClipTip) a balení", "", "12,5 / 200 / 300 / 1250 / 1000 / 384×; rack 96 nebo 384", "kapacita racků na decku", ""),
]
sheet("1_Robot", ["Parametr", "Hodnota", "Možnosti / jednotka", "K čemu to plánovač potřebuje", "Výchozí"],
      robot, [42, 28, 50, 60, 22], fill_cols=(2,))

# ---------------------------------------------------------------- 2 Deck
deck_rows = []
for i in range(6):
    deck_rows.append((f"M{i + 1}", "hlavní SBS", "přední řada" if i < 3 else "zadní řada", 127.76, 85.48, "", "", "ano", "", ""))
for pre, where in (("F", "přední úzká (předsazená)"), ("B", "zadní úzká")):
    for i in range(3):
        deck_rows.append((f"{pre}{i + 1}", "úzký", where, 127.76, "", "", "", "", "", "max. 2 řady"))
deck_rows.append(("(?)", "předsazená řada – upřesnit", "", "", "", "", "", "", "", "popište/načrtněte: kolik pozic, o kolik mm je předsazena, v jakém rozsahu dosáhne hlava"))
sheet("2_Deck", ["Slot", "Typ", "Poloha", "Šířka X mm", "Hloubka Y mm", "Střed X mm (od počátku robota)", "Střed Y mm", "Dosah všemi kanály?", "Max. výška labware mm", "Poznámka"],
      deck_rows, [8, 24, 26, 12, 12, 20, 14, 18, 18, 55], fill_cols=(5, 6, 7, 8, 9), assume_cols=(1, 2, 3, 4, 10))

# ---------------------------------------------------------------- 3 Plasticware
lw = [
    ("tube_rack_1p5ml_96", "Rack 96× Eppendorf 1,5 mL", "2 sloty", 8, 12, 9, 1500, 30, "", "zdroj/cíl"),
    ("plate96_pcr", "96w PCR destička", "1 slot SBS", 8, 12, 9, 200, 5, "", "cíl/zdroj"),
    ("plate96_dw_2ml", "96 deepwell 2 mL", "1 slot SBS", 8, 12, 9, 2000, 30, "", "cíl"),
    ("reservoir_12well", "12-jamková nádrž", "1 slot SBS", 1, 12, 9, 20000, 1500, "", "reagencie"),
    ("narrow_trough", "úzká nádržka", "úzký slot", 1, 1, "", 25000, 2000, "", "reagencie"),
    ("narrow_tube_row", "řada zkumavek v úzkém slotu", "úzký slot", 1, 12, 9, 5000, 300, "", "reagencie (1 kanál?)"),
    ("tips_clip_300", "ClipTip 300 rack 96", "1 slot SBS", 8, 12, 9, "", "", "", "špičky"),
]
sheet("3_Plasticware", ["Klíč", "Popis", "Půdorys", "Řad", "Sloupců", "Rozteč mm", "Max. objem jamky µL", "Mrtvý objem µL", "Výška mm / katalog. č.", "Použití"],
      lw, [22, 36, 14, 8, 10, 10, 18, 14, 22, 20], fill_cols=(9,), assume_cols=(1, 2, 3, 4, 5, 6, 7, 8, 10),
      nrows_extra=15, validations={"C": ["1 slot SBS", "2 sloty", "úzký slot"]})

# ---------------------------------------------------------------- 4 Liquids
liq = [("master mix 1", "reagencie", "", "", "", "", "", "", "", "", "")]
sheet("4_Kapaliny", ["Kapalina", "Role", "Vazkost (nízká/střední/vysoká)", "Těkavá?", "Pění?", "Kritické carry-over? (ano/ne)",
                     "Max. tolerované carry-over (% / ppm)", "Znovupoužití špičky povoleno?", "Preferovaný režim", "Teplota/stabilita na decku", "Poznámka"],
      liq, [24, 14, 20, 10, 10, 20, 24, 22, 20, 22, 30], fill_cols=tuple(range(2, 12)), nrows_extra=20,
      validations={"B": ["vzorek", "reagencie", "standard", "ředidlo", "odpad"], "C": ["nízká", "střední", "vysoká"],
                   "D": ["ano", "ne"], "E": ["ano", "ne"], "F": ["ano", "ne"],
                   "H": ["ne", "v rámci kroku", "napříč destičkami", "napříč runy", "auto (dle kvality)"],
                   "I": ["forward", "reverse", "multi-dispense", "auto"]})

# ---------------------------------------------------------------- 5 Steps
steps = [(1, "", "", "", "", 1, "", "", "", "", "", "", "", "")]
sheet("5_Kroky", ["#", "Název kroku", "Zdroj (kapalina/labware)", "Cíl (labware)", "Objem na jamku µL", "Opakování", "Režim dávkování",
                  "Kanály", "Politika špičky", "Dispense typ", "Míchání (cykly × µL)", "Třída přesnosti (list 6)", "Čekání / manuální krok (s)", "Poznámka"],
      steps, [5, 22, 26, 20, 14, 10, 18, 10, 26, 22, 18, 16, 20, 30], fill_cols=tuple(range(2, 15)), nrows_extra=40,
      validations={"G": ["forward", "reverse", "multi-dispense", "auto"],
                   "H": ["1", "8", "12", "16", "auto"],
                   "I": ["nová na jamku/sloupec", "1 na krok (reuse)", "1 na reagencii napříč destičkami", "1 na reagencii napříč runy (vrátit do racku)", "auto (dle kvality+kapaliny)"],
                   "J": ["air (bezkontaktně)", "wall-touch (unikátní místo)", "liquid-contact", "auto"],
                   "L": ["A", "B", "C"]})

# ---------------------------------------------------------------- 6 Quality
qual = [
    ("A – kritický", "např. standardy, enzymy, < 5 µL", "", "", "", "", "", "ne – vždy nová špička, forward/reverse, kontakt s kapalinou jen po výměně"),
    ("B – standardní", "např. master mixy 5–50 µL", "", "", "", "", "", "ano, bezkontaktně / wall-touch, multi-dispense"),
    ("C – hrubý", "např. pufry, promývání, > 50 µL", "", "", "", "", "", "ano, reuse i napříč destičkami"),
]
sheet("6_Kvalita", ["Třída kroku", "Příklad / rozsah objemů", "Správnost: max. systematická chyba (% nebo µL)", "Přesnost: max. CV (%)",
                    "Ověření (gravimetricky / barvivem / fotometricky)", "Počet opakování ověření", "Max. carry-over", "Důsledek pro špičky (náš návrh – potvrdit)"],
      qual, [18, 32, 28, 16, 30, 16, 18, 60], fill_cols=(3, 4, 5, 6, 7), assume_cols=(1, 2, 8), nrows_extra=5)

# ---------------------------------------------------------------- 7 Run
run = [
    ("Vzorků na run", "", "počet", ""),
    ("Runů za den", "", "počet", ""),
    ("Pracovní doba robota za den", "", "h", "8"),
    ("Přestavba mezi runy (nakládka/vykládka)", "", "min", "10"),
    ("Formát destiček", "", "96 / 384 / smíšené", "96"),
    ("Proměnný počet vzorků (částečné sloupce)", "", "ano / ne", "ne"),
    ("Dohled obsluhy – max. počet zásahů na run", "", "počet (výměny racků apod.)", "1"),
    ("Priorita: minimum času runu", "", "1–5", "3"),
    ("Priorita: minimum spotřeby špiček", "", "1–5", "4"),
    ("Priorita: minimum slotů/ruční práce", "", "1–5", "3"),
    ("Priorita: minimum rizika kontaminace", "", "1–5", "5"),
    ("Znovupoužití špiček mezi runy / směnami", "", "ne / v rámci dne", "ne"),
    ("Požadovaný výstup", "", "zadání pro kód / hotový kód / protokol IQ-OQ", ""),
]
sheet("7_Run", ["Parametr", "Hodnota", "Jednotka / možnosti", "Výchozí"], run, [50, 20, 40, 14], fill_cols=(2,))

# ---------------------------------------------------------------- 8 Pipettes (from the customer's list)
rows = []
if SRC:
    src = openpyxl.load_workbook(SRC[0], data_only=True).active
    mode = None
    for r in src.iter_rows(values_only=True):
        if not r[0]:
            continue
        s = str(r[0])
        if s.startswith("Pipette ClipTip / multichannel"):
            mode = "multichannel – pevná rozteč"
        elif s.startswith("Adjustable"):
            mode = "multichannel – Equalizer"
        elif s.startswith("Pipette ClipTip / single"):
            mode = "jednokanálová"
        elif s[:4].isdigit() and s.endswith("BT"):
            if mode == "jednokanálová":
                rows.append((r[0], mode, r[1], 1, r[3], r[4], "", ""))
            else:
                rows.append((r[0], mode, r[1], r[2], r[3], r[4], r[5] if mode.endswith("Equalizer") else "", ""))
ws = sheet("8_Pipety", ["Katalog. č.", "Typ", "Rozsah", "Kanálů", "Kompatibilní špičky", "Rozteč / min mm", "Rozteč max mm", "Na robotu? (ano/ne)"],
           rows, [14, 28, 16, 8, 20, 14, 14, 18], fill_cols=(8,), validations={"H": ["ano", "ne"]})

out = "docs/labot_zadani_parametry.xlsx"
wb.save(out)
print(out, len(rows), "pipettes")
