# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant PODWÓJNY, PV + ME (fotowoltaika + magazyn energii razem),
`crm/szablony/umowa_pv_me_podwojna.pdf`.

Zmierzona w issue #166, wzorowana STRUKTURALNIE na `crm/volteo_umowa_mapa.py`
(`MAPA`, wariant PV+ME jednoosobowy - nazwy kluczy, rodzaje pol, konwencje
przeliczen) - kazda wartosc liczbowa ponizej jest zmierzona OD ZERA na tym
pliku, zaden `x`/`y`/`maks_szerokosc` nie jest skopiowany z mapy jednoosobowej.

POMIAR: 2026-09-23, `pdftotext -bbox-layout crm/szablony/umowa_pv_me_podwojna.pdf`
plus `pdfminer.six` (`LTLine` dla kreski dzielacej kolumny obu tabel
komparycji, `LTChar` na obu Pelnomocnictwach, gdzie podkreslenie „Ja, nizej
podpisany/a ___," sklejone jest z przecinkiem bez spacji) - identyczna
metodologia jak `crm/volteo_umowa_mapa_pv2.py`/`crm/volteo_umowa_mapa_me2.py`
(patrz naglowek `pv2` dla pelnego opisu konwencji i rdzenia skryptu
pomiarowego, `pvme2_measure.py`, zapisanego w scratchpadzie zadania). Zadna
wartosc nie jest przepisana recznie ani wyliczona "w pamieci".

UKLAD WSPOLRZEDNYCH, KONWENCJE PRZELICZEN I ZASADA DWOCH OSOB - identyczne z
`crm/volteo_umowa_mapa_pv2.py` (patrz jego naglowek), nie powtarzane tu w
pelni. `klient2_*` i `podpis_zamawiajacy_2` sa jedynym dozwolonym dodatkiem
kluczy (6 razem). Kolumny podpisu (Zamawiajacy vs Wykonawca) rozroznione po
wspolrzednej `x` (< 300pt = Zamawiajacy, >= 300pt = Wykonawca), nie po
kolejnosci w strumieniu `pdftotext`.

STRUKTURA STRON tego wariantu (20 stron) NIE jest prostym przesunieciem
struktury jednoosobowej PVME (18 stron) o dwie strony - drugi blok komparycji
przesuwa §2 Wynagrodzenie z powrotem na strone 1 (jak w wariancie
jednoosobowym) na WLASNA strone 2 (idx1), a lista Zalacznikow dostaje
WLASNA strone 5 (idx4, pusta z pozycji mapy - tylko spis tresci). Terminologia
§2 w tym konkretnym pliku uzywa „Finansowanie zewnetrzne” / „Przelew” zamiast
„Kredyt” / „Gotowka/przelew” uzywanych w PV2/ME2 - dopasowanie do kluczy
(`fin_kredyt_100`, `fin_kredyt_wklad`, `wklad_wlasny`, `kwota_kredytu`,
`fin_gotowka`) jest po ROLI/POZYCJI pola (kolejnosc checkboxow/podkreslen w
tresci ust. 2), nie po dopasowaniu tekstu etykiety - `zbuduj_kontekst` zwraca
te same klucze niezaleznie od dokladnego sformulowania w danym szablonie.

ZNANA USTERKA ŹRÓDŁA (opisana w skorupie modulu, issue #165, potwierdzona przy
pomiarze): dwa Pełnomocnictwa tego szablonu są numerowane niespójnie jako
„Załącznik nr 8” (na liscie Zalacznikow, str. 5) i „nr 7.1” w tresci drugiego
Pelnomocnictwa (str. 20) - nie naprawiane w tym zadaniu, patrz docstring
skorupy powyzej `MAPA_PVME2`.

BEZPIECZNIK ZMIANY SZABLONU: mapa poniżej obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji oryginału. Generator PDF-u ma sprawdzić sumę SHA-256 pliku
wejściowego względem `SHA256_SZABLONU_PVME2` przed użyciem tej mapy i przerwać
z czytelnym komunikatem przy niezgodności.

Rejestracja tego wariantu w `crm.volteo_umowa_render.SZABLONY` jest zakresem
OSOBNEGO, pozniejszego zadania (issue #167) - nie jest zakresem tego pliku.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PVME2: str = "e4be94cbf1a6fe6aeca16257f2f0d0e628b77037f2dad00b6023f07000dd16ab"
"""SHA-256 pliku `crm/szablony/umowa_pv_me_podwojna.pdf` (A4, 596x842 pt,
20 stron, Producer "Skia/PDF m156 Google Docs Renderer"), przejęte bez zmian z
poprzedniej wersji tego modułu (skorupa, issue #165) - ten sam plik, ta sama
suma. Generator PDF-u (przyszłe issue #167) ma sprawdzić tę sumę przed użyciem
`MAPA_PVME2` i przerwać z czytelnym komunikatem przy niezgodności."""

LICZBA_STRON_PVME2: int = 20
"""Liczba stron oryginału, zgodna z `pdfinfo`. Dwie strony więcej niż wariant
jednoosobowy (`LICZBA_STRON` = 18 w `crm/volteo_umowa_mapa.py`) - drugi blok
komparycji (jedna dodatkowa strona przez przesuniecie tresci, zob. docstring
modulu) i drugie Pełnomocnictwo (str. 20)."""

# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja x2 (rozdzielone slowem "oraz") + S1
# Przedmiot umowy. Dwie niezalezne tabele danych klienta (5 wierszy kazda),
# pionowa kreska dzielaca kolumny (pdfminer LTLine, zbadana niezaleznie):
# x=171.5, prawa krawedz x=522.5.
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 650.55, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 626.07, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 601.6, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 577.12, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 552.65, "tekst", maks_szerokosc=342.0),
	Pole("klient2_imie_nazwisko", 0, 177.5, 514.2, "tekst", maks_szerokosc=342.0),
	Pole("klient2_adres", 0, 177.5, 489.73, "tekst", maks_szerokosc=342.0),
	Pole("klient2_pesel", 0, 177.5, 465.25, "tekst", maks_szerokosc=342.0),
	Pole("klient2_telefon", 0, 177.5, 440.78, "tekst", maks_szerokosc=342.0),
	Pole("klient2_email", 0, 177.5, 416.31, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 206.36, 713.58, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 689.49, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 111.0, 192.45, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 135.37, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 115.54, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §2 Wynagrodzenie - na osobnej stronie od komparycji.
# Ten szablon nazywa opcje finansowania "Finansowanie zewnętrzne" i "Przelew"
# zamiast "Kredyt"/"Gotówka" (PV2/ME2) - dopasowanie do kluczy po ROLI pola
# (kolejnosc w tresci), nie po tekscie etykiety, zob. docstring modulu.
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 575.09, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 548.64, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 478.34, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 458.51, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 211.44, 416.4, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 264.8, 389.96, "tekst", maks_szerokosc=249.73),
	Pole("fin_gotowka", 1, 115.5, 372.55, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §3 ust. 1 lit. f - powierzchnia budynku
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 512.79, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 512.79, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 512.28, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §7 Postanowienia końcowe - blok podpisów umowy głównej.
# DWIE linie "Zamawiający" (klient 1, klient 2), JEDNA linia "Wykonawca" -
# zweryfikowane czytaniem tresci, jak w PV2/ME2. Strona 5 (indeks 4, lista
# Zalacznikow) nie ma zadnej pozycji - patrz docstring modulu.
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 194.82, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 194.82, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 3, 75.0, 110.19, "tekst", maks_szerokosc=158.0),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik nr 1a - ARKUSZ USTALEŃ MONTAŻOWYCH -
# INSTALACJA FOTOWOLTAICZNA (bez sekcji "istniejaca instalacja PV" - ta jest
# na Zalaczniku 1b, strona 7, tak jak w mapie jednoosobowej). Wspolny naglowek
# "Zamawiajacy"/"Wykonawca" nad DWIEMA liniami podpisu Zamawiajacego i JEDNA
# linia Wykonawcy.
# ---------------------------------------------------------------------------
_STRONA_5_ZALACZNIK_1A: tuple[Pole, ...] = (
	Pole("panel_moc_wp", 5, 223.9, 715.33, "tekst", maks_szerokosc=55.15),
	Pole("panel_szt", 5, 381.7, 715.33, "tekst", maks_szerokosc=57.93),
	Pole("moc_pv_kwp", 5, 186.09, 698.08, "tekst", maks_szerokosc=57.93),
	Pole("panel_producent_model", 5, 280.02, 680.83, "tekst", maks_szerokosc=227.5),
	Pole("panel_gwarancja_lat", 5, 249.46, 663.58, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_moc_kw", 5, 183.31, 629.09, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_szt", 5, 174.42, 611.84, "tekst", maks_szerokosc=57.94),
	Pole("inwerter_producent_model", 5, 205.01, 594.59, "tekst", maks_szerokosc=230.27),
	Pole("inwerter_gwarancja_lat", 5, 250.57, 577.34, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 5, 118.95, 521.42, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 5, 173.93, 521.42, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 5, 251.14, 521.42, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 5, 229.43, 499.72, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 5, 121.72, 478.29, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 5, 157.83, 478.29, "kratka", wyrownanie="srodek"),
	Pole("montaz_dach", 5, 157.28, 452.42, "kratka", wyrownanie="srodek"),
	Pole("montaz_grunt", 5, 213.37, 452.42, "kratka", wyrownanie="srodek"),
	Pole("pokrycie_dachowe", 5, 268.9, 430.73, "tekst", maks_szerokosc=85.73),
	Pole("odgromowa_tak", 5, 182.29, 409.3, "kratka", wyrownanie="srodek"),
	Pole("odgromowa_nie", 5, 228.76, 409.3, "kratka", wyrownanie="srodek"),
	Pole("ppoz_tak", 5, 398.41, 348.93, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 5, 444.89, 348.93, "kratka", wyrownanie="srodek"),
	Pole("przekop_tak", 5, 165.06, 323.06, "kratka", wyrownanie="srodek"),
	Pole("przekop_mb", 5, 222.03, 322.55, "tekst", maks_szerokosc=38.48),
	Pole("przekop_nie", 5, 281.0, 323.06, "kratka", wyrownanie="srodek"),
	Pole("kabel_tak", 5, 161.18, 297.18, "kratka", wyrownanie="srodek"),
	Pole("kabel_mb", 5, 218.15, 296.67, "tekst", maks_szerokosc=38.48),
	Pole("kabel_nie", 5, 277.12, 297.18, "kratka", wyrownanie="srodek"),
	# Blok podpisow: wspolny naglowek, DWIE linie Zamawiajacego. Kreski
	# (pdftotext -bbox): zam1 xMin=72.0/xMax=236.0/yMax=674.22, wyk
	# xMin=360.0/xMax=521.22/yMax=674.22, zam2 xMin=72.0/xMax=236.0/yMax=727.12.
	Pole("podpis_zamawiajacy", 5, 75.0, 170.28, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 5, 363.0, 170.28, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 5, 75.0, 117.38, "tekst", maks_szerokosc=158.0),
)

# ---------------------------------------------------------------------------
# Strona 7 (indeks 6): Załącznik nr 1b - ARKUSZ USTALEŃ MONTAŻOWYCH - MAGAZYN
# ENERGII, z sekcja "W PRZYPADKU POSIADANIA INSTALACJI FOTOWOLTAICZNEJ"
# (existing-PV) - jak w mapie jednoosobowej PVME. Wspolny naglowek
# "Zamawiajacy"/"Wykonawca" nad DWIEMA liniami podpisu Zamawiajacego i JEDNA
# linia Wykonawcy.
# ---------------------------------------------------------------------------
_STRONA_6_ZALACZNIK_1B: tuple[Pole, ...] = (
	Pole("bateria_producent_model", 6, 191.13, 715.33, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 6, 153.31, 698.08, "tekst", maks_szerokosc=55.15),
	Pole("bateria_pojemnosc_jedn_kwh", 6, 293.9, 680.83, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 6, 444.49, 680.83, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_lacznie_kwh", 6, 272.24, 663.58, "tekst", maks_szerokosc=55.15),
	Pole("bateria_gwarancja_lat", 6, 236.69, 646.33, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_inwertera_kw", 6, 167.2, 572.17, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 6, 232.76, 554.92, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 6, 170.01, 537.67, "tekst", maks_szerokosc=155.23),
	# Blok podpisow: wspolny naglowek, DWIE linie Zamawiajacego. Kreski
	# (pdftotext -bbox): zam1 xMin=72.0/xMax=236.0/yMax=398.25, wyk
	# xMin=360.0/xMax=521.22/yMax=398.25, zam2 xMin=72.0/xMax=236.0/yMax=490.81.
	Pole("podpis_zamawiajacy", 6, 75.0, 446.25, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 6, 363.0, 446.25, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 6, 75.0, 353.69, "tekst", maks_szerokosc=158.0),
)

# ---------------------------------------------------------------------------
# Strona 8 (indeks 7): Załącznik nr 2 (zgody) i Załącznik nr 3 (oświadczenie
# o realizacji przed terminem odstąpienia) - JEDEN checkbox na oświadczenie,
# DWIE osobne linie podpisu (klient1, klient2) pod kazdym, bez Wykonawcy -
# identycznie jak w PV2/ME2. Kratki male (10x10pt, offset 2.0, rozmiar 8.0).
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 7, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 7, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 7, 77.0, 339.37, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Załącznik 2: podpis klienta 1, potem klienta 2.
	Pole("podpis_zamawiajacy", 7, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 7, 75.0, 520.33, "tekst", maks_szerokosc=155.22),
	# Załącznik 3: podpis klienta 1, potem klienta 2 (osobno, niżej na stronie).
	Pole("podpis_zamawiajacy", 7, 75.0, 193.7, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 7, 75.0, 114.35, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 10 (indeks 9): Załącznik nr 4 - koniec klauzuli RODO, linia podpisu
# klienta ("Zamawiający" / "data i podpis") x2 - klient1 wyzej, klient2 nizej,
# kazdy z WLASNYM naglowkiem "Zamawiajacy" - zweryfikowane czytaniem tresci.
# ---------------------------------------------------------------------------
_STRONA_10: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 9, 75.0, 575.87, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 9, 75.0, 496.52, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 19 (indeks 18): Załącznik nr 8 - Pełnomocnictwo OSD, PIERWSZE
# (klient 1). Numeracja "nr 8" (nie "nr 7" jak w PV2/ME2) - usterka zrodla
# opisana w skorupie modulu (issue #165) i w naglowku tego pliku, nie
# naprawiana tutaj.
# ---------------------------------------------------------------------------
_STRONA_19: tuple[Pole, ...] = (
	# "udzielone w dniu ___" - świadomie reużyty `data_zawarcia`.
	Pole("data_zawarcia", 18, 292.01, 681.66, "tekst", maks_szerokosc=88.51),
	# "Ja, niżej podpisany/a ___," - granica zmierzona granulacją znakową
	# `pdfminer` (`LTChar`), wykluczajac doklejony bez spacji przecinek
	# (xMax kreski bez przecinka: 262.65, jak w PV2/ME2).
	Pole("klient_imie_nazwisko", 18, 171.13, 655.21, "tekst", maks_szerokosc=88.52),
	Pole("klient_adres", 18, 336.75, 655.21, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 18, 110.01, 641.99, "tekst", maks_szerokosc=116.3),
	# Jedna linia podpisu - "Mocodawcy" (klient 1), BEZ Wykonawcy.
	Pole("podpis_zamawiajacy", 18, 365.05, 152.7, "tekst", maks_szerokosc=155.23),
)

# ---------------------------------------------------------------------------
# Strona 20 (indeks 19): Załącznik nr 7.1 - Pełnomocnictwo OSD, DRUGIE
# (klient 2). Uklad NIE jest pikselowo identyczny ze strona 19 (w odroznieniu
# od PV2/ME2, gdzie obie strony POA byly identyczne) - ta strona ma o ok.
# 26,5 pt mniej tresci nad naglowkiem "udzielone w dniu", wiec kazde pole jest
# przesuniete w gore wzgledem strony 19 - zmierzone tu w pelni niezaleznie.
# ---------------------------------------------------------------------------
_STRONA_20: tuple[Pole, ...] = (
	Pole("data_zawarcia", 19, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient2_imie_nazwisko", 19, 171.13, 681.66, "tekst", maks_szerokosc=88.52),
	Pole("klient2_adres", 19, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient2_pesel", 19, 110.01, 668.43, "tekst", maks_szerokosc=116.3),
	Pole("podpis_zamawiajacy_2", 19, 365.05, 179.15, "tekst", maks_szerokosc=155.23),
)

MAPA_PVME2: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_3
	+ _STRONA_4
	+ _STRONA_5_ZALACZNIK_1A
	+ _STRONA_6_ZALACZNIK_1B
	+ _STRONA_8
	+ _STRONA_10
	+ _STRONA_19
	+ _STRONA_20
)
"""Pełna mapa dla `crm/szablony/umowa_pv_me_podwojna.pdf`: 90 pozycji (wariant
jednoosobowy `MAPA` w `crm/volteo_umowa_mapa.py` ma 74) - roznica to drugi
blok komparycji (5 pozycji), drugie podpisy Zamawiajacego (str. 4/6/7/8x2/10,
razem 8 dodatkowych pozycji) i drugie Pelnomocnictwo (5 pozycji, str. 20) =
74 + 5 + 8 + 5 - 2 = 90 (korekta: dwie pozycje `podpis_zamawiajacy` na str. 8
- Zalacznik 2 i 3 - juz sie liczyly w mapie jednoosobowej, wiec czysty
przyrost stamtad to +2 `podpis_zamawiajacy_2`, nie +4). Generator wywolujacy
te mape (przyszle issue #167) ma narysowac wartosc we WSZYSTKICH pozycjach
danego klucza, nie tylko w pierwszej."""

# Strony 5, 9, 11, 12, 13, 14, 15, 16, 17, 18 (indeksy 4, 8, 10, 11, 12, 13,
# 14, 15, 16, 17) nie zawierają żadnej pozycji z kontekstu `zbuduj_kontekst`:
#
# - Str. 5 (idx 4): lista Zalacznikow (spis tresci, statyczny tekst).
# - Str. 9 (idx 8): Załącznik nr 4 - początek klauzuli RODO (statyczny tekst,
#   linia podpisu jest na kolejnej stronie, str. 10/idx 9).
# - Str. 11 (idx 10): Załącznik nr 5 - Pouczenie o prawie do odstąpienia
#   (statyczne, informacyjne, bez pól).
# - Str. 12 (idx 11): wzór FORMULARZA ODSTĄPIENIA - świadomie BEZ pozycji.
# - Str. 13-14 (idx 12-13): Załącznik nr 6 - Protokół odbioru Instalacji
#   Fotowoltaicznej - CAŁKOWICIE pusty (decyzja produktowa 2026-08-12),
#   wypełnia go ręcznie instalator.
# - Str. 15 (idx 14): protokół pomiarów elektrycznych PV - instalator.
# - Str. 16-17 (idx 15-16): Załącznik nr 7 - Protokół odbioru Magazynu
#   Energii - CAŁKOWICIE pusty, jak protokół PV.
# - Str. 18 (idx 17): protokół pomiarów magazynu energii - instalator.


def pozycje_dla_pvme2(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_PVME2` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_PVME2 if pole.klucz == klucz)


def klucze_w_mapie_pvme2() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_PVME2` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_PVME2)
