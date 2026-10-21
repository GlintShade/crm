# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Rdzeń kalkulatora OZE dla czterech nowych rodzajów instalacji: Rozbudowa PV/ME,
Klimatyzacja, Pompa ciepła, Kocioł (b68, issue ops#222).

Frappe-free, stdlib wyłącznie (``decimal``, ``typing``): styl `crm/czyste_powietrze/obliczenia.py`:
``Decimal`` w całej arytmetyce, zaokrąglenie do grosza (ROUND_HALF_UP) w `_kwota`, wejście
(`wejscie`/`cennik`/`dobor`/`stale`) nigdy nie jest mutowane, klucze z wiodącym podkreśleniem
nie istnieją tu (w odróżnieniu od `obliczenia.py`): ten moduł nie ma potrzeby czyszczenia
pól prywatnych na wyjściu, bo nic poza `wewnetrzne` nie niesie kosztu/marży, a `wewnetrzne`
samo jest zawsze zwracane (bramka widoczności "tylko admin" żyje w `crm/api/kalkulator_oze.py`,
przez jedno `wynik.pop("wewnetrzne", None)`, tak jak `volteo_cp_calc` robi dla CP).

Trzy funkcje mapujące (`cennik_z_wierszy`, `dobor_z_wierszy`, `stale_z_singla`) tłumaczą
płaskie wiersze Frappe (``frappe.get_all`` na `Volteo Cennik Pozycja`/`Volteo Cennik Skladowa`/
`Volteo Dobor Mocy PC`, ``frappe.db.get_singles_dict`` na `Volteo Kalkulator Stale`) na
kształty, które reszta modułu konsumuje: ta warstwa żyje TU (nie w `crm/api/kalkulator_oze.py`,
w odróżnieniu od wzorca CP), żeby była testowalna lokalnie bez Frappe. Nieznana/brakująca
struktura danych cennika/stałych to zawsze `OZEBladMapowania`: odrębne od błędów wejścia
klienta (`OZEDaneNiekompletne`), bo to problem integralności katalogu/konfiguracji, nie
błąd formularza.

Dwuznaczność z briefu, rozstrzygnięta tutaj (opisana też w raporcie agenta): kontrakt
`wewnetrzne` niesie zarówno `marza_proenergy`/`bonus_liderski`/`narzut` (składowe) jak i
zagregowane `marza`/`zysk`: które nie są zdefiniowane explicite wzorem w briefie. Ten
moduł liczy ``marza = marza_proenergy + bonus_liderski + narzut`` (= netto - koszt, czyli
CAŁA nadwyżka nad kosztem) i ``zysk = marza_proenergy + bonus_liderski`` (zysk ProEnergy
BEZ narzutu handlowca, tak jak CP liczy ``zysk = marza - prowizja_handlowa`` z
`crm/czyste_powietrze/obliczenia.py`: narzut handlowca gra tu analogiczną rolę do
prowizji handlowca w CP: trafia do handlowca, nie do firmy).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any


class OZEBlad(Exception):
	"""Wspólna klasa błędów kalkulatora OZE (nowe rodzaje instalacji)."""


class OZEDaneNiekompletne(OZEBlad):
	"""Dane wejściowe są niepełne, brakujące albo poza dozwolonym zakresem."""


class OZEPozycjaNieaktywna(OZEBlad):
	"""Wybrana pozycja katalogowa istnieje, ale nie jest aktywna."""


class OZENiedozwolonaKombinacja(OZEBlad):
	"""Wybrana kombinacja danych (albo przekroczony limit liczby elementów) jest niedozwolona."""


class OZEBrakDoboru(OZEBlad):
	"""Brak wiersza doboru mocy pompy ciepła dla podanego zapotrzebowania."""


class OZEBladMapowania(OZEBlad):
	"""Dane katalogu/stałych kalkulatora (cennik, dobór mocy, Volteo Kalkulator Stale) są
	niekompletne albo zniekształcone: problem integralności danych, nie formularza klienta."""


ROZBUDOWA = "Rozbudowa PV/ME"
KLIMATYZACJA = "Klimatyzacja"
POMPA_CIEPLA = "Pompa ciepła"
KOCIOL = "Kocioł"

RODZAJE_NOWE: frozenset[str] = frozenset({ROZBUDOWA, KLIMATYZACJA, POMPA_CIEPLA, KOCIOL})
"""Cztery nowe rodzaje instalacji OZE obsługiwane przez ten moduł (b68)."""

RODZAJE_BEZ_ULGI: frozenset[str] = frozenset({KLIMATYZACJA})
"""Rodzaje, dla których ulga termomodernizacyjna nigdy nie ma zastosowania (decyzja CEO
2026-10-04): niezależnie od typu klienta i wybranego `ulga_pct`."""

INDYWIDUALNY = "indywidualny"
BIZNESOWY = "biznesowy"
TYPY_KLIENTA: frozenset[str] = frozenset({INDYWIDUALNY, BIZNESOWY})
"""Te same dwie wartości `typ_klienta` co w silniku PV (`ops/crm-kalkulator-bom.py`):
konwencja nazewnicza celowo niezmieniona, żeby frontend mógł współdzielić pole wyboru."""

GRUPY: tuple[str, ...] = (
	"panele",
	"panele_mikro",
	"bateria",
	"klima_chlodzenie",
	"klima_dogrzewanie",
	"klima_grzanie",
	"pc_rotenso_mono",
	"pc_midea_mono",
	"pc_midea_split",
	"kociol_pellet",
	"kociol_duo",
	"cwu_pc",
	"cwu_kociol",
	"grzejnik",
	"dod_klima",
	"dod_panele",
	"dod_panele_mikro",
	"ems_breeze",
	"pstryk",
	"ev_ac",
	"ev_dc",
)
"""Dokładna lista opcji pola Select `grupa` na `Volteo Cennik Pozycja` (`ops/crm-cennik-oze.py`,
sekcja 1 planu): tutaj wyłącznie jako metadane do walidacji/sortowania przez
`crm/api/kalkulator_oze.py::volteo_oze_pozycje`; `oblicz_oferte` nie czyta tego pola."""

ROZBUDOWA_MAX: dict[str, int] = {"panele": 5, "panele_mikro": 5, "bateria": 4}
"""Maksymalna liczba elementów każdej sekcji Rozbudowy (minimum to 0: sekcja nie wybrana)."""

ZAPOTRZEBOWANIE: dict[str, Decimal] = {
	"ponizej_4": Decimal("0"),
	"4.5": Decimal("4.5"),
	"5": Decimal("5"),
	"5.5": Decimal("5.5"),
	"6": Decimal("6"),
	"6.5": Decimal("6.5"),
	"7": Decimal("7"),
	"7.5": Decimal("7.5"),
	"8": Decimal("8"),
	"8.5": Decimal("8.5"),
	"9": Decimal("9"),
	"9.5": Decimal("9.5"),
	"10": Decimal("10"),
	"10.5": Decimal("10.5"),
	"11": Decimal("11"),
	"11.5": Decimal("11.5"),
	"12": Decimal("12"),
	"12.5": Decimal("12.5"),
	"13": Decimal("13"),
	"13.5": Decimal("13.5"),
	"14": Decimal("14"),
}
"""21 wartości listy "Zapotrzebowanie budynku na moc" (nowy_kalkulator.md): `"ponizej_4"`
mapuje na `0` (dolna granica tabel doboru mocy zaczyna się od `0`, patrz `dobierz_moc_pompy`)."""

PC_PRODUCENCI: dict[str, tuple[str, ...]] = {
	"Rotenso": ("Monoblok",),
	"Midea": ("Monoblok", "Split"),
}
"""Producent -> dozwolone typy pompy ciepła. Rotenso NIE ma wariantu Split (decyzja CEO):
wybranie Rotenso+Split rzuca `OZENiedozwolonaKombinacja`, nigdy ciche przełączenie na Monoblok."""

PC_OGRZEWANIE: dict[str, str] = {
	"Grzejniki": "Grzejniki",
	"Podłogówka": "Podłogówka",
	"Mieszane": "Grzejniki",
}
"""Rodzaj ogrzewania wybrany przez klienta -> kolumna `ogrzewanie` w tabeli doboru mocy.
"Mieszane" dobiera moc z tabeli Grzejników (decyzja CEO: granica dla instalacji mieszanej
jest bezpieczniejsza przy tabeli grzejnikowej): `PC_OGRZEWANIE["Mieszane"] == "Grzejniki"`."""

PC_GRUPA: dict[tuple[str, str], str] = {
	("Rotenso", "Monoblok"): "pc_rotenso_mono",
	("Midea", "Monoblok"): "pc_midea_mono",
	("Midea", "Split"): "pc_midea_split",
}
"""(producent, typ) -> prefiks kodu pozycji cennika pompy ciepła (`<prefiks>_<moc_kw int>`,
np. `pc_rotenso_mono_6`): klucze dokładnie pokrywają `PC_PRODUCENCI` (Rotenso+Split nigdy
tu nie trafia, bo `_pozycje_pompa` odrzuca tę kombinację wcześniej)."""

GRZEJNIKI_MAX = 15
"""Maksymalna ŁĄCZNA liczba grzejników niskotemperaturowych (suma wszystkich rozmiarów) na ofercie."""

GRZEJNIKI_ROZMIARY: tuple[str, ...] = ("600x600", "600x800", "600x1000", "600x1200", "600x1600")
"""Dozwolone rozmiary grzejnika niskotemperaturowego: kod pozycji cennika to `grzejnik_<rozmiar>`."""

PROG_PPOZ_KW = Decimal("6.5")
"""Próg łącznej mocy PV (kW), powyżej którego Rozbudowa wymaga uzgodnień PPOŻ: CELOWY
duplikat tej samej stałej w `crm/volteo_umowa.py::PROG_PPOZ_KW` i w `ops/crm-kalkulator-bom.py`
(Server Script nie może importować, patrz AGENT-PLAYBOOK.md); zmiana w jednym miejscu
wymaga zmiany we WSZYSTKICH trzech."""

DOSTEPNOSC_DODATKOW: dict[str, dict[str, Any]] = {
	"dod_klima": {"warianty": ("Fotowoltaika", "Fotowoltaika + Magazyn", "Magazyn energii")},
	"dod_panele": {"warianty": ("Magazyn energii",)},
	"dod_panele_mikro": {"warianty": ("Magazyn energii",)},
	# kod historyczny, nazwa handlowa EMS Zeronest od b73 (ops#294); producent to krotka dozwolonych
	"ems_breeze": {
		"warianty": ("Fotowoltaika + Magazyn", "Magazyn energii"),
		"producent": ("Deye", "Hoymiles", "Solax"),
	},
	"pstryk": {"warianty": ("Fotowoltaika + Magazyn", "Magazyn energii"), "producent": "Sigenergy"},
	"ev_ac": {"warianty": ("Fotowoltaika + Magazyn", "Magazyn energii"), "producent": "Sigenergy"},
	"ev_dc": {
		"warianty": ("Fotowoltaika + Magazyn", "Magazyn energii"),
		"producent": "Sigenergy",
		"sigen_typ": "AIO",
	},
}
"""Macierz dostępności opcji dodatkowych w zestawach PV/PV+ME/ME (wariant x producent x
sigen_typ): WYŁĄCZNIE dokumentacyjna/referencyjna w tym module: dodatki same są liczone
przez silnik PV, `ops/crm-kalkulator-bom.py` (Server Script, bramka w safe_exec, kod nie
może importować stąd), który tę samą macierz duplikuje inline z komentarzem wiążącym oba
miejsca: identyczna konwencja co `PROG_PPOZ_KW` wyżej. `oblicz_oferte` w tym pliku NIE
czyta tej stałej (nowe rodzaje instalacji nie mają dodatków: dodatki istnieją tylko w
zestawach PV/PV+ME/ME, poza zakresem tego modułu)."""

_TYPY_SKLADOWEJ: tuple[str, ...] = ("Koszt", "Marża Proenergy", "Bonus liderski")

_ZERO = Decimal("0")
_JEDEN = Decimal("1")
_STO = Decimal("100")
_TYSIAC = Decimal("1000")

_OKRES_LAT_DOMYSLNY = 10
_OKRES_LAT_MIN, _OKRES_LAT_MAX = 1, 10

_POLA_POZYCJI_WYMAGANE: tuple[str, ...] = (
	"kod",
	"nazwa",
	"rodzaj",
	"grupa",
	"producent",
	"model",
	"kolor",
	"moc_kw",
	"ilosc",
	"parametr",
	"opis",
	"aktywny",
	"sort",
)

_POLA_DOBORU_WYMAGANE: tuple[str, ...] = (
	"producent",
	"typ",
	"ogrzewanie",
	"od_kw",
	"do_kw",
	"moc_kw",
	"aktywny",
)

_POLA_STALYCH_WYMAGANE: tuple[str, ...] = (
	"vat_indyw",
	"vat_biznes",
	"pmt_oprocentowanie_mies",
	"ppoz",
	"panel_moc_wp",
)
"""`narzut_max` celowo NIE jest tutaj: w odróżnieniu od pozostałych pięciu stałych, silnik PV
(`ops/crm-kalkulator-bom.py`) czyta je przez `frappe.utils.flt(consts.get("narzut_max", 0.0))`,
więc brak wiersza w `tabSingles` jest dla PV równoznaczny z `0` ("brak limitu"), nigdy błędem.
Na lokalnej bazie `get_singles_dict("Volteo Kalkulator Stale")["narzut_max"]` faktycznie bywa
`None` (pole nigdy jawnie nie zapisane), a klucz może też w ogóle nie wystąpić w słowniku:
wymaganie go tutaj wywaliłoby KAŻDĄ wycenę przez `OZEBladMapowania`, mimo że PV radzi sobie z
dokładnie tym samym stanem danych bez żadnego błędu. Patrz `_narzut_max` niżej."""


def _blad(komunikat: str) -> None:
	raise OZEDaneNiekompletne(komunikat)


def _decimal(wartosc: Any, pole: str) -> Decimal:
	try:
		wynik = Decimal(str(wartosc))
	except (ArithmeticError, TypeError, ValueError):
		_blad(f"Nieprawidłowa wartość pola {pole}.")
	if not wynik.is_finite():
		_blad(f"Nieprawidłowa wartość pola {pole}.")
	return wynik


def _kwota(wartosc: Decimal) -> Decimal:
	return wartosc.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _wymagany_dict(wartosc: Any, komunikat: str) -> dict[str, Any]:
	if not isinstance(wartosc, dict):
		_blad(komunikat)
	return wartosc


def _wymagana_liczba_calkowita(wartosc: Any, pole: str) -> int:
	if isinstance(wartosc, bool) or not isinstance(wartosc, int):
		_blad(f"Pole {pole} musi być liczbą całkowitą.")
	return wartosc


def _stala(stale: dict[str, Any], klucz: str) -> Any:
	"""Odczyt stałej z już-zmapowanego `stale` (wyjście `stale_z_singla`): brakujący klucz
	jest problemem integralności konfiguracji (`OZEBladMapowania`), nigdy błędem formularza."""
	if klucz not in stale:
		raise OZEBladMapowania(f"Brak stałej {klucz} w konfiguracji kalkulatora.")
	return stale[klucz]


# Bez `True`/`False` w tych dwóch zbiorach: `1 == True` i `0 == False` w Pythonie, więc
# trzymanie obu par naraz w literałach zestawu jest zduplikowanym elementem (ruff B033).
# `_flaga_tak_nie` rozstrzyga prawdziwy `bool` osobnym `isinstance` PRZED sięgnięciem do
# tych zbiorów, więc nic się nie traci - `int`/`str` warianty 1/0 zostają tu jawnie.
_FLAGA_TAK: frozenset[Any] = frozenset({1, "1", "Tak", "tak", "true"})
_FLAGA_NIE: frozenset[Any] = frozenset({0, "0", "Nie", "nie", "false", "", None})


def _flaga_tak_nie(wartosc: Any, pole: str) -> bool:
	"""Parsuje pole Tak/Nie z danych klienta tolerancyjnie na typ (``bool``/``int``/``str``),
	ale nigdy po cichu (ops#222): wbudowane ``bool(...)`` traktuje KAŻDY niepusty string,
	także literalny ``"Nie"``, jako prawdę (``bool("Nie") is True``), więc gdyby którykolwiek
	klient API (stary front, inny konsument) wysłał string zamiast prawdziwego ``bool``-a,
	flaga zostałaby cicho ustawiona na Tak. Brakujący klucz zachowuje się tak jak dotychczasowe
	``bool(dict.get(klucz, False))`` - traktowany jak `Nie`. Każda inna wartość (w tym
	nieoczekiwany typ, np. lista/dict) jest błędem danych klienta (`OZEDaneNiekompletne`),
	nigdy cichym przyjęciem."""
	if isinstance(wartosc, bool):
		return wartosc
	try:
		if wartosc in _FLAGA_TAK:
			return True
		if wartosc in _FLAGA_NIE:
			return False
	except TypeError:
		pass
	_blad(f"Nieprawidłowa wartość pola {pole}: oczekiwano Tak/Nie.")
	return False


# --- Mapery: wiersze Frappe -> kształty konsumowane przez resztę modułu -------------------


def cennik_z_wierszy(pozycje: list[dict[str, Any]], skladowe: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
	"""Buduje katalog `{kod: {..pola nagłówka.., "skladowe": [..]}}` z płaskich wierszy
	`Volteo Cennik Pozycja` (`pozycje`) i `Volteo Cennik Skladowa` (`skladowe`, powiązane
	przez pole `parent` = kod pozycji-rodzica, jak w zwykłym dziecku tabeli Frappe).

	Każdy wiersz pozycji musi nieść WSZYSTKIE pola z `_POLA_POZYCJI_WYMAGANE`; brakujące
	pole, zduplikowany kod albo składowa wskazująca na nieznaną pozycję to `OZEBladMapowania`: to są problemy integralności danych cennika, nie błędy formularza klienta.
	"""
	if not isinstance(pozycje, list) or not isinstance(skladowe, list):
		raise OZEBladMapowania("Nieprawidłowy format danych cennika.")

	katalog: dict[str, dict[str, Any]] = {}
	for wiersz in pozycje:
		if not isinstance(wiersz, dict):
			raise OZEBladMapowania("Nieprawidłowy wiersz pozycji cennika.")
		kod = wiersz.get("kod")
		if not isinstance(kod, str) or not kod:
			raise OZEBladMapowania("Pozycja cennika bez kodu.")
		if kod in katalog:
			raise OZEBladMapowania(f"Zduplikowany kod pozycji cennika: {kod}.")
		for pole in _POLA_POZYCJI_WYMAGANE:
			if pole not in wiersz:
				raise OZEBladMapowania(f"Brak pola {pole} w pozycji cennika {kod}.")
		katalog[kod] = {pole: wiersz[pole] for pole in _POLA_POZYCJI_WYMAGANE}
		# "moc_kw" jest jedynym polem nagłówka pozycji, które uczestniczy w dalszej
		# arytmetyce tego modułu (pole `pompa.moc_kw` w wyniku `oblicz_oferte`) -- mapowane
		# na Decimal dla zgodności z resztą modułu (mieszanie Decimal z surowym
		# float/str zwróconym przez Frappe rzuciłoby TypeError przy pierwszym porównaniu).
		# Pozostałe pola nagłówka (nazwa/rodzaj/grupa/producent/model/kolor/ilosc/parametr/
		# opis/aktywny/sort) są czystymi metadanymi prezentacyjnymi dla
		# `crm/api/kalkulator_oze.py::volteo_oze_pozycje` i zostają bez zmian.
		katalog[kod]["moc_kw"] = _decimal(wiersz["moc_kw"], f"moc_kw:{kod}")
		katalog[kod]["skladowe"] = []

	for wiersz in skladowe:
		if not isinstance(wiersz, dict):
			raise OZEBladMapowania("Nieprawidłowy wiersz składowej cennika.")
		rodzic = wiersz.get("parent")
		if rodzic not in katalog:
			raise OZEBladMapowania(f"Składowa wskazuje na nieznaną pozycję cennika: {rodzic!r}.")
		for pole in ("klucz", "nazwa", "typ", "kwota"):
			if pole not in wiersz:
				raise OZEBladMapowania(f"Brak pola {pole} w składowej pozycji {rodzic}.")
		if wiersz["typ"] not in _TYPY_SKLADOWEJ:
			raise OZEBladMapowania(f"Nieznany typ składowej: {wiersz['typ']!r}.")
		katalog[rodzic]["skladowe"].append(
			{
				"klucz": wiersz["klucz"],
				"nazwa": wiersz["nazwa"],
				"typ": wiersz["typ"],
				"kwota": _decimal(wiersz["kwota"], f"kwota:{rodzic}:{wiersz['klucz']}"),
				"wspolna": bool(wiersz.get("wspolna", False)),
			}
		)
	return katalog


def dobor_z_wierszy(wiersze: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Buduje listę wierszy doboru mocy pompy ciepła z płaskich wierszy `Volteo Dobor Mocy PC`.
	Wiersze z `aktywny` fałszywym są odfiltrowane (nigdy nie trafiają do wyniku, więc
	`dobierz_moc_pompy` nie musi o nich wiedzieć)."""
	if not isinstance(wiersze, list):
		raise OZEBladMapowania("Nieprawidłowy format danych doboru mocy.")

	wynik: list[dict[str, Any]] = []
	for wiersz in wiersze:
		if not isinstance(wiersz, dict):
			raise OZEBladMapowania("Nieprawidłowy wiersz doboru mocy.")
		for pole in _POLA_DOBORU_WYMAGANE:
			if pole not in wiersz:
				raise OZEBladMapowania(f"Brak pola {pole} w wierszu doboru mocy.")
		if not wiersz["aktywny"]:
			continue
		wynik.append(
			{
				"producent": wiersz["producent"],
				"typ": wiersz["typ"],
				"ogrzewanie": wiersz["ogrzewanie"],
				"od_kw": _decimal(wiersz["od_kw"], "od_kw"),
				"do_kw": _decimal(wiersz["do_kw"], "do_kw"),
				"moc_kw": _decimal(wiersz["moc_kw"], "moc_kw"),
			}
		)
	return wynik


def _narzut_max(dokument: dict[str, Any]) -> Decimal | None:
	"""`narzut_max`: brak klucza w `dokument`, `None` i `""` wszystkie znaczą to samo co
	Frappe `flt()` na PV, "brak limitu", więc mapują na `None`, tak jak jawne `0`. Każda
	inna wartość (w tym śmieciowa, nie dająca się sparsować) idzie przez `_decimal` jak
	każde inne pole: śmieciowa wartość JEST błędem formularza, w odróżnieniu od samego
	braku wiersza w `tabSingles`, co jest normalnym, oczekiwanym stanem danych."""
	if "narzut_max" not in dokument:
		return None
	wartosc = dokument["narzut_max"]
	if wartosc is None or wartosc == "":
		return None
	narzut_max = _decimal(wartosc, "narzut_max")
	return None if narzut_max == _ZERO else narzut_max


def stale_z_singla(dokument: dict[str, Any]) -> dict[str, Any]:
	"""Mapuje `frappe.db.get_singles_dict("Volteo Kalkulator Stale")` (stringi albo liczby,
	wszystkie pola opcjonalne na poziomie Frappe) na kształt z Decimal-ami, który reszta
	modułu konsumuje bez dalszej koercji. Brak KTÓREGOKOLWIEK z `_POLA_STALYCH_WYMAGANE` w
	`dokument` to głośny `OZEBladMapowania`: nigdy cichy fallback na wartość domyślną
	(patrz pułapka `get_singles_dict` kontra `get_single_value` w CLAUDE.md/WORKSHOP.md:
	`get_singles_dict` zwraca TYLKO pola faktycznie zapisane w `tabSingles`, więc brakujący
	klucz oznacza "nikt nigdy tego nie ustawił", nie "wartość to 0"). `narzut_max` jest
	WYJĄTKIEM od tej reguły: patrz `_narzut_max` i komentarz przy `_POLA_STALYCH_WYMAGANE`.
	"""
	if not isinstance(dokument, dict):
		raise OZEBladMapowania("Nieprawidłowy format stałych kalkulatora.")
	for pole in _POLA_STALYCH_WYMAGANE:
		if pole not in dokument:
			raise OZEBladMapowania(f"Brak stałej {pole} w konfiguracji kalkulatora.")

	return {
		"vat_indyw": _decimal(dokument["vat_indyw"], "vat_indyw"),
		"vat_biznes": _decimal(dokument["vat_biznes"], "vat_biznes"),
		"narzut_max": _narzut_max(dokument),
		"pmt_oprocentowanie_mies": _decimal(dokument["pmt_oprocentowanie_mies"], "pmt_oprocentowanie_mies"),
		"ppoz": _decimal(dokument["ppoz"], "ppoz"),
		"panel_moc_wp": _decimal(dokument["panel_moc_wp"], "panel_moc_wp"),
	}


# --- Dobór mocy pompy ciepła ---------------------------------------------------------------


def dobierz_moc_pompy(
	zapotrzebowanie: Decimal, producent: str, typ: str, ogrzewanie: str, dobor: list[dict[str, Any]]
) -> Decimal:
	"""Zwraca moc pompy ciepła (kW) dobraną dla `zapotrzebowanie`, wśród wierszy `dobor`
	pasujących (producent, typ, ogrzewanie) i `od_kw <= zapotrzebowanie <= do_kw`.

	Przedziały w tabeli CEO (nowy_kalkulator.md) nakładają się na granicach (np. Rotenso
	Monoblok Podłogówka: `(8.5, 9.5, 10)` i `(9.5, 10.5, 12)`: `9.5` pasuje do obu):
	wynikiem jest wtedy `max(moc_kw)` wśród wszystkich pasujących wierszy, nigdy pierwszy
	trafiony: to jedyny sposób, żeby granica zawsze dobierała WIĘKSZĄ z dwóch sąsiadujących
	pomp, zamiast zależeć od przypadkowej kolejności wierszy w bazie.

	Brak JAKIEGOKOLWIEK pasującego wiersza (zapotrzebowanie poza najwyższym przedziałem,
	np. 13-14 kW dla Rotenso) rzuca `OZEBrakDoboru` z komunikatem zawierającym dosłownie
	"Brak doboru": to literalny tekst z B5's kontraktu (`frappe.throw` z tym tekstem).
	"""
	kandydaci = [
		wiersz["moc_kw"]
		for wiersz in dobor
		if wiersz["producent"] == producent
		and wiersz["typ"] == typ
		and wiersz["ogrzewanie"] == ogrzewanie
		and wiersz["od_kw"] <= zapotrzebowanie <= wiersz["do_kw"]
	]
	if not kandydaci:
		raise OZEBrakDoboru(
			"Brak doboru pompy ciepła dla podanego zapotrzebowania. Najpierw ocieplenie budynku."
		)
	return max(kandydaci)


# --- Wybór pozycji katalogowych wg rodzaju instalacji --------------------------------------


def _pozycja_wymagana(
	kod: str, cennik: dict[str, dict[str, Any]], ilosc: int = 1, wewnetrzna: bool = False
) -> tuple[str, int]:
	"""Sprawdza, że `kod` istnieje w `cennik` i jest aktywny; zwraca `(kod, ilosc)`.

	`wewnetrzna=True` oznacza, że `kod` jest ZBUDOWANY przez ten moduł (np. z liczby paneli
	albo z wyniku doboru mocy pompy), nie podany bezpośrednio przez klienta: brak takiego
	kodu w katalogu jest więc problemem integralności cennika (`OZEBladMapowania`), nie
	błędem formularza. `wewnetrzna=False` (domyślne) jest dla kodów podanych PRZEZ klienta
	(np. wybrany model klimatyzacji): brak takiego kodu jest błędem danych wejściowych
	(`OZEDaneNiekompletne`, przez `_blad`), bo wybór mógł być po prostu nieaktualny/błędny.

	`ilosc` jest WYŁĄCZNIE polem WYŚWIETLANYM/informacyjnym dla kodów innych niż
	`grzejnik_*` (np. `roz_panele_2` niesie `ilosc=2`, żeby publiczna linia zestawu mogła
	pokazać "Panel PV x 2"): mnożnik CENOWY jest ustalany osobno w `zsumuj_skladowe`/
	`_rozbij_pozycje`, bo ceny pozycji `roz_*` już mają liczbę elementów wbudowaną w kwoty
	składowych (patrz dokumentacja `zsumuj_skladowe`).
	"""
	pozycja = cennik.get(kod)
	if pozycja is None:
		if wewnetrzna:
			raise OZEBladMapowania(f"Brak pozycji katalogowej {kod}.")
		_blad(f"Nieznana pozycja: {kod}.")
	if not pozycja.get("aktywny"):
		raise OZEPozycjaNieaktywna(f"Pozycja {kod} jest nieaktywna.")
	return (kod, ilosc)


def _pozycje_rozbudowa(dane: Any, cennik: dict[str, dict[str, Any]]) -> list[tuple[str, int]]:
	dane = _wymagany_dict(dane, "Brak danych rozbudowy.")
	panele = _wymagana_liczba_calkowita(dane.get("panele", 0), "rozbudowa.panele")
	panele_mikro = _wymagana_liczba_calkowita(dane.get("panele_mikro", 0), "rozbudowa.panele_mikro")
	bateria = _wymagana_liczba_calkowita(dane.get("bateria", 0), "rozbudowa.bateria")

	if not (0 <= panele <= ROZBUDOWA_MAX["panele"]):
		_blad("Liczba paneli PV musi być z zakresu 0-5.")
	if not (0 <= panele_mikro <= ROZBUDOWA_MAX["panele_mikro"]):
		_blad("Liczba paneli PV z mikrofalownikiem musi być z zakresu 0-5.")
	if not (0 <= bateria <= ROZBUDOWA_MAX["bateria"]):
		_blad("Liczba modułów baterii musi być z zakresu 0-4.")
	if panele > 0 and panele_mikro > 0:
		raise OZENiedozwolonaKombinacja(
			"Rozbudowa PV: wybierz albo panele PV, albo panele PV z mikrofalownikiem, nie oba naraz."
		)
	if panele == 0 and panele_mikro == 0 and bateria == 0:
		_blad("Rozbudowa wymaga wyboru przynajmniej jednego elementu (panele, panele z "
			"mikrofalownikiem albo moduły baterii).")

	pozycje: list[tuple[str, int]] = []
	if panele > 0:
		pozycje.append(_pozycja_wymagana(f"roz_panele_{panele}", cennik, ilosc=panele, wewnetrzna=True))
	if panele_mikro > 0:
		pozycje.append(
			_pozycja_wymagana(f"roz_panele_mikro_{panele_mikro}", cennik, ilosc=panele_mikro, wewnetrzna=True)
		)
	if bateria > 0:
		pozycje.append(_pozycja_wymagana(f"roz_bateria_{bateria}", cennik, ilosc=bateria, wewnetrzna=True))
	return pozycje


def _pozycje_klimatyzacja(dane: Any, cennik: dict[str, dict[str, Any]]) -> list[tuple[str, int]]:
	dane = _wymagany_dict(dane, "Brak danych klimatyzacji.")
	kod = dane.get("kod")
	if not isinstance(kod, str) or not kod:
		_blad("Brak wybranego modelu klimatyzacji.")
	pozycja = cennik.get(kod)
	if pozycja is None:
		_blad(f"Nieznana pozycja klimatyzacji: {kod}.")
	if pozycja["rodzaj"] != KLIMATYZACJA:
		_blad(f"Pozycja {kod} nie jest klimatyzacją.")
	if not pozycja.get("aktywny"):
		raise OZEPozycjaNieaktywna(f"Pozycja {kod} jest nieaktywna.")
	return [(kod, 1)]


def _pozycje_grzejnikow(grzejniki: Any, cennik: dict[str, dict[str, Any]]) -> list[tuple[str, int]]:
	if not isinstance(grzejniki, dict):
		_blad("Nieprawidłowy format listy grzejników niskotemperaturowych.")
	pozycje: list[tuple[str, int]] = []
	suma = 0
	for rozmiar, ilosc in grzejniki.items():
		if rozmiar not in GRZEJNIKI_ROZMIARY:
			_blad(f"Nieznany rozmiar grzejnika: {rozmiar!r}.")
		ilosc_int = _wymagana_liczba_calkowita(ilosc, f"grzejniki.{rozmiar}")
		if ilosc_int < 0:
			_blad("Liczba grzejników nie może być ujemna.")
		if ilosc_int == 0:
			continue
		suma += ilosc_int
		pozycje.append(_pozycja_wymagana(f"grzejnik_{rozmiar}", cennik, ilosc=ilosc_int, wewnetrzna=True))
	if suma > GRZEJNIKI_MAX:
		raise OZENiedozwolonaKombinacja(
			f"Łączna liczba grzejników niskotemperaturowych nie może przekraczać {GRZEJNIKI_MAX}."
		)
	return pozycje


def _pozycje_pompa(
	dane: Any, cennik: dict[str, dict[str, Any]], dobor: list[dict[str, Any]]
) -> list[tuple[str, int]]:
	dane = _wymagany_dict(dane, "Brak danych pompy ciepła.")

	zapotrzebowanie_kod = dane.get("zapotrzebowanie")
	if zapotrzebowanie_kod not in ZAPOTRZEBOWANIE:
		_blad("Nieznana wartość zapotrzebowania budynku na moc.")
	zapotrzebowanie = ZAPOTRZEBOWANIE[zapotrzebowanie_kod]

	producent = dane.get("producent")
	if producent not in PC_PRODUCENCI:
		_blad("Nieznany producent pompy ciepła.")
	typ = dane.get("typ")
	if typ not in PC_PRODUCENCI[producent]:
		raise OZENiedozwolonaKombinacja(f"Pompa ciepła {producent} nie jest dostępna w typie {typ}.")

	ogrzewanie_wybrane = dane.get("ogrzewanie")
	if ogrzewanie_wybrane not in PC_OGRZEWANIE:
		_blad("Nieznany rodzaj ogrzewania.")
	ogrzewanie_doboru = PC_OGRZEWANIE[ogrzewanie_wybrane]

	moc_kw = dobierz_moc_pompy(zapotrzebowanie, producent, typ, ogrzewanie_doboru, dobor)
	kod_pompy = f"{PC_GRUPA[(producent, typ)]}_{int(moc_kw)}"
	pozycje = [_pozycja_wymagana(kod_pompy, cennik, wewnetrzna=True)]

	cwu = dane.get("cwu", "") or ""
	if cwu not in ("", "200", "300"):
		_blad("Nieznana wartość zasobnika CWU.")
	if cwu:
		pozycje.append(_pozycja_wymagana(f"cwu_pc_{cwu}", cennik, wewnetrzna=True))

	pozycje.extend(_pozycje_grzejnikow(dane.get("grzejniki") or {}, cennik))
	return pozycje


def _pozycje_kociol(dane: Any, cennik: dict[str, dict[str, Any]]) -> list[tuple[str, int]]:
	dane = _wymagany_dict(dane, "Brak danych kotła.")
	kod = dane.get("kod")
	if not isinstance(kod, str) or not kod:
		_blad("Brak wybranego modelu kotła.")
	pozycja = cennik.get(kod)
	if pozycja is None:
		_blad(f"Nieznana pozycja kotła: {kod}.")
	if pozycja["rodzaj"] != KOCIOL:
		_blad(f"Pozycja {kod} nie jest kotłem.")
	if not pozycja.get("aktywny"):
		raise OZEPozycjaNieaktywna(f"Pozycja {kod} jest nieaktywna.")
	pozycje = [(kod, 1)]

	cwu = dane.get("cwu", "") or ""
	if cwu not in ("", "200", "300"):
		_blad("Nieznana wartość zasobnika CWU.")
	if cwu:
		pozycje.append(_pozycja_wymagana(f"cwu_kociol_{cwu}", cennik, wewnetrzna=True))
	return pozycje


def pozycje_dla(
	wejscie: dict[str, Any], cennik: dict[str, dict[str, Any]], dobor: list[dict[str, Any]]
) -> list[tuple[str, int]]:
	"""Zwraca listę `(kod, ilosc)` pozycji katalogowych wybranych dla `wejscie["rodzaj"]`,
	czytając WYŁĄCZNIE pod-słownik `wejscie` odpowiadający temu rodzajowi (`rozbudowa` /
	`klimatyzacja` / `pompa` / `kociol`): to strukturalnie wyklucza np. przesłanie
	grzejników dla Klimatyzacji: takie dane po prostu nigdy nie są czytane."""
	rodzaj = wejscie.get("rodzaj")
	if rodzaj == ROZBUDOWA:
		return _pozycje_rozbudowa(wejscie.get("rozbudowa"), cennik)
	if rodzaj == KLIMATYZACJA:
		return _pozycje_klimatyzacja(wejscie.get("klimatyzacja"), cennik)
	if rodzaj == POMPA_CIEPLA:
		return _pozycje_pompa(wejscie.get("pompa"), cennik, dobor)
	if rodzaj == KOCIOL:
		return _pozycje_kociol(wejscie.get("kociol"), cennik)
	_blad("Nieznany rodzaj instalacji.")


# --- Sumowanie składowych -------------------------------------------------------------------


def zsumuj_skladowe(
	pozycje: list[tuple[str, int]], cennik: dict[str, dict[str, Any]], rodzaj: str
) -> dict[str, Any]:
	"""Rozbija wybrane `pozycje` na linie kosztowe/marżowe wewnętrznego podglądu admina.

	Mnożnik ceny jest `ilosc` WYŁĄCZNIE dla kodów `grzejnik_*` (ich cennik niesie cenę JEDNEGO
	grzejnika): dla wszystkich innych kodów mnożnik jest `1`, bo liczba elementów jest już
	wbudowana w kwoty składowych pozycji (np. `roz_panele_2` ma w cenniku kwotę "Panele" równą
	2x400, nie 1x400: patrz SEED `ops/crm-cennik-oze.py`).

	Dla Rozbudowy (`rodzaj == ROZBUDOWA`) składowe oznaczone `wspolna=True` (Dostawa,
	Kilometrówka, Papiery OSD, Bonus liderski) są liczone RAZ dla całej rozbudowy: wśród
	wszystkich wybranych pozycji bierzemy `max(kwota)` per `klucz` składowej, nie sumę:
	decyzja CEO 2026-10-04. Dla innych rodzajów `wspolna` jest ignorowane (nie ma znaczenia,
	bo wybierana jest zawsze dokładnie jedna "główna" pozycja).

	Zwraca `{"linie": [...], "koszt_calkowity", "marza_proenergy", "bonus_liderski"}`: PPOŻ
	(dla Rozbudowy) jest dołączane PO tej funkcji, w `oblicz_oferte` (zależy od `wejscie` i
	`stale`, których ta funkcja celowo nie przyjmuje: sygnatura `(pozycje, cennik, rodzaj)`).
	"""
	linie: list[dict[str, Any]] = []
	wspolne: dict[str, tuple[Decimal, str, str]] = {}
	koszt_calkowity = _ZERO
	marza_proenergy = _ZERO
	bonus_liderski = _ZERO

	def _naliczaj(typ: str, kwota: Decimal) -> None:
		nonlocal koszt_calkowity, marza_proenergy, bonus_liderski
		if typ == "Koszt":
			koszt_calkowity += kwota
		elif typ == "Marża Proenergy":
			marza_proenergy += kwota
		elif typ == "Bonus liderski":
			bonus_liderski += kwota

	for kod, ilosc in pozycje:
		pozycja = cennik[kod]
		mnoznik = ilosc if kod.startswith("grzejnik_") else 1
		for skladowa in pozycja["skladowe"]:
			kwota = skladowa["kwota"] * mnoznik
			if rodzaj == ROZBUDOWA and skladowa["wspolna"]:
				klucz = skladowa["klucz"]
				dotychczasowa = wspolne.get(klucz)
				if dotychczasowa is None or kwota > dotychczasowa[0]:
					wspolne[klucz] = (kwota, skladowa["nazwa"], skladowa["typ"])
				continue
			linie.append(
				{
					"klucz": f"{kod}:{skladowa['klucz']}",
					"etykieta": f"{skladowa['nazwa']} ({pozycja['nazwa']})",
					"typ": skladowa["typ"],
					"kwota": _kwota(kwota),
				}
			)
			_naliczaj(skladowa["typ"], kwota)

	for klucz, (kwota, nazwa, typ) in wspolne.items():
		linie.append({"klucz": f"wspolne:{klucz}", "etykieta": nazwa, "typ": typ, "kwota": _kwota(kwota)})
		_naliczaj(typ, kwota)

	return {
		"linie": linie,
		"koszt_calkowity": koszt_calkowity,
		"marza_proenergy": marza_proenergy,
		"bonus_liderski": bonus_liderski,
	}


def _rozbij_pozycje(pozycje: list[tuple[str, int]], cennik: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
	"""Rozbicie per-pozycja (`wewnetrzne.pozycje` kontraktu): `ilosc` tutaj jest wyłącznie
	WYŚWIETLANA (np. "2" dla `roz_panele_2"), mnożnik cenowy jest ten sam co w
	`zsumuj_skladowe` (`1`, poza `grzejnik_*`), żeby `netto`/`koszt`/`marza`/`bonus` per
	pozycja NIE liczyły podwójnie ceny już wbudowanej w kod `roz_*`."""
	wynik: list[dict[str, Any]] = []
	for kod, ilosc in pozycje:
		pozycja = cennik[kod]
		mnoznik = ilosc if kod.startswith("grzejnik_") else 1
		netto = _ZERO
		koszt = _ZERO
		marza = _ZERO
		bonus = _ZERO
		for skladowa in pozycja["skladowe"]:
			kwota = skladowa["kwota"] * mnoznik
			netto += kwota
			if skladowa["typ"] == "Koszt":
				koszt += kwota
			elif skladowa["typ"] == "Marża Proenergy":
				marza += kwota
			elif skladowa["typ"] == "Bonus liderski":
				bonus += kwota
		wynik.append(
			{
				"kod": kod,
				"nazwa": pozycja["nazwa"],
				"ilosc": ilosc,
				"netto": _kwota(netto),
				"koszt": _kwota(koszt),
				"marza": _kwota(marza),
				"bonus": _kwota(bonus),
			}
		)
	return wynik


def _linie_publiczne(
	rodzaj: str, pozycje: list[tuple[str, int]], cennik: dict[str, dict[str, Any]], ppoz: bool
) -> list[dict[str, Any]]:
	"""Linie `custom_zestaw` (klient-facing): dla Rozbudowy BEZ producenta/modelu/Wp/kWh,
	tylko "Panel PV x N" / "Panel PV + mikrofalownik x N" / "Moduł baterii x N" (decyzja CEO
	2026-10-04); dla innych rodzajów pełna nazwa pozycji katalogowej z cennika."""
	linie: list[dict[str, Any]] = []
	if rodzaj == ROZBUDOWA:
		for kod, ilosc in pozycje:
			if kod.startswith("roz_panele_mikro_"):
				nazwa = f"Panel PV + mikrofalownik x {ilosc}"
			elif kod.startswith("roz_panele_"):
				nazwa = f"Panel PV x {ilosc}"
			elif kod.startswith("roz_bateria_"):
				nazwa = f"Moduł baterii x {ilosc}"
			else:
				nazwa = cennik[kod]["nazwa"]
			linie.append({"kod": kod, "typ": "Rozbudowa", "nazwa": nazwa, "ilosc": ilosc, "jednostka": "szt"})
		if ppoz:
			linie.append(
				{"kod": "ppoz", "typ": "Rozbudowa", "nazwa": "Uzgodnienia PPOŻ", "ilosc": 1, "jednostka": "szt"}
			)
		return linie

	typ_glowny = {KLIMATYZACJA: "Klimatyzacja", POMPA_CIEPLA: "Pompa ciepła", KOCIOL: "Kocioł"}[rodzaj]
	for kod, ilosc in pozycje:
		if kod.startswith("cwu_"):
			typ_linii = "CWU"
		elif kod.startswith("grzejnik_"):
			typ_linii = "Grzejnik niskotemperaturowy"
		else:
			typ_linii = typ_glowny
		linie.append(
			{"kod": kod, "typ": typ_linii, "nazwa": cennik[kod]["nazwa"], "ilosc": ilosc, "jednostka": "szt"}
		)
	return linie


# --- Rata kredytu (annuity) -----------------------------------------------------------------


def _rata_kredytu(kwota_kredytu: Decimal, okres_lat: int, oprocentowanie_mies_pct: Decimal) -> Decimal:
	"""Rata annuitetowa, identyczny wzór co `crm/czyste_powietrze/obliczenia.py::oblicz_finansowanie`."""
	if kwota_kredytu <= _ZERO:
		return _ZERO
	n = okres_lat * 12
	i = oprocentowanie_mies_pct / _STO
	if i == _ZERO:
		return kwota_kredytu / n
	mnoznik = (_JEDEN + i) ** n
	return kwota_kredytu * i * mnoznik / (mnoznik - _JEDEN)


# --- Punkt wejścia ---------------------------------------------------------------------------


def oblicz_oferte(
	wejscie: dict[str, Any], cennik: dict[str, dict[str, Any]], dobor: list[dict[str, Any]], stale: dict[str, Any]
) -> dict[str, Any]:
	"""Liczy ofertę dla jednego z czterech nowych rodzajów instalacji OZE, bez dostępu do
	frameworka, bazy danych ani innych źródeł danych. Żaden argument nie jest mutowany.

	`wewnetrzne` jest ZAWSZE obecne w wyniku (bramka widoczności "tylko admin" żyje w
	`crm/api/kalkulator_oze.py`, przez `wynik.pop("wewnetrzne", None)` dla nie-admina:
	identyczny wzorzec co `volteo_cp_calc` dla Czyste Powietrze).
	"""
	if not isinstance(wejscie, dict) or not isinstance(cennik, dict) or not isinstance(dobor, list) or not isinstance(stale, dict):
		_blad("Nieprawidłowe dane wejściowe kalkulatora.")

	rodzaj = wejscie.get("rodzaj")
	if rodzaj not in RODZAJE_NOWE:
		_blad("Nieznany rodzaj instalacji.")
	typ_klienta = wejscie.get("typ_klienta")
	if typ_klienta not in TYPY_KLIENTA:
		_blad("Nieznany typ klienta.")

	narzut = _decimal(wejscie.get("narzut", 0), "narzut")
	if narzut < _ZERO:
		_blad("Narzut nie może być ujemny.")
	narzut_max = _stala(stale, "narzut_max")
	if narzut_max is not None and narzut > narzut_max:
		_blad("Narzut przekracza dopuszczalny limit.")

	ulga_pct = _decimal(wejscie.get("ulga_pct", 0), "ulga_pct")
	if not (_ZERO <= ulga_pct <= _STO):
		_blad("Procent ulgi termomodernizacyjnej musi być z zakresu 0-100.")

	wplata_wlasna = _decimal(wejscie.get("wplata_wlasna", 0), "wplata_wlasna")
	if wplata_wlasna < _ZERO:
		_blad("Wpłata własna nie może być ujemna.")

	okres_lat = wejscie.get("okres_lat", _OKRES_LAT_DOMYSLNY)
	if isinstance(okres_lat, bool) or not isinstance(okres_lat, int):
		_blad("Okres kredytowania musi być liczbą całkowitą lat.")
	if not (_OKRES_LAT_MIN <= okres_lat <= _OKRES_LAT_MAX):
		_blad("Okres kredytowania musi być z zakresu 1-10 lat.")

	pozycje = pozycje_dla(wejscie, cennik, dobor)
	skladowe = zsumuj_skladowe(pozycje, cennik, rodzaj)
	koszt_calkowity = skladowe["koszt_calkowity"]
	marza_proenergy = skladowe["marza_proenergy"]
	bonus_liderski = skladowe["bonus_liderski"]
	linie_wewnetrzne = list(skladowe["linie"])

	ppoz = False
	ppoz_prog = False
	pompa_info: dict[str, Any] | None = None

	if rodzaj == ROZBUDOWA:
		rozbudowa = wejscie.get("rozbudowa") or {}
		panele = _wymagana_liczba_calkowita(rozbudowa.get("panele", 0), "rozbudowa.panele")
		panele_mikro = _wymagana_liczba_calkowita(rozbudowa.get("panele_mikro", 0), "rozbudowa.panele_mikro")
		istniejaca = _decimal(rozbudowa.get("istniejaca_pv_moc_kwp", 0), "rozbudowa.istniejaca_pv_moc_kwp")
		if istniejaca < _ZERO:
			_blad("Istniejąca moc PV nie może być ujemna.")
		ppoz_recznie = _flaga_tak_nie(rozbudowa.get("ppoz_recznie", False), "rozbudowa.ppoz_recznie")

		panel_moc_wp = _stala(stale, "panel_moc_wp")
		moc_dodana = Decimal(panele + panele_mikro) * panel_moc_wp / _TYSIAC
		ppoz_prog = (istniejaca + moc_dodana) > PROG_PPOZ_KW
		ppoz = ppoz_prog or ppoz_recznie
		if ppoz:
			ppoz_kwota = _kwota(_stala(stale, "ppoz"))
			linie_wewnetrzne.append(
				{"klucz": "ppoz", "etykieta": "Uzgodnienia PPOŻ", "typ": "Koszt", "kwota": ppoz_kwota}
			)
			koszt_calkowity += ppoz_kwota

	if rodzaj == POMPA_CIEPLA:
		pompa_kod = next((kod for kod, _ in pozycje if kod.startswith("pc_")), None)
		if pompa_kod is not None:
			pompa_info = {"moc_kw": cennik[pompa_kod]["moc_kw"], "kod": pompa_kod}

	netto = _kwota(koszt_calkowity + marza_proenergy + bonus_liderski + narzut)
	vat_rate = _stala(stale, "vat_indyw") if typ_klienta == INDYWIDUALNY else _stala(stale, "vat_biznes")
	vat = _kwota(netto * vat_rate / _STO)
	brutto = _kwota(netto + vat)

	dotacja = _ZERO
	cena_po_dotacji = _kwota(brutto - dotacja)

	if typ_klienta == BIZNESOWY or rodzaj in RODZAJE_BEZ_ULGI:
		ulga = _ZERO
	else:
		ulga = _kwota(cena_po_dotacji * ulga_pct / _STO)
	cena_po_uldze = _kwota(cena_po_dotacji - ulga)

	if typ_klienta == BIZNESOWY:
		rata_brutto = _ZERO
		rata_po_dotacji = _ZERO
		rata_po_uldze = _ZERO
	else:
		pmt = _stala(stale, "pmt_oprocentowanie_mies")
		rata_brutto = _rata_kredytu(max(_ZERO, brutto - wplata_wlasna), okres_lat, pmt)
		rata_po_dotacji = _rata_kredytu(max(_ZERO, cena_po_dotacji - wplata_wlasna), okres_lat, pmt)
		rata_po_uldze = _rata_kredytu(max(_ZERO, cena_po_uldze - wplata_wlasna), okres_lat, pmt)

	# Dwuznaczność rozstrzygnięta i opisana w dockstringu modułu: "marza" = CAŁA nadwyżka nad
	# kosztem (marża ProEnergy + bonus liderski + narzut handlowca), "zysk" = ta nadwyżka BEZ
	# narzutu (bo narzut trafia do handlowca, nie do firmy) -- analogicznie do CP (marza -
	# prowizja_handlowa = zysk).
	marza_calkowita = _kwota(marza_proenergy + bonus_liderski + narzut)
	zysk = _kwota(marza_proenergy + bonus_liderski)

	return {
		"rodzaj": rodzaj,
		"typ_klienta": typ_klienta,
		"netto": netto,
		"vat": vat,
		"vat_rate": vat_rate,
		"brutto": brutto,
		"narzut": _kwota(narzut),
		"dotacja": _kwota(dotacja),
		"cena_po_dotacji": cena_po_dotacji,
		"ulga": ulga,
		"cena_po_uldze": cena_po_uldze,
		"raty": {
			"brutto": _kwota(rata_brutto),
			"po_dotacji": _kwota(rata_po_dotacji),
			"po_uldze": _kwota(rata_po_uldze),
		},
		"linie": _linie_publiczne(rodzaj, pozycje, cennik, ppoz),
		"pompa": pompa_info,
		"ppoz": ppoz,
		"ppoz_prog": ppoz_prog,
		"wewnetrzne": {
			"koszt_calkowity": _kwota(koszt_calkowity),
			"marza_proenergy": _kwota(marza_proenergy),
			"bonus_liderski": _kwota(bonus_liderski),
			"narzut": _kwota(narzut),
			"marza": marza_calkowita,
			"zysk": zysk,
			"linie": linie_wewnetrzne,
			"pozycje": _rozbij_pozycje(pozycje, cennik),
		},
	}


def zloz_adres_montazu(ulica: Any, nr_domu: Any, nr_mieszkania: Any = None) -> str:
	"""Składa jedno pole ulicy szansy z trzech pól kontaktu, tą samą regułą co `composeAddress()`
	w `KalkulatorTab.vue` (kalkulator PV): "Ulica NrDomu", a przy numerze mieszkania
	"Ulica NrDomu/NrMieszkania". Puste i None są pomijane. Numer mieszkania bez ulicy i domu nie
	tworzy adresu (zwraca ""), bo sam nic nie opisuje."""

	def _tekst(wartosc: Any) -> str:
		return "" if wartosc is None else str(wartosc).strip()

	glowna = " ".join(czesc for czesc in (_tekst(ulica), _tekst(nr_domu)) if czesc)
	mieszkanie = _tekst(nr_mieszkania)
	if glowna and mieszkanie:
		return f"{glowna}/{mieszkanie}"
	return glowna
