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
    "2_Deck       – sloty A1–B3 (SBS na výšku), C1–C3 a 1–3 (úzké), L/R (boční), rozměry a omezení",
    "3_Plasticware – použité nádoby/destičky/racky/špičky",
    "4_Kapaliny   – každá kapalina: chování, riziko kontaminace, povolené znovupoužití špičky",
    "5_Kroky      – jeden řádek = jeden pipetovací krok (z–do, objem, režim, špička, dispense)",
    "6_Kvalita    – definice přesnosti a správnosti (třídy A/B/C) a způsob ověření",
    "7_Run        – počty vzorků a runů, směny, priority optimalizace",
    "8_Pipety     – seznam ClipTip pipet (ze zaslané tabulky) – zaškrtněte, které robot reálně má",
    "9_Konfigurace – obsah slotů pro 12,5 µL a 300 µL pipetu (předvyplněno z vaší tabulky)",
    "10_Pick_list – cherry-picking / pooling / repliky jako seznam přenosů",
    "11_Prikazy_G – logické operace pipety a vaše G-kódy (home → confirm; blow_out → drop_tip …)",
    "12_Rozmery   – rozměry potřebné pro výpočty (stav: známo / hypotéza / čeká)",
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
    ("Počet pipet/hlav současně na gantry", "1 – vždy jen jedna, výměna ruční a výjimečná", "1 / 2 / výměna nástroje", "jeden běh = jedna pipeta", "1"),
    ("Osa řady kanálů vůči decku", "podél X (zleva doprava) – odvozeno z boční pozice 'levý/pravý kanál' a SBS na výšku", "podél X / podél Y", "potvrdit; sloupec 96w destičky (A–H) leží podél X, 8 kanálů se vejde do úzké řady 1×8 zkumavek", "podél X"),
    ("Boční pozice L/R – které kanály dosáhnou", "jen krajní kanál (levý pro L, pravý pro R)", "kanál č. / všechny", "cherry-picking a odběr z vakutejnerů, 15/50 mL, Eppendorf", "krajní"),
    ("Jednotlivé kanály: lze nasadit špičku jen na vybrané kanály (maska)?", "", "ano / ne / jen krajní", "cherry-picking, pooling, částečné sloupce", "ano"),
    ("Výměna pipety mezi konfiguracemi (12,5 µL ⇄ 300 µL)", "ruční, výjimečná, mimo běh", "ruční / automatická / hlava výměnná", "konfigurace A3/B3 se mění jen mezi běhy", "ruční"),
    ("Rozteč kanálů (min / max)", "", "mm (9 / 4,5 / 9–19,8 …)", "9 mm hlava na 384 destičce = každý 2. řádek, 4 průchody; 4,5 mm hlava = celý sloupec", "9"),
    ("Rozsah pipety / pipet (viz list 8)", "", "µL min–max", "horní mez = max. nasátý objem na špičku (ne jmenovitý objem špičky)", ""),
    ("Pracovní okno přesnosti", "", "např. ≥ 10 % max. objemu pipety", "pod tím se krok nesmí dělat touto pipetou", "≥10 % max."),
    ("Dispense režimy podporované hlavou", "", "forward / reverse / multi-dispense (repeat) / blow-out / mix / touch-off / air-gap / pre-wet", "řídí, co smí plánovač použít", "forward, reverse, multi, mix"),
    ("Multi-dispense: minimální/typický přebytek", "", "µL na kanál", "ztráty a počet dávek na 1 nasátí", "5"),
    ("Prime/zahozená první dávka", "", "ano / ne", "zpřesňuje první dávku při multi-dispense", "ne"),
    ("Detekce hladiny (LLD)", "", "ano / ne / kapacitní / tlaková", "bezkontaktní dávkování – bez LLD se výška hladiny počítá z objemu a geometrie jamky", "ne"),
    ("Dispense: kontakt se stěnou/hladinou", "", "air / wall-touch / liquid-contact – které jsou řiditelné", "pravidla znovupoužití špičky", "air, wall-touch"),
    ("Vrácení špičky do racku (tip return)", "", "ano / ne", "umožní znovupoužití špiček mezi runy a úsporu špiček", ""),
    ("Odpad špiček – poloha", "", "souřadnice nebo slot", "dráha eject", ""),
    ("Rychlosti pohybu X / Y / Z", "", "mm/s", "model času a minimalizace pohybů", ""),
    ("Doba nasazení / vyhození špičky", "", "s", "model času", "3 / 2"),
    ("Průtoky nasátí / dávkování (min–max)", "", "µL/s", "model času, vazkost", "100"),
    ("Maximální výška labware na decku", "", "mm", "kolize hlavy", ""),
    ("Moduly na decku (třepačka, ohřev, chlazení, magnet)", "", "seznam + sloty", "zabírají sloty", "žádné"),
    ("Vzorkové racky 96× Eppendorf – zabírají 2 sloty", "A1+B1 (svisle) – dle tabulky zákazníka", "svisle (A+B) / vodorovně", "povolená poloha dvojslotové položky", "svisle"),
    ("Typ špiček (ClipTip) a balení", "", "12,5 / 200 / 300 / 1250 / 1000 / 384×; rack 96 nebo 384", "kapacita racků na decku", ""),
]
_upd = {
    "Pipetovací hlava – typ": "8 kanálů, osa řady podél X; fixní rozteč 9 mm i roztahovací (Equalizer)",
    "Počet pipet/hlav současně na gantry": "1 – vždy jen jedna, rychlá výměna",
    "Rozsah pipety / pipet (viz list 8)": "12,5 / 300 / 1250 µL (všechny 8 kanálů)",
    "Dispense režimy podporované hlavou": "forward, reverse, multi-dispense, blow-out, vrácení špičky do racku (vlastní G-kódy pístu)",
    "Vrácení špičky do racku (tip return)": "ano",
    "Detekce hladiny (LLD)": "",
    "Příkaz Confirm": "",
}
robot = [(p_, _upd.get(p_, v_), o_, w_, d_) for (p_, v_, o_, w_, d_) in robot]
robot += [
    ("Drop špičky – řízení", "stepper motor; vždy musí předcházet blow-out", "popis", "pevné pravidlo příkazové gramatiky (list 11)", "blow_out → drop_tip"),
    ("Příkaz Confirm", "jen na začátku běhu po Home (kontrola pozice X, Y, Z)", "není součástí drop makra", "gramatika příkazů", "po Home"),
    ("Tip racky: povýšení v Z", "výška se liší podle rack a je optimalizovaná kvůli kolizím; max zdvih = délka špičky (30–120 mm dle pipety) + 25 mm", "mm na rack (výstup optimalizace)", "jednotlivá špička levým/pravým kanálem – ostatní kanály přečnívají nad sousedy", ""),
    ("Délka špičky ClipTip 12,5 / 300 / 1250", "", "mm", "kolizní kontrola přečnívajících kanálů bez špičky", ""),
    ("Odběr jednotlivých špiček z racku", "levý kanál od jednoho kraje, pravý od druhého (od kraje dovnitř)", "potvrdit pořadí", "plánovač spotřeby špiček a kolizní pravidla", ""),
    ("Equalizer – změna rozteče", "G-kód, samostatné servo; rozsah viz list 8", "mm", "krok s přenosem mezi různými rozteč. formáty", ""),
    ("Výměna pipety", "ruční, výjimečná – v jednom běhu se s ní nepočítá", "", "jeden běh = jedna pipeta (rozsah objemů musí pokrýt všechny kroky)", "1 pipeta / běh"),
    ("Rychlosti a zrychlení X/Y/Z", "odloženo – dodá zákazník v konfiguračním souboru a pravidlech", "", "strategické plánování počítá počty pohybů a vzdálenosti, ne čas", ""),
    ("Rozsah pojezdů X / Y / Z a bezpečná Z", "", "mm", "dosah na boční pozice, kolize", ""),
]
sheet("1_Robot", ["Parametr", "Hodnota", "Možnosti / jednotka", "K čemu to plánovač potřebuje", "Výchozí"],
      robot, [42, 28, 50, 60, 22], fill_cols=(2,))

# ---------------------------------------------------------------- 2 Deck
deck_rows = []
for r, where in (("A", "přední hlavní řada"), ("B", "zadní hlavní řada")):
    for i in range(3):
        deck_rows.append((f"{r}{i + 1}", "hlavní SBS (na výšku)", where, 85.48, 127.76, "", "", "3 šrouby do trojúhelníku", "všech 8 kanálů", ""))
for i in range(3):
    deck_rows.append((f"C{i + 1}", "úzký (max. 2 řady)", "zadní úzká řada – v tabulce zákazníka chybí", 85.5, "≈27–30", "", "", "3 šrouby v řadě (rozteč 128 mm), společné pro C1–C3", "", "doplnit využití"))
for i in range(3):
    deck_rows.append((f"{i + 1}", "úzký (max. 2 řady)", "přední úzká řada", 85.5, "≈27", "", "", "3 šrouby v řadě (rozteč 128 mm), společné pro 1–3", "8 kanálů u řady 1×8 podél X", "tabulka: WASTE / 8 F-PRIMERS + MM / pufr"))
for sid, where in (("L", "levý okraj"), ("R", "pravý okraj")):
    deck_rows.append((sid, "boční pozice", where, "≈64", "≈256 (3 šrouby, rozteč 128 mm)", "", "", "3 šrouby v řadě podél Y", "jen krajní kanál", "vakutejnery, 15/50 mL, Eppendorf"))
sheet("2_Deck", ["Slot", "Typ", "Poloha", "Šířka X mm", "Hloubka Y mm", "Střed X mm (od středu decku)", "Střed Y mm", "Kotvení", "Dosah kanály", "Poznámka"],
      deck_rows, [8, 24, 36, 12, 18, 20, 14, 38, 24, 44], fill_cols=(6, 7), assume_cols=(1, 2, 3, 4, 8, 9, 10))
ws2 = wb["2_Deck"]
ws2.append([None])
for line in ["Rozměry odvozeny z výkresu kotev (měřítko 0,455 mm/px při předpokladu, že hlavní sloty jsou SBS a těsně vedle sebe) – potvrdit skutečné rozměry plechu.",
             "Potvrdit: (1) která strana je přední (obsluha), (2) poloha slotu vůči trojúhelníku kotev, (3) do jakého rozsahu dosáhne hlava přes okraje (osa X/Y min–max)."]:
    ws2.append([line])

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
                   "H": ["1", "8", "12", "16", "levý krajní", "pravý krajní", "auto"],
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
    ("Pipeta pro běh (jedna)", "", "12,5 / 300 / 1250 µL (+ fixní / Equalizer)", "plánovač zvolí podle rozsahu objemů, pokud nezadáte"),
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

# ---------------------------------------------------------------- 9 Configurations (customer's table)
conf = [
    ("A1+B1", "IN_TUBES – vzorky: 2 holdery po 96 Eppendorf 1,5 mL nebo QIAGEN 2,0 mL (dvojslotová svislá dvojice)", "stejné", "obě"),
    ("A2", "96 TIPS pro vzorky", "stejné", "obě"),
    ("B2", "96 TIPS pro R-primery NEBO pufry", "stejné", "obě"),
    ("A3", "OUT_PLATE / MAGNETIC PLATE / IN_PLATE (PCR 200 µL, chlazení)", "RESERVOIRS", "obě"),
    ("B3", "96_R-PRIMERS (PCR 200 µL, chlazení) nebo OUT_PLATE (PCR 200 µL, chlazení)", "RESERVOIRS", "obě"),
    ("1", "WASTE", "stejné", "obě"),
    ("2", "8 F-PRIMERS + MM mix (pro 1 plate)", "stejné", "obě"),
    ("3", "Alkalický / neutralizační pufr (pro 1 plate)", "stejné", "obě"),
    ("C1–C3", "", "", ""),
    ("L / R", "", "", ""),
]
sheet("9_Konfigurace", ["Slot", "Konfigurace s pipetou 12,5 µL (z tabulky zákazníka)", "Konfigurace s pipetou 300 µL", "Platí pro kroky"],
      conf, [10, 80, 34, 20], fill_cols=(2, 3, 4), assume_cols=(1,), nrows_extra=6)

# ---------------------------------------------------------------- 10 Pick list
pick = [("pl1", "samples#0", "A1", 10, "plate96_pcr#0", "A1", "", "")]
sheet("10_Pick_list", ["Seznam", "Zdroj (labware)", "Zdrojová jamka", "Objem µL", "Cíl (labware)", "Cílová jamka", "Kanál (levý/pravý/auto)", "Poznámka"],
      pick, [10, 22, 14, 10, 22, 14, 22, 40], fill_cols=tuple(range(1, 9)), nrows_extra=60,
      validations={"G": ["auto", "levý krajní", "pravý krajní", "libovolný 1 kanál"]})
ws = wb["10_Pick_list"]
ws.append([None])
ws.append(["Cherry-picking / pooling / repliky: libovolný seznam přenosů. Plánovač seskupí přenosy do vícekanálových pohybů, pokud jamky sedí na rozteči 9 mm, jinak použije 1 (krajní) kanál."])
ws.append(["Pooling = více zdrojů do 1 cílové jamky (nová špička na zdroj, pokud se špička dotýká kapaliny); repliky = 1 zdroj do více cílů."])

# ---------------------------------------------------------------- 11 Command grammar
cg = [
    ("pick_up_tip", "nasazení špičky(ek) – všechny kanály nebo maska / krajní kanál", "rack, sloupec, kanály", "rack zvýšený; při jedné špičce odběr od kraje dovnitř", "", ""),
    ("aspirate (forward)", "nasátí", "objem, rychlost, výška", "špička nasazená", "", ""),
    ("dispense (forward)", "vydání", "objem, rychlost, výška", "", "", ""),
    ("aspirate/dispense (reverse)", "reverse pipetting", "objem + přebytek", "", "", ""),
    ("multi-dispense", "více dávek z jednoho nasátí", "objem dávky, počet dávek, přebytek", "k = ⌊(Vmax − přebytek)/v⌋", "", ""),
    ("blow_out", "vyfouknutí zbytku", "", "VŽDY před drop_tip", "", ""),
    ("drop_tip", "odhození špičky stepper motorem", "", "bezprostředně po blow_out", "", ""),
    ("confirm", "vynulování pozice stepper motoru", "", "jen na začátku běhu po Home (kontrola X, Y, Z)", "", ""),
    ("return_tip_to_rack", "vrácení špičky na původní pozici v racku", "rack, pozice", "blow_out? rack musí být dosažitelný týmž kanálem", "", ""),
    ("mix", "míchání pístem", "objem, cykly", "", "", ""),
    ("move X/Y/Z", "pojezd gantry", "souřadnice, rychlost", "bezpečná Z při přejezdu", "", ""),
    ("home", "Home + kontrola pozice X, Y, Z", "", "na začátku běhu, následuje confirm", "", ""),
    ("set_spacing", "Equalizer – rozteč kanálů", "mm", "jen u roztahovací pipety", "", ""),
]
sheet("11_Prikazy_G", ["Operace (logická)", "Význam", "Parametry", "Pravidla / pořadí", "Vaše G-kódy (příkaz + parametry)", "Doba s / poznámka"],
      cg, [26, 46, 34, 46, 46, 24], fill_cols=(5, 6), assume_cols=(1, 2, 3, 4), nrows_extra=8)

# ---------------------------------------------------------------- 12 Dimensions
dims = [
 # id, group, quantity, status/value, unit, source, used for
 ("D1", "Deck", "Rozteč kotev hlavních slotů ve směru X (střed trojúhelníku ↔ střed sousedního)", "HYPOTÉZA 90 (z výkresu jen px: 187)", "mm", "výkres kotev", "jediné číslo dá měřítko celého výkresu; poloha všech pozic"),
 ("D2", "Deck", "Rozteč ve směru Y (A ↔ B)", "HYPOTÉZA 135 (poměr Y/X změřen 1,50)", "mm", "výkres kotev", "vzdálenosti přejezdů, mezera mezi plasticware"),
 ("D3", "Deck", "Trojúhelník kotev: základna × výška", "z výkresu ≈ ½·P_x × P_x (45 × 90)", "mm", "výkres kotev", "střed plasticware = střed trojúhelníku?"),
 ("D4", "Deck", "Úzké řady 1–3 a C1–C3: kolik pozic a kde je střed vůči 3 šroubům v řadě", "ČEKÁ – hypotéza: každý šroub = střed jedné pozice (rozteč ≈ 135)", "ano/ne", "tabulka + výkres", "poloha úzkých pozic; konflikt s přední hranou A při středění na šroub"),
 ("D5", "Deck", "Boční pozice L/R: kolik pozic na stranu a střed vůči šroubům", "ČEKÁ – hypotéza: 3 pozice na stranu, střed na šroubu (Y rozteč ≈ 135, X ≈ ±189 od středu)", "mm", "výkres kotev", "boční labware a dosah krajního kanálu"),
 ("D6", "Deck", "Posun pozic dopředu (housing pipety, ≈ 40 mm) a dosah bočních šroubů −20 mm", "IGNOROVAT (zadáno)", "mm", "zákazník", "–"),
 ("D7", "Deck", "Mezery mezi plasticware", "vyplývají z rozteče kotev − rozměr labware (stejná mezera v Y)", "mm", "D1–D2, L1", "kontrola kolizí, vycentrování na šrouby"),
 ("M1", "Stroj", "Rozsah pojezdů X / Y / Z", "ČEKÁ (nebo v config souboru)", "mm", "config", "kontrola dosahu, boční pozice"),
 ("M2", "Stroj", "Home pozice a vztah k souřadnicím kotev", "ČEKÁ (v config souboru)", "mm", "config", "převod pozice → G-kód souřadnice"),
 ("M3", "Stroj", "Referenční kanál pro XY (K1 / střed hlavy) a offset ostatních kanálů", "ČEKÁ", "mm", "config", "poloha k-tého kanálu = ref + (k−1)·rozteč"),
 ("M4", "Stroj", "Rozteč kanálů: fixní 9 mm; Equalizer rozsah", "fixní 9; Equalizer dle listu 8 (9–14,2 / 4,5–14,2), G-kód na separátním servu", "mm", "list 8", "mapování formátů 9 ↔ 14,2 mm ↔ 4,5 mm"),
 ("M5", "Stroj", "Délka špičky ClipTip 12,5 / 300 / 1250 (a délka kužele pipety)", "30–120 mm dle pipety – přesně ČEKÁ", "mm", "zákazník", "kolizní kontrola přečnívajících kanálů"),
 ("M6", "Stroj", "Max zdvih = délka špičky + 25 mm", "ČEKÁ: co přesně? (max. povýšení racku nad deskou / max. zdvih Z osy od pracovní hladiny)", "mm", "zákazník", "horní mez výšky racků špiček"),
 ("M7", "Stroj", "Bezpečná Z pro přejezdy mezi pozicemi", "ČEKÁ (config)", "mm", "config", "legalita přejezdu nad vyššími labware"),
 ("L1", "Labware", "Půdorys L × W včetně holderu/racku (SBS destička 127,76 × 85,48; rack Eppendorf, deepwell, zásobník, boční držáky)", "SBS známo; holdery ČEKÁ", "mm", "katalog výrobce / měření", "mezery, zakrytí kotev"),
 ("L2", "Labware", "Výška H včetně podstavce / chlazení / magnetické desky", "ČEKÁ", "mm", "měření", "kolize s přečnívajícími kanály"),
 ("L3", "Labware", "Poloha jamky A1 vůči středu labware a rozteč jamek", "SBS 9 mm standard; holdery ČEKÁ", "mm", "katalog", "souřadnice všech jamek"),
 ("L4", "Labware", "Tvar jamky/zkumavky: vnitřní průměr nebo průřez, hloubka, tvar dna", "ČEKÁ (1,5 mL, 2 mL QIAGEN, PCR 200 µL, deepwell, 15/50 mL, vakutejner)", "mm", "katalog", "výška hladiny z objemu → bezkontaktní/kontaktní dávkování, ponor"),
 ("L5", "Labware", "Max a mrtvý objem na jamku", "předvyplněno v listu 3 – potvrdit", "µL", "list 3", "počet nasátí, plnění zdrojů"),
 ("L6", "Labware", "Tip rack: rozteč špiček, výška špiček nad rackem, výška podstavce h_rack na každý rack", "rozteč 9; ostatní ČEKÁ; h_rack = výstup optimalizace", "mm", "měření", "odběr jednotlivých špiček, kolize"),
 ("L7", "Labware", "Úzká řada: hloubka (≤ 2 řady), počet zkumavek v řadě (8 po 9 mm?), výška", "ČEKÁ", "mm", "měření", "dosah všemi 8 kanály, nasátí z 8 primerů najednou"),
 ("L8", "Labware", "Boční držáky: průměr a výška zkumavek (15/50 mL, vakutejner, Eppendorf), rozteč", "ČEKÁ", "mm", "měření", "krajní kanál, hloubka ponoru"),
 ("T1", "Špičky", "Min / max objem pipety a špičky", "0,5–12,5 / 10–300 / 15–1250 µL (list 8)", "µL", "list 8", "volba pipety pro běh, multi-dispense počet dávek"),
 ("T2", "Špičky", "Průměr ústí špičky (ponor do jamky) a rozteč 9 mm vs 4,5 mm formát", "ČEKÁ", "mm", "katalog ClipTip", "kontakt s kapalinou / stěnou, 384 destičky"),
]
sheet("12_Rozmery", ["ID", "Skupina", "Rozměr / veličina", "Stav / hodnota", "Jednotka", "Zdroj", "K čemu se použije ve výpočtu"],
      dims, [6, 10, 66, 60, 10, 18, 56], fill_cols=(4,), assume_cols=(3,))

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
                rows.append((r[0], mode, r[1], 1, r[3], r[4], "", "ne"))
            else:
                rows.append((r[0], mode, r[1], r[2], r[3], r[4], r[5] if mode.endswith("Equalizer") else "", "ano (předpoklad)" if (r[2] == 8 and r[3] in ("ClipTip 12.5", "ClipTip 300", "ClipTip 1250", "ClipTip 384 12.5") and r[1] in ("0.5 to 12.5 μL", "10 to 300 μL", "15 to 1250 μL")) else ""))
ws = sheet("8_Pipety", ["Katalog. č.", "Typ", "Rozsah", "Kanálů", "Kompatibilní špičky", "Rozteč / min mm", "Rozteč max mm", "Na robotu? (ano/ne)"],
           rows, [14, 28, 16, 8, 20, 14, 14, 18], fill_cols=(8,), assume_cols=(8,), validations={"H": ["ano", "ano (předpoklad)", "ne"]})

wb.move_sheet("8_Pipety", offset=-4)
out = "docs/labot_zadani_parametry.xlsx"
wb.save(out)
print(out, len(rows), "pipettes")
