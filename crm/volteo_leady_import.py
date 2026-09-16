# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Import leadów z arkusza Grega (`CRM_ProEnergy_FINAL_import_CRM.xlsx`, arkusz
„Leady") do `CRM Lead` — reimport b59 (issue #98), zastępuje poprzedni parser
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
odstępstwo (brakująca, nadmiarowa albo przestawiona kolumna) — zero
zgadywania kształtu pliku.

## Puste komórki

`_pusta()` traktuje jako pustkę (bez rozróżniania wielkości liter): pustą
komórkę, `-`, `brak`, `nie`. To poszerzenie względem poprzedniego formatu
(który znał tylko `""`/`-`) NIE zmienia zachowania żadnej z zachowanych
funkcji na ich dotychczasowych testach — `normalizuj_wojewodztwo("brak")` i
`mapuj_zainteresowanie("brak")` już wcześniej zwracały `None` (bo `"brak"`
nie pasował do żadnego kanonu), więc dodatkowa wczesna ścieżka przez
`_pusta()` daje ten sam wynik, tylko szybciej. Nowy marker `nie` nie był
dotąd używany w żadnym teście, więc nie ma czego złamać.

## Odrzucenia pól kontra odrzucenia wierszy

Zły telefon (nie przechodzi `normalizuj_telefon`) odrzuca CAŁY wiersz —
`zbuduj_leada_z_arkusza` zwraca `(None, [OdrzuconePole(...)])`. Każda inna
kolumna słownikowa (Data pozyskania, Status źródła, Zasady rozliczania,
Obecne produkty, Produkt w procesie, Zainteresowanie, Województwo, Źródło)
idzie przez wspólny helper `_pole_slownikowe`: niepusta wartość, której
normalizator nie rozpozna (czy to przez wyjątek `WartoscOdrzucona`, czy przez
zwrócenie `None`), odrzuca TYLKO to jedno pole — pole w wynikowym słowniku
leada staje się `None`, wpis trafia do listy `OdrzuconePole`, a wiersz i tak
wchodzi do wyniku. To jest kontrakt uzgodniony z Gregiem: nieznany token w
Obecne produkty / Produkt w procesie / Źródło nie ma unieważniać całego
leada, tylko to jedno pole.

Wyjątek: pusta komórka `Źródło` jest odrzucana z powodem `"wymagane"` mimo że
inne puste komórki nie trafiają do raportu — źródło leada jest jedynym polem
z tej grupy, które ma być zawsze wypełnione.

## Adres

`rozbij_adres_arkusza` rozbija jedną kolumnę `Adres` (`"<ulica>, <kod>
<miejscowość>[ (dopisek]"`) na ulicę, numer domu, kod, miejscowość i dopisek
w nawiasie. `_WZOR_ADRES` ma ZACHŁANNĄ grupę 1, więc kotwiczy się na
OSTATNIM wystąpieniu `, dd-ddd ` w tekście — dla adresu z dwoma przecinkami
(„Rogierówko, Ul. Kościuszki 16A, 62-090 Rokietnica") grupa 1 to CAŁE
„Rogierówko, Ul. Kościuszki 16A" (z przecinkiem w środku), które dopiero
`rozbij_adres` rozbija na ulicę „Rogierówko, Ul. Kościuszki" i numer „16A".
Dopisek w nawiasie bywa ucięty bez zamykającego `)` (obcięta komórka Excela)
— `rozbij_adres_arkusza` radzi sobie z obiema wersjami. Brak dopasowania do
`_WZOR_ADRES` odrzuca CAŁE pole Adres do raportu; surowy tekst zostaje w
`custom_install_address` bez zmian, reszta adresowych pól zostaje pusta.
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

_WZOR_SAM_NUMER = re.compile(r"^\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?$")
"""Cała wartość adresu to sam numer domu (wieś bez nazwy ulicy) - `rozbij_adres`."""

_WZOR_ULICA_I_NUMER = re.compile(r"^(.+)\s+(\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?)$")
"""Ulica + numer domu (z opcjonalną literą/ukośnikiem) na końcu - `rozbij_adres`."""

_WZOR_KOD_POCZTOWY = re.compile(r"^\d{2}-\d{3}$")
"""Wygląda jak polski kod pocztowy, nie nazwa ulicy - straż w `rozbij_adres` przeciwko np. '62-300 300' (kod pocztowy wpisany w kolumnie Ulica)."""

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
	"""Wynik `rozbij_adres_arkusza` - pięć składowych jednej komórki `Adres`."""

	ulica: str
	nr_domu: str
	kod: str
	miejscowosc: str
	dopisek: str


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


def rozbij_adres(adres: str, miasto: str) -> tuple[str, str] | None:
	"""Rozbija fragment ulicowy adresu na `(ulica, numer_domu)`.

	Numer domu rozpoznaje literę i ukośnik na końcu (`19A`, `5/2`). Gdy CAŁA wartość
	`adres` to sam numer - przy wsiach bez nazwy ulicy taki fragment bywa właśnie
	samym numerem, a wieś leży w `miasto` (reguła „Zbożowo 5, 64-300 Zbożowo"):
	ulicą staje się `miasto`, zwraca `(miasto, numer)`. Wszystko nierozpoznane -
	pusty `adres`, brak liczby na końcu, sam numer bez `miasto` do podstawienia,
	albo ulica po rozbiciu pusta lub wyglądająca jak kod pocztowy (dwie cyfry,
	myślnik, trzy cyfry - np. źle wpisane "62-300 300", produkcyjna anomalia
	danych) - zwraca `None`: zero zgadywania, wywołujący ma zostawić oryginalną
	wartość bez zmian.
	"""
	tekst = (adres or "").strip()
	if not tekst:
		return None
	if _WZOR_SAM_NUMER.match(tekst):
		miasto_czyste = (miasto or "").strip()
		if not miasto_czyste:
			return None
		return miasto_czyste, tekst
	dopasowanie = _WZOR_ULICA_I_NUMER.match(tekst)
	if dopasowanie:
		ulica = dopasowanie.group(1).strip()
		if not ulica or _WZOR_KOD_POCZTOWY.match(ulica):
			return None
		return ulica, dopasowanie.group(2)
	return None


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
	puste — też bez zmian, nie ma czego dzielić.

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

	Miejscowość to część przed pierwszym ` (` w tym, co zostaje po kodzie
	pocztowym; dopisek to reszta, z obciętym końcowym `)` gdy jest obecny (bywa
	ucięty przez Excela bez zamykającego nawiasu - obie wersje dają ten sam wynik).

	Fragment ulicy równy dokładnie `-` (wiersz bez żadnej ulicy) daje puste `ulica`
	i `nr_domu` - CELOWO nie kopiujemy tu miejscowości do ulicy (w odróżnieniu od
	`rozbij_adres`, który to robi dla starego formatu "sam numer domu"). W
	pozostałych przypadkach fragment ulicy idzie przez `rozbij_adres(fragment,
	miejscowosc)`; gdy ten zwróci `None` (np. „Blizińskiego" - ulica bez numeru na
	końcu) fragment zostaje w całości jako `ulica`, `nr_domu` pusty - to NIE jest
	odrzucenie, tylko brakujący numer domu (statystyka "ulica bez numeru").
	"""
	tekst = (adres or "").strip()
	if not tekst:
		return None
	dopasowanie = _WZOR_ADRES.match(tekst)
	if not dopasowanie:
		return None
	czesc_ulicy = dopasowanie.group(1).strip()
	kod = dopasowanie.group(2)
	reszta = dopasowanie.group(3).strip()

	if " (" in reszta:
		miejscowosc_surowa, _, dopisek_surowy = reszta.partition(" (")
		miejscowosc = miejscowosc_surowa.strip()
		dopisek = dopisek_surowy.rstrip(")").strip()
	else:
		miejscowosc = reszta
		dopisek = ""

	if czesc_ulicy == "-":
		ulica, nr_domu = "", ""
	else:
		rozbite = rozbij_adres(czesc_ulicy, miejscowosc)
		if rozbite:
			ulica, nr_domu = rozbite
		else:
			ulica, nr_domu = czesc_ulicy, ""

	return AdresRozbity(ulica=ulica, nr_domu=nr_domu, kod=kod, miejscowosc=miejscowosc, dopisek=dopisek)


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
	oczyszczony = [(pole or "").lstrip("﻿").strip() for pole in naglowek]
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
	zmian (`custom_nr_domu`/kod/miejscowość/dopisek zostają puste). Dopisek w
	nawiasie NIE trafia do `custom_install_city` - dokleja się jako ostatnia linia
	`custom_uwagi_import` przez `normalizuj_uwagi` (decyzja właściciela 2026-09-16).

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

	imie, nazwisko = rozdziel_imie_nazwisko(
		wiersz.get("Imię", "") or "", wiersz.get("Nazwisko", "") or ""
	)

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
			ulica, nr_domu, kod, miejscowosc, dopisek = rozbite_adres

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
