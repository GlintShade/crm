# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: Rozbudowa instalacji PV i/lub magazynu energii,
`crm/szablony/umowa_rozbudowa.pdf`.

Plik zrodlowy wzoru: `Umowa Rozbudowa ProEnergy - 06.10.2026-3.pdf` (ostateczny wzor
z 06.10.2026, b69), A4 596x842 pt, 17 stron.

POCHODZENIE WSPOLRZEDNYCH: pomiar OD ZERA, 2026-10-10 (b69, chunk U2k, issue ops#249),
narzedziem `ops/narzedzia/umowa-mapa-pomiar.py` z repo `proenergy-crm-ops`
(deklaracja `ops/narzedzia/deklaracje/umowa_rozbudowa.py`) na pliku o SHA-256 ponizej.
Zadna wartosc nie pochodzi z map siostrzanych ani ze starej wersji wzoru. Konwencje
ukladu (`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkresleniu, kratek i
komorek tabeli): naglowek `crm/volteo_umowa_mapa.py`. Wynik przejrzany wzrokowo na
renderze `--sprawdz` (pdftoppm -r 110) strona po stronie.

POLITYKA (klucze na strony):
- idx 0: komparycja, adres montazu, rodzaj budynku; idx 1: §2 (kratki `fin_*`
  mapowane 1:1: Kredyt 100% / Kredyt z wkladem / Przelew); idx 2: powierzchnia;
- podpisy: Zamawiajacy i Wykonawca w umowie glownej (idx 3) oraz w Zal. 1a i 1b
  (oba na idx 4); w Zal. 2, 3 (idx 5), RODO (idx 7) i pelnomocnictwie (idx 16) tylko
  linia Zamawiajacego; `data_zawarcia` reuzywana w "udzielone w dniu" pelnomocnictwa;
- BEZ pozycji (celowo): idx 6 (RODO czesc 1), idx 8 (pouczenie o odstapieniu), idx 9
  (formularz odstapienia), idx 10 do 15 (protokoly odbioru PV i magazynu, listy,
  protokoly pomiarow): wypelnia je instalator albo klient po montazu;
- osobliwosci wzoru: brak arkusza PV/ME (inwerter, panele, internet, fazy, moc
  przylaczeniowa, dach/grunt, odgromowa, przekop, kabel), brak OSD i typu falownika,
  brak rubryki "producent istniejacego falownika" i "moc istniejacego magazynu kW";
  kratki "Mikroinwertery TAK/NIE" na idx 4 niosa `roz_mikro_tak`/`roz_mikro_nie`,
  rubryki `roz_*` leza WYLACZNIE w Zal. 1a/1b.

BEZPIECZNIK ZMIANY SZABLONU: generator sprawdza SHA-256 pliku wzgledem
`SHA256_SZABLONU_ROZ` i odmawia renderu przy niezgodnosci.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_ROZ: str = "6cd50df2b3c8b7e56f16ed989102d8e1b24038446a6ce9080fc677aafc665eb5"
"""SHA-256 pliku `crm/szablony/umowa_rozbudowa.pdf`, policzone na pliku w repo."""

LICZBA_STRON_ROZ: int = 17
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""


# ---------------------------------------------------------------------------
# Strona 1: komparycja (tabela danych klienta, numer, data zawarcia), adres miejsca
# montazu (§1 ust. 1) i rodzaj budynku (§1 ust. 2).
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 658.48, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 634.01, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 609.53, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 585.06, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 560.58, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 206.36, 721.51, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 697.43, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 111.0, 331.4, "tekst", maks_szerokosc=385.93),
	Pole("budynek_wielorodzinny", 0, 115.5, 287.55, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 267.72, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2: §2 wynagrodzenie netto/brutto, trzy kratki platnosci (Kredyt 100% / Kredyt
# z wkladem wlasnym / Przelew), wklad wlasny i kwota kredytu. Trzecia kratka "Przelew"
# niesie klucz `fin_gotowka` (literal bazy `Gotowka 100%`, etykieta wzoru to przelew).
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 734.55, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 708.11, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 637.81, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 617.97, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 575.87, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 549.42, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 532.01, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 3: §3 ust. 1 lit. g, kratki powierzchni budynku (do 300 m2 / ponad 300 m2) i
# powierzchnia w m2 na kresce za "wynosi".
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
	Pole("pow_do_300", 2, 115.5, 703.93, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 2, 242.73, 703.93, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 2, 379.34, 703.42, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4: blok podpisow umowy glownej (Zamawiajacy po lewej, Wykonawca po prawej).
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 399.18, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 399.18, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5: Zalacznik 1a (rozbudowa PV) i Zalacznik 1b (rozbudowa magazynu) na JEDNEJ
# stronie. 1a: liczba dodatkowych modulow, mikroinwertery TAK/NIE, moc istniejacej
# instalacji, uzgodnienia p.poz TAK/NIE, podpisy obu stron. 1b: liczba dodatkowych
# modulow magazynu, pojemnosc istniejacego magazynu, podpisy obu stron. Kreski pol
# danych wpadaja do kolumn lewa/prawa razem z liniami podpisu, wiec podpisy 1a to
# kreski n=1, a 1b n=3 (zmierzone wg kolejnosci z gory).
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("roz_panele_szt", 4, 314.46, 715.33, "tekst", maks_szerokosc=69.05),
	Pole("roz_mikro_tak", 4, 150.04, 693.9, "kratka", wyrownanie="srodek"),
	Pole("roz_mikro_nie", 4, 196.51, 693.9, "kratka", wyrownanie="srodek"),
	Pole("roz_ist_pv_moc_kwp", 4, 284.99, 672.21, "tekst", maks_szerokosc=69.05),
	Pole("ppoz_tak", 4, 253.97, 616.28, "kratka", wyrownanie="srodek"),
	Pole("ppoz_nie", 4, 300.44, 616.28, "kratka", wyrownanie="srodek"),
	Pole("podpis_zamawiajacy", 4, 75.0, 482.47, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 482.47, "tekst", maks_szerokosc=155.22),
	Pole("roz_bateria_szt", 4, 320.02, 304.56, "tekst", maks_szerokosc=69.05),
	Pole("roz_ist_me_kwh", 4, 296.68, 287.32, "tekst", maks_szerokosc=69.05),
	Pole("podpis_zamawiajacy", 4, 75.0, 140.7, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 140.7, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6: Zalacznik 2 (zgody telefon/promocja, podpis Zamawiajacego) i Zalacznik 3
# (wczesniejsza realizacja, podpis Zamawiajacego); obie linie podpisu tylko Zamawiajacy.
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 261.35, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 5, 75.0, 115.68, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 8: koniec Zalacznika 4 (RODO), data i podpis Zamawiajacego.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 17: Zalacznik 8 (pelnomocnictwo OSD): data udzielenia, dane Mocodawcy i jego
# podpis (prawa kolumna; tylko linia Zamawiajacego).
# ---------------------------------------------------------------------------
_STRONA_17: tuple[Pole, ...] = (
	Pole("data_zawarcia", 16, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	Pole("klient_imie_nazwisko", 16, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 16, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 16, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	Pole("podpis_zamawiajacy", 16, 365.05, 245.27, "tekst", maks_szerokosc=155.22),
)

MAPA_ROZ: tuple[Pole, ...] = (
	*_STRONA_1,
	*_STRONA_2,
	*_STRONA_3,
	*_STRONA_4,
	*_STRONA_5,
	*_STRONA_6,
	*_STRONA_8,
	*_STRONA_17,
)
"""Wszystkie pozycje mapy wzoru ROZ, strona po stronie."""
