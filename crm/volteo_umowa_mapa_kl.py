# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: Klimatyzacja, `crm/szablony/umowa_klimatyzacja.pdf`.

Plik zrodlowy wzoru: `Umowa Klimatyzacja ProEnergy - 09.10.2026.pdf` (wzor dostarczony przez CEO 2026-10-09,
b69, dogrywka chunka U1), A4, 12 stron.

POCHODZENIE WSPOLRZEDNYCH: pomiar OD ZERA, 2026-10-10 (b69, chunk U2l, issue ops#256),
narzedziem `ops/narzedzia/umowa-mapa-pomiar.py` z repo `proenergy-crm-ops`
(deklaracja `ops/narzedzia/deklaracje/umowa_klimatyzacja.py`) na pliku o SHA-256 ponizej.
Zadna wartosc nie pochodzi z map siostrzanych ani ze starej wersji wzoru. Konwencje ukladu
(`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkresleniu, kratek i komorek tabeli):
naglowek `crm/volteo_umowa_mapa.py`. Wynik przejrzany wzrokowo na renderze `--sprawdz`
(pdftoppm -r 110) strona po stronie.

STRUKTURA WZORU (12 stron): bez pelnomocnictwa OSD; Zal. 1 klimatyzacja; Zal. 2 i 3 zgody;
Zal. 4 RODO; Zal. 5 pouczenie i formularz odstapienia; Zal. 6 protokol odbioru.

POLITYKA (klucze na strony): idx 0 komparycja, adres, budynek; idx 1 §2 (netto, brutto, kratki
`fin_*`, wklad, kredyt) i §3 f (powierzchnia); idx 3 podpisy umowy glownej; idx 4 Zal. 1
(`klima_rodzaj`, `klima_moc_kw`, podpisy obu stron); idx 5 Zal. 2 i 3 (zgody, dwa podpisy
Zamawiajacego); idx 7 koniec RODO (`rodo_data_imie_nazwisko`). BEZ pozycji (celowo): idx 2
(§3 do §7), idx 6 (RODO czesc 1), idx 8 (pouczenie o odstapieniu), idx 9 (formularz
odstapienia), idx 10 i 11 (protokol odbioru klimatyzacji z lista instalatora): wypelnia je
instalator albo klient po montazu. Osobliwosci: wzor NIE ma pelnomocnictwa, wiec zadna pozycja
nie lezy na ostatniej stronie; powierzchnia (§3 ust. 1 f) lezy na idx 1, nie 2; Zal. 1 nie ma
rubryki modelu (`klima_model` bez pozycji).

BEZPIECZNIK ZMIANY SZABLONU: generator sprawdza SHA-256 pliku wzgledem
`SHA256_SZABLONU_KL` i odmawia renderu przy niezgodnosci.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_KL: str = "3b688e43f36ca2ac7691414748781e29c36472c270d41dc3b1a6b23776053791"
"""SHA-256 pliku `crm/szablony/umowa_klimatyzacja.pdf`, policzone na pliku w repo."""

LICZBA_STRON_KL: int = 12
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

# ---------------------------------------------------------------------------
# Strona 1 (idx 0): komparycja (tabela danych klienta), numer i data umowy, adres miejsca montazu
# (§1 ust. 1, jedyna gola kreska pod "pod adresem") i rodzaj budynku (§1 ust. 2).
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 666.55, "tekst", maks_szerokosc=342.0),
	Pole("klient_adres", 0, 177.5, 642.07, "tekst", maks_szerokosc=342.0),
	Pole("klient_pesel", 0, 177.5, 617.6, "tekst", maks_szerokosc=342.0),
	Pole("klient_telefon", 0, 177.5, 593.12, "tekst", maks_szerokosc=342.0),
	Pole("klient_email", 0, 177.5, 568.65, "tekst", maks_szerokosc=342.0),
	Pole("umowa_nr", 0, 210.11, 735.42, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 701.49, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 111.0, 353.57, "tekst", maks_szerokosc=385.93),
	Pole("budynek_wielorodzinny", 0, 115.5, 309.72, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 289.88, "kratka", wyrownanie="srodek"),
)

# ---------------------------------------------------------------------------
# Strona 2 (idx 1): §2 wynagrodzenie netto i brutto (dwie kreski), opcje finansowania (kratki
#  1:1: Kredyt 100% / Kredyt z wkladem / Przelew, kwoty wkladu i kredytu) oraz §3 ust. 1 lit. f
# (powierzchnia do 300 m2 albo wiecej, z wartoscia).
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("wynagrodzenie_netto", 1, 113.78, 708.11, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 1, 113.78, 681.66, "tekst", maks_szerokosc=155.22),
	Pole("fin_kredyt_100", 1, 115.5, 611.36, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 591.52, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 549.42, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 522.97, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 505.57, "kratka", wyrownanie="srodek"),
	Pole("pow_do_300", 1, 115.5, 89.02, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 1, 242.73, 89.02, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 1, 379.34, 88.51, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (idx 3): podpisy umowy glownej, Zamawiajacy (lewa kolumna) i Wykonawca (prawa).
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 456.85, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 456.85, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5 (idx 4): Zalacznik 1 (arkusz ustalen montazowych, klimatyzacja): rodzaj i moc
# klimatyzacji oraz podpisy obu stron.
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
	Pole("klima_rodzaj", 4, 165.55, 711.56, "tekst", maks_szerokosc=227.5),
	Pole("klima_moc_kw", 4, 177.18, 687.41, "tekst", maks_szerokosc=227.5),
	Pole("podpis_zamawiajacy", 4, 75.0, 624.16, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 624.16, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6 (idx 5): Zalaczniki 2 i 3 (zgody): trzy male kratki zgod (10x10 pt) i dwie osobne linie
# podpisu Zamawiajacego (bez Wykonawcy).
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 8 (idx 7): koniec Zalacznika 4 (RODO), linia "data i podpis" Zamawiajacego.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
)

MAPA_KL: tuple[Pole, ...] = (
	*_STRONA_1,
	*_STRONA_2,
	*_STRONA_4,
	*_STRONA_5,
	*_STRONA_6,
	*_STRONA_8,
)
"""Wszystkie pozycje mapy wzoru KL, strona po stronie."""
