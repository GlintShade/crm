# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF —
wariant WYŁĄCZNIE fotowoltaiczny (bez magazynu energii), `crm/szablony/umowa_pv.pdf`.

Ten moduł jest odpowiednikiem `crm/volteo_umowa_mapa.py` (mapa PV+ME) dla
DRUGIEGO, krótszego szablonu — 14 stron zamiast 18, bez Załącznika 1b
(magazyn energii) i bez osobnego protokołu odbioru magazynu. Konwencje
pomiarowe, układ współrzędnych i styl są IDENTYCZNE jak w tamtym module —
przeczytaj jego docstring, jeśli edytujesz tę mapę. W skrócie:

UKŁAD WSPÓŁRZĘDNYCH: ``pdftotext -bbox`` podaje ``yMin``/``yMax`` liczone OD
GÓRY strony. ``reportlab`` rysuje w układzie liczonym OD DOŁU strony. Każda
wartość ``y`` zapisana w tym pliku jest już PRZELICZONA: ``y_reportlab =
842 - y_od_gory``. Strona ma wymiary 596x842 pt (A4).

Każda wartość w ``MAPA_PV`` została policzona SKRYPTEM (`pdftotext -bbox`
dla tekstu i podkreśleń; ekstrakcja wektorowych linii tabeli przez
`pdfminer.six` — `LTLine` — dla granicy kolumn tabeli danych klienta na
stronie 1, gdzie nie ma osobnego glifu do zmierzenia; granulacja znakowa
`pdfminer` (`LTChar`) dla jednego pola, gdzie podkreślenie sąsiaduje bez
spacji z przecinkiem i `pdftotext` scaliłby oba w jedno „słowo") — żadna
wartość nie jest przepisana ręcznie ani zgadnięta. Zmierzone 2026-08-12.

Dla pól z podkreśleniem: ``x = xMin(kreski) + 3``, ``y = 842 - yMax(kreski)
+ 2.5``, ``maks_szerokosc = szerokość(kreski) - 6``. Dla kratek (``☐``/``▢``)
standardowych (~15x15 pt): ``x`` = środek poziomy glifu, ``y = 842 -
yMax(glifu) + 3.0``. Dla małych kratek (~10x10 pt, strona zgód — Załącznik
2/3): ten sam wzór z offsetem ``+2.0`` i ``rozmiar=8.0``. Wszystkie kratki w
tym szablonie (w tym te na stronie zgód) są emitowane przez `pdftotext` jako
zwykłe słowa — inaczej niż w mapie PV+ME, gdzie kratki strony zgód trzeba
było mierzyć ze strumienia treści PDF; tu taki obejście nie było potrzebne.
Dla komórki tabeli (dane klienta, strona 1): ``x`` = zmierzona wektorowo
(`pdfminer` `LTLine`) współrzędna pionowej kreski dzielącej kolumny +6 pt
wcięcia, ``y = 842 - yMax(etykiety)`` bez korekty 2,5 pt (jak w tabeli mapy
PV+ME), ``maks_szerokosc`` = prawa krawędź tabeli - ``x``.

Wiele pozycji w tym pliku ma DOKŁADNIE te same ``x``/``maks_szerokosc`` co
odpowiadające pola w `MAPA` (PV+ME) — oba szablony dzielą tę samą stopkę,
blok podpisów, sekcję arkusza PV i stronę pełnomocnictwa, tylko wygenerowane
z osobnego pliku źródłowego (Google Docs → PDF) o innym całkowitym układzie
akapitów, stąd różne ``y``. Tam gdzie się różnią o więcej niż 2 pt, przy
danym polu jest komentarz z wyjaśnieniem (np. `ist_pv_producent_inwertera` —
dłuższa linia podkreślenia w tym pliku niż w PV+ME).

BEZPIECZNIK ZMIANY SZABLONU: mapa poniżej obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji oryginału. Generator PDF-u ma sprawdzić sumę SHA-256 pliku
wejściowego względem ``SHA256_SZABLONU_PV`` przed użyciem tej mapy i
przerwać z czytelnym komunikatem przy niezgodności.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PV: str = "cc2685726d7d7245940e6ae0caec9e3c2e5c7b26140ff1ca313cbb251e8494a3"
"""SHA-256 pliku `Umowa PV ProEnergy - 28.07.2026.pdf` (A4, 596x842 pt, 14 stron,
bez pól formularza), policzone `shasum -a 256` na oryginale dostarczonym do tego
zadania (2026-08-12) i zweryfikowane ponownie po skopiowaniu do
`crm/szablony/umowa_pv.pdf`. Mapa `MAPA_PV` poniżej jest skalibrowana WYŁĄCZNIE
dla tego dokładnego pliku — każda zmiana szablonu (nawet kosmetyczna) unieważnia
współrzędne."""

LICZBA_STRON_PV: int = 14
"""Liczba stron oryginału, zgodna z `pdfinfo`. Używana przez testy/generator do
sprawdzenia, że żadna pozycja w mapie nie wskazuje strony poza dokumentem."""

# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): komparycja (dane klienta, adres montażu, typ budynku)
# oraz — w odróżnieniu od PV+ME, gdzie to osobna strona — §2 Wynagrodzenie na
# tej samej stronie (krótszy szablon mieści oba paragrafy razem).
#
# Tabela danych klienta: 5 wierszy (Imię i nazwisko / Adres / PESEL / Telefon
# / Adres e-mail), 2 kolumny. Pionowa kreska dzieląca kolumny zmierzona
# WEKTOROWO (`pdfminer` `LTLine`, nie pikselowo z rastra): x=171.5, prawa
# krawędź tabeli x=522.5, lewa x=72.5 (nieużywana). Poziome kreski wierszy
# (`LTLine`, y w układzie reportlab wprost, bez przeliczenia): 684.5, 659.5,
# 635.5, 610.5, 586.5, 561.5 — potwierdzają przypisanie etykiet do wierszy.
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
	Pole("klient_imie_nazwisko", 0, 177.5, 666.56, "tekst", maks_szerokosc=345.0),
	Pole("klient_adres", 0, 177.5, 642.08, "tekst", maks_szerokosc=345.0),
	Pole("klient_pesel", 0, 177.5, 617.6, "tekst", maks_szerokosc=345.0),
	Pole("klient_telefon", 0, 177.5, 593.12, "tekst", maks_szerokosc=345.0),
	Pole("klient_email", 0, 177.5, 568.65, "tekst", maks_szerokosc=345.0),
	Pole("umowa_nr", 0, 210.11, 735.42, "tekst", maks_szerokosc=194.21),
	Pole("data_zawarcia", 0, 135.56, 701.49, "tekst", maks_szerokosc=88.51),
	Pole("adres_montazu", 0, 110.25, 353.57, "tekst", maks_szerokosc=383.16),
	Pole("budynek_wielorodzinny", 0, 115.5, 309.72, "kratka", wyrownanie="srodek"),
	Pole("budynek_jednorodzinny", 0, 115.5, 289.88, "kratka", wyrownanie="srodek"),
	# §2 Wynagrodzenie — na tej samej stronie, na samym dole (ostatnia treść
	# przed stopką, patrz komentarz modułu wyżej).
	Pole("wynagrodzenie_netto", 0, 113.78, 102.31, "tekst", maks_szerokosc=155.22),
	Pole("wynagrodzenie_brutto", 0, 113.78, 75.87, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §2 cd. (finansowanie) i §3 ust. 1 lit. f (powierzchnia
# budynku) — w tym szablonie obie sekcje mieszczą się na jednej stronie,
# inaczej niż w PV+ME, gdzie finansowanie i powierzchnia są rozdzielone.
# Pole powierzchni jest tu też inaczej sformułowane niż w PV+ME: „☐ nie
# przekracza 300m2 / ☐ przekracza 300m2 i wynosi ___ m2" — wszystko w jednej
# linii, nie w osobnym akapicie.
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
	Pole("fin_kredyt_100", 1, 115.5, 703.93, "kratka", wyrownanie="srodek"),
	Pole("fin_kredyt_wklad", 1, 115.5, 684.09, "kratka", wyrownanie="srodek"),
	Pole("wklad_wlasny", 1, 175.44, 641.99, "tekst", maks_szerokosc=280.31),
	Pole("kwota_kredytu", 1, 143.78, 615.54, "tekst", maks_szerokosc=310.89),
	Pole("fin_gotowka", 1, 115.5, 598.13, "kratka", wyrownanie="srodek"),
	Pole("pow_do_300", 1, 115.5, 168.36, "kratka", wyrownanie="srodek"),
	Pole("pow_ponad_300", 1, 242.73, 168.36, "kratka", wyrownanie="srodek"),
	Pole("powierzchnia_m2", 1, 379.34, 167.85, "tekst", maks_szerokosc=66.27),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): §6 Postanowienia końcowe — blok podpisów umowy głównej
# oraz lista Załączników (1-7 w tym szablonie, o jeden mniej niż PV+ME, bo
# brak osobnego Załącznika dla magazynu energii i tylko jeden protokół
# odbioru zamiast dwóch).
#
# Autenti dokleja jedno zbiorcze poświadczenie na końcu całego pliku — patrz
# uzasadnienie przy `_STRONA_4` w `crm/volteo_umowa_mapa.py`, identyczne tu.
# Kreska podpisu (pdftotext -bbox): Zamawiający xMin=72.0/xMax=236.0,
# Wykonawca xMin=360.0/xMax=521.22, oba yMax=162.84.
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = (
	Pole("podpis_zamawiajacy", 3, 75.0, 681.66, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 3, 363.0, 681.66, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): Załącznik nr 1 — ARKUSZ USTALEŃ MONTAŻOWYCH -
# INSTALACJA FOTOWOLTAICZNA. W tym szablonie jest JEDEN arkusz (nie 1a/1b jak
# w PV+ME), bo nie ma magazynu energii do opisania osobno. Zawiera też sekcję
# "W PRZYPADKU POSIADANIA INSTALACJI FOTOWOLTAICZNEJ" (istniejąca PV) na tej
# samej stronie — w PV+ME analogiczna sekcja jest na osobnej stronie
# (Załącznik 1b, razem z magazynem).
#
# UWAGA na dwie różne etykiety "Moc inwertera": "Moc inwertera PV (kW)" w
# sekcji NOWEJ instalacji (`inwerter_moc_kw`) vs "Moc inwertera (kW)" w
# sekcji ISTNIEJĄCEJ instalacji PV (`ist_pv_moc_inwertera_kw`) — dopasowane
# po sekcji (pozycja na stronie), nie po samej etykiecie, zgodnie z
# ostrzeżeniem z briefu zadania.
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
	Pole("ist_pv_moc_inwertera_kw", 4, 167.2, 255.04, "tekst", maks_szerokosc=57.93),
	Pole("ist_pv_moc_kwp", 4, 232.76, 237.8, "tekst", maks_szerokosc=55.16),
	# `maks_szerokosc` różni się o 2,77 pt od odpowiednika w PV+ME (155.23) —
	# świadoma różnica źródła, nie błąd pomiaru: linia podkreślenia w TYM
	# pliku jest dłuższa (zmierzona xMin=167.01/xMax=331.01), bo oba
	# dokumenty PDF powstały z niezależnie wyeksportowanych plików Google
	# Docs, każdy z inaczej dobraną długością podkreślenia w tym miejscu.
	Pole("ist_pv_producent_inwertera", 4, 170.01, 220.55, "tekst", maks_szerokosc=158.0),
	# Blok podpisów Załącznika 1 — patrz uzasadnienie przy `_STRONA_4`.
	# Kreska (pdftotext -bbox): Zamawiający xMin=72.0/xMax=236.0, Wykonawca
	# xMin=360.0/xMax=521.22, oba yMax=746.42.
	Pole("podpis_zamawiajacy", 4, 75.0, 98.08, "tekst", maks_szerokosc=158.0),
	Pole("podpis_wykonawca", 4, 363.0, 98.08, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): Załącznik nr 2 (zgody na kontakt/promocję) i Załącznik
# nr 3 (oświadczenie o realizacji przed terminem odstąpienia) — oba na tej
# samej stronie, tak jak w PV+ME. Kratki tej strony (10x10 pt) SĄ tu
# emitowane przez `pdftotext` jako zwykłe słowa (inaczej niż w mapie PV+ME,
# gdzie trzeba było sięgnąć do strumienia treści PDF) — zweryfikowano
# bezpośrednio w `umowa_pv_bbox.html`.
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = (
	Pole("zgoda_telefon", 5, 77.0, 721.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_promocja", 5, 77.0, 681.87, "kratka", wyrownanie="srodek", rozmiar=8.0),
	Pole("zgoda_wczesniejsza_realizacja", 5, 77.0, 271.93, "kratka", wyrownanie="srodek", rozmiar=8.0),
	# Blok podpisów Załącznika 2 i (osobno, niżej) Załącznika 3 — oba mają
	# WYŁĄCZNIE linię Zamawiającego, bez Wykonawcy, jak w PV+ME. Kreski
	# (pdftotext -bbox): Zał. 2 xMin=72.0/xMax=233.22/yMax=242.19; Zał. 3
	# xMin=72.0/xMax=233.22/yMax=718.25.
	Pole("podpis_zamawiajacy", 5, 75.0, 602.31, "tekst", maks_szerokosc=155.22),
	Pole("podpis_zamawiajacy", 5, 75.0, 126.25, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 8 (indeks 7): Załącznik nr 4 — koniec klauzuli RODO, linia podpisu
# klienta ("data i podpis" pod kreską). Kreska (pdftotext -bbox):
# xMin=72.0/xMax=233.22/yMax=281.86.
# ---------------------------------------------------------------------------
_STRONA_8: tuple[Pole, ...] = (
	Pole("rodo_data_imie_nazwisko", 7, 75.0, 562.64, "tekst", maks_szerokosc=155.22),
)

# ---------------------------------------------------------------------------
# Strona 14 (indeks 13): Załącznik nr 7 — Pełnomocnictwo OSD (ostatni
# załącznik w tym szablonie; w PV+ME to Załącznik nr 8). Ta strona jest
# niemal bit-identyczna z odpowiadającą stroną w PV+ME (te same x, te same
# y, maks_szerokosc różni się od zera do 0,64 pt) — oba dokumenty najwyraźniej
# dzielą wspólny, niezmieniony wzorzec tekstu Pełnomocnictwa.
# ---------------------------------------------------------------------------
_STRONA_14: tuple[Pole, ...] = (
	# "udzielone w dniu ___" — jak w PV+ME, świadomie reużyty `data_zawarcia`
	# (pełnomocnictwo podpisywane tego samego dnia co umowa), brak osobnego
	# klucza kontekstu na tę datę.
	Pole("data_zawarcia", 13, 292.01, 708.11, "tekst", maks_szerokosc=88.51),
	# "Ja, niżej podpisany/a ___," — podkreślenie sąsiaduje z przecinkiem bez
	# spacji; `pdftotext` scala oba w jedno „słowo" (`xMax` obejmowałby też
	# przecinek), więc granicę pola zmierzono granulacją znakową `pdfminer`
	# (`LTChar`), żeby wykluczyć szerokość samego przecinka z `maks_szerokosc`.
	Pole("klient_imie_nazwisko", 13, 171.13, 681.66, "tekst", maks_szerokosc=88.51),
	Pole("klient_adres", 13, 336.75, 681.66, "tekst", maks_szerokosc=171.9),
	Pole("klient_pesel", 13, 110.01, 668.43, "tekst", maks_szerokosc=116.31),
	# Jedna linia podpisu — "Mocodawcy" (klient), BEZ Wykonawcy, jak w PV+ME.
	# Kreska (pdftotext -bbox): xMin=362.05/xMax=523.28/yMax=665.35.
	Pole("podpis_zamawiajacy", 13, 365.05, 179.15, "tekst", maks_szerokosc=155.22),
)

MAPA_PV: tuple[Pole, ...] = (
	_STRONA_1
	+ _STRONA_2
	+ _STRONA_4
	+ _STRONA_5
	+ _STRONA_6
	+ _STRONA_8
	+ _STRONA_14
)
"""Pełna mapa dla `crm/szablony/umowa_pv.pdf`: krotka wszystkich `Pole` na
wszystkich stronach. Jeden klucz kontekstu może wystąpić wielokrotnie (raz na
każdej stronie, gdzie faktycznie jest drukowany) — generator ma narysować
wartość we WSZYSTKICH pozycjach danego klucza, nie tylko w pierwszej.

Ta mapa NIE zawiera sześciu kluczy `bateria_*` (`bateria_producent_model`,
`bateria_moc_kw`, `bateria_pojemnosc_jedn_kwh`, `bateria_szt`,
`bateria_pojemnosc_lacznie_kwh`, `bateria_gwarancja_lat`) — szablon PV nie ma
Załącznika dotyczącego magazynu energii, więc te pola nie mają gdzie się
wydrukować. Generator wywołujący tę mapę dla umów bez magazynu ma pominąć te
klucze z kontekstu (albo je zignorować, jeśli `zbuduj_kontekst` i tak je
zwraca) — `zbuduj_kontekst` jest wspólny dla obu wariantów umowy i zawsze
zwraca pełny zestaw 63 kluczy."""

# Strony 3, 7, 9, 10, 11, 12, 13 (indeksy 2, 6, 8, 9, 10, 11, 12) nie zawierają
# żadnej pozycji z kontekstu `zbuduj_kontekst`:
#
# - Str. 3 (idx 2): §3 cd. (oświadczenia stron), §4, §5, §6 pocz. — statyczne
#   klauzule umowne, bez pól do wypełnienia.
# - Str. 7 (idx 6): Załącznik nr 4 — początek klauzuli informacyjnej RODO
#   (statyczny tekst; podpis klienta jest na kolejnej stronie, str. 8/idx 7,
#   patrz `_STRONA_8` wyżej).
# - Str. 9 (idx 8): Załącznik nr 5 — Pouczenie o prawie do odstąpienia od
#   umowy (statyczne, informacyjne, bez pól).
# - Str. 10 (idx 9): wzór FORMULARZA ODSTĄPIENIA — świadomie NIE ma tu żadnej
#   pozycji, mimo obecności linii do wypełnienia w oryginale: to pusty
#   formularz do ewentualnego wypełnienia przez klienta W PRZYSZŁOŚCI, tylko
#   gdy faktycznie odstępuje od umowy — wydrukowanie tam naszych danych
#   poświadczałoby coś, co się nie wydarzyło (ta sama zasada co w PV+ME).
# - Str. 11 (idx 10): Załącznik nr 6 — Protokół odbioru Instalacji
#   Fotowoltaicznej — decyzją produktową z 2026-08-12 (patrz `crm/volteo_
#   umowa_mapa.py`) protokoły odbioru są CAŁKOWICIE puste, wypełnia je ręcznie
#   instalator dopiero po montażu; ten szablon ma tylko JEDEN protokół
#   (nie dwa jak PV+ME), bo nie ma osobnej instalacji do odebrania.
# - Str. 12 (idx 11): lista szkoleniowa/zdjęć — wypełniana przez instalatora
#   i klienta przy montażu, nie pochodzi z `Volteo Umowa`/`CRM Deal`.
# - Str. 13 (idx 12): protokół pomiarów elektrycznych instalacji — wypełniany
#   przez instalatora przy montażu, z tego samego powodu.
#
# Żadna z tych stron nie ma bloku podpisów wypełnianego przez generator:
# protokoły/listy (str. 11-13) podpisuje instalator dopiero po montażu, a
# formularz odstąpienia (str. 10) klient wypełnia tylko wtedy, gdy faktycznie
# odstępuje od umowy — z tych samych powodów co w mapie PV+ME.


def pozycje_dla_pv(klucz: str) -> tuple[Pole, ...]:
	"""Zwraca wszystkie pozycje `Pole` w `MAPA_PV` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_PV if pole.klucz == klucz)


def klucze_w_mapie_pv() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_PV` (bez duplikatów, bez kolejności)."""
	return frozenset(pole.klucz for pole in MAPA_PV)
