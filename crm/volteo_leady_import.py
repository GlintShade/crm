# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Import historycznych leadów z CSV (`Baza kontakty Arago_SD_CC`) do `CRM Lead`.

Moduł celowo nie importuje ``frappe`` — precedens ``crm/volteo_naming.py``.
To jedyny sposób, żeby dało się go przetestować lokalnie (``frappe`` nie jest
instalowalne na tej maszynie, więc reszta backendu ma wyłącznie bramkę
składniową `ruff`/`py_compile`). Wszystko co dotyka dokumentu `CRM Lead`
(insert, uprawnienia, deduplikacja względem istniejących kontaktów) mieszka
poza tym plikiem, w whitelisted API forka.

Cały plik operuje wyłącznie na czystych strukturach `str`/`dict`/`list` —
zero zależności od frameworka, zero mutacji argumentów wejściowych.

Pułapka pliku źródłowego (naprawiona, nie zignorowana): nagłówek CSV ma
DWIE kolumny o pustej nazwie — jedna (tuż po „Uwagi") niesie stary status
szansy sprzed importu („wygrana"/„przegrana"/„nieaktualna"/„otwarta" —
5046 wierszy niepustych na 18574), druga (na samym końcu wiersza) niesie
znacznik „STARE"/„NOWE". Goły `csv.DictReader` buduje słownik przez
`zip(fieldnames, wiersz)`, więc przy dwóch kolumnach o kluczu `""` druga
PO CICHU nadpisuje pierwszą i historia szansy znika bez śladu — dokładnie
tego typu cichej utraty danych ten moduł ma unikać. `wczytaj_wiersze`
dlatego czyta nagłówek pozycyjnie (`csv.reader`, nie `DictReader`),
wykrywa bezimienne kolumny i nadaje im jawne, unikalne klucze
(`_historia_wyniku` / `_stare_nowe`) w kolejności występowania w
nagłówku — z asercją, że jest ich dokładnie dwie, żeby zmiana kształtu
pliku źródłowego głośno wywaliła błąd zamiast po cichu pomieszać kolumny.
Historia trafia do handlowca jako tekst (`[HISTORIA] <wartość>` w
uwagach), NIE jako nowy status leada — leady zawsze wchodzą ze statusem
`Nowy`.
"""

import csv
import datetime
import io
import re
from typing import Any

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
"""Mapowanie skrótów z kolumny `Rachunek na mc` na etykietę `custom_product_interest`."""

KLUCZ_HISTORIA = "_historia_wyniku"
"""Klucz nadawany pierwszej (w kolejności występowania) bezimiennej kolumnie nagłówka —
niesie stary status szansy sprzed importu (`wygrana`/`przegrana`/`nieaktualna`/`otwarta`/...)."""

KLUCZ_STARE_NOWE = "_stare_nowe"
"""Klucz nadawany drugiej (w kolejności występowania) bezimiennej kolumnie nagłówka —
niesie znacznik `STARE`/`NOWE`."""


def _pusta(wartosc: str | None) -> bool:
	"""Czy wartość pola CSV oznacza pustkę.

	W całym pliku źródłowym `-` znaczy puste; traktujemy tak samo brak wartości i sam biały znak.
	"""
	if wartosc is None:
		return True
	oczyszczona = wartosc.strip()
	return oczyszczona in ("", "-")


def _tekst_albo_puste(wartosc: str | None) -> str:
	"""Zwraca oczyszczoną wartość albo pusty string, gdy `_pusta()` uznaje ją za pustkę."""
	if _pusta(wartosc):
		return ""
	assert wartosc is not None
	return wartosc.strip()


def normalizuj_telefon(surowy: str) -> str | None:
	"""Normalizuje numer telefonu do formatu `+48XXXXXXXXX`.

	Akceptuje cztery formaty spotykane w źródłowym CSV: `48XXXXXXXXX`,
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
	"""Mapuje kolumnę `Rachunek na mc` (de facto zainteresowanie produktem) na etykietę Leada.

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


def _przemianuj_puste_naglowki(naglowek_surowy: list[str]) -> list[str]:
	"""Nadaje jawne, unikalne klucze bezimiennym (`""`) kolumnom nagłówka, w kolejności
	występowania — zamiast pozwolić `dict()`/`csv.DictReader` po cichu nadpisać jedną drugą.

	Brak bezimiennych kolumn zwraca nagłówek bez zmian (przypadek plików
	testowych/uproszczonych). Gdy jakieś się znajdą, musi ich być
	DOKŁADNIE dwie — inna liczba oznacza, że plik źródłowy zmienił kształt
	i dalsze pozycyjne mapowanie (`KLUCZ_HISTORIA`/`KLUCZ_STARE_NOWE`)
	byłoby zgadywaniem, więc zgłaszamy błąd głośno zamiast pomieszać dane.
	"""
	indeksy_pustych = [i for i, nazwa in enumerate(naglowek_surowy) if nazwa.strip() == ""]
	if not indeksy_pustych:
		return list(naglowek_surowy)
	if len(indeksy_pustych) != 2:
		raise ValueError(
			f"Oczekiwano dokładnie 2 bezimiennych kolumn w nagłówku CSV, "
			f"znaleziono {len(indeksy_pustych)}: {naglowek_surowy}"
		)
	nowy_naglowek = list(naglowek_surowy)
	nowy_naglowek[indeksy_pustych[0]] = KLUCZ_HISTORIA
	nowy_naglowek[indeksy_pustych[1]] = KLUCZ_STARE_NOWE
	return nowy_naglowek


def wczytaj_wiersze(tekst_csv: str) -> list[dict[str, str]]:
	"""Wczytuje CSV (jako string) do listy słowników — po jednym na wiersz, kluczami są nagłówki.

	Czyta nagłówek pozycyjnie przez `csv.reader` (nie `csv.DictReader`),
	żeby bezimienne kolumny (patrz `_przemianuj_puste_naglowki` i pułapka
	opisana w docstringu modułu) dostały jawne, unikalne klucze zamiast
	po cichu się zderzyć. Wiersze krótsze niż nagłówek są dopełniane
	pustymi polami; dłuższe — przycinane do długości nagłówka.
	"""
	czytnik = csv.reader(io.StringIO(tekst_csv))
	try:
		naglowek_surowy = next(czytnik)
	except StopIteration:
		return []
	naglowek = _przemianuj_puste_naglowki(naglowek_surowy)
	wiersze: list[dict[str, str]] = []
	for wiersz_surowy in czytnik:
		if len(wiersz_surowy) < len(naglowek):
			wiersz_wyrownany = wiersz_surowy + [""] * (len(naglowek) - len(wiersz_surowy))
		else:
			wiersz_wyrownany = wiersz_surowy[: len(naglowek)]
		wiersze.append(dict(zip(naglowek, wiersz_wyrownany, strict=True)))
	return wiersze


def _liczba_wypelnionych_pol(wiersz: dict[str, str]) -> int:
	"""Liczy pola wiersza, które NIE są pustką wg `_pusta()` — używane w tie-breaku dedupu."""
	return sum(1 for wartosc in wiersz.values() if not _pusta(wartosc))


def _klucz_rankingu(wiersz: dict[str, str]) -> tuple[bool, str, int]:
	"""Klucz sortowania do wyboru zwycięzcy grupy dedupu: najnowsza data, potem kompletność."""
	data = normalizuj_date(wiersz.get("Data", ""))
	return (data is not None, data or "", _liczba_wypelnionych_pol(wiersz))


def _linia_uwag(wiersz: dict[str, str]) -> str:
	"""Składa tekstową linię uwag dla jednego wiersza źródłowego: Uwagi + Typ dachu + Pokrycie +
	znacznik STARE/NOWE, otagowaną źródłem (`[SD]`/`[CC]`/`[ARG]`).

	Decyzja właściciela: te pola idą do wolnego tekstu, nie do osobnych
	pól strukturalnych.
	"""
	fragmenty: list[str] = []
	uwagi = wiersz.get("Uwagi", "")
	if not _pusta(uwagi):
		fragmenty.append(uwagi.strip())
	typ_dachu = wiersz.get("Typ dachu", "")
	if not _pusta(typ_dachu):
		fragmenty.append(f"Typ dachu: {typ_dachu.strip()}")
	pokrycie = wiersz.get("Pokrycie", "")
	if not _pusta(pokrycie):
		fragmenty.append(f"Pokrycie: {pokrycie.strip()}")
	stare_nowe = wiersz.get(KLUCZ_STARE_NOWE, "")
	if not _pusta(stare_nowe):
		fragmenty.append(stare_nowe.strip())
	if not fragmenty:
		return ""
	zrodlo = wiersz.get("ŹRÓDŁO", "").strip() or "?"
	return f"[{zrodlo}] " + ", ".join(fragmenty)


def deduplikuj(wiersze: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
	"""Deduplikuje wiersze CSV po znormalizowanym numerze telefonu.

	Wiersze bez poprawnego telefonu (`normalizuj_telefon` zwraca `None`)
	odpadają — nie trafiają do wyniku i nie liczą się do żadnej grupy.
	Zwycięzcą grupy zostaje wiersz z najnowszą datą, a przy remisie —
	wiersz z największą liczbą wypełnionych pól. Przegrani nie znikają:
	ich źródło dokłada się do unii `zrodlo`, a ich uwagi (razem z Typ
	dachu/Pokrycie/STARE-NOWE) doklejają się do tekstu `uwagi` zwycięzcy,
	każde otagowane własnym źródłem. Historia wyniku szansy sprzed importu
	(kolumna `_historia_wyniku` — patrz docstring modułu) trafia do `uwagi`
	jako `[HISTORIA] <wartość>`, zbierana ze WSZYSTKICH wierszy grupy (nie
	tylko zwycięzcy) i deduplikowana po wartości, więc dwa wiersze z tym
	samym „wygrana" nie dają dwóch identycznych tagów.

	Zwraca `dict[telefon, rekord]`, gdzie `rekord` jest już gotowy do
	przekazania do `zbuduj_leada`.
	"""
	grupy: dict[str, list[dict[str, str]]] = {}
	for wiersz in wiersze:
		telefon = normalizuj_telefon(wiersz.get("Numer", ""))
		if telefon is None:
			continue
		grupy.setdefault(telefon, []).append(wiersz)

	wynik: dict[str, dict[str, Any]] = {}
	for telefon, grupa in grupy.items():
		zwyciezca = max(grupa, key=_klucz_rankingu)

		zrodla_unikalne: list[str] = []
		for wiersz in grupa:
			zrodlo = wiersz.get("ŹRÓDŁO", "").strip()
			if zrodlo and zrodlo not in zrodla_unikalne:
				zrodla_unikalne.append(zrodlo)

		linie_uwag = [linia for wiersz in grupa if (linia := _linia_uwag(wiersz))]

		historia_unikalna: list[str] = []
		for wiersz in grupa:
			wartosc_historii = wiersz.get(KLUCZ_HISTORIA, "")
			if not _pusta(wartosc_historii):
				oczyszczona = wartosc_historii.strip()
				if oczyszczona not in historia_unikalna:
					historia_unikalna.append(oczyszczona)
		linie_historii = [f"[HISTORIA] {wartosc}" for wartosc in historia_unikalna]

		wynik[telefon] = {
			"telefon": telefon,
			"imie": _tekst_albo_puste(zwyciezca.get("Imię")),
			"nazwisko": _tekst_albo_puste(zwyciezca.get("Nazwisko")),
			"wojewodztwo": _tekst_albo_puste(zwyciezca.get("Województwo")),
			"powiat": _tekst_albo_puste(zwyciezca.get("Powiat")),
			"miasto": _tekst_albo_puste(zwyciezca.get("Miasto")),
			"kod_pocztowy": _tekst_albo_puste(zwyciezca.get("Kod pocztowy")),
			"ulica": _tekst_albo_puste(zwyciezca.get("Ulica")),
			"rachunek_na_mc": _tekst_albo_puste(zwyciezca.get("Rachunek na mc")),
			"data": _tekst_albo_puste(zwyciezca.get("Data")),
			"zrodlo": "+".join(zrodla_unikalne),
			"uwagi": " | ".join(linie_uwag + linie_historii),
		}
	return wynik


def zbuduj_leada(rekord: dict[str, Any]) -> dict[str, Any]:
	"""Buduje słownik pól `CRM Lead` z połączonego rekordu zwróconego przez `deduplikuj`.

	`first_name` ma fallback `"Kontakt"`, gdy imię jest puste — `lead_name`
	nie może być pusty. Świadomie BEZ `lead_owner` — przypisanie właściciela
	to osobny krok poza tym modułem.
	"""
	imie = rekord.get("imie", "") or ""
	return {
		"first_name": imie if imie else "Kontakt",
		"last_name": rekord.get("nazwisko", "") or "",
		"mobile_no": rekord.get("telefon", "") or "",
		"status": "Nowy",
		"business_line": "D2D",
		"custom_install_address": rekord.get("ulica", "") or "",
		"custom_install_city": rekord.get("miasto", "") or "",
		"custom_install_postal_code": normalizuj_kod(rekord.get("kod_pocztowy", "") or ""),
		"custom_powiat": rekord.get("powiat", "") or "",
		"custom_voivodeship": normalizuj_wojewodztwo(rekord.get("wojewodztwo", "") or ""),
		"custom_import_source": rekord.get("zrodlo", "") or "",
		"custom_import_date": normalizuj_date(rekord.get("data", "") or ""),
		"custom_uwagi_import": rekord.get("uwagi", "") or "",
		"custom_product_interest": mapuj_zainteresowanie(rekord.get("rachunek_na_mc", "") or ""),
	}
