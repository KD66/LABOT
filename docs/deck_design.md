# LABOT – rozvaha: rozložení plasticware, znovupoužití špiček, zadání

Půdorys: `docs/deck_floorplan.png|svg`. Tabulka k vyplnění: `docs/labot_zadani_parametry.xlsx`.

## 0. Geometrie decku (aktualizováno podle výkresu kotev a tabulky zákazníka)
* SBS destičky stojí **na výšku**: 85,5 mm ve směru X, 127,8 mm ve směru Y. Sloupec 96w destičky (A–H, 8 × 9 mm) tak leží podél X
  – přesně tam, kde je řada kanálů hlavy.
* Hlavní sloty: **A1–A3** (přední řada), **B1–B3** (zadní řada); 3 šrouby do trojúhelníku na slot.
* Úzké řady (≤ 2 řady hloubky, ≈ 27 mm): **1–3** vpředu (tabulka zákazníka), **C1–C3** vzadu (v tabulce chybí); 3 šrouby v řadě.
  Řada 1×8 zkumavek podél X je dosažitelná **všemi 8 kanály najednou** (např. „8 F-PRIMERS“ = každý kanál jiný primer).
* Boční pozice **L/R** (3 šrouby v řadě podél Y, ≈ 64 × 256 mm): vakutejnery, 15/50 mL, Eppendorf; dosáhne je jen **krajní kanál**
  (levý/pravý). Z toho plyne osa kanálů podél X.
* Rack 96 Eppendorf = dva holdery A1+B1 – dvouslotová dvojice je **svislá**.
* Dvě konfigurace podle pipety: 12,5 µL (A3/B3 = plate, chlazení/magnet) a 300 µL (A3/B3 = zásobníky).
* Neověřeno: která strana je přední, poloha slotu vůči kotvám, měřítko (odvozeno z rozteče slotů).

## 0b. Špičky, pipety a ovládání (z odpovědí zákazníka)
**Tip racky uprostřed a zvýšené v Z.** Jednotlivou špičku bere levý nebo pravý kanál; ostatní kanály nemají špičku a přečnívají přes okraj racku
nad sousední labware, jehož horní hrana musí být pod kužely těchto kanálů (proto zvýšený rack, viz `docs/tip_pickup_geometry.png`).
Důsledky pro plánovač:
* racky špiček pevně ve sloupci 2 (A2, B2); ostatní labware v sousedních sloupcích musí být nižší než zvýšený rack (výška = parametr);
* pořadí spotřeby při jednotlivých špičkách jde **od kraje dovnitř** (levý kanál od jednoho kraje, pravý od druhého), jinak by přečnívající kanály
  najely na špičky; plný sloupec (8 špiček) se bere bez omezení;
* kolizní kontrola pro každou operaci s maskou kanálů: pod každým kanálem bez špičky nesmí být labware vyšší než (Z práce + délka špičky − rezerva);
* vrácení špičky do racku = špička drží svou pozici → „parkování“ špiček na reagencii (F-primery: 8 kanálů = 8 vlastních špiček na celý run
  i napříč destičkami; R-primery: nová špička na primer = rack B2).

**Pipety:** 12,5 / 300 / 1250 µL, 8 kanálů, fixní 9 mm i roztahovací (Equalizer; rozteč řízena G-kódem na samostatném servu).
Výměna je ruční a výjimečná → **jeden běh = jedna pipeta**. Plánovač proto musí pro celý běh vybrat jednu pipetu, jejíž rozsah pokryje všechny
objemy (nad horní mezí se dělí / multi-dispense, pod dolní mezí je krok neproveditelný) a odpovídá třídě přesnosti. Rack špiček pro zvolenou
pipetu je v A2/B2; konfigurace A3/B3 (12,5 µL: plate, 300 µL: zásobníky) se mění jen mezi běhy.

**Příkazová gramatika:** forward, reverse, multi-dispense, blow-out, vrácení špičky do racku. Drop je stepper motor →
makro `DROP = blow_out → drop_tip`. `confirm` se posílá jen na začátku běhu po `home` (kontrola X, Y, Z). Generátor kódu hlídá:
drop jen po blow-outu, žádný aspirate bez špičky, žádné míchání při znovupoužité špičce, objem v rozsahu pipety.

**Výška racků špiček:** liší se podle racku a je výstupem optimalizace (kolize s přečnívajícími kanály); horní mez = délka špičky (30–120 mm
podle pipety) + 25 mm (přesný význam k potvrzení, viz list 12_Rozmery M6).

## 0c. Strategické plánování (model, ne rychlosti)
Rychlosti a zrychlení se odkládají (config + rules dodá zákazník). Optimalizuje se **počet a délka pohybů**.
* Událost: (pipeta, maska kanálů, zdrojové jamky, cílové jamky, objem, režim forward/reverse/multi, dispense air/wall/liquid, politika špičky).
* Cena J = w₁·počet nasátí + w₂·počet přejezdů mezi pozicemi + w₃·Σ vzdálenost přejezdů (mm) + w₄·počet nasazení/odhození/vrácení špiček;
  váhy jsou nastavitelné, výchozí lexikograficky: kvalita (tvrdé omezení) → přejezdy → vzdálenost → špičky.
* Proměnné: přiřazení labware → pozice (≤ 18 pozic: 6 hlavních, 2×3 úzké, 2×3 boční, kde pozice = střed na šroubu), pořadí kroků v rámci závislostí,
  seskupení do multi-dispense, maska kanálů, politika špičky.
* Tvrdá omezení: rozsah pipety, třída přesnosti → povolený režim/kontakt/reuse, kapacita špičky, dosah (boční pozice jen krajní kanál),
  rack Eppendorf = 2 sousední pozice (svisle A+B), úzká řada ≤ 2 řady, kolize (výška racků vs sousedé), jedna pipeta na běh.
* Řešení: pozic i labware je málo → úplné prohledání s ořezáním (branch & bound) a přesné vyhodnocení J simulací běhu; pořadí kroků lokálním hledáním.
  Výstup: pořadí rozložení + rozpad J (kolik přejezdů a kde), aby bylo vidět, co rozložení stojí.
* Geometrie pro výpočty: pozice = střed plasticware na šroubech, stejné mezery mezi pozicemi v Y; posun o housing (≈ 40 mm) a dosah bočních šroubů
  (−20 mm) se zatím ignorují. Potřebné rozměry: `docs/labot_zadani_parametry.xlsx`, list `12_Rozmery`.

## Cherry-picking, pooling, repliky
Fyzicky nejsou omezené: špička se nasadí jen na krajní kanál (levý/pravý) nebo na masku kanálů a přenos jde z libovolné jamky do libovolné.
Dřívější „bez cherry-pickingu“ byla mezera v plánovači, ne limit robota. Plán: krok `pick_list` (seznam zdroj→cíl, objem), plánovač seskupí
přenosy do vícekanálových pohybů tam, kde jamky sedí na rozteči 9 mm, zbytek jede 1 kanálem (krajní kanál volí podle blízkosti
bočních pozic). Pooling = N zdrojů → 1 jamka (nová špička na zdroj při kontaktu s kapalinou), repliky = 1 zdroj → N cílů.
384 destičky: 9 mm hlava dosáhne každý 2. řádek (4 prokládané průchody), 4,5 mm hlava celý sloupec.

## Hodnocení rozložení zákazníka (12,5 µL)
* Vzorky (A1+B1) – špičky pro vzorky (A2) – plate (A3/B3): tok vlevo→doprava s tipy uprostřed, nejkratší dráha hlavy. Dobré.
* R-primery (B3) sousedí se špičkami R-primerů (B2); F-primery a MM v řadě 2 vpředu, těsně u A3. Dobré.
* Při znovupoužití špiček pro MM/pufry stačí 1 rack → B2 se může uvolnit pro druhou destičku/modul; C1–C3 jsou volné pro reagencie.

## 1. Co optimalizujeme
Rozhodovací proměnné: (a) slot každého plasticware, (b) pořadí kroků, (c) politika špičky na krok,
(d) režim dávkování, (e) pipeta/špička (rozsah).
Cena runu = Σ vzdálenost hlavy mezi po sobě jdoucími pozicemi + (nasazení+vyhození špiček) + počet nasátí
+ penalizace za zásah obsluhy (výměna racku) + penalizace za porušení kvality (tvrdé omezení, ne váha).

## 2. Pravidla umístění (heuristiky, ověřitelné výpočtem QAP nad ≤ 12 sloty)
1. Dvojice „cíl ↔ špičky ↔ reagencie“ tvoří kompaktní trojúhelník uprostřed přední řady: cílová destička
   je v každém kroku → nejčastější návštěvy; špičky sousedí s ní; reagencie v úzkém slotu přímo před/za ní.
2. Matice toků: f(i,j) = počet přesunů hlavy mezi labware i a j za run. Sloty přiřadit tak, aby
   Σ f·vzdálenost bylo minimální (6 hlavních + 6 úzkých slotů → brute force/branch&bound).
3. Zdroje používané 1× za run (vzorky, index plate) dozadu/na kraj – dlouhá dráha 12× nevadí.
4. Úzké sloty (max. 2 řady): reagencie v tubách/nádržkách. Zda je smí obsloužit víc kanálů najednou,
   rozhoduje **osa řady kanálů** (podél X ano, podél Y jen 1–2 kanály) – nejdůležitější otevřená otázka.
5. Operátor nakládá zepředu: často měněné věci (cílové destičky, racky špiček) vpředu a po straně; těžké/méně měněné vzadu.
6. Mokré (znovupoužité) špičky nepřejíždět nad otevřenými destičkami s jinými vzorky – reagencie mimo dráhu, nebo
   cestu vést po okraji / ve větší výšce.
7. Znovupoužití špiček uvolní sloty: 2 špičky místo 24 → 1 rack místo 3–4 → 2–3 hlavní sloty volné
   pro moduly, 2. cíl nebo odkládání.

## 3. Politika špičky podle kvality a kontaktu
| Dispense typ | Kapalina / třída kroku | Povolená politika špičky |
|---|---|---|
| air (bezkontaktně, nad hladinou) | reagencie, třída B/C | 1 špička na reagencii; multi-dispense; mezi destičkami i mezi runy (tip return) |
| wall-touch na unikátní místo jamky | reagencie do prázdné/suché stěny | stejně, pokud špička nepřijde do styku s kapalinou v jamce |
| liquid-contact (do vzorku, mix) | cokoli | nová špička na jamku/sloupec (jinak kontaminace zdroje) |
| třída A (kritická přesnost, < 5 % rozsahu, standardy) | cokoli | nová špička, forward/reverse, bez multi-dispense |

Multi-dispense/reverse: první a poslední dávka mají větší chybu → buď „prime“ (zahozená první dávka), nebo přebytek;
rozhoduje customer definice správnosti a přesnosti (list 6). Počet dávek na nasátí k = ⌊(V_max − přebytek)/v⌋.
Příklad: 12 sloupců × 15 µL = 180 µL → jedna špička a jedno nasátí s pipetou 10–300 µL; s pipetou 2–125 µL k = 8 → 2 nasátí;
s pipetou 15–1250 µL jedno nasátí, ale 15 µL je na spodní mezi rozsahu → vyřazeno kvalitou. Proto se pipeta vybírá podle okna přesnosti.

## 4. Důsledek pro stávající kód (příští fáze)
Katalog špiček přepsat z 50/200/1000 na ClipTip a kapacitu špičky brát jako **horní mez pipety** (12,5 / 125 / 300 / 850–1250 µL),
ne jmenovitý objem špičky. Přidat: třídy kroku A/B/C, dispense typy air/wall/liquid, tip return, QAP optimalizátor slotů,
úzké sloty s pravidlem dosahu podle osy kanálů, předsazenou řadu.
