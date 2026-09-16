# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Import leadów z arkusza Grega (`CRM_ProEnergy_FINAL_import_CRM.xlsx`, arkusz
„Leady") do `CRM Lead`: reimport b59 (issue #98), zastępuje poprzedni parser
CSV historycznej bazy Arago/SD/CC.

Moduł celowo nie importuje ``frappe`` — precedens ``crm/volteo_naming.py``.
To jedyny sposób, żeby dało się go przetestować lokalnie (``frappe`` nie jest
instalowalne na tej maszynie, więc reszta backendu ma wyłącznie bramkę
składniową `ruff`/`py_compile`). Wszystko co dotyka dokumentu `CRM Lead`
(insert, uprawnienia, dedup względem istniejących kontaktów, geokod) mieszka
poza tym plikiem, w ``ops/crm-import-leady.py``.

Cały plik operuje wyłącznie na czystych strukturach `str`/`dict`/`list` —
zero zależności od frameworka, zero mutacji argumentów wejściowych.

## Format arkusza

Dokładnie 14 nazwanych kolumn, w tej kolejności (`NAGLOWKI_ARKUSZA`): Telefon,
Imię, Nazwisko, Adres, Powiat, Województwo, Źródło, Data pozyskania, Status
źródła, Zasady rozliczania, Obecne produkty, Produkt w procesie,
Zainteresowanie, Uwagi. `waliduj_naglowek` rzuca głośno na jakiekolwiek
odstępstwo (brakująca, nadmiarowa albo przestawiona kolumna): zero
zgadywania kształtu pliku.

## Puste komórki

`_pusta()` traktuje jako pustkę (bez rozróżniania wielkości liter): pustą
komórkę, `-`, `brak`, `nie`. To poszerzenie względem poprzedniego formatu
(który znał tylko `""`/`-`) NIE zmienia zachowania żadnej z zachowanych
funkcji na ich dotychczasowych testach: `normalizuj_wojewodztwo("brak")` i
`mapuj_zainteresowanie("brak")` już wcześniej zwracały `None` (bo `"brak"`
nie pasował do żadnego kanonu), więc dodatkowa wczesna ścieżka przez
`_pusta()` daje ten sam wynik, tylko szybciej. Nowy marker `nie` nie był
dotąd używany w żadnym teście, więc nie ma czego złamać.

## Odrzucenia pól kontra odrzucenia wierszy

Zły telefon (nie przechodzi `normalizuj_telefon`) odrzuca CAŁY wiersz:
`zbuduj_leada_z_arkusza` zwraca `(None, [OdrzuconePole(...)])`. Każda inna
kolumna słownikowa (Data pozyskania, Status źródła, Zasady rozliczania,
Obecne produkty, Produkt w procesie, Zainteresowanie, Województwo, Źródło)
idzie przez wspólny helper `_pole_slownikowe`: niepusta wartość, której
normalizator nie rozpozna (czy to przez wyjątek `WartoscOdrzucona`, czy przez
zwrócenie `None`), odrzuca TYLKO to jedno pole: pole w wynikowym słowniku
leada staje się `None`, wpis trafia do listy `OdrzuconePole`, a wiersz i tak
wchodzi do wyniku. To jest kontrakt uzgodniony z Gregiem: nieznany token w
Obecne produkty / Produkt w procesie / Źródło nie ma unieważniać całego
leada, tylko to jedno pole.

Wyjątek: pusta komórka `Źródło` jest odrzucana z powodem `"wymagane"` mimo że
inne puste komórki nie trafiają do raportu: źródło leada jest jedynym polem
z tej grupy, które ma być zawsze wypełnione.

## Adres

`rozbij_adres_arkusza` rozbija jedną kolumnę `Adres` (`"<fragment ulicy>, <kod>
<miejscowość>[ (dopisek]"`) na ulicę, numer domu, kod, miejscowość i dopisek.
`_WZOR_ADRES` ma ZACHŁANNĄ grupę 1, więc kotwiczy się na OSTATNIM wystąpieniu
`, dd-ddd ` w tekście: dla adresu z dwoma przecinkami („Rogierówko, Ul.
Kościuszki 16A, 62-090 Rokietnica") grupa 1 to CAŁE „Rogierówko, Ul.
Kościuszki 16A" (z przecinkiem w środku) - fragment ulicy, dopiero rozbijany
dalej. Brak dopasowania do `_WZOR_ADRES` odrzuca CAŁE pole Adres do raportu;
surowy tekst zostaje w `custom_install_address` bez zmian, reszta adresowych
pól zostaje pusta.

Fragment ulicy równy `-` (albo pusty wg `_pusta`) - wieś bez nazwy ulicy -
daje `ulica = miejscowość`, `nr_domu = ""` (decyzja właściciela, issue #116,
2026-09-09: OBA pola mają nieść tę samą wartość, żeby "ulica" nigdy nie była
pusta tam, gdzie jest jakikolwiek adres). W pozostałych przypadkach fragment
idzie przez `rozbij_fragment_ulicy(fragment, miejscowość)`, która rozpoznaje
numer domu tolerancyjnie (litery, ukośniki, słowo „nr", numer sklejony bez
odstępu, nawiasy w środku fragmentu, segmenty po przecinku - patrz jej
docstring dla pełnych reguł a-g). Gdy numer domu nie zostanie rozpoznany, a
pozostawiony w Ulicy tekst zawiera choć jedną cyfrę (`ulica_zawiera_cyfre`),
`zbuduj_leada_z_arkusza` dokłada wpis INFORMACYJNY do raportu odrzuceń
(kolumna „Adres", powód „numer domu nierozpoznany, tekst zostawiony w
Ulicy") - to NIE jest odrzucenie pola ani wiersza, lead wchodzi normalnie.

Dopiski (nawiasy w środku fragmentu ulicy, segmenty odrzucone przy podziale
po przecinku, oraz klasyczny dopisek w nawiasie PO miejscowości) łączą się w
JEDNĄ linię `custom_uwagi_import` w formacie `Adres (dopisek): <segmenty
złączone przecinkiem>`, dokładaną przez `normalizuj_uwagi`.

## Duble telefonu

`scal_duble` grupuje wiersze arkusza po znormalizowanym telefonie i SCALA
każdą grupę powtórzeń w jeden wiersz zamiast odrzucać kolejne wystąpienia
(kontrakt z Gregiem, `docs/LEADY-ARKUSZ-IMPORT-GREG.md`, sekcja „Duble":
„importer scali je sam po numerze, źródła po plusie, uwagi sklejone").
Pierwsze wystąpienie wygrywa jako baza; `Źródło`/`Obecne produkty`/`Produkt w
procesie` sumują surowe tokeny obu wierszy (normalizacja i tak dzieje się
później, w `zbuduj_leada_z_arkusza`), `Uwagi` się doklejają, `Status źródła`
idzie wg priorytetu Wygrana > Potencjał > Przegrana > Nieaktualna, `Data
pozyskania` bierze nowszą, a każda inna pusta komórka bazy dopełnia się z
kolejnego wiersza. Wiersze z niepoprawnym telefonem NIE są ze sobą grupowane
(każdy taki wiersz to własna, jednoelementowa "grupa") - `zbuduj_leada_z_arkusza`
i tak je odrzuci później. `wykryj_duble_telefonow` zostaje bez zmian (używa
jej konwerter `ops/leady-xlsx-do-csv.py`, który tylko RAPORTUJE duble, nie
scala ich).

## Pisownia imion i nazwisk

Decyzja właściciela 2026-09-16 (ujednolicenie pisowni): `zbuduj_leada_z_arkusza`
normalizuje `first_name`/`last_name` przez `normalizuj_pisownie_osoby` -
pierwsza litera wielka, reszta mała, na KAŻDYM słowie, także po myślniku i
apostrofie (`str.title()` już to robi poprawnie, diakrytyki polskie
włącznie - patrz jej docstring). WYJĄTEK: gdy `_wyglada_na_firme` rozpoznaje
firmę w surowej kolumnie `Imię`, pisownia zostaje bez zmian (firmowe nazwy
nie są tytułowane). Ulice NIE są normalizowane tą funkcją - ryzyko przy
nazwach typu „dywizjonu 303" czy „Zbyszka z Bogdańca", gdzie title-case
psułby sens.
"""

import csv
import datetime
import io
import re
from collections.abc import Callable
from typing import Any, NamedTuple

KANONICZNE_WOJEWODZTWA: frozenset[str] = frozenset(
	{
		"dolnośląskie",
		"kujawsko-pomorskie",
		"lubelskie",
		"lubuskie",
		"łódzkie",
		"małopolskie",
		"mazowieckie",
		"opolskie",
		"podkarpackie",
		"podlaskie",
		"pomorskie",
		"śląskie",
		"świętokrzyskie",
		"warmińsko-mazurskie",
		"wielkopolskie",
		"zachodniopomorskie",
	}
)
"""Kanoniczna lista 16 województw, zapisana małymi literami z polskimi diakrytykami."""

TOKENY_ZAINTERESOWANIA: dict[str, str] = {
	"PC": "Pompa ciepła",
	"PV": "Fotowoltaika",
	"MGZ": "Magazyn energii",
}
"""Mapowanie skrótów kolumny `Zainteresowanie` na etykietę `custom_product_interest`."""

PUSTE_MARKERY: frozenset[str] = frozenset({"", "-", "brak", "nie"})
"""Markery pustej komórki w arkuszu Grega, dopasowywane bez rozróżniania wielkości
liter (patrz `_pusta`)."""

_WZOR_SAM_NUMER = re.compile(r"^\d+\s?[A-Za-z]?(?:\s*/\s*(?:\d+[A-Za-z]?|[A-Za-z]))?$")
"""Cała wartość to sam numer domu (wieś bez nazwy ulicy) - `_rozbij_c_do_f` regula f.
Tolerancyjny tak samo jak `_CZESC_NUMERU_GLOWNA`/`_CZESC_NUMERU_DRUGA` (odstęp przed
literą, druga część po ukośniku może być samą literą, np. `21/A`) - spójność z
regułą d, żeby ta sama forma numeru nie działała inaczej w zależności od tego, czy
przed nią stoi nazwa ulicy."""

_WZOR_KOD_POCZTOWY = re.compile(r"^\d{2}-\d{3}$")
"""Wygląda jak polski kod pocztowy, nie nazwa ulicy - straż w `_rozbij_c_do_f` i
`_podziel_segmenty_przecinkiem` przeciwko np. '62-300 300' (kod pocztowy wpisany
w kolumnie Ulica) albo segmentowi-kodowi w adresie z dwoma przecinkami."""

_ZNAK_LITERA = r"[^\W\d_]"
"""Jeden znak-litera (unicode, z polskimi diakrytykami włącznie) - `\\w` minus
cyfra minus podkreślnik. Używane w `_WZOR_NUMER_SKLEJONY` (regula e)."""

_CZESC_NUMERU_GLOWNA = r"\d+\s?[A-Za-z]?"
"""Pierwsza część tolerancyjnego numeru domu: cyfry plus opcjonalna litera,
z opcjonalnym POJEDYNCZYM odstępem przed literą (`16A`, `41a`, `5`, `21 A` -
w realnym arkuszu „21 A"/„3 B" jest częstszym zapisem niż sklejone „21A") -
`_rozbij_c_do_f` reguły d/e. `_znormalizuj_numer` usuwa odstęp z wyniku, więc
`21 A` i `21A` dają ten sam znormalizowany numer `21A`."""

_CZESC_NUMERU_DRUGA = r"(?:\d+[A-Za-z]?|[A-Za-z])"
"""Część numeru PO ukośniku: cyfry z opcjonalną literą, albo sama litera
(`22/A` - druga część to sama litera `A`) - `_rozbij_c_do_f` reguła d."""

_WZOR_PREFIKS_ULICY = re.compile(r"^(?:ulica\s+|ul\.\s*|ul\s+)", re.IGNORECASE)
"""Prefiks 'ul.'/'ul'/'ulica' na początku fragmentu (`_rozbij_c_do_f` reguła c)
- wymaga kropki LUB białego znaku zaraz po 'ul', żeby nie okroić prawdziwej
nazwy ulicy zaczynającej się od liter 'ul' (np. 'Ulicowa'). Dopasowuje też
sklejone 'UL.PARKOWA5' (kropka bez spacji za nią)."""

_WZOR_NUMER_Z_NR = re.compile(
	rf"^(?P<ulica>.+?)\s+nr\.?\s*(?P<numer>{_CZESC_NUMERU_GLOWNA})"
	rf"(?:\s*/\s*(?P<numer2>{_CZESC_NUMERU_DRUGA}))?\s*\.?\s*$",
	re.IGNORECASE,
)
"""Numer domu poprzedzony jawnym słowem 'nr'/'nr.' (`_rozbij_c_do_f` reguła d) -
SPRAWDZANY PRZED `_WZOR_NUMER_ZWYKLY`: bez tego priorytetu nie-zachłanna grupa
ulicy wciągnęłaby samo słowo 'nr' do nazwy ulicy (np. 'dywizjonu 303 nr 34.'
dałoby błędnie ulica='dywizjonu 303 nr')."""

_WZOR_NUMER_ZWYKLY = re.compile(
	rf"^(?P<ulica>.+?)\s+(?P<numer>{_CZESC_NUMERU_GLOWNA})"
	rf"(?:\s*/\s*(?P<numer2>{_CZESC_NUMERU_DRUGA}))?\s*\.?\s*$"
)
"""Numer domu na końcu bez słowa 'nr' (`_rozbij_c_do_f` reguła d), oddzielony
od ulicy co najmniej jednym białym znakiem."""

_WZOR_NUMER_SKLEJONY = re.compile(
	rf"^(?P<ulica>.*?{_ZNAK_LITERA})(?P<numer>{_CZESC_NUMERU_GLOWNA})"
	rf"(?:\s*/\s*(?P<numer2>{_CZESC_NUMERU_DRUGA}))?\s*\.?\s*$"
)
"""Numer sklejony bez odstępu z ulicą (`_rozbij_c_do_f` reguła e, np.
'KOWALEWICZKI32', 'PARKOWA5' po zdjęciu prefiksu 'UL.') - ulica musi kończyć
się LITERĄ (nie dowolnym znakiem), żeby np. '4.0' (reguła f) nie złapało się
tu jako ulica='4.', numer='0'. Wywołujący (`_rozbij_c_do_f`) używa tego wzorca
TYLKO gdy cały tekst jest jednym tokenem bez białych znaków - inaczej złapałby
np. 'Rzepkowo 14m2' jako ulica='Rzepkowo 14m', numer='2'."""

_WZOR_SAM_NUMER_KROPKA = re.compile(r"^\d+\.0$")
"""Liczba całkowita zapisana przez Excela jako float ('4.0', '1.0') -
`_rozbij_c_do_f` reguła f; końcówka '.0' jest ucinana przed sprawdzeniem
`_WZOR_SAM_NUMER`."""

MARKERY_FIRMY: frozenset[str] = frozenset(
	{
		"SPÓŁKA",
		"SP",  # „Sp. z o.o." skrócone — po obcięciu kropki token to „SP"
		"S.A",  # „S.A." po obcięciu końcowej kropki
		"FIRMA",
		"F.H.U",
		"P.H.U",
		"P.P.H",
		"USŁUGI",
		"GOSPODARSTWO",
		"STOWARZYSZENIE",
		"FUNDACJA",
		"HOTEL",
		"RESTAURACJA",
		"ZAKŁAD",
		"PRZEDSIĘBIORSTWO",
		"CENTRUM",
		"BIURO",
		"SKLEP",
		"AUTO",
		"SERWIS",
	}
)
"""Markery firmowe z ops#30 — dopasowywane jako CAŁE słowo (wielkie litery, otaczające
kropki/przecinki obcięte), nie jako podciąg wewnątrz dłuższego słowa. `HANDLOW*` jest
wyjątkiem obsługiwanym osobno w `_wyglada_na_firme` (dopasowanie prefiksem)."""

KOLEJNOSC_PRODUKTOW: tuple[str, ...] = (
	"PV",
	"ME",
	"PC",
	"PP",
	"AUDYT",
	"TERMO",
	"REKU",
	"OKNA",
	"GRUNT",
)
"""Kanoniczna, stała kolejność tokenów `custom_posiadane_produkty` (issue ops#91) -
zawsze w tej kolejności, niezależnie od kolejności wystąpienia w tekście źródłowym."""

KOLEJNOSC_PRODUKTOW_PROCESU: tuple[str, ...] = ("PV", "PVME", "ME", "PC", "CP")
"""Kanoniczna, stała kolejność tokenów `custom_produkt_procesu` (issue #131) - kolumna
`Produkt w procesie` arkusza Grega. Słownik jest CELOWO inny niż `KOLEJNOSC_PRODUKTOW`
(brak PP/AUDYT/TERMO/REKU/OKNA/GRUNT, obecne PVME i CP) - to "co się dzieje teraz", nie
"co klient już ma"."""

KOLEJNOSC_ZRODEL: tuple[str, ...] = ("ARG", "CC", "SD")
"""Kanoniczna, stała kolejność tokenów kolumny `Źródło` (Arago/Call Center/telemarketing),
łączonych `+` w `custom_import_source` gdy lead ma kilka źródeł naraz (np. `ARG+CC`)."""

STATUSY_ZRODLA: frozenset[str] = frozenset({"Wygrana", "Przegrana", "Nieaktualna", "Potencjał"})
"""Cztery kanoniczne wartości kolumny `Status źródła` (`custom_status_zrodla`)."""

ZASADY_DOTACJI: dict[str, str] = {
	"NOWE": "Nowe zasady",
	"STARE": "Stare zasady",
	"NOWE ZASADY": "Nowe zasady",
	"STARE ZASADY": "Stare zasady",
}
"""Warianty wejścia kolumny `Zasady rozliczania` (wielkimi literami po `.upper()`)
zmapowane na literały `custom_zasady_dotacji`, identyczne z `CRM Deal.custom_zasady_dotacji`
(`"Nowe zasady"` / `"Stare zasady"`) - `create_deal()` przepisuje wartość na szansę
bez żadnego dodatkowego mapowania."""

SEPARATOR_UWAG: str = " | "
"""Separator łączonych linii `custom_uwagi_import` - `Lead.vue` dzieli po tym samym
tekście, żeby renderować uwagi jako osobne wiersze."""

NAGLOWKI_ARKUSZA: tuple[str, ...] = (
	"Telefon",
	"Imię",
	"Nazwisko",
	"Adres",
	"Powiat",
	"Województwo",
	"Źródło",
	"Data pozyskania",
	"Status źródła",
	"Zasady rozliczania",
	"Obecne produkty",
	"Produkt w procesie",
	"Zainteresowanie",
	"Uwagi",
)
"""Dokładna, uporządkowana lista 14 nagłówków arkusza „Leady" - `waliduj_naglowek`
rzuca głośno na jakiekolwiek odstępstwo (brak, nadmiar, inna kolejność)."""

_WZOR_ADRES = re.compile(r"^(.*),\s*(\d{2}-\d{3})\s+(.+)$")
"""Kolumna `Adres` w całym arkuszu pasuje do `<reszta>, <kod pocztowy> <miejscowość>[ (dopisek]`.
Grupa 1 jest ZACHŁANNA (`.*`), więc kotwiczy się na OSTATNIM wystąpieniu `, dd-ddd ` w
tekście - przy dwóch przecinkach w adresie („Rogierówko, Ul. Kościuszki 16A, 62-090
Rokietnica") grupa 1 połyka CAŁY fragment przed ostatnim kodem pocztowym, przecinek w
środku włącznie. Patrz `rozbij_adres_arkusza`."""

_WZOR_SEPARATOR_TOKENOW = re.compile(r"[+,/;\s]+")
"""Separatory tokenów w kolumnach wielowartościowych (Obecne produkty, Produkt w
procesie, Źródło) - `_rozloz_tokeny`."""


class WartoscOdrzucona(ValueError):
	"""Podniesione przez normalizator kolumny słownikowej, gdy wartość nie pasuje do
	zadanego zbioru tokenów/etykiet - patrz `_rozloz_tokeny` i `normalizuj_zasady`.

	Atrybut `tokeny` niesie surowe (znormalizowane do wielkich liter) tokeny, które nie
	zostały rozpoznane - przydatne przy budowaniu czytelnego raportu odrzuceń bez
	re-parsowania `str(wyjątek)`. Pusty dla normalizatorów, które nie operują na
	tokenach (np. `normalizuj_zasady`)."""

	def __init__(self, powod: str, tokeny: tuple[str, ...] = ()) -> None:
		super().__init__(powod)
		self.tokeny = tokeny


class OdrzuconePole(NamedTuple):
	"""Jeden wpis raportu odrzuceń - jedno pole jednego wiersza, którego wartość nie
	dała się znormalizować. `wiersz` to numer wiersza W ARKUSZU EXCELA (nagłówek to
	wiersz 1), `telefon` to znormalizowany telefon leada (pusty string wyłącznie gdy
	odrzucany jest sam telefon - patrz `zbuduj_leada_z_arkusza`), `kolumna` to nazwa
	kolumny arkusza dokładnie jak w `NAGLOWKI_ARKUSZA`, `wartosc` to surowy,
	oczyszczony (przycięty) tekst komórki, `powod` to czytelne polskie wyjaśnienie."""

	wiersz: int
	telefon: str
	kolumna: str
	wartosc: str
	powod: str


class AdresRozbity(NamedTuple):
	"""Wynik `rozbij_adres_arkusza` - sześć składowych jednej komórki `Adres`.

	`numer_nierozpoznany_z_cyfra` ma domyślną wartość `False`, żeby istniejące
	konstrukcje `AdresRozbity(...)` bez tego argumentu (testy sprzed b59-#141)
	nadal działały - `True` tylko wtedy, gdy `rozbij_fragment_ulicy` nie
	rozpoznała numeru domu (reguła g), a pozostawiony w `ulica` tekst zawiera
	choć jedną cyfrę (patrz `ulica_zawiera_cyfre`) - `zbuduj_leada_z_arkusza`
	dokłada wtedy wpis informacyjny do raportu odrzuceń."""

	ulica: str
	nr_domu: str
	kod: str
	miejscowosc: str
	dopisek: str
	numer_nierozpoznany_z_cyfra: bool = False


def _pusta(wartosc: str | None) -> bool:
	"""Czy wartość pola arkusza oznacza pustkę.

	Bez rozróżniania wielkości liter dopasowuje `PUSTE_MARKERY`: pustą komórkę, `-`,
	`brak`, `nie` (decyzja właściciela z komentarzy issue #98 - patrz docstring modułu
	o tym, że to poszerzenie nie zmienia zachowania żadnej zachowanej funkcji na jej
	dotychczasowych testach).
	"""
	if wartosc is None:
		return True
	return wartosc.strip().lower() in PUSTE_MARKERY


def _tekst_albo_puste(wartosc: str | None) -> str:
	"""Zwraca oczyszczoną wartość albo pusty string, gdy `_pusta()` uznaje ją za pustkę."""
	if _pusta(wartosc):
		return ""
	assert wartosc is not None
	return wartosc.strip()


def normalizuj_telefon(surowy: str) -> str | None:
	"""Normalizuje numer telefonu do formatu `+48XXXXXXXXX`.

	Akceptuje cztery formaty spotykane w źródłowym arkuszu: `48XXXXXXXXX`,
	`+48XXXXXXXXX`, gołe 9 cyfr (opcjonalnie z odstępami, myślnikami albo
	kropkami jako separatorami, np. `604-932-720`) oraz uszkodzone przez
	Excela wartości z twardymi spacjami (`\\xa0`) i końcówką `,00` (np.
	`"507\\xa0063\\xa0129,00"`). Separatory są usuwane PRZED walidacją
	formatu, więc pola z kilkoma numerami naraz (przecinek, ukośnik) albo
	z literami/notacją naukową nadal poprawnie odpadają — walidacja końcowa
	akceptuje wyłącznie same cyfry w długości 9 albo 11 (z prefiksem 48).
	Wszystko inne — za krótkie, z literami, 12-cyfrowe bez prefiksu 48 —
	zwraca `None`.
	"""
	if not surowy:
		return None
	oczyszczony = (
		surowy.replace("\xa0", "")
		.replace(" ", "")
		.replace("-", "")
		.replace(".", "")
		.strip()
	)
	if oczyszczony.endswith(",00"):
		oczyszczony = oczyszczony[:-3]
	if not oczyszczony:
		return None
	ma_plus = oczyszczony.startswith("+")
	same_cyfry = oczyszczony[1:] if ma_plus else oczyszczony
	if not same_cyfry.isdigit():
		return None
	if same_cyfry.startswith("48") and len(same_cyfry) == 11:
		numer_9_cyfr = same_cyfry[2:]
	elif len(same_cyfry) == 9:
		numer_9_cyfr = same_cyfry
	else:
		return None
	return f"+48{numer_9_cyfr}"


def normalizuj_date(surowa: str) -> str | None:
	"""Normalizuje datę do ISO `YYYY-MM-DD`.

	Akceptuje `YYYY-MM-DD`, `DD-MM-YYYY` i `D-M-YYYY` (dzień/miesiąc bez
	wiodącego zera). Puste wartości i śmieci (w tym daty kalendarzowo
	niepoprawne, np. 31 lutego) zwracają `None`.
	"""
	if _pusta(surowa):
		return None
	tekst = surowa.strip()
	czesci = tekst.split("-")
	if len(czesci) != 3:
		return None
	if len(czesci[0]) == 4:
		rok, miesiac, dzien = czesci
	elif len(czesci[2]) == 4:
		dzien, miesiac, rok = czesci
	else:
		return None
	if not (rok.isdigit() and miesiac.isdigit() and dzien.isdigit()):
		return None
	try:
		data = datetime.date(int(rok), int(miesiac), int(dzien))
	except ValueError:
		return None
	return data.isoformat()


def normalizuj_kod(surowy: str) -> str | None:
	"""Normalizuje polski kod pocztowy do formatu `dd-ddd`. Wszystko inne zwraca `None`."""
	if _pusta(surowy):
		return None
	tekst = surowy.strip()
	if len(tekst) != 6 or tekst[2] != "-":
		return None
	prefiks, sufiks = tekst[:2], tekst[3:]
	if not (prefiks.isdigit() and sufiks.isdigit()):
		return None
	return tekst


def normalizuj_wojewodztwo(surowe: str) -> str | None:
	"""Normalizuje nazwę województwa do kanonicznej, małoliterowej formy z 16-elementowej listy.

	`brak`, `-`, puste i cokolwiek spoza kanonu zwraca `None`.
	"""
	if _pusta(surowe):
		return None
	kandydat = surowe.strip().lower()
	if kandydat in KANONICZNE_WOJEWODZTWA:
		return kandydat
	return None


def mapuj_zainteresowanie(surowe: str) -> str | None:
	"""Mapuje kolumnę `Zainteresowanie` na etykietę `custom_product_interest`.

	Rozpoznaje tokeny `PC`, `PV`, `MGZ` (w dowolnym połączeniu przez `+`, `/`,
	`,` albo spację, np. `PC+MGZ`) i składa je w jedną etykietę zachowując
	kolejność pierwszego wystąpienia, bez powtórzeń. Brak rozpoznanego tokenu
	(kwoty, `brak`, `-`, tekst wolny) zwraca `None`.
	"""
	if _pusta(surowe):
		return None
	tekst = surowe.strip().upper()
	czesci = re.split(r"[+/,\s]+", tekst)
	rozpoznane: list[str] = []
	for czesc in czesci:
		etykieta = TOKENY_ZAINTERESOWANIA.get(czesc)
		if etykieta and etykieta not in rozpoznane:
			rozpoznane.append(etykieta)
	if not rozpoznane:
		return None
	return " + ".join(rozpoznane)


def ulica_zawiera_cyfre(tekst: str) -> bool:
	"""Czy `tekst` (fragment ulicy pozostawiony BEZ rozpoznanego numeru domu -
	`rozbij_fragment_ulicy` reguła g) zawiera choć jedną cyfrę.

	Używane przez `rozbij_adres_arkusza`/`zbuduj_leada_z_arkusza`, żeby odróżnić
	zwykły „brak numeru" (np. „Blizińskiego" - nic do zgłoszenia) od przypadku,
	gdzie w Ulicy został jakiś nierozpoznany numer/tekst z cyfrą (np. „Rzepkowo
	14m2", „1952-01-22T00:00:00") - ten drugi przypadek dostaje wpis
	informacyjny w raporcie odrzuceń."""
	return any(znak.isdigit() for znak in (tekst or ""))


def _znormalizuj_numer(numer: str, numer2: str | None) -> str:
	"""Składa numer domu z grup regexu tolerancyjnego dopasowania (reguły d/e):
	`("22", "A")` -> `"22/A"`, `("34", None)` -> `"34"`, `("21 A", None)` ->
	`"21A"` (odstęp przed literą - patrz `_CZESC_NUMERU_GLOWNA` - jest usuwany
	tu, w JEDNYM miejscu). Wielkość liter obu części zostaje bez zmian (spec:
	„litera bez zmian")."""
	numer_czysty = re.sub(r"\s+", "", numer)
	if numer2:
		numer2_czysty = re.sub(r"\s+", "", numer2)
		return f"{numer_czysty}/{numer2_czysty}"
	return numer_czysty


def _usun_prefiks_ulicy(tekst: str) -> str:
	"""Usuwa wiodący prefiks 'ul.'/'ul'/'ulica' (reguła c) - patrz
	`_WZOR_PREFIKS_ULICY`."""
	return _WZOR_PREFIKS_ULICY.sub("", tekst, count=1)


def _rozbij_c_do_f(segment: str, miejscowosc: str) -> tuple[str, str]:
	"""Rozbija JEDEN segment (cały fragment ulicy, albo jeden kawałek po
	podziale po przecinku - patrz `rozbij_fragment_ulicy`) na `(ulica,
	nr_domu)`, stosując reguły c-f w tej kolejności; `nr_domu` pusty oznacza
	regułę g („numer nierozpoznany", NIE odrzucenie - patrz `ulica_zawiera_cyfre`
	i docstring modułu, sekcja Adres)."""
	tekst = (segment or "").strip()
	if not tekst:
		return "", ""

	# c) prefiks 'ul.'/'ul'/'ulica'
	tekst = _usun_prefiks_ulicy(tekst).strip()
	if not tekst:
		return "", ""

	# d) numer na końcu, tolerancyjnie - ze słowem 'nr' MA PIERWSZEŃSTWO przed
	# wzorcem bez 'nr' (patrz docstring `_WZOR_NUMER_Z_NR`)
	dopasowanie = _WZOR_NUMER_Z_NR.match(tekst) or _WZOR_NUMER_ZWYKLY.match(tekst)
	if dopasowanie:
		ulica = dopasowanie.group("ulica").strip()
		if ulica and not _WZOR_KOD_POCZTOWY.match(ulica):
			numer = _znormalizuj_numer(dopasowanie.group("numer"), dopasowanie.group("numer2"))
			return ulica, numer

	# e) numer sklejony bez odstępu - TYLKO gdy cały tekst to jeden token bez
	# białych znaków (patrz docstring `_WZOR_NUMER_SKLEJONY`)
	if not re.search(r"\s", tekst):
		dopasowanie_sklejone = _WZOR_NUMER_SKLEJONY.match(tekst)
		if dopasowanie_sklejone:
			ulica = dopasowanie_sklejone.group("ulica").strip()
			if ulica and not _WZOR_KOD_POCZTOWY.match(ulica):
				numer = _znormalizuj_numer(
					dopasowanie_sklejone.group("numer"), dopasowanie_sklejone.group("numer2")
				)
				return ulica, numer

	# f) cały (pozostały) tekst to sam numer domu (wieś bez nazwy ulicy) - w
	# tym zapis Excela "4.0"/"1.0" dla liczb całkowitych
	kandydat_sam_numer = tekst[:-2] if _WZOR_SAM_NUMER_KROPKA.match(tekst) else tekst
	if _WZOR_SAM_NUMER.match(kandydat_sam_numer):
		miasto_czyste = (miejscowosc or "").strip()
		if miasto_czyste:
			return miasto_czyste, re.sub(r"\s+", "", kandydat_sam_numer)

	# g) numer nierozpoznany - segment zostaje w całości jako ulica
	return tekst, ""


def _wyciagnij_nawias(tekst: str) -> tuple[str, str]:
	"""Wyciąga treść PIERWSZEGO nawiasu z `tekst` (także niedomkniętego -
	obcięta komórka Excela) - `rozbij_fragment_ulicy` reguła a. Zwraca
	`(tekst_bez_nawiasu, tresc_nawiasu)`; brak `(` zwraca `(tekst, "")` bez
	zmian."""
	if "(" not in tekst:
		return tekst, ""
	przed, _, po_nawiasie = tekst.partition("(")
	if ")" in po_nawiasie:
		tresc, _, po_zamknieciu = po_nawiasie.partition(")")
		pozostaly = f"{przed.rstrip()} {po_zamknieciu.strip()}".strip()
	else:
		tresc = po_nawiasie
		pozostaly = przed.strip()
	return pozostaly, tresc.strip()


_WZOR_KOD_POCZTOWY_PREFIKS = re.compile(r"^\d{2}-\d{3}\s+")
"""Wiodący kod pocztowy Z ODSTĘPEM na początku segmentu (np. „62-640
Boryslawice Kościelne 20" - drugi kod pocztowy sklejony przecinkiem bez
spacji do pierwszego trafia jako OSTATNI segment po podziale po przecinku,
z tym wiodącym kodem) - `_podziel_segmenty_przecinkiem` zdejmuje ten prefiks,
NIE cały segment (w odróżnieniu od `_WZOR_KOD_POCZTOWY`, który dopasowuje
segment BĘDĄCY w całości kodem pocztowym i taki segment odrzuca)."""


def _podziel_segmenty_przecinkiem(tekst: str) -> list[str]:
	"""Dzieli `tekst` po przecinku, przycina każdy kawałek i odrzuca puste
	segmenty (wg `_pusta` - a więc też sam „-"/„brak"/„nie") oraz segmenty
	wyglądające jak kod pocztowy (`_WZOR_KOD_POCZTOWY`, cały segment). Segment
	zaczynający się od kodu pocztowego Z DALSZYM tekstem po nim (np. „62-640
	Boryslawice Kościelne 20") ma ten wiodący kod ZDJĘTY, nie jest odrzucany w
	całości - `_WZOR_KOD_POCZTOWY_PREFIKS`. Używane zarówno przez
	`rozbij_fragment_ulicy` (reguła b) jak i `rozbij_adres_arkusza` (część PO
	kodzie pocztowym, gdy ta też niesie przecinki)."""
	wynik: list[str] = []
	for czesc in (surowa.strip() for surowa in tekst.split(",")):
		if not czesc or _pusta(czesc):
			continue
		if _WZOR_KOD_POCZTOWY.match(czesc):
			continue
		czesc = _WZOR_KOD_POCZTOWY_PREFIKS.sub("", czesc, count=1).strip()
		if czesc:
			wynik.append(czesc)
	return wynik


def rozbij_fragment_ulicy(fragment: str, miejscowosc: str) -> tuple[str, str, str]:
	"""Rozbija fragment ulicy (część komórki `Adres` PRZED kodem pocztowym) na
	`(ulica, nr_domu, dopisek_dodatkowy)`, tolerancyjnie rozpoznając numer domu
	(uniformizacja danych z arkusza Grega, b59). Reguły stosowane W TEJ
	KOLEJNOŚCI:

	a) Nawias w środku fragmentu (np. „Kolejowa (budynek ma mieć odbiór...)"),
	   także niedomknięty (obcięta komórka Excela) - treść nawiasu jest
	   usuwana z fragmentu i dokładana do dopisku (patrz `_wyciagnij_nawias`).
	b) Segmenty po przecinku (np. „Rogierówko, Ul. Kościuszki 16A", „ul.
	   Szafranowa 14, Jezierzyce") - fragment (PO usunięciu nawiasu) jest
	   dzielony po przecinku (`_podziel_segmenty_przecinkiem`, odrzuca puste i
	   segmenty-kody-pocztowe). Segmentem ulicy zostaje PIERWSZY segment, który
	   po regułach c-f daje rozpoznany numer domu; jeśli żaden segment go nie
	   da, segmentem ulicy zostaje OSTATNI segment (numer wtedy pusty - reguła
	   g). Pozostałe segmenty (w oryginalnej kolejności) trafiają do dopisku,
	   złączone przecinkiem.
	c-f) Patrz `_rozbij_c_do_f`: prefiks 'ul.'/'ulica' zdjęty, numer domu
	   rozpoznany tolerancyjnie (ze słowem 'nr' albo bez, sklejony bez
	   odstępu, albo cały segment to sam numer - wieś bez ulicy).
	g) Brak rozpoznanego numeru - segment (po c) zostaje w całości jako
	   `ulica`, `nr_domu` pusty. To NIE jest odrzucenie - `ulica_zawiera_cyfre`
	   decyduje, czy wywołujący dołoży wpis informacyjny do raportu.

	Dopiski z a) i b) łączą się w jedną wartość `dopisek_dodatkowy`, segmenty
	złączone przecinkiem (pusta lista dopiskow daje pusty string)."""
	tekst = (fragment or "").strip()
	dopisek_czesci: list[str] = []

	tekst, dopisek_nawiasu = _wyciagnij_nawias(tekst)
	if dopisek_nawiasu:
		dopisek_czesci.append(dopisek_nawiasu)

	if "," in tekst:
		segmenty = _podziel_segmenty_przecinkiem(tekst)
		if not segmenty:
			ulica, nr_domu = "", ""
		else:
			wybrany_indeks: int | None = None
			wybrany_wynik: tuple[str, str] | None = None
			for indeks, segment in enumerate(segmenty):
				kandydat_ulica, kandydat_nr = _rozbij_c_do_f(segment, miejscowosc)
				if kandydat_nr:
					wybrany_indeks = indeks
					wybrany_wynik = (kandydat_ulica, kandydat_nr)
					break
			if wybrany_wynik is None:
				wybrany_indeks = len(segmenty) - 1
				wybrany_wynik = _rozbij_c_do_f(segmenty[-1], miejscowosc)
			ulica, nr_domu = wybrany_wynik
			pozostale = [s for i, s in enumerate(segmenty) if i != wybrany_indeks]
			if pozostale:
				dopisek_czesci.append(", ".join(pozostale))
	else:
		ulica, nr_domu = _rozbij_c_do_f(tekst, miejscowosc)

	dopisek_dodatkowy = ", ".join(dopisek_czesci)
	return ulica, nr_domu, dopisek_dodatkowy


def normalizuj_pisownie_osoby(tekst: str) -> str:
	"""Normalizuje pisownię imienia/nazwiska do formy „pierwsza litera wielka,
	reszta mała" na KAŻDYM słowie, także po myślniku i apostrofie (decyzja
	właściciela 2026-09-16, ujednolicenie pisowni: „RADOSŁAW GIEREMEK" ->
	„Radosław Gieremek", „kowalska-nowak" -> „Kowalska-Nowak", „o'brien" ->
	„O'Brien").

	`str.title()` już dzieli słowa na każdym znaku niealfabetycznym (spacja,
	myślnik, apostrof włącznie) i poprawnie obsługuje polskie diakrytyki w
	tablicach Unicode Pythona 3 (`"ŁUKASZ".title() == "Łukasz"`,
	`"ŚWIĘTOSŁAWA".title() == "Świętosława"`) - ta funkcja jest cienką warstwą
	nad `str.title()`, tylko po to, żeby mieć jedno udokumentowane miejsce dla
	tej decyzji i przyszłych wyjątków. Puste wejście zwraca bez zmian.

	Wywoływana W `zbuduj_leada_z_arkusza` PO `rozdziel_imie_nazwisko`, NIGDY
	gdy `_wyglada_na_firme` rozpoznaje firmę w oryginalnej (nierozbitej)
	kolumnie `Imię` - firmowa pisownia zostaje bez zmian. Ulice NIE przechodzą
	przez tę funkcję - ryzyko przy nazwach typu „dywizjonu 303" albo „Zbyszka
	z Bogdańca", gdzie title-case psułby sens (patrz docstring modułu)."""
	if not tekst:
		return tekst
	return tekst.title()


def _wyglada_na_firme(tekst: str) -> bool:
	"""Czy wielowyrazowy tekst z kolumny `Imię` wygląda na nazwę firmy, nie osobę.

	Sprawdza każde słowo osobno (rozdzielone białymi znakami), po ujednoliceniu
	do wielkich liter i obcięciu otaczających kropek/przecinków — dopasowanie
	jako CAŁE słowo z `MARKERY_FIRMY`, nie podciąg (żeby np. nazwisko
	zawierające "biuro" w środku dłuższego słowa nie dało fałszywego trafienia).
	`HANDLOW*` jest jedynym wyjątkiem dopasowywanym prefiksem (`HANDLOWA`,
	`HANDLOWY`, `HANDLOWE`... są zbyt liczne, żeby wymieniać je z osobna) —
	świadomy kompromis: nazwisko takie jak „Handlowski" też by tu trafiło,
	ale w praktyce firmowe „(Firma/Usługi) Handlow*" jest znacznie częstsze
	w tym pliku niż takie nazwisko w polu wielowyrazowym bez Nazwiska.
	"""
	for surowe_slowo in tekst.split():
		oczyszczone = surowe_slowo.strip(".,").upper()
		if not oczyszczone:
			continue
		if oczyszczone in MARKERY_FIRMY:
			return True
		if oczyszczone.startswith("HANDLOW"):
			return True
	return False


def rozdziel_imie_nazwisko(imie: str, nazwisko: str) -> tuple[str, str]:
	"""Rozdziela sklejone imię i nazwisko z kolumny `Imię`, gdy `Nazwisko` jest puste.

	Gdy `nazwisko` jest już niepuste — zwraca oba pola bez zmian (po
	ujednoliceniu pustki wg `_pusta()`). Gdy `imie` jest jednowyrazowe albo
	puste, też bez zmian, nie ma czego dzielić.

	Dla wielowyrazowego `imie` przy pustym `nazwisko`:
	- wygląda na firmę (`_wyglada_na_firme`) → CAŁOŚĆ zostaje w `first_name`,
	  tak jak dziś — firm się nie dzieli na imię/nazwisko;
	- dokładnie 2 słowa → (słowo1, słowo2);
	- 3 i więcej słów → (pierwsze słowo, reszta razem). Świadomy kompromis
	  odnotowany w issue ops#30: to poprawnie zostawia w całości podwójne
	  nazwiska („Ratajczak Witkowska") i partykuły („de Groot") w
	  `last_name`, kosztem tego, że drugie imię („Katarzyna" w „Agnieszka
	  Katarzyna Marciniak") trafia do `last_name` razem z właściwym
	  nazwiskiem zamiast zostać osobno rozpoznane.
	"""
	imie_czyste = _tekst_albo_puste(imie)
	nazwisko_czyste = _tekst_albo_puste(nazwisko)
	if nazwisko_czyste:
		return imie_czyste, nazwisko_czyste
	if not imie_czyste:
		return imie_czyste, nazwisko_czyste
	slowa = imie_czyste.split()
	if len(slowa) < 2:
		return imie_czyste, nazwisko_czyste
	if _wyglada_na_firme(imie_czyste):
		return imie_czyste, nazwisko_czyste
	return slowa[0], " ".join(slowa[1:])


def _rozloz_tokeny(tekst: str, dozwolone: tuple[str, ...]) -> str:
	"""Rozkłada tekst na tokeny oddzielone `+`, `,`, `/`, `;` albo białym znakiem,
	ujednolica do wielkich liter, usuwa duplikaty i składa wynik z powrotem w
	kolejności `dozwolone` (NIE w kolejności wystąpienia w tekście źródłowym).

	Każdy token musi być w `dozwolone` - inaczej CAŁE pole jest odrzucone
	(`WartoscOdrzucona`, kontrakt z Gregiem dla kolumn Obecne produkty, Produkt w
	procesie i Źródło: jeden nierozpoznany token unieważnia całe pole, nie tylko ten
	token). Pusty `tekst` zwraca pusty string - w praktyce wywołujący
	(`_pole_slownikowe`) już wcześniej odsiał puste komórki, więc ta gałąź służy
	głównie bezpośrednim wywołaniom z testów.
	"""
	if not tekst or not tekst.strip():
		return ""
	surowe = [czesc for czesc in _WZOR_SEPARATOR_TOKENOW.split(tekst.strip()) if czesc]
	tokeny = [czesc.upper() for czesc in surowe]
	nieznane = tuple(token for token in tokeny if token not in dozwolone)
	if nieznane:
		raise WartoscOdrzucona(f"nieznany token: {', '.join(nieznane)}", nieznane)
	unikalne = set(tokeny)
	return "+".join(token for token in dozwolone if token in unikalne)


def normalizuj_posiadane_produkty(tekst: str) -> str:
	"""Normalizuje kolumnę `Obecne produkty` (co klient już ma) do tokenów `+`
	w kolejności `KOLEJNOSC_PRODUKTOW`. Patrz `_rozloz_tokeny`."""
	return _rozloz_tokeny(tekst, KOLEJNOSC_PRODUKTOW)


def normalizuj_produkt_procesu(tekst: str) -> str:
	"""Normalizuje kolumnę `Produkt w procesie` (co się teraz dzieje) do tokenów `+`
	w kolejności `KOLEJNOSC_PRODUKTOW_PROCESU`. Patrz `_rozloz_tokeny`."""
	return _rozloz_tokeny(tekst, KOLEJNOSC_PRODUKTOW_PROCESU)


def normalizuj_zrodlo(tekst: str) -> str:
	"""Normalizuje kolumnę `Źródło` do tokenów `+` w kolejności `KOLEJNOSC_ZRODEL`.
	Patrz `_rozloz_tokeny`."""
	return _rozloz_tokeny(tekst, KOLEJNOSC_ZRODEL)


def normalizuj_status_zrodla(tekst: str) -> str | None:
	"""Normalizuje kolumnę `Status źródła` do jednej z czterech kanonicznych wartości
	`STATUSY_ZRODLA` (dopasowanie bez rozróżniania wielkości liter). Wszystko poza
	tymi czterema słowami zwraca `None` - w arkuszu Grega ta kolumna nie niesie
	śmieci (w przeciwieństwie do Zasad rozliczania, patrz `normalizuj_zasady`), więc
	`None` jest tu wyłącznie teoretycznym zabezpieczeniem."""
	kandydat = tekst.strip()
	for kanoniczny in STATUSY_ZRODLA:
		if kandydat.lower() == kanoniczny.lower():
			return kanoniczny
	return None


def domyslny_status_zrodla(zrodlo: str) -> str | None:
	"""Domyślna wartość `custom_status_zrodla`, gdy komórka `Status źródła` jest pusta.

	`Potencjał`, gdy znormalizowane `zrodlo` zawiera `CC` albo `SD` (ktoś z call
	center albo telemarketingu miał kontakt z leadem) - inaczej `None` (sam `ARG`,
	baza zakupiona bez żadnego kontaktu, nie zasługuje na zgadywany status)."""
	zrodlo_upper = (zrodlo or "").upper()
	if "CC" in zrodlo_upper or "SD" in zrodlo_upper:
		return "Potencjał"
	return None


def normalizuj_zasady(tekst: str) -> str:
	"""Normalizuje kolumnę `Zasady rozliczania` do literału `custom_zasady_dotacji`
	(`"Nowe zasady"` / `"Stare zasady"`, identycznego z `CRM Deal.custom_zasady_dotacji`).

	Akceptuje cztery warianty wejścia bez rozróżniania wielkości liter: `NOWE`,
	`STARE`, `Nowe zasady`, `Stare zasady` (patrz `ZASADY_DOTACJI`). W arkuszu Grega
	11 wierszy niesie w tej kolumnie śmieci - nazwy nagłówków innych kolumn wklejone
	przez pomyłkę (`Telefon`, `Adres`, ...) - dla nich funkcja RZUCA
	`WartoscOdrzucona` zamiast zwracać `None`: to jedyny normalizator kolumny
	słownikowej w tym module, który zawsze rzuca zamiast czasem zwracać `None`, bo
	każde wywołanie tej funkcji z `_pole_slownikowe` dostaje już niepustą wartość
	(puste komórki są odsiane wcześniej) - nie ma tu przypadku "poprawnie puste".
	"""
	kandydat = tekst.strip().upper()
	if kandydat in ZASADY_DOTACJI:
		return ZASADY_DOTACJI[kandydat]
	raise WartoscOdrzucona(f"nieznana wartosc zasad rozliczania: {tekst.strip()}")


def rozbij_adres_arkusza(adres: str) -> AdresRozbity | None:
	"""Rozbija komórkę `Adres` arkusza Grega na `AdresRozbity`.

	Format źródłowy: `<fragment ulicy>, <kod pocztowy> <miejscowość>[ (dopisek]`.
	Brak dopasowania do `_WZOR_ADRES` (patrz jej docstring o zachłannej grupie 1)
	zwraca `None` - CAŁE pole Adres jest wtedy odrzucane przez wywołującego
	(`zbuduj_leada_z_arkusza`), surowy tekst zostaje bez zmian.

	Miejscowość: część PO kodzie pocztowym też bywa z przecinkiem (np. „-,
	66-010 Przybymierz,", „-, 72-006 Dołuje,Mierzyn", „-, 78-627 Wałcz,
	Różewo", „-, 23-114 Jabłonna (gmina), Chmiel Kolonia- miejscowość" -
	decyzja właściciela po QA parsera, 2026-09-16): nawias jest najpierw
	wycięty (`_wyciagnij_nawias`, tak jak dotąd - obsługuje też obcięty bez
	zamykającego `)`), reszta idzie przez `_podziel_segmenty_przecinkiem`;
	miejscowością zostaje PIERWSZY niepusty segment (przycięty, bez końcowej
	interpunkcji `,;.`), pozostałe segmenty trafiają do dopisku razem z
	treścią nawiasu (nawias pierwszy, potem segmenty, złączone przecinkiem).

	Fragment ulicy równy `-` (albo pusty wg `_pusta`) - wieś bez nazwy ulicy -
	daje `ulica = miejscowość`, `nr_domu = ""` (decyzja właściciela, issue
	#116, 2026-09-09: OBA pola niosą tę samą wartość). W pozostałych
	przypadkach fragment idzie przez `rozbij_fragment_ulicy(fragment,
	miejscowosc)` (patrz jej docstring dla pełnych reguł a-g rozpoznawania
	numeru domu). `numer_nierozpoznany_z_cyfra` jest `True` tylko gdy ta druga
	ścieżka nie rozpoznała numeru domu (reguła g), a pozostawiony `ulica`
	zawiera choć jedną cyfrę (`ulica_zawiera_cyfre`) - NIGDY dla ścieżki
	"wieś bez ulicy" powyżej, gdzie brak numeru jest oczekiwany, nie błędny.

	`dopisek` łączy dopisek zwrócony przez `rozbij_fragment_ulicy` (nawiasy w
	środku fragmentu, segmenty odrzucone przy podziale po przecinku) z
	dopiskiem-po-miejscowości, segmenty złączone przecinkiem."""
	tekst = (adres or "").strip()
	if not tekst:
		return None
	dopasowanie = _WZOR_ADRES.match(tekst)
	if not dopasowanie:
		return None
	czesc_ulicy = dopasowanie.group(1).strip()
	kod = dopasowanie.group(2)
	reszta = dopasowanie.group(3).strip()

	reszta_bez_nawiasu, dopisek_nawiasu = _wyciagnij_nawias(reszta)
	segmenty_miejscowosci = _podziel_segmenty_przecinkiem(reszta_bez_nawiasu)
	if segmenty_miejscowosci:
		miejscowosc = segmenty_miejscowosci[0].rstrip(",;.")
		dopisek_pozostale_segmenty = ", ".join(segmenty_miejscowosci[1:])
	else:
		miejscowosc = ""
		dopisek_pozostale_segmenty = ""
	segmenty_dopisku_miejscowosci = [d for d in (dopisek_nawiasu, dopisek_pozostale_segmenty) if d]
	dopisek_miejscowosci = ", ".join(segmenty_dopisku_miejscowosci)

	if _pusta(czesc_ulicy):
		ulica, nr_domu, dopisek_fragmentu = miejscowosc, "", ""
		numer_nierozpoznany_z_cyfra = False
	else:
		ulica, nr_domu, dopisek_fragmentu = rozbij_fragment_ulicy(czesc_ulicy, miejscowosc)
		numer_nierozpoznany_z_cyfra = not nr_domu and ulica_zawiera_cyfre(ulica)

	segmenty_dopisku = [d for d in (dopisek_fragmentu, dopisek_miejscowosci) if d]
	dopisek = ", ".join(segmenty_dopisku)

	return AdresRozbity(
		ulica=ulica,
		nr_domu=nr_domu,
		kod=kod,
		miejscowosc=miejscowosc,
		dopisek=dopisek,
		numer_nierozpoznany_z_cyfra=numer_nierozpoznany_z_cyfra,
	)


def normalizuj_uwagi(tekst: str, dopisek_adresu: str = "") -> str:
	"""Buduje `custom_uwagi_import` z kolumny `Uwagi`.

	Rozdziela na linie po `|` (separator w arkuszu Grega), przycina każdą linię i
	odrzuca puste wg `_pusta()` (a więc też same `-`/`brak`/`nie` jako fragment -
	spójnie z resztą modułu, nie tylko dosłowny pusty string). Gdy `dopisek_adresu` jest niepusty (dopisek w nawiasie po
	miejscowości z kolumny Adres - decyzja właściciela 2026-09-16: dopisek NIE
	trafia do `custom_install_city`, tylko do uwag), dokleja go jako OSTATNIĄ linię
	w formacie `"Adres (dopisek): <tekst>"`. Wynik złączony `SEPARATOR_UWAG` -
	`Lead.vue` dzieli po tym samym separatorze, żeby renderować uwagi jako osobne
	wiersze."""
	surowe = (tekst or "").split("|")
	linie = [linia.strip() for linia in surowe if not _pusta(linia)]
	if dopisek_adresu:
		linie.append(f"Adres (dopisek): {dopisek_adresu.strip()}")
	return SEPARATOR_UWAG.join(linie)


def waliduj_naglowek(naglowek: list[str]) -> None:
	"""Waliduje nagłówek arkusza względem `NAGLOWKI_ARKUSZA` (dokładna kolejność).

	Toleruje wiodący BOM (`\\ufeff`, częsty w plikach zapisanych z Excela) i
	otaczające białe znaki w każdej komórce nagłówka. Brakująca, nadmiarowa albo
	przestawiona kolumna to twardy błąd (`ValueError` z nazwami) - zmiana kształtu
	arkusza ma się ujawnić głośno, zanim jakikolwiek wiersz zostanie źle zmapowany
	na kolumny."""
	oczyszczony = [(pole or "").lstrip("\ufeff").strip() for pole in naglowek]
	oczekiwany = list(NAGLOWKI_ARKUSZA)
	if oczyszczony == oczekiwany:
		return
	brakujace = [nazwa for nazwa in oczekiwany if nazwa not in oczyszczony]
	nadmiarowe = [nazwa for nazwa in oczyszczony if nazwa not in oczekiwany]
	raise ValueError(
		"Naglowek arkusza nie zgadza sie z oczekiwanym formatem. "
		f"Brakujace kolumny: {brakujace or '(brak)'}. "
		f"Nadmiarowe kolumny: {nadmiarowe or '(brak)'}. "
		f"Otrzymano: {oczyszczony}."
	)


def wczytaj_arkusz(tekst_csv: str) -> list[dict[str, str]]:
	"""Wczytuje CSV (jako string) arkusza Grega do listy słowników, po jednym na wiersz.

	Nagłówek jest walidowany przez `waliduj_naglowek` (rzuca głośno na niezgodność)
	- od tego momentu klucze każdego wiersza to zawsze dokładnie `NAGLOWKI_ARKUSZA`.
	Pusty plik (brak nawet nagłówka) zwraca pustą listę. Wiersze krótsze niż
	nagłówek są dopełniane pustymi polami, dłuższe - przycinane; żaden wiersz nie
	wywala funkcji z powodu samej długości.

	Indeks `i` zwróconej listy odpowiada wierszowi Excela `i + 2` (nagłówek to
	wiersz 1, pierwszy wiersz danych to wiersz 2) - konwencja używana przez
	`wykryj_duble_telefonow` i przez importer w `ops/`."""
	czytnik = csv.reader(io.StringIO(tekst_csv))
	try:
		naglowek_surowy = next(czytnik)
	except StopIteration:
		return []
	waliduj_naglowek(naglowek_surowy)
	wiersze: list[dict[str, str]] = []
	for wiersz_surowy in czytnik:
		if len(wiersz_surowy) < len(NAGLOWKI_ARKUSZA):
			wiersz_wyrownany = wiersz_surowy + [""] * (len(NAGLOWKI_ARKUSZA) - len(wiersz_surowy))
		else:
			wiersz_wyrownany = wiersz_surowy[: len(NAGLOWKI_ARKUSZA)]
		wiersze.append(dict(zip(NAGLOWKI_ARKUSZA, wiersz_wyrownany, strict=True)))
	return wiersze


def wykryj_duble_telefonow(wiersze: list[dict[str, str]]) -> dict[int, int]:
	"""Wykrywa duble numeru telefonu w liście wierszy z `wczytaj_arkusz`.

	Zwraca `{numer_wiersza_pozniejszego: numer_wiersza_pierwszego}` dla KAZDEGO
	powtorzonego, poprawnego numeru telefonu (wg `normalizuj_telefon`) -
	numeracja to numer wiersza w Excelu (naglowek = wiersz 1, pierwszy wiersz
	danych = wiersz 2), czyli indeks w `wiersze` + 2 (patrz `wczytaj_arkusz`).
	Wiersze z nieprawidlowym telefonem sa pomijane - o odrzuceniu calego wiersza
	z tego powodu decyduje `zbuduj_leada_z_arkusza`, nie ta funkcja."""
	pierwsze_wystapienie: dict[str, int] = {}
	duble: dict[int, int] = {}
	for i, wiersz in enumerate(wiersze):
		nr_wiersza = i + 2
		telefon = normalizuj_telefon(wiersz.get("Telefon", ""))
		if telefon is None:
			continue
		if telefon in pierwsze_wystapienie:
			duble[nr_wiersza] = pierwsze_wystapienie[telefon]
		else:
			pierwsze_wystapienie[telefon] = nr_wiersza
	return duble


_PRIORYTET_STATUSU_ZRODLA: tuple[str, ...] = ("Wygrana", "Potencjał", "Przegrana", "Nieaktualna")
"""Priorytet `Status źródła` przy scalaniu dubli (`scal_duble`) - pierwsza
wartość z tej listy znaleziona wśród obu scalanych wierszy wygrywa."""

_KOLUMNY_SUMA_TOKENOW_PRZECINEK: frozenset[str] = frozenset({"Obecne produkty", "Produkt w procesie"})
"""Kolumny `scal_duble` sumuje tekstowo (surowo, złączone przecinkiem) zamiast
brać pierwszą niepustą wartość - normalizacja/dedup tokenów i tak dzieje się
później, w `_rozloz_tokeny`."""


def _polacz_tokeny_scalania(a: str, b: str, separator: str) -> str:
	"""Łączy dwie surowe komórki `separator`-em, pomijając puste wg `_pusta`
	(np. `Źródło` „SD"+„CC" -> „SD CC", `Obecne produkty` „PV"+„PC" ->
	„PV,PC") - `scal_duble`. Normalizację/dedup tokenów robi dopiero
	`_rozloz_tokeny` w `zbuduj_leada_z_arkusza`."""
	czesci = [c.strip() for c in (a, b) if not _pusta(c)]
	return separator.join(czesci)


def _polacz_uwagi_scalania(a: str, b: str) -> str:
	"""Doklejenie uwag przy scalaniu dubli - `a` + `|` + `b`, puste pomijane -
	`scal_duble`. Ten sam separator `|` co w arkuszu, `normalizuj_uwagi`
	dzieli po nim później na osobne linie."""
	czesci = [c.strip() for c in (a, b) if not _pusta(c)]
	return "|".join(czesci)


def _wybierz_status_priorytet(a: str, b: str) -> str:
	"""Wybiera `Status źródła` przy scalaniu dubli wg `_PRIORYTET_STATUSU_ZRODLA`
	(dopasowanie bez rozróżniania wielkości liter) - `scal_duble`. Gdy żadna z
	dwóch wartości nie jest jednym z czterech priorytetowych słów (śmieci w tej
	kolumnie się zdarzają - patrz `normalizuj_status_zrodla`), pierwsza niepusta
	wygrywa; gdy obie puste, zwraca `a` bez zmian."""
	for status in _PRIORYTET_STATUSU_ZRODLA:
		for kandydat in (a, b):
			if not _pusta(kandydat) and kandydat.strip().lower() == status.lower():
				return kandydat.strip()
	for kandydat in (a, b):
		if not _pusta(kandydat):
			return kandydat.strip()
	return a


def _nowsza_data_scalania(a: str, b: str) -> str:
	"""Wybiera `Data pozyskania` przy scalaniu dubli - nowsza z dwóch (porównanie
	przez `normalizuj_date`, więc działa niezależnie od formatu wejścia -
	`scal_duble`). Niepoprawna/pusta data traktowana jak brak; gdy żadna z
	dwóch wartości nie jest poprawną datą, pierwsza niepusta wygrywa (żeby nie
	gubić surowego, choćby nierozpoznanego tekstu)."""
	data_a = normalizuj_date(a) if not _pusta(a) else None
	data_b = normalizuj_date(b) if not _pusta(b) else None
	if data_a and data_b:
		return a.strip() if data_a >= data_b else b.strip()
	if data_a:
		return a.strip()
	if data_b:
		return b.strip()
	for kandydat in (a, b):
		if not _pusta(kandydat):
			return kandydat.strip()
	return a


def _scal_dwa_wiersze(pierwszy: dict[str, str], drugi: dict[str, str]) -> dict[str, str]:
	"""Scala `drugi` wiersz W `pierwszy` (zwraca NOWY słownik, `pierwszy` i
	`drugi` zostają bez zmian - konwencja immutability modułu) wg reguł
	`scal_duble`. `Telefon` zostaje wartością `pierwszy` (oba wiersze mają ten
	sam znormalizowany telefon, inaczej nie trafiłyby tutaj)."""
	wynik = dict(pierwszy)
	for kolumna in NAGLOWKI_ARKUSZA:
		if kolumna == "Telefon":
			continue
		if kolumna == "Źródło":
			wynik[kolumna] = _polacz_tokeny_scalania(pierwszy.get(kolumna, ""), drugi.get(kolumna, ""), " ")
		elif kolumna == "Uwagi":
			wynik[kolumna] = _polacz_uwagi_scalania(pierwszy.get(kolumna, ""), drugi.get(kolumna, ""))
		elif kolumna in _KOLUMNY_SUMA_TOKENOW_PRZECINEK:
			wynik[kolumna] = _polacz_tokeny_scalania(pierwszy.get(kolumna, ""), drugi.get(kolumna, ""), ",")
		elif kolumna == "Status źródła":
			wynik[kolumna] = _wybierz_status_priorytet(pierwszy.get(kolumna, ""), drugi.get(kolumna, ""))
		elif kolumna == "Data pozyskania":
			wynik[kolumna] = _nowsza_data_scalania(pierwszy.get(kolumna, ""), drugi.get(kolumna, ""))
		elif _pusta(pierwszy.get(kolumna, "")):
			# kazda inna pusta komorka pierwszego dopelniana z drugiego
			wynik[kolumna] = drugi.get(kolumna, "")
	return wynik


def scal_duble(
	wiersze: list[dict[str, str]],
) -> tuple[list[tuple[int, dict[str, str]]], list[tuple[int, int]]]:
	"""Grupuje wiersze arkusza po znormalizowanym telefonie (`normalizuj_telefon`)
	i SCALA każdą grupę > 1 w jeden wiersz - kontrakt z Gregiem,
	`docs/LEADY-ARKUSZ-IMPORT-GREG.md`, sekcja „Duble": „importer scali je sam
	po numerze, źródła po plusie, uwagi sklejone" (patrz docstring modułu,
	sekcja Duble telefonu).

	Wiersze z niepoprawnym telefonem (`normalizuj_telefon` zwraca `None`) NIE
	są ze sobą grupowane - każdy taki wiersz to WŁASNA, jednoelementowa grupa
	i zostaje bez zmian (ich odrzucenie należy do `zbuduj_leada_z_arkusza`,
	nie do tej funkcji).

	Scalanie kolejnego wiersza z tym samym numerem DO pierwszego (patrz
	`_scal_dwa_wiersze` dla reguł per kolumna: `Źródło`/`Obecne
	produkty`/`Produkt w procesie` sumują tokeny, `Uwagi` się doklejają,
	`Status źródła` idzie wg priorytetu, `Data pozyskania` bierze nowszą,
	każda inna pusta komórka pierwszego dopełnia się z drugiego).

	Zwraca `(scalone, pary_dubli)`:
	- `scalone`: lista `(nr_wiersza_pierwszego_wystapienia, scalony_wiersz)` w
	  KOLEJNOŚCI PIERWSZYCH WYSTĄPIEŃ (nie w kolejności numeru telefonu ani
	  numeru wiersza scalonego rekordu).
	- `pary_dubli`: lista `(nr_wiersza_pozniejszego, nr_wiersza_pierwszego)` -
	  jeden wpis na KAŻDY scalony (późniejszy) wiersz, do wpisu informacyjnego
	  w raporcie odrzuceń („scalono z wierszem N")."""
	grupy: dict[str, int] = {}  # telefon znormalizowany -> nr_wiersza pierwszego
	wynik_by_nr: dict[int, dict[str, str]] = {}
	kolejnosc: list[int] = []  # nr_wiersza pierwszych wystapien, w kolejnosci
	pary_dubli: list[tuple[int, int]] = []

	for i, wiersz in enumerate(wiersze):
		nr = i + 2
		telefon = normalizuj_telefon(wiersz.get("Telefon", "") or "")
		if telefon is None:
			wynik_by_nr[nr] = dict(wiersz)
			kolejnosc.append(nr)
			continue
		if telefon not in grupy:
			grupy[telefon] = nr
			wynik_by_nr[nr] = dict(wiersz)
			kolejnosc.append(nr)
		else:
			nr_pierwszy = grupy[telefon]
			wynik_by_nr[nr_pierwszy] = _scal_dwa_wiersze(wynik_by_nr[nr_pierwszy], wiersz)
			pary_dubli.append((nr, nr_pierwszy))

	scalone = [(nr, wynik_by_nr[nr]) for nr in kolejnosc]
	return scalone, pary_dubli


def _pole_slownikowe(
	nr_wiersza: int,
	telefon: str,
	kolumna: str,
	surowa: str,
	normalizator: Callable[[str], str | None],
	odrzucone: list[OdrzuconePole],
) -> str | None:
	"""Normalizuje jedną kolumnę słownikową wiersza - wspólny helper dla wszystkich
	ośmiu takich kolumn w `zbuduj_leada_z_arkusza` (Data pozyskania, Status źródła,
	Zasady rozliczania, Obecne produkty, Produkt w procesie, Zainteresowanie,
	Województwo, Źródło).

	Pusta komórka (`_pusta()`) NIGDY nie trafia do raportu odrzuceń - pustka jest
	normalnym stanem większości wierszy tej kolumny, nie błędem - i zwraca `None`
	bez wywoływania `normalizator`. Dla niepustej komórki: `normalizator` może albo
	rzucić `WartoscOdrzucona` (`_rozloz_tokeny`-owe funkcje, `normalizuj_zasady`),
	albo po prostu zwrócić `None` dla wartości, której nie rozpoznaje
	(`normalizuj_date`, `normalizuj_wojewodztwo`, `mapuj_zainteresowanie`,
	`normalizuj_status_zrodla` - niezmienione bądź nieraz-rzucające funkcje). Oba
	przypadki są tu traktowane identycznie: pole wynikowe staje się `None`, wiersz
	dostaje wpis w `odrzucone`, a CAŁY wiersz i tak wchodzi do wyniku (odrzucone
	jest tylko to jedno pole, nigdy lead)."""
	if _pusta(surowa):
		return None
	tekst = surowa.strip()
	try:
		wynik = normalizator(tekst)
	except WartoscOdrzucona as blad:
		odrzucone.append(OdrzuconePole(nr_wiersza, telefon, kolumna, tekst, str(blad)))
		return None
	if wynik is None:
		odrzucone.append(OdrzuconePole(nr_wiersza, telefon, kolumna, tekst, "nierozpoznana wartosc"))
		return None
	return wynik


def zbuduj_leada_z_arkusza(
	wiersz: dict[str, str], nr_wiersza: int
) -> tuple[dict[str, Any] | None, list[OdrzuconePole]]:
	"""Buduje słownik pól `CRM Lead` z jednego wiersza arkusza Grega (`wczytaj_arkusz`).

	Zły telefon (`normalizuj_telefon` zwraca `None`) odrzuca CAŁY wiersz: zwraca
	`(None, [jeden OdrzuconePole dla kolumny "Telefon"])`. W przeciwnym razie zwraca
	`(lead, odrzucone)`, gdzie `odrzucone` może być pustą listą (typowy przypadek) -
	lead wchodzi zawsze, niezależnie od tego, ile jego pól słownikowych zostało po
	drodze odrzuconych (patrz `_pole_slownikowe` i docstring modułu).

	Adres: `rozbij_adres_arkusza` na kolumnie `Adres`; brak dopasowania odrzuca CAŁE
	pole Adres do raportu i zostawia surowy tekst w `custom_install_address` bez
	zmian (`custom_nr_domu`/kod/miejscowość/dopisek zostają puste). Dopisek
	(nawiasy w środku fragmentu ulicy, segmenty odrzucone przy podziale po
	przecinku, dopisek po miejscowości) NIE trafia do `custom_install_city` -
	dokleja się jako ostatnia linia `custom_uwagi_import` przez `normalizuj_uwagi`
	(decyzja właściciela 2026-09-16). Gdy numer domu nie zostanie rozpoznany, a
	pozostawiony w Ulicy tekst zawiera choć jedną cyfrę
	(`AdresRozbity.numer_nierozpoznany_z_cyfra`), dokłada się wpis INFORMACYJNY
	do raportu (powód „numer domu nierozpoznany, tekst zostawiony w Ulicy") -
	to NIE jest odrzucenie, lead i pole Adres wchodzą normalnie.

	Imię/nazwisko: `rozdziel_imie_nazwisko`, potem `normalizuj_pisownie_osoby`
	na obu polach (decyzja właściciela 2026-09-16, ujednolicenie pisowni) -
	POMIJANE, gdy `_wyglada_na_firme` rozpoznaje firmę w surowej kolumnie
	`Imię` (firmowa pisownia zostaje bez zmian).

	Źródło: pusta komórka `Źródło` jest odrzucana z powodem `"wymagane"` (jedyne pole
	tej grupy odrzucane mimo pustki - źródło ma być zawsze wypełnione). Status
	źródła: pusta komórka bierze wartość domyślną z `domyslny_status_zrodla(zrodlo)`
	zamiast trafić do raportu.

	Świadomie BEZ `lead_owner`, `custom_cc`, `custom_lat`/`custom_lng` - przypisanie
	właściciela/CC i geokod to osobne kroki poza tym modułem (ops warstwa)."""
	odrzucone: list[OdrzuconePole] = []

	telefon_surowy = wiersz.get("Telefon", "") or ""
	telefon = normalizuj_telefon(telefon_surowy)
	if telefon is None:
		odrzucone.append(
			OdrzuconePole(nr_wiersza, "", "Telefon", telefon_surowy.strip(), "nieprawidlowy numer telefonu")
		)
		return None, odrzucone

	imie_surowy = _tekst_albo_puste(wiersz.get("Imię"))
	imie, nazwisko = rozdziel_imie_nazwisko(
		wiersz.get("Imię", "") or "", wiersz.get("Nazwisko", "") or ""
	)
	if not _wyglada_na_firme(imie_surowy):
		imie = normalizuj_pisownie_osoby(imie)
		nazwisko = normalizuj_pisownie_osoby(nazwisko)

	adres_surowy = wiersz.get("Adres", "") or ""
	if _pusta(adres_surowy):
		ulica, nr_domu, kod, miejscowosc, dopisek = "", "", "", "", ""
	else:
		rozbite_adres = rozbij_adres_arkusza(adres_surowy)
		if rozbite_adres is None:
			odrzucone.append(
				OdrzuconePole(nr_wiersza, telefon, "Adres", adres_surowy.strip(), "nie pasuje do wzorca adresu")
			)
			ulica, nr_domu, kod, miejscowosc, dopisek = adres_surowy.strip(), "", "", "", ""
		else:
			ulica, nr_domu, kod, miejscowosc, dopisek = rozbite_adres[:5]
			if rozbite_adres.numer_nierozpoznany_z_cyfra:
				odrzucone.append(
					OdrzuconePole(
						nr_wiersza,
						telefon,
						"Adres",
						adres_surowy.strip(),
						"numer domu nierozpoznany, tekst zostawiony w Ulicy",
					)
				)

	powiat = _tekst_albo_puste(wiersz.get("Powiat"))

	wojewodztwo = _pole_slownikowe(
		nr_wiersza, telefon, "Województwo", wiersz.get("Województwo", "") or "", normalizuj_wojewodztwo, odrzucone
	)

	zrodlo_surowy = wiersz.get("Źródło", "") or ""
	if _pusta(zrodlo_surowy):
		odrzucone.append(OdrzuconePole(nr_wiersza, telefon, "Źródło", zrodlo_surowy.strip(), "wymagane"))
		zrodlo = ""
	else:
		zrodlo = (
			_pole_slownikowe(
				nr_wiersza, telefon, "Źródło", zrodlo_surowy, normalizuj_zrodlo, odrzucone
			)
			or ""
		)

	data_pozyskania = _pole_slownikowe(
		nr_wiersza,
		telefon,
		"Data pozyskania",
		wiersz.get("Data pozyskania", "") or "",
		normalizuj_date,
		odrzucone,
	)

	status_zrodla_surowy = wiersz.get("Status źródła", "") or ""
	if _pusta(status_zrodla_surowy):
		status_zrodla = domyslny_status_zrodla(zrodlo)
	else:
		status_zrodla = _pole_slownikowe(
			nr_wiersza, telefon, "Status źródła", status_zrodla_surowy, normalizuj_status_zrodla, odrzucone
		)

	zasady = _pole_slownikowe(
		nr_wiersza,
		telefon,
		"Zasady rozliczania",
		wiersz.get("Zasady rozliczania", "") or "",
		normalizuj_zasady,
		odrzucone,
	)

	posiadane_produkty = _pole_slownikowe(
		nr_wiersza,
		telefon,
		"Obecne produkty",
		wiersz.get("Obecne produkty", "") or "",
		normalizuj_posiadane_produkty,
		odrzucone,
	)

	produkt_procesu = _pole_slownikowe(
		nr_wiersza,
		telefon,
		"Produkt w procesie",
		wiersz.get("Produkt w procesie", "") or "",
		normalizuj_produkt_procesu,
		odrzucone,
	)

	product_interest = _pole_slownikowe(
		nr_wiersza,
		telefon,
		"Zainteresowanie",
		wiersz.get("Zainteresowanie", "") or "",
		mapuj_zainteresowanie,
		odrzucone,
	)

	uwagi = normalizuj_uwagi(wiersz.get("Uwagi", "") or "", dopisek)

	lead: dict[str, Any] = {
		"first_name": imie if imie else "Kontakt",
		"last_name": nazwisko,
		"mobile_no": telefon,
		"status": "Nowy",
		"business_line": "D2D",
		"custom_install_address": ulica,
		"custom_nr_domu": nr_domu,
		"custom_install_postal_code": kod or None,
		"custom_install_city": miejscowosc,
		"custom_powiat": powiat,
		"custom_voivodeship": wojewodztwo,
		"custom_import_source": zrodlo,
		"custom_import_date": data_pozyskania,
		"custom_uwagi_import": uwagi,
		"custom_product_interest": product_interest,
		"custom_posiadane_produkty": posiadane_produkty,
		"custom_produkt_procesu": produkt_procesu,
		"custom_status_zrodla": status_zrodla,
		"custom_zasady_dotacji": zasady,
	}
	return lead, odrzucone
