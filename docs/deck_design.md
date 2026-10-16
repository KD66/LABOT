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
