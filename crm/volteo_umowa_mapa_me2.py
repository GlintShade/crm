# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant PODWÓJNY (dwóch Zamawiających, np. małżonkowie), „ME” (magazyn
energii, sprzedaż i montaż bez fotowoltaiki), `crm/szablony/umowa_me_podwojna.pdf`.

Zmierzona w issue #166, wzorowana STRUKTURALNIE na `crm/volteo_umowa_mapa_me.py`
(nazwy kluczy, rodzaje pol, konwencje przeliczen) - kazda wartosc liczbowa
ponizej jest zmierzona OD ZERA na tym pliku, zgodnie z zasada tego zadania:
zaden `x`/`y`/`maks_szerokosc` nie jest skopiowany z mapy jednoosobowej.

POMIAR: 2026-09-23, `pdftotext -bbox-layout crm/szablony/umowa_me_podwojna.pdf`
plus `pdfminer.six` (`LTLine` dla kreski dzielacej kolumny obu tabel
komparycji, `LTChar` na Pelnomocnictwie, gdzie podkreslenie „Ja, nizej
podpisany/a ___," sklejone jest z przecinkiem bez spacji) - identyczna
metodologia jak `crm/volteo_umowa_mapa_pv2.py` (patrz jego naglowek dla
pelnego opisu konwencji i rdzenia skryptu pomiarowego, `pv2_measure.py`/
`me2_measure.py`, zapisanych w scratchpadzie zadania). Zadna wartosc nie jest
przepisana recznie ani wyliczona "w pamieci" - kazda linia `Pole(...)` ponizej
jest bezposrednim wyjsciem skryptu.

UKLAD WSPOLRZEDNYCH, KONWENCJE PRZELICZEN I ZASADA DWOCH OSOB - identyczne z
`crm/volteo_umowa_mapa_pv2.py` (patrz jego naglowek), nie powtarzane tu w
pelni. W skrocie: `y_reportlab = 842 - y_od_gory`; tekst na podkresleniu
`x=xMin+3, y=842-yMax+2.5, maks=szerokosc-6`; kratka standardowa (15x15pt)
`y=842-yMax+3.0`; kratka mala (10x10pt, strona zgod) `y=842-yMax+2.0,
rozmiar=8.0`; komorka tabeli `x=kreska_LTLine+6, y=842-yMax(etykiety)`.
`klient2_*` i `podpis_zamawiajacy_2` sa jedynym dozwolonym dodatkiem kluczy
(6 razem), reszta jest identyczna nazewniczo z `crm/volteo_umowa_mapa_me.py`.
Kolumny podpisu (Zamawiajacy vs Wykonawca) rozroznione po wspolrzednej `x`
(< 300pt = Zamawiajacy, >= 300pt = Wykonawca), NIE po kolejnosci w strumieniu
`pdftotext` (zweryfikowane niestala miedzy stronami tego samego dokumentu -
patrz uzasadnienie w `crm/volteo_umowa_mapa_pv2.py`).

TEN SZABLON NIE MA pola `inwerter_szt` (Ilosc inwerterow) - dokladnie jak
wariant jednoosobowy ME: magazyn energii montowany jest zawsze z jednym
falownikiem/hybryda, wiec pole jest nieobecne w tresci (zweryfikowane
czytaniem strony 5 - etykieta "Ilosc inwerterow (szt)" po prostu tam nie ma).

BEZPIECZNIK ZMIANY SZABLONU: mapa poniżej obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji oryginału. Generator PDF-u ma sprawdzić sumę SHA-256 pliku
wejściowego względem `SHA256_SZABLONU_ME2` przed użyciem tej mapy i przerwać
z czytelnym komunikatem przy niezgodności.

Rejestracja tego wariantu w `crm.volteo_umowa_render.SZABLONY` jest zakresem
OSOBNEGO, pozniejszego zadania (issue #167) - nie jest zakresem tego pliku.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_ME2: str = "df88a28fd3a1c68378d02c3bd9d610528779d2d732900b42fc41f77d992fa51d"
"""SHA-256 pliku `PODWÓJNA Umowa ME ProEnergy - 28.07.2026.pdf` (A4, 596x842 pt,
15 stron), policzone `shasum -a 256` na pliku W REPO (`crm/szablony/umowa_me_podwojna.pdf`),
przejęte bez zmian z poprzedniej wersji tego modułu (skorupa, issue #165) - ten
sam plik, ta sama suma. Generator PDF-u (przyszłe issue #167) ma sprawdzić tę
sumę przed użyciem `MAPA_ME2` i przerwać z czytelnym komunikatem przy
niezgodności."""

LICZBA_STRON_ME2: int = 15
"""Liczba stron oryginału, zgodna z `pdfinfo`. Jedna strona więcej niż wariant
jednoosobowy (`LICZBA_STRON_ME` = 14) - dodatkowe dane drugiego Zamawiającego
(drugie Pełnomocnictwo, str. 15)."""

# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja x2 (rozdzielone slowem "oraz") + S1
# Przedmiot umowy. Dwie niezalezne tabele danych klienta (5 wierszy kazda),
# pionowa kreska dzielaca kolumny (pdfminer LTLine, zbadana niezaleznie):
# x=171.5, prawa krawedz x=522.5 - identycznie jak w PV2 (ten sam wzorzec
# strony 1, wspolny dla obu wariantow podwojnych, zmierzony tu osobno).
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
	Pole("adres_montazu", 0, 111.0, 217.22, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 173.37, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 153.54, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §2 Wynagrodzenie - na osobnej stronie od komparycji.
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 628.76, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 532.01, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 512.18, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 470.08, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 443.63, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 426.22, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §3 ust. 1 lit. g - powierzchnia budynku
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 624.58, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 624.58, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 624.07, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §7 Postanowienia końcowe - blok podpisów umowy głównej.
# DWIE linie "Zamawiający" (klient 1, klient 2), JEDNA linia "Wykonawca" -
# zweryfikowane czytaniem tresci, identycznie jak w PV2. Kreski (pdftotext
# -bbox): zam1 xMin=72.0/xMax=236.0/yMax=519.89, wyk xMin=360.0/xMax=521.22/
# yMax=519.89, zam2 xMin=72.0/xMax=236.0/yMax=572.78.
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 324.61, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 324.61, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 3, 75.0, 271.72, "tekst", maks_szerokosc=158.0),
)

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): Załącznik nr 1 - ARKUSZ USTALEŃ MONTAŻOWYCH, jak w
# wariancie jednoosobowym ME (falownik/bateria na jednej stronie, bez podziału
# 1a/1b, bez `inwerter_szt` - patrz uzasadnienie w naglowku modulu). Wspolny
# naglowek "Zamawiajacy"/"Wykonawca" nad DWIEMA liniami podpisu Zamawiajacego
# i JEDNA linia Wykonawcy (identycznie jak Zalacznik 1 w PV2) - zweryfikowane
# czytaniem tresci strony.
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("inwerter_producent_model", 4, 205.01, 708.11, "tekst", maks_szerokosc=244.17),
	Pole("inwerter_moc_kw", 4, 167.2, 690.86, "tekst", maks_szerokosc=57.93),
	Pole("inwerter_gwarancja_lat", 4, 250.57, 673.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_producent_model", 4, 191.13, 639.11, "tekst", maks_szerokosc=246.95),
	Pole("bateria_moc_kw", 4, 153.31, 621.86, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_jedn_kwh", 4, 293.9, 604.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_szt", 4, 444.49, 604.61, "tekst", maks_szerokosc=55.16),
	Pole("bateria_pojemnosc_lacznie_kwh", 4, 272.24, 587.37, "tekst", maks_szerokosc=57.93),
	Pole("bateria_gwarancja_lat", 4, 236.69, 570.12, "tekst", maks_szerokosc=57.93),
	Pole("moc_przylaczeniowa_kw", 4, 229.43, 509.75, "tekst", maks_szerokosc=85.73),
	Pole("ist_pv_moc_inwertera_kw", 4, 167.2, 426.95, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 4, 232.76, 409.71, "tekst", maks_szerokosc=55.16),
	Pole("ist_pv_producent_inwertera", 4, 170.01, 392.46, "tekst", maks_szerokosc=155.22),
	# Blok podpisow: wspolny naglowek, DWIE linie Zamawiajacego. Kreski
	# (pdftotext -bbox): zam1 xMin=72.0/xMax=236.0/yMax=574.51, wyk
	# xMin=360.0/xMax=521.22/yMax=574.51, zam2 xMin=72.0/xMax=236.0/yMax=627.4.
	Pole("podpis_zamawiajacy", 4, 75.0, 269.99, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 269.99, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 4, 75.0, 217.1, "tekst", maks_szerokosc=158.0),
	Pole("internet_wifi", 4, 118.95, 531.44, "kratka", wyrownanie="srodek"),
	Pole("internet_kablowy", 4, 173.93, 531.44, "kratka", wyrownanie="srodek"),
	Pole("internet_brak", 4, 251.14, 531.44, "kratka", wyrownanie="srodek"),
	Pole("fazy_1", 4, 121.72, 488.32, "kratka", wyrownanie="srodek"),
	Pole("fazy_3", 4, 157.83, 488.32, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik nr 2 (zgody) i Załącznik nr 3 (oświadczenie
# o realizacji przed terminem odstąpienia) - JEDEN checkbox na oświadczenie,
# DWIE osobne linie podpisu (klient1, klient2) pod kazdym, bez Wykonawcy -
# identycznie jak w PV2. Kratki male (10x10pt, offset 2.0, rozmiar 8.0).
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 695.09, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 655.42, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 356.56, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Załącznik 2: podpis klienta 1, potem klienta 2.
	Pole("podpis_zamawiajacy", 5, 75.0, 575.87, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 5, 75.0, 528.26, "tekst", maks_szerokosc=155.22),
	# Załącznik 3: podpis klienta 1, potem klienta 2 (osobno, niżej na stronie).
	Pole("podpis_zamawiajacy", 5, 75.0, 210.89, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 8 (indeks 7): Załącznik nr 4 - klauzula RODO, linia podpisu klienta
# ("Zamawiający" / "data i podpis") x2 - klient1 wyzej, klient2 nizej, kazdy
# z WLASNYM naglowkiem "Zamawiajacy" - zweryfikowane czytaniem tresci.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 575.87, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy_2", 7, 75.0, 480.65, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 14 (indeks 13): Załącznik nr 7 - Pełnomocnictwo OSD, PIERWSZE
# (klient 1). Tekst niemal bit-identyczny z odpowiadającą stroną w PV2 (ten
# sam wzorzec Pełnomocnictwa, wklejony bez zmian w oba warianty PODWÓJNE),
# zmierzony tu niezaleznie.
# ---------------------------------------------------------------------------
_STRONA_14: tuple[Pole, ...] = (
	# "udzielone w dniu ___" - świadomie reużyty `data_zawarcia`.
	Pole("data_zawarcia", 13, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	# "Ja, niżej podpisany/a ___," - granica zmierzona granulacją znakową
	# `pdfminer` (`LTChar`), żeby wykluczyć doklejony bez spacji przecinek
	# (xMax kreski bez przecinka: 262.65, jak w PV2 - ten sam wzorzec tekstu).
	Pole("klient_imie_nazwisko", 13, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 13, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 13, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	# Jedna linia podpisu - "Mocodawcy" (klient 1), BEZ Wykonawcy.
	Pole("podpis_zamawiajacy", 13, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 15 (indeks 14): Załącznik nr 7.1 - Pełnomocnictwo OSD, DRUGIE
# (klient 2). Uklad identyczny ze strona 14 (te same wspolrzedne co do
# 0,01 pt - zweryfikowane niezaleznie), wypelniany danymi `klient2_*`.
# ---------------------------------------------------------------------------
_STRONA_15: tuple[Pole, ...] = (
	Pole("data_zawarcia", 14, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient2_imie_nazwisko", 14, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient2_adres", 14, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient2_pesel", 14, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy_2", 14, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_ME2: tuple[Pole, ...] = (
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
"""Pełna mapa dla `crm/szablony/umowa_me_podwojna.pdf`: 68 pozycji (wariant
jednoosobowy `MAPA_ME` ma 53) - roznica to drugi blok komparycji (5 pozycji),
drugie podpisy Zamawiajacego (str. 4/5/6x2/8, razem 6 dodatkowych pozycji) i
drugie Pelnomocnictwo (5 pozycji, str. 15) = 53 + 5 + 6 + 5 - 1 = 68 (jedna
korekta: `podpis_wykonawca` na str. 5 jednoosobowej mapy juz sie liczyl, wiec
przyrost z tamtej strony to tylko +1 `podpis_zamawiajacy_2`, nie +2, stad
suma czystych dodatkow to 15, nie 16). Generator wywolujacy te mape (przyszle
issue #167) ma narysowac wartosc we WSZYSTKICH pozycjach danego klucza, nie
tylko w pierwszej."""

# Strony 7, 9, 10, 11, 12, 13 (indeksy 6, 8, 9, 10, 11, 12) nie zawierają
# żadnej pozycji z kontekstu `zbuduj_kontekst`, analogicznie do mapy
# jednoosobowej ME:
#
# - Str. 7 (idx 6): Załącznik nr 4 - początek klauzuli RODO (statyczny tekst).
# - Str. 9 (idx 8): Załącznik nr 5 - Pouczenie o prawie do odstąpienia
#   (statyczne, informacyjne, bez pól).
# - Str. 10 (idx 9): wzór FORMULARZA ODSTĄPIENIA - świadomie BEZ pozycji.
# - Str. 11 (idx 10): Załącznik nr 6 - Protokół odbioru magazynu energii,
#   str. 1 - CAŁKOWICIE pusty (decyzja produktowa 2026-08-12).
# - Str. 12 (idx 11): Protokół odbioru, str. 2 - listy szkoleniowe/zdjęć +
#   linie podpisu klienta/instalatora, wypełniane ręcznie przy montażu.
# - Str. 13 (idx 12): protokół pomiarów elektrycznych magazynu - wypełniany
#   przez instalatora przy montażu.


def pozycje_dla_me2(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_ME2` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_ME2 if pole.klucz == klucz)


def klucze_w_mapie_me2() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_ME2` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_ME2)
