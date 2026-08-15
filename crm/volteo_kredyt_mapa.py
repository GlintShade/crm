# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych formularza kredytowego na oryginalny plik PDF.

Odpowiednik `crm/volteo_umowa_mapa.py` dla trzeciego dokumentu — „Ankieta danych
do wniosku kredytowego" (`crm/szablony/formularz_kredytowy.pdf`, 6 stron). Moduł
celowo nie importuje ``frappe`` ani ``reportlab`` — jest to czysta struktura
danych, więc daje się w pełni przetestować lokalnie, tak jak `MAPA`/`MAPA_PV`/
`MAPA_ME`. `Pole` jest importowany z `crm.volteo_umowa_mapa` — NIE definiować
go tu ponownie, zgodnie z konwencją `volteo_umowa_mapa_pv.py`.

UKŁAD WSPÓŁRZĘDNYCH (identyczny jak w `volteo_umowa_mapa.py` — przeczytaj tamten
docstring, jeśli edytujesz tę mapę): ``pdftotext -bbox`` podaje ``yMin``/``yMax``
liczone OD GÓRY strony. ``reportlab`` (generator, który skorzysta z tej mapy)
rysuje w układzie liczonym OD DOŁU strony. Każda wartość ``y`` zapisana w tym
pliku jest już PRZELICZONA: ``y_reportlab = 842 - y_od_gory``. Strona ma wymiary
596x842 pt (A4). Strony numerowane 0-indeksowo (strona 1 dokumentu = 0).

Ten szablon jest formularzem TABELARYCZNYM (etykiety w lewej kolumnie, wartości
w prawej), inaczej niż umowy (akapity + podkreślenia). Trzy rodzaje pozycji:

1. **Komórka tabeli** (większość pól): ``x`` = zmierzona WEKTOROWO (`pdfminer`
   `LTLine`, nie pikselowo z rastra) współrzędna pionowej kreski dzielącej
   kolumnę etykiet od kolumny wartości, plus 6 pt wcięcia; ``y = 842 -
   yMax(etykiety)`` — bez korekty 2,5 pt, bo w tabeli nie ma osobnej kreski do
   podkreślenia, wartość ma po prostu stanąć w tej samej linii co etykieta
   wiersza (identyczna konwencja jak w `MAPA`/`MAPA_PV` dla tabeli danych
   klienta); ``maks_szerokosc`` = prawa krawędź tabeli (też zmierzona
   wektorowo) minus ``x``. Etykiety wielowierszowe (np. „LICZBA OSÓB W
   GOSPODARSTWIE DOMOWYM NA UTRZYMANIU") używają ``yMax`` DOLNEJ linii etykiety.

2. **Pole z kropkowaną linią** (``…………………``) — pytania TAK/NIE o adres
   zamieszkania/korespondencji (str. 1) i pole „inne" w formie opodatkowania
   (str. 2), oraz linia podpisu (kreska ciągła ``_____``, ta sama formuła):
   ``x = xMin(linii) + 3``, ``y = 842 - yMax(linii) + 2,5``, ``maks_szerokosc =
   szerokość(linii) - 6``.

3. **Kratka** (``☐``/``□``): wszystkie kratki w tym szablonie mają jednolitą
   wysokość glifu 13,41 pt (zmierzone `pdftotext -bbox`, patrz `build_map.py`
   w raporcie zadania), ale glif ``□`` jest wyraźnie mniejszy w środku niż
   jego 13,41-punktowa obwódka — domyślny ``rozmiar=10.0`` dawał znak „X"
   za wysoki na kratkę (feedback właściciela po pierwszym wydruku PDF-u).
   Każda kratka w tej mapie ma więc jawne ``rozmiar=8.0`` (ta sama wartość co
   „standardowa" mała kratka w `volteo_umowa_mapa.py`), a ``y`` jest liczone
   nie od ``yMax(glifu)`` z offsetem, tylko WPROST z pionowego środka kratki:
   ``y = 842 - (yMin(glifu)+yMax(glifu))/2 - 0,36*rozmiar`` — ``0,36*rozmiar``
   to przybliżony offset od linii bazowej do pionowego środka wielkiej litery
   „X" (cap-height ≈ 0,72 em, więc połowa to ≈0,36 em), tak żeby narysowany
   znak wypadł wyśrodkowany w kratce, a nie przy jej górnej krawędzi. ``x``
   jest środkiem kratki w poziomie (generator ma wyśrodkować znak „X"
   względem tego punktu, ``wyrownanie="srodek"``).

Wszystkie współrzędne w ``MAPA_KREDYT`` zostały policzone SKRYPTEM
(`pdftotext -bbox` dla tekstu/kropkowanych linii i glifów kratek; `pdfminer.six`
`LTLine`/`LTRect` dla wektorowych granic kolumn/wierszy tabeli, których
`pdftotext` nie oddaje — nie ma tam osobnego glifu do zmierzenia) — żadna
wartość nie jest przepisana ręcznie ani zgadnięta. Każdy wiersz komórki
tabelarycznej został dodatkowo zweryfikowany asercją, że obliczone ``y`` mieści
się w granicach wiersza zmierzonych z siatki `pdfminer` (zob. raport zadania) —
to właśnie ten rodzaj pomyłki (przypisanie wartości do sąsiedniego wiersza),
którego dotyczy ostrzeżenie w `volteo_umowa_mapa.py` o „sześciu błędach z
ręcznego liczenia".

Linia podpisu na str. 3 (indeks 2) i str. 5 (indeks 4) jest WSPÓLNA dla daty i
imienia/nazwiska — jedna kreska pod „(data, imię i nazwisko)", nie dwie osobne
linie. Mapa dzieli tę jedną zmierzoną linię na dwa nienachodzące się pola
tekstowe: ``podpis_data`` zajmuje lewe ~32% szerokości (daty są krótkie:
„15.08.2026"), ``podpis_imie_nazwisko`` resztę (imię i nazwisko bywają
dłuższe) — podział jest arbitralny w sensie proporcji (nie zmierzony z żadnego
elementu graficznego, bo oryginał nie dzieli tej linii wizualnie), ale sam
punkt startowy/koniec linii i przeliczenie osi Y są zmierzone identycznie jak
każde inne pole tekstowe.

TRANSKRYPCJA DOKŁADNYCH TREŚCI OPCJI KRATEK (autorytatywne źródło — inne
moduły mają kopiować stąd, nie z PDF-u bezpośrednio):

    Wykształcenie (§3, str. 1):        wyższe / średnie / zawodowe /
                                        podstawowe/gimnazjalne
    Stan cywilny (§3, str. 1):         kawaler/panna / Rozwiedziony/a /
                                        W związku małżeńskim rozdzielność
                                        majątkowa / W związku małżeńskim
                                        wspólnota majątkowa / Wdowiec/wdowa /
                                        Separacja
    Forma zatrudnienia (§4, str. 2):   Umowa o pracę / Umowa zlecenie /
                                        Umowa o dzieło
    Forma opodatkowania (§7, str. 2):  ryczałt / księga przychodów i
                                        rozchodów (KPiR) / inne
                                        …………………………… (kropkowana linia obok
                                        „inne" — pole `dzialalnosc_forma_inna`)

BEZPIECZNIK ZMIANY SZABLONU: mapa poniżej obowiązuje WYŁĄCZNIE dla dokładnie
tej wersji oryginału. Generator PDF-u ma sprawdzić sumę SHA-256 pliku
wejściowego względem ``SHA256_SZABLONU_KREDYT`` przed użyciem tej mapy i
przerwać z czytelnym komunikatem przy niezgodności — nigdy nie wpisywać danych
w oparciu o niepewne współrzędne.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_KREDYT: str = "d766aadcebdfb0d66d84499fe2a4a4f0cf8a63b0a16f0c774dbaddba0604dd31"
"""SHA-256 pliku `Formularz kredytowy.pdf` (A4, 596x842 pt, 6 stron, bez pól
formularza, wygenerowany przez Skia/PDF m153 Google Docs Renderer), policzone
`shasum -a 256` na oryginale dostarczonym do tego zadania (2026-08-15) i
zweryfikowane ponownie po skopiowaniu do `crm/szablony/formularz_kredytowy.pdf`.
Mapa `MAPA_KREDYT` poniżej jest skalibrowana WYŁĄCZNIE dla tego dokładnego
pliku — każda zmiana szablonu (nawet kosmetyczna) unieważnia współrzędne."""

LICZBA_STRON_KREDYT: int = 6
"""Liczba stron oryginału, zgodna z `pdfinfo`. Używana przez generator/testy do
sprawdzenia, że żadna pozycja w mapie nie wskazuje strony poza dokumentem."""

# ---------------------------------------------------------------------------
# Strona 1 (indeks 0): §1 DANE PODSTAWOWE, §2 ADRES ZAMIESZKANIA,
# §3 INFORMACJE O WNIOSKODAWCY (wykształcenie, stan cywilny, gospodarstwo
# domowe — część 1)
# ---------------------------------------------------------------------------
_STRONA_1: tuple[Pole, ...] = (
    # §1 DANE PODSTAWOWE — tabela, kreska dzieląca kolumny x=290.5 (zmierzona
    # wektorowo `pdfminer` LTLine), prawa krawędź tabeli x=523.5, 9 wierszy po
    # 15 pt (zweryfikowane: każde y poniżej mieści się w granicach swojego
    # wiersza z siatki LTLine).
    Pole("pesel", 0, 296.50, 728.33, "tekst", maks_szerokosc=227.00),
    Pole("miejsce_urodzenia", 0, 296.50, 713.33, "tekst", maks_szerokosc=227.00),
    Pole("imiona", 0, 296.50, 698.33, "tekst", maks_szerokosc=227.00),
    Pole("nazwisko", 0, 296.50, 683.33, "tekst", maks_szerokosc=227.00),
    Pole("rodzaj_seria_numer_dokumentu", 0, 296.50, 668.33, "tekst", maks_szerokosc=227.00),
    Pole("data_waznosci_dokumentu", 0, 296.50, 653.33, "tekst", maks_szerokosc=227.00),
    Pole("data_wydania_dokumentu", 0, 296.50, 638.33, "tekst", maks_szerokosc=227.00),
    Pole("telefon", 0, 296.50, 623.33, "tekst", maks_szerokosc=227.00),
    Pole("email", 0, 296.50, 608.33, "tekst", maks_szerokosc=227.00),
    # §2 ADRES ZAMIESZKANIA — ta sama tabela (kolumny 290.5/523.5) kontynuuje
    # się przez KOD POCZTOWY..NR LOKALU (5 wierszy).
    Pole("kod_pocztowy", 0, 296.50, 554.91, "tekst", maks_szerokosc=227.00),
    Pole("miejscowosc", 0, 296.50, 539.16, "tekst", maks_szerokosc=227.00),
    Pole("ulica", 0, 296.50, 523.79, "tekst", maks_szerokosc=227.00),
    Pole("nr_domu", 0, 296.50, 508.41, "tekst", maks_szerokosc=227.00),
    Pole("nr_lokalu", 0, 296.50, 493.79, "tekst", maks_szerokosc=227.00),
    # Pytanie „CZY ADRES ZAMIESZKANIA JEST TAKI SAM, JAK ADRES ZAMELDOWANIA?"
    # — kratki TAK/NIE (glif 13,41 pt, offset standardowy +3,0) + kropkowana
    # linia „Adres zamieszkania: ……" pod pytaniem.
    Pole("adres_zameldowania_tak", 0, 299.52, 473.11, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("adres_zameldowania_nie", 0, 337.27, 473.11, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("adres_zameldowania", 0, 298.90, 448.79, "tekst", maks_szerokosc=209.80),
    # Pytanie „CZY ADRES DO KORESPONDENCJI JEST TAKI SAM, JAK ADRES
    # ZAMELDOWANIA?" — analogicznie.
    Pole("adres_korespondencji_tak", 0, 299.52, 423.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("adres_korespondencji_nie", 0, 337.27, 423.54, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("adres_korespondencji", 0, 298.90, 399.21, "tekst", maks_szerokosc=209.80),
    # §3 INFORMACJE O WNIOSKODAWCY — WYKSZTAŁCENIE (4 kratki, x środek glifu
    # jednolity 249.27, jedna kolumna checkboxów).
    Pole("wyksztalcenie_wyzsze", 0, 249.27, 352.78, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("wyksztalcenie_srednie", 0, 249.27, 338.99, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("wyksztalcenie_zawodowe", 0, 249.27, 325.19, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("wyksztalcenie_podstawowe", 0, 249.27, 311.39, "kratka", wyrownanie="srodek", rozmiar=8.0),
    # STAN CYWILNY (6 kratek, ta sama kolumna x=249.27).
    Pole("stan_kawaler_panna", 0, 249.27, 296.84, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("stan_rozwiedziony", 0, 249.27, 283.04, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("stan_malzenstwo_rozdzielnosc", 0, 249.27, 269.24, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("stan_malzenstwo_wspolnota", 0, 249.27, 255.44, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("stan_wdowiec_wdowa", 0, 249.27, 241.64, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("stan_separacja", 0, 249.27, 227.85, "kratka", wyrownanie="srodek", rozmiar=8.0),
    # §3 ciąg dalszy — komórki tabeli (kolumna dzieli się teraz przy x=240.4,
    # szersza niż 290.5 powyżej, bo ten fragment tabeli mieści też checkboxy;
    # prawa krawędź x=523.9). 7 wierszy.
    # liczba_osob_na_utrzymaniu/dochod_wspolmalzonka/suma_zobowiazan sit in
    # taller (19-20 pt), two-line-label rows (LTRect grid: y[204.5,224.5],
    # y[170.5,189.5], y[121.5,140.5] — `extract_lines.py` page 0). The other,
    # single-line-label rows in this block anchor the value on the label's
    # own yMax, which lands ~2,7-2,9 pt above the row's bottom border — fine
    # for a 15 pt row, but for these three the label's LAST line sits right
    # at the row bottom, so the same anchor put the value flush against the
    # border. Fixed by centring on the row instead: baseline = row_centre -
    # 4,70 pt, where 4,70 is the row-centre-to-baseline offset measured from
    # the three well-behaved single-line rows in the same block
    # (kwota_800_plus/zrodlo_dochodu_malzonka/oplaty_miesieczne: 4,60/4,75/
    # 4,75 pt) — not guessed, calibrated from neighbouring rows.
    Pole("liczba_osob_na_utrzymaniu", 0, 246.40, 209.80, "tekst", maks_szerokosc=277.50),
    Pole("kwota_800_plus", 0, 246.40, 192.40, "tekst", maks_szerokosc=277.50),
    Pole("dochod_wspolmalzonka", 0, 246.40, 175.30, "tekst", maks_szerokosc=277.50),
    Pole("zrodlo_dochodu_malzonka", 0, 246.40, 158.25, "tekst", maks_szerokosc=277.50),
    Pole("oplaty_miesieczne", 0, 246.40, 143.25, "tekst", maks_szerokosc=277.50),
    Pole("suma_zobowiazan", 0, 246.40, 126.30, "tekst", maks_szerokosc=277.50),
    Pole("numer_rachunku", 0, 246.40, 102.43, "tekst", maks_szerokosc=277.50),
)

# ---------------------------------------------------------------------------
# Strona 2 (indeks 1): §4 UMOWA O PRACĘ/ZLECENIE/DZIEŁO, §5 EMERYTURA,
# §6 RENTA, §7 DZIAŁALNOŚĆ GOSPODARCZA
# ---------------------------------------------------------------------------
_STRONA_2: tuple[Pole, ...] = (
    # §4 — forma zatrudnienia: 3 kratki (kolumna x=249.27, jak na str. 1).
    Pole("praca_umowa_o_prace", 1, 249.27, 741.84, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("praca_zlecenie", 1, 249.27, 728.04, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("praca_dzielo", 1, 249.27, 714.24, "kratka", wyrownanie="srodek", rozmiar=8.0),
    # DATA ZATRUDNIENIA — komórka tabeli (kolumna x=240.4/523.9, jak w dolnej
    # części §3 na str. 1 — ten sam układ powtarza się na całej stronie 2).
    Pole("praca_data_zatrudnienia", 1, 246.40, 690.45, "tekst", maks_szerokosc=277.50),
    # OKRES ZATRUDNIENIA — DWIE kropkowane linie „Czas określony od: … do: …"
    # NA JEDNEJ LINII (nie kratki — zgodnie z briefem) plus osobna linia niżej
    # „Czas nieokreślony od: …". Wszystkie trzy mieszczą się w tym samym,
    # wysokim (38 pt) wierszu tabeli.
    Pole("praca_okreslony_od", 1, 318.84, 663.77, "tekst", maks_szerokosc=60.16),
    Pole("praca_okreslony_do", 1, 400.54, 663.77, "tekst", maks_szerokosc=76.14),
    Pole("praca_nieokreslony_od", 1, 329.50, 645.37, "tekst", maks_szerokosc=110.33),
    Pole("praca_nip", 1, 246.40, 622.90, "tekst", maks_szerokosc=277.50),
    Pole("praca_nazwa_zakladu", 1, 246.40, 592.90, "tekst", maks_szerokosc=277.50),
    Pole("praca_adres_telefon", 1, 246.40, 558.30, "tekst", maks_szerokosc=277.50),
    Pole("praca_kwota_dochodu", 1, 246.40, 532.90, "tekst", maks_szerokosc=277.50),
    # §5 EMERYTURA
    Pole("emerytura_numer_swiadczenia", 1, 246.40, 475.02, "tekst", maks_szerokosc=277.50),
    Pole("emerytura_od_kiedy", 1, 246.40, 440.42, "tekst", maks_szerokosc=277.50),
    Pole("emerytura_kwota_dochodu", 1, 246.40, 415.02, "tekst", maks_szerokosc=277.50),
    # §6 RENTA
    Pole("renta_numer_swiadczenia", 1, 246.40, 357.15, "tekst", maks_szerokosc=277.50),
    Pole("renta_od_kiedy", 1, 246.40, 322.55, "tekst", maks_szerokosc=277.50),
    Pole("renta_kwota_dochodu", 1, 246.40, 297.15, "tekst", maks_szerokosc=277.50),
    # §7 DZIAŁALNOŚĆ GOSPODARCZA — forma opodatkowania: 3 kratki + kropkowana
    # linia obok „inne" (wszystkie w tym samym wierszu tabeli).
    Pole("dzialalnosc_ryczalt", 1, 249.27, 248.52, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("dzialalnosc_kpir", 1, 249.27, 234.72, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("dzialalnosc_inne", 1, 249.27, 220.92, "kratka", wyrownanie="srodek", rozmiar=8.0),
    Pole("dzialalnosc_forma_inna", 1, 275.45, 220.45, "tekst", maks_szerokosc=81.92),
    Pole("dzialalnosc_nip", 1, 246.40, 197.95, "tekst", maks_szerokosc=277.50),
    Pole("dzialalnosc_nazwa", 1, 246.40, 169.60, "tekst", maks_szerokosc=277.50),
    Pole("dzialalnosc_adres_telefon", 1, 246.40, 141.25, "tekst", maks_szerokosc=277.50),
    Pole("dzialalnosc_od_kiedy", 1, 246.40, 103.71, "tekst", maks_szerokosc=277.50),
    Pole("dzialalnosc_kwota_dochodu", 1, 246.40, 75.36, "tekst", maks_szerokosc=277.50),
)

# ---------------------------------------------------------------------------
# Strona 3 (indeks 2): §8 GOSPODARSTWO ROLNE, §9 INNE DOCHODY, oświadczenia
# + pierwsza linia podpisu (data, imię i nazwisko)
# ---------------------------------------------------------------------------
_STRONA_3: tuple[Pole, ...] = (
    Pole("gospodarstwo_nip", 2, 246.40, 688.01, "tekst", maks_szerokosc=277.50),
    Pole("gospodarstwo_od_kiedy", 2, 246.40, 653.41, "tekst", maks_szerokosc=277.50),
    Pole("gospodarstwo_kwota_dochodu", 2, 246.40, 628.01, "tekst", maks_szerokosc=277.50),
    # §9 INNE DOCHODY — dwie osobne, ułożone pionowo dwuwierszowe tabelki
    # (typ + kwota), jedna pod drugą.
    Pole("inne_1_typ", 2, 246.40, 561.41, "tekst", maks_szerokosc=277.50),
    Pole("inne_1_kwota", 2, 246.40, 531.41, "tekst", maks_szerokosc=277.50),
    Pole("inne_2_typ", 2, 246.40, 482.73, "tekst", maks_szerokosc=277.50),
    Pole("inne_2_kwota", 2, 246.40, 452.73, "tekst", maks_szerokosc=277.50),
    # Linia podpisu nad „(data, imię i nazwisko)" — JEDNA zmierzona kreska
    # ciągła (nie kropkowana, ale ta sama formuła x=xMin+3/y=842-yMax+2,5/
    # szerokość-6 stosuje się identycznie), podzielona na dwa nienachodzące
    # się pola: lewe ~32% szerokości na datę, reszta na imię i nazwisko
    # (zob. uzasadnienie podziału w docstringu modułu).
    Pole("podpis_data", 2, 325.90, 174.82, "tekst", maks_szerokosc=45.59),
    Pole("podpis_imie_nazwisko", 2, 377.49, 174.82, "tekst", maks_szerokosc=103.63),
)

# ---------------------------------------------------------------------------
# Strona 4 (indeks 3): „ZGODA NA POZYSKIWANIE DANYCH OSOBOWYCH" — czysty
# tekst prawny, bez pól formularza (zweryfikowane: brak jakiegokolwiek glifu
# kratki/linii kropkowanej/podpisu na tej stronie).
# ---------------------------------------------------------------------------
_STRONA_4: tuple[Pole, ...] = ()

# ---------------------------------------------------------------------------
# Strona 5 (indeks 4): kontynuacja zgody RODO + DRUGA linia podpisu
# (data, imię i nazwisko) — te same klucze `podpis_data`/`podpis_imie_nazwisko`
# co na stronie 3, druga, osobna pozycja (Pole wspiera powtórzone klucze).
# ---------------------------------------------------------------------------
_STRONA_5: tuple[Pole, ...] = (
    Pole("podpis_data", 4, 342.36, 474.25, "tekst", maks_szerokosc=45.59),
    Pole("podpis_imie_nazwisko", 4, 393.96, 474.25, "tekst", maks_szerokosc=103.63),
)

# ---------------------------------------------------------------------------
# Strona 6 (indeks 5): „INFORMACJA DOTYCZĄCA FIRMY, KTÓRA PRZEKAŻE DANE
# KLIENTA DO INSTYTUCJI BANKOWYCH I POŚREDNICZĄCYCH" — informacyjna, bez pól
# formularza (zweryfikowane: brak glifu kratki/linii kropkowanej/podpisu).
# ---------------------------------------------------------------------------
_STRONA_6: tuple[Pole, ...] = ()

MAPA_KREDYT: tuple[Pole, ...] = _STRONA_1 + _STRONA_2 + _STRONA_3 + _STRONA_4 + _STRONA_5 + _STRONA_6
"""Pełna mapa współrzędnych formularza kredytowego — 74 pozycje na stronach
0, 1, 2 (37 + 26 + 9) i 2 pozycje na stronie 4 (drugi podpis); strony 3 i 5
celowo puste (patrz komentarze przy `_STRONA_4`/`_STRONA_6`)."""
