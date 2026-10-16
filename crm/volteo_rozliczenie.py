# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta logika rozliczeń prowizji z odbiorcami (Handlowiec, Manager, Partner), ops#280.

Moduł celowo nie importuje ``frappe`` (precedens ``crm/volteo_naming.py``,
``crm/volteo_aktywnosc.py``): wszystko tu jest testowalne lokalnie przez ``unittest``.
Dotykanie bazy robi adapter ``crm/rozliczenia.py``.

Wiersz rozliczenia to słownik z kluczami ``rola``, ``status``, ``kwota``,
``data_wyplaty`` (pozostałe są ignorowane). Pieniądze przez ``Decimal``, zaokrąglenie
do grosza (ROUND_HALF_UP) raz, w liściu. Moduły nie mutują wejścia.
"""

import datetime
import json
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

ROLA_HANDLOWIEC = "Handlowiec"
ROLA_MANAGER = "Manager"
ROLA_PARTNER = "Partner"
ROLE: tuple[str, ...] = (ROLA_HANDLOWIEC, ROLA_MANAGER, ROLA_PARTNER)

STATUS_DO_WYPLATY = "Do wypłaty"
STATUS_WYPLACONE = "Wypłacone"
STATUS_WSTRZYMANE = "Wstrzymane"
STATUS_NIE_DOTYCZY = "Nie dotyczy"
STATUSY_WIERSZA: tuple[str, ...] = (
	STATUS_DO_WYPLATY,
	STATUS_WYPLACONE,
	STATUS_WSTRZYMANE,
	STATUS_NIE_DOTYCZY,
)

STAN_NIEROZLICZONE = "Nierozliczone"
STAN_CZESCIOWO = "Częściowo rozliczone"
STAN_ROZLICZONE = "Rozliczone"
STAN_WSTRZYMANE = "Wstrzymane"
STAN_NIE_DOTYCZY = "Nie dotyczy"
STANY_SZANSY: tuple[str, ...] = (
	"",
	STAN_NIEROZLICZONE,
	STAN_CZESCIOWO,
	STAN_ROZLICZONE,
	STAN_WSTRZYMANE,
	STAN_NIE_DOTYCZY,
)

ZRODLA_KWOTY: tuple[str, ...] = ("Snapshot", "Ręcznie", "Automat")

ZNACZNIK_ROZLICZENIE = "[volteo:rozliczenie]"
"""Znacznik wiodący śladu rozliczenia w Aktywności szansy; linia tylko dla administracji
(dopisany do `crm.volteo_aktywnosc.ZNACZNIKI_ADMIN`)."""

RODZAJ_CP = "Czyste Powietrze"

_KWANT = Decimal("0.01")
_ZERO = Decimal("0")

_LITERA_STATUSU = {
	STATUS_WYPLACONE: "W",
	STATUS_DO_WYPLATY: "D",
	STATUS_WSTRZYMANE: "S",
	STATUS_NIE_DOTYCZY: "N",
}
_STATUS_Z_LITERY = {litera: status for status, litera in _LITERA_STATUSU.items()}
_LITERA_ROLI = {ROLA_HANDLOWIEC: "H", ROLA_MANAGER: "M", ROLA_PARTNER: "P"}
_ROLA_Z_LITERY = {litera: rola for rola, litera in _LITERA_ROLI.items()}


# --- pieniądze i daty -----------------------------------------------------------------


def _kwota(wartosc: Any) -> Decimal:
	"""Koercja do `Decimal` zaokrąglonego do grosza. Przyjmuje Decimal, int, float, str
	(spacje zwykłe i nierozdzielające usuwane, przecinek jako separator dziesiętny).
	Śmieci i brak skończonej liczby to `ValueError`."""
	if isinstance(wartosc, bool) or wartosc is None:
		raise ValueError(f"Nieprawidłowa kwota: {wartosc!r}.")
	if isinstance(wartosc, str):
		wartosc = wartosc.replace("\xa0", "").replace(" ", "").replace(",", ".")
	try:
		wynik = Decimal(str(wartosc)) if not isinstance(wartosc, Decimal) else wartosc
	except InvalidOperation:
		raise ValueError(f"Nieprawidłowa kwota: {wartosc!r}.") from None
	if not wynik.is_finite():
		raise ValueError(f"Nieprawidłowa kwota: {wartosc!r}.")
	return wynik.quantize(_KWANT, rounding=ROUND_HALF_UP)


def _kwota_lub_zero(wartosc: Any) -> Decimal:
	try:
		return _kwota(wartosc)
	except ValueError:
		return _ZERO


def _data(wartosc: Any) -> datetime.date | None:
	"""`date`, `datetime`, tekst ISO (`RRRR-MM-DD`, ewentualnie z godziną) albo `None`."""
	if wartosc is None or wartosc == "":
		return None
	if isinstance(wartosc, datetime.datetime):
		return wartosc.date()
	if isinstance(wartosc, datetime.date):
		return wartosc
	try:
		return datetime.date.fromisoformat(str(wartosc).strip()[:10])
	except ValueError:
		return None


def formatuj_kwote(kwota: Any) -> str:
	"""`2400` -> `2 400,00 zł` (spacja jako separator tysięcy, przecinek dziesiętny)."""
	wartosc = _kwota(kwota)
	calosci, _, ulamek = f"{wartosc:.2f}".partition(".")
	znak = ""
	if calosci.startswith("-"):
		znak, calosci = "-", calosci[1:]
	grupy = []
	while len(calosci) > 3:
		grupy.insert(0, calosci[-3:])
		calosci = calosci[:-3]
	grupy.insert(0, calosci)
	return f"{znak}{' '.join(grupy)},{ulamek} zł"


# --- stan zbiorczy --------------------------------------------------------------------


def _liczace(wiersze: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
	return [w for w in wiersze if w.get("status") != STATUS_NIE_DOTYCZY]


def stan_zbiorczy(wiersze: Iterable[Mapping[str, Any]]) -> str:
	"""Stan zbiorczy szansy: `""` (brak wierszy), `Nie dotyczy`, `Wstrzymane`,
	`Rozliczone`, `Nierozliczone` albo `Częściowo rozliczone`."""
	wiersze = list(wiersze)
	if not wiersze:
		return ""
	liczace = _liczace(wiersze)
	if not liczace:
		return STAN_NIE_DOTYCZY
	statusy = [w.get("status") for w in liczace]
	if STATUS_WSTRZYMANE in statusy and STATUS_DO_WYPLATY not in statusy:
		return STAN_WSTRZYMANE
	if all(s == STATUS_WYPLACONE for s in statusy):
		return STAN_ROZLICZONE
	if STATUS_WYPLACONE not in statusy:
		return STAN_NIEROZLICZONE
	return STAN_CZESCIOWO


def licznik(wiersze: Iterable[Mapping[str, Any]]) -> str:
	"""`wypłacone/liczące się`, np. `1/3`. Role `Nie dotyczy` pomijane; brak wierszy
	(lub same `Nie dotyczy`) daje `""`."""
	liczace = _liczace(wiersze)
	if not liczace:
		return ""
	wyplacone = sum(1 for w in liczace if w.get("status") == STATUS_WYPLACONE)
	return f"{wyplacone}/{len(liczace)}"


def tokeny_odbiorcow(wiersze: Iterable[Mapping[str, Any]]) -> str:
	"""`H:W;M:D;P:S`: litera roli (H, M, P), litera statusu (W wypłacone, D do wypłaty,
	S wstrzymane, N nie dotyczy). Kolejność H, M, P; tylko role mające wiersz."""
	wg_roli = {w.get("rola"): w.get("status") for w in wiersze}
	czesci = []
	for rola in ROLE:
		if rola in wg_roli:
			litera = _LITERA_STATUSU.get(wg_roli[rola])
			if litera:
				czesci.append(f"{_LITERA_ROLI[rola]}:{litera}")
	return ";".join(czesci)


def parsuj_tokeny(tekst: str | None) -> dict[str, str]:
	"""Odwrotność `tokeny_odbiorcow`: `{rola: status}`. Tolerancyjna: białe znaki i wielkość
	liter ignorowane, nieznane lub uszkodzone fragmenty pomijane, `None` daje `{}`."""
	wynik: dict[str, str] = {}
	if not tekst:
		return wynik
	for fragment in str(tekst).split(";"):
		klucz, sep, wartosc = fragment.strip().partition(":")
		if not sep:
			continue
		rola = _ROLA_Z_LITERY.get(klucz.strip().upper())
		status = _STATUS_Z_LITERY.get(wartosc.strip().upper())
		if rola and status:
			wynik[rola] = status
	return wynik


def sumy(wiersze: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
	"""Sumy kwot: `do_wyplaty` (Do wypłaty + Wstrzymane), `wyplacono`, `lacznie` (suma tych
	dwóch, bez `Nie dotyczy`) jako `Decimal`, oraz `ostatnia_wyplata` (najpóźniejsza
	`data_wyplaty` wśród wierszy Wypłacone albo `None`)."""
	do_wyplaty = _ZERO
	wyplacono = _ZERO
	daty: list[datetime.date] = []
	for w in wiersze:
		status = w.get("status")
		kwota = _kwota_lub_zero(w.get("kwota"))
		if status in (STATUS_DO_WYPLATY, STATUS_WSTRZYMANE):
			do_wyplaty += kwota
		elif status == STATUS_WYPLACONE:
			wyplacono += kwota
			data = _data(w.get("data_wyplaty"))
			if data:
				daty.append(data)
	return {
		"do_wyplaty": do_wyplaty,
		"wyplacono": wyplacono,
		"lacznie": do_wyplaty + wyplacono,
		"ostatnia_wyplata": max(daty) if daty else None,
	}


def pola_szansy(wiersze: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
	"""Sześć wartości dla pól `custom_rozliczenie_*` na `CRM Deal` (klucze bez prefiksu
	`custom_rozliczenie_`): status, odbiorcy, licznik, ostatnia_wyplata, do_wyplaty,
	wyplacono. Brak wierszy daje puste teksty, `None` i zera."""
	wiersze = list(wiersze)
	s = sumy(wiersze)
	return {
		"status": stan_zbiorczy(wiersze),
		"odbiorcy": tokeny_odbiorcow(wiersze),
		"licznik": licznik(wiersze),
		"ostatnia_wyplata": s["ostatnia_wyplata"],
		"do_wyplaty": s["do_wyplaty"],
		"wyplacono": s["wyplacono"],
	}


# --- walidacje ------------------------------------------------------------------------


def waliduj_wyplate(status: str | None, data_wyplaty: Any) -> str | None:
	"""Komunikat błędu albo `None`. Status `Wypłacone` wymaga daty wypłaty."""
	if status == STATUS_WYPLACONE and _data(data_wyplaty) is None:
		return "Wypłata wymaga daty wypłaty."
	return None


def waliduj_kwote(kwota: Any) -> str | None:
	"""Komunikat błędu albo `None`. Kwota musi być liczbą nieujemną."""
	try:
		wartosc = _kwota(kwota)
	except ValueError:
		return "Kwota rozliczenia musi być liczbą."
	if wartosc < _ZERO:
		return "Kwota rozliczenia nie może być ujemna."
	return None


def waliduj_unikalnosc(wiersze: Iterable[Mapping[str, Any]], nowy: Mapping[str, Any]) -> str | None:
	"""Komunikat błędu albo `None`. Jedna rola na szansę: błąd, gdy `wiersze` zawierają
	inny wiersz (inna `name`) z tą samą rolą co `nowy`."""
	rola = nowy.get("rola")
	if rola not in ROLE:
		return f"Nieznana rola odbiorcy: {rola!r}."
	nazwa = nowy.get("name")
	for w in wiersze:
		if w.get("rola") == rola and (nazwa is None or w.get("name") != nazwa):
			return f"Szansa ma już wiersz rozliczenia dla roli {rola}."
	return None


# --- kwoty odbiorców ------------------------------------------------------------------


def _skladniki_marzy(snapshot: Any) -> list[Any]:
	if isinstance(snapshot, str):
		try:
			snapshot = json.loads(snapshot) if snapshot.strip() else None
		except ValueError:
			return []
	if not isinstance(snapshot, Mapping):
		return []
	skladniki = snapshot.get("skladniki_marzy")
	if skladniki is None and isinstance(snapshot.get("podsumowanie"), Mapping):
		skladniki = snapshot["podsumowanie"].get("skladniki_marzy")
	return list(skladniki) if isinstance(skladniki, list) else []


def _narzut_ze_snapshotu(snapshot: Any) -> Decimal | None:
	for skladnik in _skladniki_marzy(snapshot):
		if isinstance(skladnik, Mapping) and skladnik.get("klucz") == "narzut":
			try:
				return _kwota(skladnik.get("kwota"))
			except ValueError:
				return None
	return None


def kwoty_odbiorcow(
	rodzaj: str | None,
	snapshot: Any,
	pola_cp: Mapping[str, Any] | None,
	deal_owner: str | None,
	manager: str | None,
) -> dict[str, dict[str, Any]]:
	"""Kwoty prowizji per rola: `{rola: {"kwota": Decimal | None, "zrodlo": str, "odbiorca": str | None}}`.

	Rola bez wpisu w wyniku nie dostaje wiersza. `kwota` `None` znaczy "nieznana" (adapter
	zakłada wiersz z 0 i źródłem `Ręcznie`).

	* Czyste Powietrze: trzy kwoty z `pola_cp` (`custom_cp_prowizja_handlowa`,
	  `custom_cp_nadprowizja_manager`, `custom_cp_nadprowizja_partner`), źródło `Snapshot`;
	  Manager i Partner tylko gdy kwota > 0.
	* OZE: Handlowiec = składnik `narzut` ze snapshotu kosztów (`skladniki_marzy`); Manager
	  i Partner bez wiersza (kwoty wpisuje admin ręcznie).

	To JEDYNE miejsce, w którym w przyszłości powstanie automat kwot managera i partnera
	dla OZE (źródło `Automat`); nic innego nie powinno liczyć tych kwot.
	"""
	if rodzaj == RODZAJ_CP:
		pola = pola_cp or {}
		wynik: dict[str, dict[str, Any]] = {}

		def kwota_pola(klucz: str) -> Decimal | None:
			wartosc = pola.get(klucz)
			if wartosc is None or wartosc == "":
				return None
			try:
				return _kwota(wartosc)
			except ValueError:
				return None

		handlowiec = kwota_pola("custom_cp_prowizja_handlowa")
		wynik[ROLA_HANDLOWIEC] = {
			"kwota": handlowiec,
			"zrodlo": "Snapshot" if handlowiec is not None else "Ręcznie",
			"odbiorca": deal_owner,
		}
		for rola, klucz, odbiorca in (
			(ROLA_MANAGER, "custom_cp_nadprowizja_manager", manager),
			(ROLA_PARTNER, "custom_cp_nadprowizja_partner", None),
		):
			kwota = kwota_pola(klucz)
			if kwota is not None and kwota > _ZERO:
				wynik[rola] = {"kwota": kwota, "zrodlo": "Snapshot", "odbiorca": odbiorca}
		return wynik

	narzut = _narzut_ze_snapshotu(snapshot)
	return {
		ROLA_HANDLOWIEC: {
			"kwota": narzut,
			"zrodlo": "Snapshot" if narzut is not None else "Ręcznie",
			"odbiorca": deal_owner,
		}
	}


def warunek_naliczenia(dane: Mapping[str, Any]) -> bool:
	"""Punkt rozszerzenia przyszłego automatycznego naliczania odbiorców. DZIŚ ZAWSZE `False`
	(decyzja właściciela 2026-10-16: naliczanie wyłącznie ręczne, przyciskiem w zakładce).

	Docelowo: "inwestycja opłacona w 100% i sprzęt zamontowany". Funkcja ma czytać ze
	słownika `dane` (bez frappe, żeby test go nie potrzebował) płatność (stan rozliczeń
	z klientem: suma wpłat wobec ceny brutto szansy) oraz status montażu (etap procesu
	lub zakończony montaż na zakładce Montaż). Gdy zacznie zwracać `True`, wołająca ją
	`crm.rozliczenia.nalicz_jesli_spelnione` utworzy brakujące wiersze."""
	return False


def data_podpisania(wpisy: Iterable[Mapping[str, Any]]) -> datetime.date | None:
	"""Data przejścia szansy na `Umowa Podpisana` z wpisów `status_change_log`
	(pola `to`, `to_date`); najpóźniejszy pasujący wpis, brak wpisu to `None`."""
	daty = [_data(w.get("to_date")) for w in wpisy if w.get("to") == "Umowa Podpisana"]
	daty = [d for d in daty if d is not None]
	return max(daty) if daty else None


# --- okres ----------------------------------------------------------------------------


def _koniec_miesiaca(rok: int, miesiac: int) -> datetime.date:
	if miesiac == 12:
		return datetime.date(rok, 12, 31)
	return datetime.date(rok, miesiac + 1, 1) - datetime.timedelta(days=1)


def _miesiac_wstecz(rok: int, miesiac: int, ile: int) -> tuple[int, int]:
	numer = rok * 12 + (miesiac - 1) - ile
	return numer // 12, numer % 12 + 1


def zakres_okresu(
	preset: str,
	dzis: datetime.date,
	od: datetime.date | None = None,
	do: datetime.date | None = None,
) -> tuple[datetime.date, datetime.date]:
	"""Zakres dat `(od, do)`, oba końce włącznie. Presety: `dzisiaj`, `ten_tydzien` i
	`poprzedni_tydzien` (tydzień od poniedziałku), `ten_miesiac`, `poprzedni_miesiac`,
	`ten_kwartal`, `poprzedni_kwartal`, `ten_rok`, `ostatnie_30_dni`, `ostatnie_90_dni`
	(ostatnie N dni to `dzis - (N-1)` do `dzis`), `wlasny` (wymaga `od` i `do`, `od <= do`).
	Nieznany preset albo zły zakres własny to `ValueError`."""
	if preset == "dzisiaj":
		return dzis, dzis
	if preset in ("ten_tydzien", "poprzedni_tydzien"):
		poniedzialek = dzis - datetime.timedelta(days=dzis.weekday())
		if preset == "poprzedni_tydzien":
			poniedzialek -= datetime.timedelta(days=7)
		return poniedzialek, poniedzialek + datetime.timedelta(days=6)
	if preset in ("ten_miesiac", "poprzedni_miesiac"):
		rok, miesiac = (
			(dzis.year, dzis.month) if preset == "ten_miesiac" else _miesiac_wstecz(dzis.year, dzis.month, 1)
		)
		return datetime.date(rok, miesiac, 1), _koniec_miesiaca(rok, miesiac)
	if preset in ("ten_kwartal", "poprzedni_kwartal"):
		pierwszy_miesiac = (dzis.month - 1) // 3 * 3 + 1
		rok, miesiac = dzis.year, pierwszy_miesiac
		if preset == "poprzedni_kwartal":
			rok, miesiac = _miesiac_wstecz(rok, miesiac, 3)
		return datetime.date(rok, miesiac, 1), _koniec_miesiaca(*_miesiac_wstecz(rok, miesiac, -2))
	if preset == "ten_rok":
		return datetime.date(dzis.year, 1, 1), datetime.date(dzis.year, 12, 31)
	if preset in ("ostatnie_30_dni", "ostatnie_90_dni"):
		dni = 30 if preset == "ostatnie_30_dni" else 90
		return dzis - datetime.timedelta(days=dni - 1), dzis
	if preset == "wlasny":
		if od is None or do is None:
			raise ValueError("Własny zakres wymaga daty początkowej i końcowej.")
		if od > do:
			raise ValueError("Data początkowa nie może być późniejsza niż końcowa.")
		return od, do
	raise ValueError(f"Nieznany preset okresu: {preset!r}.")


# --- ślad w Aktywności ----------------------------------------------------------------

_AKCJE_SLADU = {
	"wyplata": "oznaczył wypłatę dla",
	"cofniecie": "cofnął wypłatę dla",
	"wstrzymanie": "wstrzymał rozliczenie dla",
	"nie_dotyczy": "oznaczył jako niedotyczące rozliczenie dla",
	"do_wyplaty": "przywrócił do wypłaty rozliczenie dla",
	"zmiana_kwoty": "zmienił kwotę rozliczenia dla",
	"dodanie": "dodał odbiorcę rozliczenia:",
	"naliczenie": "naliczył rozliczenie dla",
}
_ROLA_DOPELNIACZ = {ROLA_HANDLOWIEC: "Handlowca", ROLA_MANAGER: "Managera", ROLA_PARTNER: "Partnera"}


def tekst_sladu(
	akcja: str,
	rola: str,
	odbiorca_nazwa: str | None,
	kwota: Any,
	data: Any,
	kto: str,
	partia_n: int = 0,
) -> str:
	"""Tekst śladu zaczynający się od `ZNACZNIK_ROZLICZENIE`, np. `[volteo:rozliczenie]
	Leszek Furmann oznaczył wypłatę dla Handlowca (Marek Nowak, 2 400,00 zł), data
	2026-10-06, z rejestru prowizji razem z 4 innymi pozycjami`. `partia_n` to liczba
	INNYCH pozycji w akcji masowej (0 = akcja pojedyncza, bez dopisku). `akcja` to jeden
	z: wyplata, cofniecie, wstrzymanie, nie_dotyczy, do_wyplaty, zmiana_kwoty, dodanie,
	naliczenie (inny to `ValueError`)."""
	if akcja not in _AKCJE_SLADU:
		raise ValueError(f"Nieznana akcja śladu rozliczenia: {akcja!r}.")
	rola_txt = rola if akcja == "dodanie" else _ROLA_DOPELNIACZ.get(rola, rola)
	szczegoly = [s for s in (odbiorca_nazwa, formatuj_kwote(kwota) if kwota not in (None, "") else "") if s]
	tekst = f"{ZNACZNIK_ROZLICZENIE} {kto} {_AKCJE_SLADU[akcja]} {rola_txt}"
	if szczegoly:
		tekst += f" ({', '.join(szczegoly)})"
	data_d = _data(data)
	if data_d:
		tekst += f", data {data_d.isoformat()}"
	if partia_n > 0:
		if partia_n == 1:
			tekst += ", z rejestru prowizji razem z 1 inną pozycją"
		else:
			tekst += f", z rejestru prowizji razem z {partia_n} innymi pozycjami"
	return tekst
