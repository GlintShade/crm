# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant PODWÓJNY (dwóch Zamawiających, np. małżonkowie), wyłącznie
fotowoltaiczny (bez magazynu energii), `crm/szablony/umowa_pv_podwojna.pdf`.

Zmierzona w issue #166, wzorowana STRUKTURALNIE na `crm/volteo_umowa_mapa_pv.py`
(nazwy kluczy, rodzaje pol, konwencje przeliczen) - ale KAZDA wartosc liczbowa
ponizej jest zmierzona OD ZERA na tym pliku, zaden `x`/`y`/`maks_szerokosc` nie
jest skopiowany z mapy jednoosobowej. Wstawienie drugiego bloku komparycji na
stronie 1 przesuwa cala tresc ponizej, wiec ukladu jednoosobowego nie dalo by
sie odgadnac.

POMIAR: 2026-09-23, skryptem `pdftotext -bbox-layout crm/szablony/umowa_pv_podwojna.pdf`
(surowe `xMin`/`xMax`/`yMax` liczone OD GORY strony) plus `pdfminer.six`:
`LTLine` do namierzenia pionowej kreski dzielacej kolumny obu tabel komparycji
na stronie 1 (dwie niezalezne tabele, kazda z wlasna kreska w tym samym x),
oraz `LTChar` na Pelnomocnictwie (str. 14/15), gdzie podkreslenie „Ja, nizej
podpisany/a ___," sklejone jest z przecinkiem bez spacji - dokladnie ten sam
problem, co w `crm/volteo_umowa_mapa_pv.py`. Skrypt (`pv2_measure.py`,
zapisany w scratchpadzie zadania, rdzen wklejony ponizej dla odtwarzalnosci)
wypisuje gotowe linie `Pole(...)` - zadna wartosc nie jest przepisana recznie
ani wyliczona "w pamieci".

UKLAD WSPOLRZEDNYCH - identyczny jak w `crm/volteo_umowa_mapa.py` (patrz jego
naglowek dla pelnego wyjasnienia): `y_reportlab = 842 - y_od_gory`. Strona A4
596x842 pt. Tekst na podkresleniu: `x = xMin(kreski) + 3`, `y = 842 -
yMax(kreski) + 2.5`, `maks_szerokosc = szerokosc(kreski) - 6`. Kratki
standardowe (15x15pt): `x` = srodek poziomy glifu, `y = 842 - yMax(glifu) +
3.0`. Kratki male (10x10pt, strona zgod - Zalacznik 2/3): offset `+2.0` i
`rozmiar=8.0`. Komorka tabeli (komparycja): `x` = zmierzona wektorowo
(pdfminer `LTLine`) kreska dzielaca kolumny + 6 pt wciecia, `y = 842 -
yMax(etykiety)`, bez korekty 2,5 pt.

DWIE OSOBY: ten szablon ma DWA bloki komparycji na stronie 1 (rozdzielone
slowem "oraz"), rozne tabele ale ten sam pionowy podzial kolumn (x=171.5,
prawa krawedz x=522.5 - zweryfikowane pdfminer `LTLine` niezaleznie dla obu
tabel). Klucze drugiej osoby (`klient2_*`) NIE istnieja w mapach
jednoosobowych - sa jedynym dozwolonym dodatkiem kluczy w tym zadaniu, razem
z `podpis_zamawiajacy_2` uzywanym wszedzie tam, gdzie szablon drukuje DRUGA
linie podpisu Zamawiajacego (umowa glowna str. 4, Zalacznik 1 str. 5, Zalacznik
2 i 3 str. 6, Zalacznik 4 RODO str. 8, drugie Pelnomocnictwo str. 15) - zawsze
zweryfikowane czytaniem tresci obok linii, nigdy zgadywane po pozycji.
Pierwsze Pelnomocnictwo (str. 14) uzywa `klient_*`/`podpis_zamawiajacy` jak w
mapie jednoosobowej, drugie (str. 15) uzywa `klient2_*`/`podpis_zamawiajacy_2`.
Kolejnosc kolumn podpisu (Zamawiajacy/Wykonawca) w strumieniu `pdftotext` NIE
jest stala miedzy stronami tego samego dokumentu (na str. 4 kolejnosc w pliku
to zam1, zam2, wyk1; na str. 5 to zam1, wyk1, zam2) - `pv2_measure.py`
rozroznia kolumny po wspolrzednej `x` (Zamawiajacy < 300pt, Wykonawca >= 300pt),
nigdy po kolejnosci w pliku.

RDZEN SKRYPTU POMIAROWEGO (pv2_measure.py, w calosci w scratchpadzie zadania):

    def tekst_pole(word, xmax_override=None):
        xmax = xmax_override if xmax_override is not None else word.xMax
        return (round(word.xMin + 3, 2), round(842 - word.yMax + 2.5, 2),
                 round(xmax - word.xMin - 6, 2))

    def kratka_pole(word, maly=False):
        offset = 2.0 if maly else 3.0
        return (round((word.xMin + word.xMax) / 2, 2),
                 round(842 - word.yMax + offset, 2))

    def komorka_pole(label, kreska_x, prawa_krawedz_tabeli):
        x = round(kreska_x + 6, 2)
        y = round(842 - label.yMax, 2)
        maks = round((prawa_krawedz_tabeli - 3) - x, 2)
        return (x, y, maks)

    def podzial_kolumn(linie, prog_x=300.0):
        lewa = sorted([w for w in linie if w.xMin < prog_x], key=lambda w: w.yMax)
        prawa = sorted([w for w in linie if w.xMin >= prog_x], key=lambda w: w.yMax)
        return lewa, prawa

BEZPIECZNIK ZMIANY SZABLONU: mapa poniżej obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji oryginału. Generator PDF-u ma sprawdzić sumę SHA-256 pliku
wejściowego względem `SHA256_SZABLONU_PV2` przed użyciem tej mapy i przerwać
z czytelnym komunikatem przy niezgodności - dokładnie jak dla trzech
dotychczasowych szablonów jednoosobowych.

Rejestracja tego wariantu w `crm.volteo_umowa_render.SZABLONY` jest zakresem
OSOBNEGO, pozniejszego zadania (issue #167), razem ze zmiana `zbuduj_kontekst`,
zeby zwracal `klient2_*`/`podpis_zamawiajacy_2` - nie jest zakresem tego pliku.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PV2: str = "ab8054541a09a64e8a63ffb3d01fd6b3659296094965fd6c7c120b378a641b74"
"""SHA-256 pliku `PODWÓJNA Umowa PV ProEnergy - 28.07.2026.pdf` (A4, 596x842 pt,
15 stron), policzone `shasum -a 256` na pliku W REPO (`crm/szablony/umowa_pv_podwojna.pdf`),
przejęte bez zmian z `crm/volteo_umowa_mapa_pv2.py` (skorupa, issue #165) - ten
sam plik, ta sama suma. Generator PDF-u (przyszłe issue #167) ma sprawdzić tę
sumę przed użyciem `MAPA_PV2` i przerwać z czytelnym komunikatem przy
niezgodności."""

LICZBA_STRON_PV2: int = 15
"""Liczba stron oryginału, zgodna z `pdfinfo`. Jedna strona więcej niż wariant
jednoosobowy (`LICZBA_STRON_PV` = 14) - dodatkowe dane drugiego Zamawiającego
(drugie Pełnomocnictwo, str. 15)."""

# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja x2 (rozdzielone slowem "oraz") + S1
# Przedmiot umowy. Dwie niezalezne tabele danych klienta, kazda 5 wierszy
# (Imie i nazwisko / Adres / PESEL / Telefon / Adres e-mail), 2 kolumny.
# Pionowa kreska dzielaca kolumny (pdfminer LTLine, ZBADANA NIEZALEZNIE dla
# obu tabel): x=171.5 w obu przypadkach, prawa krawedz obu tabel x=522.5,
# lewa x=72.5 (nieuzywana) - identycznie jak w mapach jednoosobowych PV/ME,
# ale to zbieznosc uklad strony, nie skopiowana wartosc: zmierzona osobno na
# TYM pliku. Poziome kreski wierszy tabeli 1 (LTLine): 684.5, 659.5, 635.5,
# 610.5, 586.5, 561.5; tabeli 2 (klient 2, nizej na stronie): 547.5, 523.5,
# 498.5, 474.5, 449.5, 425.5.
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 666.55, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 642.07, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 617.6, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 593.12, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 568.65, "tekst", maks_szerokosc=342.0),
	Pole("klient2_imie_nazwisko", 0, 177.5, 530.2, "tekst", maks_szerokosc=342.0),
	Pole("klient2_adres", 0, 177.5, 505.73, "tekst", maks_szerokosc=342.0),
	Pole("klient2_pesel", 0, 177.5, 481.25, "tekst", maks_szerokosc=342.0),
	Pole("klient2_telefon", 0, 177.5, 456.78, "tekst", maks_szerokosc=342.0),
	Pole("klient2_email", 0, 177.5, 432.31, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 210.11, 735.42, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 701.49, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 110.25, 217.22, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 173.37, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 153.54, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §2 Wynagrodzenie - na osobnej stronie od komparycji
# (w wariancie jednoosobowym PV oba mieszczą się na stronie 1 razem - tu drugi
# blok komparycji zajął dodatkowe miejsce, wypychając §2 na kolejną stronę).
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 655.21, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 628.76, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 558.46, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 538.63, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 496.52, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 470.08, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 452.67, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §3 ust. 1 lit. f - powierzchnia budynku
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 717.15, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 717.15, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 716.64, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §7 Postanowienia końcowe - blok podpisów umowy głównej.
# DWIE linie "Zamawiający" (klient 1 i klient 2), JEDNA linia "Wykonawca" -
# zweryfikowane czytaniem tresci: drugi blok ma etykiete "Zamawiający" bez
# towarzyszacego "Wykonawca" obok. Kreski podpisu (pdftotext -bbox): zam1
# xMin=72.0/xMax=235.999663/yMax=308.304934, wyk xMin=360.0/xMax=521.223511/
# yMax=308.304934, zam2 xMin=72.0/xMax=235.999663/yMax=387.648194.
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 536.2, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 536.2, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 3, 75.0, 456.85, "tekst", maks_szerokosc=158.0),
)

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): Załącznik nr 1 - ARKUSZ USTALEŃ MONTAŻOWYCH - jak w
# mapie jednoosobowej PV (jeden arkusz, bez podziału 1a/1b), ale ze wspolnym
# naglowkiem "Zamawiajacy"/"Wykonawca" nad DWIEMA liniami podpisu
# Zamawiajacego (klient1 wyzej, klient2 nizej) i JEDNA linia Wykonawcy -
# zweryfikowane czytaniem tresci strony (jeden wspolny naglowek kolumny, nie
# powtorzony dla drugiego wiersza).
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("panel_moc_wp", 4, 223.9, 708.11, "tekst", maks_szerokosc=55.16),
	Pole("panel_szt", 4, 381.7, 708.11, "tekst", maks_szerokosc=57.93),
	Pole("moc_pv_kwp", 4, 186.09, 690.86, "tekst", maks_szerokosc=57.93),
	Pole("panel_producent_model", 4, 280.02, 673.61, "tekst", maks_szerokosc=227.5),
	Pole("panel_gwarancja_lat", 4, 249.46, 656.36, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_moc_kw", 4, 183.31, 621.86, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_szt", 4, 174.42, 604.61, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_producent_model", 4, 205.01, 587.37, "tekst", maks_szerokosc=230.27),
	Pole("inwerter_gwarancja_lat", 4, 250.57, 570.12, "tekst", maks_szerokosc=57.93),
	Pole("internet_wifi", 4, 118.95, 514.19, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 4, 173.93, 514.19, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 4, 251.14, 514.19, "kratka", wyrownanie="srodek"),
	Pole("moc_przylaczeniowa_kw", 4, 229.43, 492.5, "tekst", maks_szerokosc=85.73),
	Pole("fazy_1", 4, 121.72, 471.07, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 4, 157.83, 471.07, "kratka", wyrownanie="srodek"),
	Pole("montaz_dach", 4, 157.28, 445.2, "kratka", wyrownanie="srodek"),
	Pole("montaz_grunt", 4, 213.37, 445.2, "kratka", wyrownanie="srodek"),
	Pole("pokrycie_dachowe", 4, 268.9, 423.5, "tekst", maks_szerokosc=85.73),
	Pole("odgromowa_tak", 4, 182.29, 402.08, "kratka", wyrownanie="srodek"),
	Pole("odgromowa_nie", 4, 228.76, 402.08, "kratka", wyrownanie="srodek"),
	Pole("ppoz_tak", 4, 398.41, 358.95, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 4, 444.89, 358.95, "kratka", wyrownanie="srodek"),
	Pole("przekop_tak", 4, 165.06, 333.08, "kratka", wyrownanie="srodek"),
	Pole("przekop_mb", 4, 222.03, 332.57, "tekst", maks_szerokosc=38.48),
	Pole("przekop_nie", 4, 281.0, 333.08, "kratka", wyrownanie="srodek"),
	Pole("kabel_tak", 4, 161.18, 307.21, "kratka", wyrownanie="srodek"),
	Pole("kabel_mb", 4, 218.15, 306.7, "tekst", maks_szerokosc=38.48),
	Pole("kabel_nie", 4, 277.12, 307.21, "kratka", wyrownanie="srodek"),
	Pole("ist_pv_moc_inwertera_kw", 4, 167.2, 272.29, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 4, 232.76, 255.04, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 4, 170.01, 237.8, "tekst", maks_szerokosc=155.22),
	# Blok podpisow: wspolny naglowek "Zamawiajacy"/"Wykonawca", DWIE linie
	# Zamawiajacego. Kreski (pdftotext -bbox): zam1 xMin=72.0/xMax=235.999663/
	# yMax=711.92, wyk xMin=360.0/xMax=521.223511/yMax=711.92, zam2
	# xMin=72.0/xMax=235.999663/yMax=748.95.
	Pole("podpis_zamawiajacy", 4, 75.0, 132.58, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 132.58, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 4, 75.0, 95.55, "tekst", maks_szerokosc=158.0),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik nr 2 (zgody) i Załącznik nr 3 (oświadczenie
# o realizacji przed terminem odstąpienia) - JEDEN checkbox na oświadczenie
# (wspolny dla obu Zamawiajacych), ale DWIE osobne linie podpisu pod kazdym
# oswiadczeniem (klient1, klient2), bez Wykonawcy - zweryfikowane czytaniem
# tresci (jeden naglowek "Zamawiajacy" nad kazda para linii podpisu na tej
# stronie, jak w Zalaczniku 1). Kratki male (10x10pt, offset 2.0, rozmiar 8.0)
# jak w mapach jednoosobowych.
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 330.12, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Załącznik 2: podpis klienta 1, potem klienta 2.
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 5, 75.0, 528.26, "tekst", maks_szerokosc=155.22),
	# Załącznik 3: podpis klienta 1, potem klienta 2 (osobno, niżej na stronie).
	Pole("podpis_zamawiajacy", 5, 75.0, 184.44, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 5, 75.0, 110.39, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 8 (indeks 7): Załącznik nr 4 - klauzula RODO, linia podpisu klienta
# ("Zamawiający" nad kreską, "data i podpis" pod nią) x2 - klient1 wyzej,
# klient2 nizej, kazdy z WLASNYM naglowkiem "Zamawiajacy" (inaczej niz na
# str. 5/6, gdzie naglowek byl wspolny) - zweryfikowane czytaniem tresci.
# Druga linia uzywa `podpis_zamawiajacy_2` (zgodnie z briefem zadania), nie
# osobnego klucza RODO dla klienta 2 - kontekst nie definiuje takiego klucza.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 536.2, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 7, 75.0, 417.18, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 14 (indeks 13): Załącznik nr 7 - Pełnomocnictwo OSD, PIERWSZE
# (klient 1). Tekst niemal bit-identyczny z odpowiadającą stroną w mapie
# jednoosobowej PV (ten sam wzorzec Pełnomocnictwa), zmierzony tu niezaleznie.
# ---------------------------------------------------------------------------
_STRONA_14: tuple[Pole, ...] = (
	# "udzielone w dniu ___" - jak w wariancie jednoosobowym, świadomie
	# reużyty `data_zawarcia` (podpisywane tego samego dnia co umowa).
	Pole("data_zawarcia", 13, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	# "Ja, niżej podpisany/a ___," - podkreślenie sąsiaduje z przecinkiem bez
	# spacji; granica zmierzona granulacją znakową `pdfminer` (`LTChar`), żeby
	# wykluczyć szerokość samego przecinka z `maks_szerokosc` (xMax kreski bez
	# przecinka: 262.65, zweryfikowane osobno dla tej strony i dla str. 15).
	Pole("klient_imie_nazwisko", 13, 171.13, 681.66, "tekst", maks_szerokosc=88.52),
	Pole("klient_adres", 13, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 13, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	# Jedna linia podpisu - "Mocodawcy" (klient 1), BEZ Wykonawcy.
	Pole("podpis_zamawiajacy", 13, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 15 (indeks 14): Załącznik nr 7.1 - Pełnomocnictwo OSD, DRUGIE
# (klient 2). Tekst identyczny w ukladzie ze strona 14 (te same wspolrzedne
# co do 0,01 pt - zweryfikowane niezaleznie), ale wypelniany danymi drugiego
# Zamawiajacego (`klient2_*`) i drugim podpisem.
# ---------------------------------------------------------------------------
_STRONA_15: tuple[Pole, ...] = (
	Pole("data_zawarcia", 14, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient2_imie_nazwisko", 14, 171.13, 681.66, "tekst", maks_szerokosc=88.52),
	Pole("klient2_adres", 14, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient2_pesel", 14, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy_2", 14, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_PV2: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_3
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_8
	+ _STRONA_14
	+ _STRONA_15
)
"""Pełna mapa dla `crm/szablony/umowa_pv_podwojna.pdf`: 81 pozycji (wariant
jednoosobowy `MAPA_PV` ma 66) - roznica to drugi blok komparycji (5 pozycji),
drugie podpisy Zamawiajacego (na str. 4/5/6x2/8, razem 7 dodatkowych pozycji)
i drugie Pelnomocnictwo (5 pozycji, str. 15) = 66 + 5 + 7 + 5 - 2 (dwie
pozycje `podpis_zamawiajacy` na str. 6, ktore jednoosobowa mapa juz liczyla
jako 2, wiec przyrost stamtad to tylko +2 `podpis_zamawiajacy_2`, nie +4) =
81. Generator wywolujacy te mape (przyszle issue #167) ma narysowac wartosc
we WSZYSTKICH pozycjach danego klucza, nie tylko w pierwszej."""

# Strony 7, 9, 10, 11, 12, 13 (indeksy 6, 8, 9, 10, 11, 12) nie zawierają
# żadnej pozycji z kontekstu `zbuduj_kontekst`, analogicznie do mapy
# jednoosobowej PV:
#
# - Str. 7 (idx 6): Załącznik nr 4 - początek klauzuli RODO (statyczny tekst,
#   linia podpisu jest na kolejnej stronie, str. 8/idx 7).
# - Str. 9 (idx 8): Załącznik nr 5 - Pouczenie o prawie do odstąpienia
#   (statyczne, informacyjne, bez pól).
# - Str. 10 (idx 9): wzór FORMULARZA ODSTĄPIENIA - świadomie BEZ pozycji, jak
#   w mapach jednoosobowych: pusty formularz do ewentualnego wypełnienia przez
#   klienta W PRZYSZŁOŚCI, tylko gdy faktycznie odstępuje od umowy.
# - Str. 11 (idx 10): Załącznik nr 6 - Protokół odbioru Instalacji
#   Fotowoltaicznej, str. 1 - CAŁKOWICIE pusty (decyzja produktowa 2026-08-12,
#   patrz `crm/volteo_umowa_mapa.py`), wypełnia go ręcznie instalator.
# - Str. 12 (idx 11): Protokół odbioru, str. 2 - listy szkoleniowe/zdjęć +
#   linie podpisu klienta/instalatora, wypełniane ręcznie przy montażu.
# - Str. 13 (idx 12): protokół pomiarów elektrycznych - wypełniany przez
#   instalatora przy montażu.
#
# Żadna z tych stron nie ma bloku podpisów wypełnianego przez generator, z
# tych samych powodów co w mapach jednoosobowych.


def pozycje_dla_pv2(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_PV2` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_PV2 if pole.klucz == klucz)


def klucze_w_mapie_pv2() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_PV2` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_PV2)
