# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Edycja zestawu i ceny szansy przez administracje (ops#269, b72).

Modul celowo NIE importuje ``frappe``: cala logika (straznik rol, walidacja
wierszy, roznice, lancuch ceny, propozycja konfiguracji, tekst sladu) da sie
wtedy przetestowac lokalnie. Odczyt rol, `throw`, zapis i `zapisz_slad`
mieszkaja w adapterach (`CRMDeal.validate()`, `crm/api/zestaw.py`).

Zasady:
- kwoty w `Decimal`, ROUND_HALF_UP, do 2 miejsc; pola wejscia moga przyjsc jako
  string ("12", "12,5", ""), `kwota()` je normalizuje;
- struktury niemutowalne: funkcje zwracaja nowe obiekty, wejscia nie zmieniaja;
- lancuch ceny odtwarza `ops/crm-kalkulator-bom.py` (okolice linii 1635 do 1708),
  w tym wylaczenie klimatyzacji i ladowarki EV z podstawy ulgi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import Any

from crm.czyste_powietrze.obliczenia import CPBlad, _trify, oblicz_finansowanie
from crm.volteo_kalkulator_oze import RODZAJE_NOWE

# ---------------------------------------------------------------------------
# 1. Straznik rol
# ---------------------------------------------------------------------------

ROLE_EDYCJI_ZESTAWU: frozenset[str] = frozenset({"System Manager", "Volteo Core Admin"})
"""Role, ktore moga zmieniac zestaw i cene szansy (lustro `ADMIN_ROLE` z `crm.api.koszty`)."""


def czy_moze_edytowac_zestaw(role: Any) -> bool:
	"""True, gdy ktoras z `role` jest w `ROLE_EDYCJI_ZESTAWU`."""
	return bool(set(role or ()) & ROLE_EDYCJI_ZESTAWU)


# ---------------------------------------------------------------------------
# 2. Normalizacja liczb i pola chronione
# ---------------------------------------------------------------------------

_GROSZ = Decimal("0.01")
_ZERO = Decimal(0)


def kwota(x: Any) -> Decimal:
	"""Normalizuje wartosc do `Decimal`: przecinek na kropke, puste i `None` na 0.

	Zwraca wartosc NIEZAOKRAGLONA. Niepoprawny tekst daje `ValueError`.
	"""
	if x is None:
		return _ZERO
	if isinstance(x, bool):
		return Decimal(int(x))
	if isinstance(x, Decimal):
		return x
	if isinstance(x, int):
		return Decimal(x)
	if isinstance(x, float):
		return Decimal(str(x))
	tekst = "".join(str(x).split()).replace(",", ".")
	if tekst == "":
		return _ZERO
	try:
		return Decimal(tekst)
	except InvalidOperation as exc:
		raise ValueError(f"Niepoprawna liczba: {x!r}") from exc


def _grosze(d: Decimal) -> Decimal:
	return d.quantize(_GROSZ, rounding=ROUND_HALF_UP)


POLA_CENY: frozenset[str] = frozenset(
	{
		"custom_netto",
		"custom_vat_pct",
		"deal_value",
		"custom_dotacja",
		"custom_estimated_subsidy_pln",
		"custom_cena_po_dotacji",
		"custom_ulga_pct",
		"custom_ulga_kwota",
		"custom_cena_po_uldze",
		"custom_rata_brutto",
		"custom_rata_po_dotacji",
		"custom_rata_po_uldze",
		"custom_dodatki_netto",
	}
)
"""Pola ceny `CRM Deal`, ktorych zmiana wymaga roli z `ROLE_EDYCJI_ZESTAWU`."""

POLE_ZESTAWU = "custom_zestaw"
"""Pseudo-pole zwracane przez `zmienione_pola_chronione`, gdy zmienily sie wiersze."""


def _pole(wiersz: Any, klucz: str) -> Any:
	return wiersz.get(klucz) if hasattr(wiersz, "get") else getattr(wiersz, klucz, None)


def _tekst(x: Any) -> str:
	return "" if x is None else str(x).strip()


def _liczby_rowne(a: Any, b: Any) -> bool:
	try:
		return kwota(a) == kwota(b)
	except ValueError:
		return _tekst(a) == _tekst(b)


def _krotka_wiersza(wiersz: Any) -> tuple:
	"""Tresciowy odcisk wiersza: typ, nazwa, ilosc, jednostka, netto, brutto."""

	def liczba(klucz: str) -> Any:
		surowa = _pole(wiersz, klucz)
		try:
			return kwota(surowa)
		except ValueError:
			return _tekst(surowa)

	return (
		_tekst(_pole(wiersz, "typ")),
		_tekst(_pole(wiersz, "nazwa")),
		liczba("ilosc"),
		_tekst(_pole(wiersz, "jednostka")),
		liczba("netto"),
		liczba("brutto"),
	)


def zmienione_pola_chronione(stare: Any, nowe: Any, wiersze_stare: Any, wiersze_nowe: Any) -> frozenset[str]:
	"""Pola z `POLA_CENY` (i pseudo-pole `custom_zestaw`), ktore faktycznie sie zmienily.

	Liczby porownywane przez `Decimal`; `None`, `""`, `"0"` i `0` sa rowne, wiec zapis
	bez zmian nie uruchamia straznika. Wiersze porownywane trescia (nie po `name`),
	kolejnosc ma znaczenie.
	"""
	stare = stare or {}
	nowe = nowe or {}
	zmienione = {p for p in POLA_CENY if not _liczby_rowne(stare.get(p), nowe.get(p))}
	odciski_stare = [_krotka_wiersza(w) for w in (wiersze_stare or ())]
	odciski_nowe = [_krotka_wiersza(w) for w in (wiersze_nowe or ())]
	if odciski_stare != odciski_nowe:
		zmienione.add(POLE_ZESTAWU)
	return frozenset(zmienione)


# ---------------------------------------------------------------------------
# 3. Walidacja wierszy
# ---------------------------------------------------------------------------

TYPY_WIERSZY_OZE: tuple[str, ...] = (
	# PV / PV+ME / ME (ops/crm-kalkulator-bom.py, lista `lines`)
	"Falownik",
	"Panele PV",
	"Konstrukcja",
	"Magazyn energii",
	"Kabel",
	"Spoldzielnia",
	"Licznik",
	"PPOZ",
	"Klimatyzacja",
	"Panele PV (dodatek)",
	"Panele PV + mikro (dodatek)",
	"EMS Breeze",  # literal historyczny (szanse sprzed b73)
	"EMS Zeronest",
	"Licznik Pstryk",
	"Ladowarka EV",
	# ops#299: wiersze informacyjne (skladniki wliczone w cene, bez cen)
	"Montaż",
	"Akcesoria",
	"Sterownik",
	"Zasilanie awaryjne",
	# nowe rodzaje (crm/volteo_kalkulator_oze.py, `_linie_zestawu`)
	"Rozbudowa",
	"Pompa ciepła",
	"Kocioł",
	"CWU",
	"Grzejnik niskotemperaturowy",
)
"""Znane typy wierszy zestawu OZE. Typ spoza listy jest dozwolony (wolny tekst), UI
podpowiada te wartosci; typ steruje synchronizacja konfiguracji."""

TYPY_WIERSZY_CP: tuple[str, ...] = (
	"Źródło ciepła",
	"Centralne Ogrzewanie i Ciepła Woda Użytkowa",
	"Termomodernizacja",
)
"""Etykiety grup prac Czystego Powietrza (lustro `_KATEGORIA_TYP` w
`crm/api/czyste_powietrze.py`; `_typ_grupy_dla_linii` zamienia kategorie pozycji na te
etykiety). Typ spoza listy jest dozwolony (wolny tekst), UI podpowiada te wartosci."""

MSG_BRAK_WIERSZY = "Zestaw musi zawierać co najmniej jedną pozycję."
MSG_OZE_BEZ_CEN = "Pozycje OZE nie mają cen, cenę zmienia się w bloku Cena."
MSG_DWA_FALOWNIKI = "Zestaw może zawierać najwyżej jedną pozycję typu Falownik."


def waliduj_wiersze(wiersze: Any, linia: str = "oze") -> list[str]:
	"""Lista komunikatow bledow wierszy zestawu (pusta lista = OK)."""
	if not wiersze:
		return [MSG_BRAK_WIERSZY]
	bledy: list[str] = []
	falowniki = 0
	ceny_w_oze = False
	for nr, w in enumerate(wiersze, start=1):
		przedrostek = f"Pozycja {nr}: "
		typ = _pole(w, "typ")
		nazwa = _pole(w, "nazwa")
		if not _tekst(typ):
			bledy.append(przedrostek + "typ jest wymagany.")
		if not _tekst(nazwa):
			bledy.append(przedrostek + "nazwa jest wymagana.")
		try:
			ilosc = kwota(_pole(w, "ilosc"))
			if ilosc <= 0:
				bledy.append(przedrostek + "ilość musi być większa od zera.")
		except ValueError:
			bledy.append(przedrostek + "ilość nie jest liczbą.")
		wartosci_cen: dict[str, Decimal] = {}
		for klucz in ("netto", "brutto"):
			try:
				wartosc = kwota(_pole(w, klucz))
			except ValueError:
				bledy.append(przedrostek + f"{klucz} nie jest liczbą.")
				continue
			wartosci_cen[klucz] = wartosc
			if linia == "oze":
				if wartosc != 0:
					ceny_w_oze = True
			elif wartosc < 0:
				bledy.append(przedrostek + f"{klucz} nie może być ujemne.")
		if linia == "cp":
			if not _tekst(_pole(w, "jednostka")):
				bledy.append(przedrostek + "jednostka jest wymagana.")
			if len(wartosci_cen) == 2 and wartosci_cen["netto"] > wartosci_cen["brutto"]:
				bledy.append(przedrostek + "netto nie może być większe od brutto.")
		if _tekst(typ) == "Falownik":
			falowniki += 1
	if ceny_w_oze:
		bledy.append(MSG_OZE_BEZ_CEN)
	if linia == "oze" and falowniki > 1:
		bledy.append(MSG_DWA_FALOWNIKI)
	return bledy


# ---------------------------------------------------------------------------
# 4. Roznice zestawu
# ---------------------------------------------------------------------------

POLA_PORZADKOWE_WIERSZA: tuple[str, ...] = ("typ", "nazwa", "ilosc", "jednostka", "netto", "brutto")


@dataclass(frozen=True)
class Roznice:
	"""Wynik `roznice_zestawu`: wiersze dodane, usuniete i zmienione.

	`zmienione` to krotka `(wiersz_stary, wiersz_nowy, pola)`, gdzie `pola` to krotka
	nazw pol z rozna wartoscia.
	"""

	dodane: tuple = ()
	usuniete: tuple = ()
	zmienione: tuple = ()

	@property
	def puste(self) -> bool:
		return not (self.dodane or self.usuniete or self.zmienione)


def _slownik_wiersza(w: Any) -> dict[str, Any]:
	if isinstance(w, dict):
		return dict(w)
	if hasattr(w, "as_dict"):
		return dict(w.as_dict())
	return {k: _pole(w, k) for k in (*POLA_PORZADKOWE_WIERSZA, "name", "reczna_ilosc")}


def roznice_zestawu(stare: Any, nowe: Any) -> Roznice:
	"""Dopasowanie wierszy po `name`; wiersz bez `name` (lub z nieznanym) jest nowy."""
	stare_w = [_slownik_wiersza(w) for w in (stare or ())]
	nowe_w = [_slownik_wiersza(w) for w in (nowe or ())]
	stare_po_nazwie = {w["name"]: w for w in stare_w if w.get("name")}
	uzyte: set[str] = set()
	dodane: list[dict[str, Any]] = []
	zmienione: list[tuple] = []
	for w in nowe_w:
		nazwa = w.get("name")
		if not nazwa or nazwa not in stare_po_nazwie or nazwa in uzyte:
			dodane.append(w)
			continue
		uzyte.add(nazwa)
		poprzedni = stare_po_nazwie[nazwa]
		o_s, o_n = _krotka_wiersza(poprzedni), _krotka_wiersza(w)
		pola = tuple(p for p, a, b in zip(POLA_PORZADKOWE_WIERSZA, o_s, o_n, strict=True) if a != b)
		if pola:
			zmienione.append((poprzedni, w, pola))
	usuniete = [w for w in stare_w if w.get("name") and w["name"] not in uzyte]
	return Roznice(tuple(dodane), tuple(usuniete), tuple(zmienione))


# ---------------------------------------------------------------------------
# 5. Lancuch ceny
# ---------------------------------------------------------------------------


def _typ_indywidualny(typ_klienta: Any) -> bool:
	return _tekst(typ_klienta).lower() == "indywidualny"


def waliduj_cene(wejscie: dict) -> list[str]:
	"""Lista komunikatow bledow wejscia ceny (pusta = OK)."""
	bledy: list[str] = []

	def liczba(klucz: str, etykieta: str) -> Decimal | None:
		try:
			return kwota(wejscie.get(klucz))
		except ValueError:
			bledy.append(f"{etykieta} nie jest liczbą.")
			return None

	netto = liczba("netto", "Netto")
	vat = liczba("vat_pct", "Stawka VAT")
	dotacja = liczba("dotacja", "Dotacja")
	ulga_pct = liczba("ulga_pct", "Ulga")
	okres = liczba("okres_lat", "Okres rat")
	wplata = liczba("wplata_wlasna", "Wpłata własna")
	dodatki = liczba("dodatki_bez_ulgi_brutto", "Dodatki wyłączone z ulgi")
	if netto is not None and netto <= 0:
		bledy.append("Netto musi być większe od zera.")
	if vat is not None and not (0 <= vat <= 100):
		bledy.append("Stawka VAT musi być w zakresie 0 do 100.")
	if ulga_pct is not None and not (0 <= ulga_pct <= 100):
		bledy.append("Ulga musi być w zakresie 0 do 100 procent.")
	if okres is not None and (okres < 0 or okres != okres.to_integral_value()):
		bledy.append("Okres rat musi być całkowitą liczbą lat, nie mniejszą od zera.")
	if wplata is not None and wplata < 0:
		bledy.append("Wpłata własna nie może być ujemna.")
	if dodatki is not None and dodatki < 0:
		bledy.append("Dodatki wyłączone z ulgi nie mogą być ujemne.")
	if dotacja is not None and dotacja < 0:
		bledy.append("Dotacja nie może być ujemna.")
	if netto is not None and netto > 0 and vat is not None and 0 <= vat <= 100 and dotacja is not None:
		brutto = _grosze(netto) + _grosze(_grosze(netto) * vat / 100)
		if dotacja > brutto:
			bledy.append("Dotacja nie może być większa od brutto.")
		elif (
			_typ_indywidualny(wejscie.get("typ_klienta"))
			and dodatki is not None
			and ulga_pct is not None
			and ulga_pct > 0
			and dodatki > brutto - dotacja
		):
			bledy.append("Dodatki wyłączone z ulgi nie mogą przekraczać ceny po dotacji.")
	if not _typ_indywidualny(wejscie.get("typ_klienta")):
		if dotacja is not None and dotacja != 0:
			bledy.append("Dla klienta firmowego dotacja musi wynosić 0.")
		if ulga_pct is not None and ulga_pct != 0:
			bledy.append("Dla klienta firmowego ulga musi wynosić 0.")
	return bledy


def _rata(kwota_raty: Decimal, wplata: Decimal, i: Decimal, factor: Decimal, months: int) -> Decimal:
	principal = kwota_raty - wplata
	if principal <= 0:
		return _ZERO
	if i <= 0 or factor <= 1:
		return principal / months if months > 0 else _ZERO
	return principal * i * factor / (factor - 1)


def przelicz_cene(wejscie: dict, stale: dict) -> dict:
	"""Lancuch pochodnych ceny w `Decimal` (2 miejsca), wzor z `ops/crm-kalkulator-bom.py`.

	Wejscie: `netto`, `vat_pct`, `dotacja`, `ulga_pct`, `okres_lat`, `wplata_wlasna`,
	`typ_klienta`, `dodatki_bez_ulgi_brutto`. Stale: `pmt_oprocentowanie_mies`
	(procent miesieczny, argument, nigdy czytany w rdzeniu). Niepoprawne wejscie
	daje `ValueError` z polaczonymi komunikatami z `waliduj_cene`.
	"""
	bledy = waliduj_cene(wejscie)
	if bledy:
		raise ValueError(" ".join(bledy))
	netto = _grosze(kwota(wejscie.get("netto")))
	vat_pct = kwota(wejscie.get("vat_pct"))
	vat = _grosze(netto * vat_pct / 100)
	brutto = netto + vat
	indywidualny = _typ_indywidualny(wejscie.get("typ_klienta"))
	okres_lat = int(kwota(wejscie.get("okres_lat")))
	wplata = _grosze(kwota(wejscie.get("wplata_wlasna")))
	months = okres_lat * 12

	if indywidualny:
		dotacja = _grosze(kwota(wejscie.get("dotacja")))
		ulga_pct = kwota(wejscie.get("ulga_pct"))
		dodatki = _grosze(kwota(wejscie.get("dodatki_bez_ulgi_brutto")))
		cena_po_dotacji = brutto - dotacja
		ulga_kwota = _grosze((cena_po_dotacji - dodatki) * ulga_pct / 100)
		cena_po_uldze = cena_po_dotacji - ulga_kwota
		i = kwota((stale or {}).get("pmt_oprocentowanie_mies")) / 100
		with localcontext() as ctx:
			ctx.prec = 60
			factor = (1 + i) ** months if months > 0 else Decimal(1)
			rata_brutto = _grosze(_rata(brutto, wplata, i, factor, months))
			rata_po_dotacji = _grosze(_rata(cena_po_dotacji, wplata, i, factor, months))
			rata_po_uldze = _grosze(_rata(cena_po_uldze, wplata, i, factor, months))
	else:
		dotacja = ulga_kwota = rata_brutto = rata_po_dotacji = rata_po_uldze = _ZERO
		ulga_pct = _ZERO
		cena_po_dotacji = cena_po_uldze = brutto

	return {
		"netto": netto,
		"vat_pct": vat_pct,
		"brutto": brutto,
		"dotacja": _grosze(dotacja),
		"cena_po_dotacji": _grosze(cena_po_dotacji),
		"ulga_pct": _grosze(ulga_pct),
		"ulga_kwota": _grosze(ulga_kwota),
		"cena_po_uldze": _grosze(cena_po_uldze),
		"rata_brutto": rata_brutto,
		"rata_po_dotacji": rata_po_dotacji,
		"rata_po_uldze": rata_po_uldze,
	}


def odtworz_dodatki_bez_ulgi(cena_po_dotacji: Any, ulga_kwota: Any, ulga_pct: Any) -> Decimal:
	"""Kwota wylaczona z podstawy ulgi (brutto klimatyzacji i ladowarki EV), odzyskana
	z zapisanej szansy: `cena_po_dotacji - ulga_kwota / (ulga_pct / 100)`; 0, gdy
	`ulga_pct` nie jest dodatni albo wynik jest ujemny. Wartosc domyslna pola w UI."""
	pct = kwota(ulga_pct)
	if pct <= 0:
		return _ZERO
	wynik = kwota(cena_po_dotacji) - kwota(ulga_kwota) / (pct / 100)
	if wynik < 0:
		return _ZERO
	return _grosze(wynik)


# ---------------------------------------------------------------------------
# 5b. Cena Czystego Powietrza (ops#274)
# ---------------------------------------------------------------------------

KLUCZE_DOTACJI_CP: tuple[str, ...] = ("zrodlo", "co", "termo")
"""Grupy dotacji CP: pola szansy `custom_cp_dotacja_<grupa>`."""

MSG_CP_BRAK_STALYCH_KREDYTU = "Brak stałych finansowania Czystego Powietrza (oprocentowanie raty)."


def waliduj_cene_cp(wiersze: Any, dotacje: dict | None, finansowanie: dict | None) -> list[str]:
	"""Lista komunikatow bledow ceny CP (pusta = OK).

	`wiersze` musza byc juz poprawne (`waliduj_wiersze(..., "cp")`); tu liczy sie tylko
	suma brutto. Dotacje: kazda `>= 0`, ich suma `<= deal_value`. `okres_lat` calkowity
	w zakresie 0 do 10 (0 = bez kredytu), `wplata_gotowka >= 0`.
	"""
	bledy: list[str] = []
	dotacje = dotacje or {}
	suma_dotacji = _ZERO
	for grupa in KLUCZE_DOTACJI_CP:
		try:
			d = kwota(dotacje.get(grupa))
		except ValueError:
			bledy.append(f"Dotacja ({grupa}) nie jest liczbą.")
			continue
		if d < 0:
			bledy.append(f"Dotacja ({grupa}) nie może być ujemna.")
		else:
			suma_dotacji += d
	try:
		deal_value = sum((_grosze(kwota(_pole(w, "brutto"))) for w in (wiersze or ())), _ZERO)
	except ValueError:
		deal_value = None
	if deal_value is not None and suma_dotacji > deal_value:
		bledy.append("Dotacja łączna nie może być większa od sumy brutto pozycji.")
	try:
		okres = kwota((finansowanie or {}).get("okres_lat"))
	except ValueError:
		okres = None
		bledy.append("Okres rat nie jest liczbą.")
	if okres is not None and (okres < 0 or okres > 10 or okres != okres.to_integral_value()):
		bledy.append("Okres rat musi być całkowitą liczbą lat z zakresu 0 do 10.")
	try:
		if kwota((finansowanie or {}).get("wplata_gotowka")) < 0:
			bledy.append("Wpłata gotówką nie może być ujemna.")
	except ValueError:
		bledy.append("Wpłata gotówką nie jest liczbą.")
	return bledy


def przelicz_cene_cp(
	wiersze: Any, dotacje: dict | None, finansowanie: dict | None, stale: dict | None
) -> dict:
	"""Cena CP z wierszy i dotacji wpisanych przez admina (bez silnika katalogowego).

	`stale`: `{"oprocentowanie_mies", "trify_udzial", "trify_stawka_za_1000"}`; wartosci
	moga byc `None` (Single nie zasiany). Wtedy `podstawa_trify`/`rata_trify` = `None`
	(nigdy 0), a przy `okres_lat > 0` rzucany jest `ValueError`. Finansowanie i Trify
	licza istniejace funkcje `oblicz_finansowanie` / `_trify` z `obliczenia.py`.
	Wynik w `Decimal`: `deal_value`, `netto_suma`, `dotacje` (3 grupy), `dotacja_laczna`,
	`wklad_wlasny`, `okres_lat`, `wplata_gotowka`, `kwota_kredytu`, `rata_wkladu`
	(`None` przy `okres_lat` 0), `podstawa_trify`, `rata_trify`.
	"""
	bledy = waliduj_cene_cp(wiersze, dotacje, finansowanie)
	if bledy:
		raise ValueError(" ".join(bledy))
	lista = list(wiersze or ())
	deal_value = sum((_grosze(kwota(_pole(w, "brutto"))) for w in lista), _ZERO)
	netto_suma = sum((_grosze(kwota(_pole(w, "netto"))) for w in lista), _ZERO)
	dotacje_grup = {g: _grosze(kwota((dotacje or {}).get(g))) for g in KLUCZE_DOTACJI_CP}
	dotacja_laczna = sum(dotacje_grup.values(), _ZERO)
	wklad = max(_ZERO, deal_value - dotacja_laczna)
	okres = int(kwota((finansowanie or {}).get("okres_lat")))
	wplata = _grosze(kwota((finansowanie or {}).get("wplata_gotowka")))
	stale = stale or {}

	stale_trify = None
	if stale.get("trify_udzial") is not None and stale.get("trify_stawka_za_1000") is not None:
		stale_trify = {
			"trify_udzial": stale["trify_udzial"],
			"trify_stawka_za_1000": stale["trify_stawka_za_1000"],
		}
	try:
		trify = _trify(dotacja_laczna, stale_trify)
	except CPBlad as exc:
		raise ValueError(str(exc)) from exc

	kwota_kredytu = rata_wkladu = None
	if okres > 0:
		if stale.get("oprocentowanie_mies") is None or stale_trify is None:
			raise ValueError(MSG_CP_BRAK_STALYCH_KREDYTU)
		try:
			fin = oblicz_finansowanie(
				wklad,
				dotacja_laczna,
				{"okres_lat": okres, "wplata_gotowka": wplata},
				{**stale_trify, "oprocentowanie_mies": stale["oprocentowanie_mies"]},
			)
		except CPBlad as exc:
			raise ValueError(str(exc)) from exc
		kwota_kredytu, rata_wkladu = fin["kwota_kredytu"], fin["rata_wkladu"]

	return {
		"deal_value": deal_value,
		"netto_suma": netto_suma,
		"dotacje": dotacje_grup,
		"dotacja_laczna": dotacja_laczna,
		"wklad_wlasny": wklad,
		"okres_lat": okres,
		"wplata_gotowka": wplata,
		"kwota_kredytu": kwota_kredytu,
		"rata_wkladu": rata_wkladu,
		"podstawa_trify": trify[0] if trify else None,
		"rata_trify": trify[1] if trify else None,
	}


# ---------------------------------------------------------------------------
# 6. Propozycja konfiguracji PV
# ---------------------------------------------------------------------------

_RX_ILOSC_W_NAZWIE = re.compile(r"\b[xX]\s*(\d+)")


def _jako_licznik(d: Decimal) -> int | Decimal:
	return int(d) if d == d.to_integral_value() else d


def _wiersze_typu(wiersze: list[Any], typ: str) -> list[Any]:
	return [w for w in wiersze if _tekst(_pole(w, "typ")) == typ]


def _ilosc_z_nazwy_lub_pola(wiersz: Any) -> int:
	"""Dodatki paneli niosa liczbe sztuk w nazwie ("Panele PV x 3 (dodatek)"), `ilosc` = 1."""
	trafienie = _RX_ILOSC_W_NAZWIE.search(_tekst(_pole(wiersz, "nazwa")))
	if trafienie:
		return int(trafienie.group(1))
	try:
		return int(kwota(_pole(wiersz, "ilosc")))
	except ValueError:
		return 0


def zaproponuj_konfiguracje(
	wiersze: Any, komponenty: Any, obecna: dict | None = None, rodzaj: str | None = None
) -> dict:
	"""Deterministyczna propozycja pol konfiguracji PV z wierszy zestawu.

	`komponenty`: lista slownikow `nazwa`, `model`, `kategoria`, `pojemnosc_kwh`;
	dopasowanie baterii po `f"{nazwa} {model}"`. Brak dopasowania daje pojemnosc z
	`obecna` i ostrzezenie w kluczu `_ostrzezenia`. Nie sa wyliczane:
	`custom_pv_power_kwp`, `custom_producent`, `custom_spoldzielnia`. Dla nowych
	rodzajow OZE (`rodzaj` w `RODZAJE_NOWE`) zwraca pusty slownik.
	"""
	if rodzaj in RODZAJE_NOWE:
		return {}
	obecna = obecna or {}
	lista = list(wiersze or ())
	ostrzezenia: list[str] = []

	falowniki = _wiersze_typu(lista, "Falownik")
	baterie = _wiersze_typu(lista, "Magazyn energii")
	panele = _wiersze_typu(lista, "Panele PV")
	konstrukcje = _wiersze_typu(lista, "Konstrukcja")
	kable = _wiersze_typu(lista, "Kabel")

	pojemnosc = _ZERO
	bez_dopasowania = False
	pelne_nazwy = {}
	for k in komponenty or ():
		if k.get("kategoria") == "Magazyn energii":
			pelne_nazwy.setdefault(f"{k.get('nazwa') or ''} {k.get('model') or ''}".strip(), k)
	for b in baterie:
		komp = pelne_nazwy.get(_tekst(_pole(b, "nazwa")))
		if komp is None:
			bez_dopasowania = True
			ostrzezenia.append(
				f'Nie znaleziono magazynu "{_tekst(_pole(b, "nazwa"))}" w katalogu komponentów, '
				"pojemność zostaje bez zmian."
			)
			continue
		pojemnosc += kwota(komp.get("pojemnosc_kwh")) * kwota(_pole(b, "ilosc"))
	if bez_dopasowania:
		pojemnosc = kwota(obecna.get("custom_pojemnosc_kwh"))

	kabel_m = sum((kwota(_pole(k, "ilosc")) for k in kable), _ZERO)

	def nazwa_wiersza(typ: str) -> str:
		znalezione = _wiersze_typu(lista, typ)
		return _tekst(_pole(znalezione[0], "nazwa")) if znalezione else ""

	def tak_nie(typ: str) -> str:
		return "Tak" if _wiersze_typu(lista, typ) else "Nie"

	def sztuki(typ: str) -> int:
		return sum(_ilosc_z_nazwy_lub_pola(w) for w in _wiersze_typu(lista, typ))

	wynik: dict[str, Any] = {
		"custom_falownik": _tekst(_pole(falowniki[0], "nazwa")) if falowniki else "",
		"custom_bateria": " + ".join(_tekst(_pole(b, "nazwa")) for b in baterie),
		"custom_pojemnosc_kwh": pojemnosc,
		"custom_panel": _tekst(_pole(panele[0], "nazwa")) if panele else "",
		"custom_panele": _jako_licznik(kwota(_pole(panele[0], "ilosc"))) if panele else 0,
		"custom_konstrukcja": _tekst(_pole(konstrukcje[0], "nazwa")) if konstrukcje else "",
		"custom_kabel_m": _jako_licznik(kabel_m),
		"custom_licznik_dodatkowy": tak_nie("Licznik"),
		"custom_dod_klima": nazwa_wiersza("Klimatyzacja"),
		"custom_dod_panele": sztuki("Panele PV (dodatek)"),
		"custom_dod_panele_mikro": sztuki("Panele PV + mikro (dodatek)"),
		"custom_ems_breeze": "Tak" if (_wiersze_typu(lista, "EMS Zeronest") or _wiersze_typu(lista, "EMS Breeze")) else "Nie",
		"custom_pstryk": tak_nie("Licznik Pstryk"),
		"custom_ev_ladowarka": nazwa_wiersza("Ladowarka EV"),
		"_ostrzezenia": ostrzezenia,
	}
	return wynik


# ---------------------------------------------------------------------------
# 7. Tekst sladu
# ---------------------------------------------------------------------------

ZNACZNIK_ZESTAW = "[volteo:zestaw]"
"""Znacznik wiodacy sladu edycji zestawu (linia widoczna tylko dla administracji)."""

_ETYKIETY_POL_WIERSZA = {
	"typ": "typ",
	"nazwa": "nazwa",
	"ilosc": "ilość",
	"jednostka": "jednostka",
	"netto": "netto",
	"brutto": "brutto",
}

_ETYKIETY_CENY = (
	("netto", "netto"),
	("brutto", "brutto"),
	("dotacja", "dotacja"),
	("cena_po_uldze", "po uldze"),
)


def formatuj_kwote(x: Any) -> str:
	"""`48200` -> `48 200,00` (spacja jako separator tysiecy, przecinek dziesietny)."""
	d = _grosze(kwota(x))
	calosc, ulamek = f"{abs(d):.2f}".split(".")
	grupy = []
	while calosc:
		grupy.append(calosc[-3:])
		calosc = calosc[:-3]
	znak = "-" if d < 0 else ""
	return f"{znak}{' '.join(reversed(grupy))},{ulamek}"


def _formatuj_ilosc(x: Any) -> str:
	try:
		d = kwota(x)
	except ValueError:
		return _tekst(x)
	tekst = f"{d:f}"
	if "." in tekst:
		tekst = tekst.rstrip("0").rstrip(".")
	return tekst.replace(".", ",") or "0"


def _opis_wiersza(w: dict[str, Any]) -> str:
	typ = _tekst(w.get("typ"))
	nazwa = _tekst(w.get("nazwa"))
	opis = typ
	if nazwa:
		opis += f' "{nazwa}"'
	opis += f" x {_formatuj_ilosc(w.get('ilosc'))}"
	jednostka = _tekst(w.get("jednostka"))
	if jednostka:
		opis += f" {jednostka}"
	return opis


def _opis_wiersza_z_kwotami(w: dict[str, Any]) -> str:
	return f"{_opis_wiersza(w)} (netto {formatuj_kwote(w.get('netto'))}, brutto {formatuj_kwote(w.get('brutto'))})"


def _opis_zmiany(stary: dict[str, Any], nowy: dict[str, Any], pola: tuple[str, ...]) -> str:
	etykieta = _tekst(stary.get("typ")) or "Pozycja"
	nazwa = _tekst(stary.get("nazwa"))
	if nazwa and "nazwa" not in pola:
		etykieta += f' "{nazwa}"'
	elementy = []
	for p in pola:
		nazwa_pola = _ETYKIETY_POL_WIERSZA.get(p, p)
		if p in ("netto", "brutto"):
			a, b = formatuj_kwote(stary.get(p)), formatuj_kwote(nowy.get(p))
		elif p == "ilosc":
			a, b = _formatuj_ilosc(stary.get(p)), _formatuj_ilosc(nowy.get(p))
		else:
			a, b = f'"{_tekst(stary.get(p))}"', f'"{_tekst(nowy.get(p))}"'
		elementy.append(f"{nazwa_pola} {a} -> {b}")
	return f"{etykieta}: {', '.join(elementy)}"


def _kropka(tekst: str) -> str:
	return tekst if tekst.endswith(".") else tekst + "."


def tekst_sladu_zestawu(
	roznice: Roznice,
	cena_przed: dict | None,
	cena_po: dict | None,
	konfiguracja_zmiany: Any,
	powod: str | None,
	status_umowy: str | None,
	etykiety: dict | None = None,
	snapshot: str | None = None,
	cp: dict | None = None,
) -> str:
	"""Jedna linia sladu `[volteo:zestaw]`; czlony puste sa pomijane.

	`cena_przed`/`cena_po`: slowniki z kluczami `netto`, `brutto`, `dotacja`,
	`cena_po_uldze` (kwoty). `konfiguracja_zmiany`: lista nazw zmienionych pol
	konfiguracji, `etykiety`: fieldname -> polska etykieta (z `frappe.get_meta`).
	`cp` (Czyste Powietrze): slownik `przed`/`po` z kluczami `deal_value`,
	`dotacja_laczna`, `wklad_wlasny`; wlacza kwoty wierszy oraz czlony "prowizje CP bez
	zmian" i "wejscie kalkulatora nie odpowiada juz zestawowi".
	"""
	etykiety = etykiety or {}
	powod = _tekst(powod)
	naglowek = f"Edycja zestawu (powód: {powod})." if powod else "Edycja zestawu."
	czlony = [naglowek]
	opis = _opis_wiersza_z_kwotami if cp else _opis_wiersza
	if roznice.dodane:
		czlony.append("Dodano: " + "; ".join(opis(w) for w in roznice.dodane) + ".")
	if roznice.usuniete:
		czlony.append("Usunięto: " + "; ".join(opis(w) for w in roznice.usuniete) + ".")
	if roznice.zmienione:
		czlony.append("Zmieniono: " + "; ".join(_opis_zmiany(s, n, p) for s, n, p in roznice.zmienione) + ".")
	if cena_przed and cena_po:
		elementy = []
		zmiana = False
		for klucz, etykieta in _ETYKIETY_CENY:
			if klucz in cena_przed and klucz in cena_po:
				a, b = _grosze(kwota(cena_przed[klucz])), _grosze(kwota(cena_po[klucz]))
				zmiana = zmiana or a != b
				elementy.append(f"{etykieta} {formatuj_kwote(a)} -> {formatuj_kwote(b)}")
		if elementy and zmiana:
			czlony.append("Cena: " + ", ".join(elementy) + " zł.")
	if cp:
		przed, po = cp.get("przed") or {}, cp.get("po") or {}
		elementy = []
		for klucz, etykieta in (
			("deal_value", "wartość szansy"),
			("dotacja_laczna", "dotacja łączna"),
			("wklad_wlasny", "wkład własny"),
		):
			if klucz in przed and klucz in po:
				a, b = _grosze(kwota(przed[klucz])), _grosze(kwota(po[klucz]))
				elementy.append(f"{etykieta} {formatuj_kwote(a)} -> {formatuj_kwote(b)}")
		if elementy:
			czlony.append("Cena CP: " + ", ".join(elementy) + " zł.")
		czlony.append("Prowizje CP bez zmian.")
		czlony.append("Wejście kalkulatora (custom_cp_wejscie_json) nie odpowiada już zestawowi.")
	pola_konf = [etykiety.get(p, p) for p in (konfiguracja_zmiany or ())]
	if pola_konf:
		czlony.append("Konfiguracja: " + ", ".join(pola_konf) + ".")
	if _tekst(status_umowy):
		czlony.append("Umowa: " + _kropka(_tekst(status_umowy)))
	if _tekst(snapshot):
		czlony.append("Snapshot kosztów: " + _kropka(_tekst(snapshot)))
	return f"{ZNACZNIK_ZESTAW} " + " ".join(czlony)


# ---------------------------------------------------------------------------
# 8. Producent i zestaw (ops#300, b74)
# ---------------------------------------------------------------------------

ZESTAW_PRODUCENT: dict[str, str] = {
	"COMFORT": "Hoymiles",
	"COMFORT PREMIUM": "Solax",
	"PREMIUM +": "Sigenergy",
}
"""Jedyna mapa zestaw -> producent w forku (kolejnosc = kolejnosc zestawow w UI). Lustro
`ZESTAWY` w `frontend/src/utils/pvForm.js` i `ZESTAWY_PRODUCENT` w
`ops/crm-kalkulator-bom.py` (Server Script nie importuje). Producent spoza mapy
(FoxESS, Deye) albo sama fotowoltaika to zestaw pusty."""

ZESTAWY_OZE: tuple[str, ...] = tuple(ZESTAW_PRODUCENT)
"""Dozwolone wartosci `zestaw_typ` (karta panelu, `CRM Deal.custom_zestaw_typ`)."""

RODZAJ_PV = "Fotowoltaika"
RODZAJE_Z_MAGAZYNEM: frozenset[str] = frozenset({"Fotowoltaika + Magazyn", "Magazyn energii"})
"""Rodzaje umowy, w ktorych zestaw (COMFORT / COMFORT PREMIUM / PREMIUM +) ma sens."""

PRODUCENT_PV = "FoxESS"
PRODUCENCI_WYBIERALNI: tuple[str, ...] = ("FoxESS", "Sigenergy", "Hoymiles", "Solax")
"""Producenci do wyboru w edycji zestawu. Deye (historyczny) nigdy nie jest wybieralny,
moze byc tylko wartoscia biezaca szansy."""


def producenci_dla_rodzaju(rodzaj: Any) -> tuple[str, ...]:
	"""Producenci, ktorych mozna wybrac dla rodzaju umowy: sama PV tylko FoxESS."""
	return (PRODUCENT_PV,) if _tekst(rodzaj) == RODZAJ_PV else PRODUCENCI_WYBIERALNI


def zestaw_dla_producenta(producent: Any, rodzaj: Any) -> str:
	"""Zestaw wyprowadzony z producenta. Pusty, gdy rodzaj nie ma magazynu albo producent
	nie ma zestawu (FoxESS, Deye, brak)."""
	if _tekst(rodzaj) not in RODZAJE_Z_MAGAZYNEM:
		return ""
	wybrany = _tekst(producent)
	for zestaw, prod in ZESTAW_PRODUCENT.items():
		if prod == wybrany:
			return zestaw
	return ""


def nowy_zestaw_typ(producent_obecny: Any, producent_nowy: Any, zestaw_obecny: Any, rodzaj: Any) -> str:
	"""Zestaw do zapisania przy edycji. Wyprowadzany z producenta WYLACZNIE gdy producent
	rzeczywiscie sie zmienia; bez zmiany producenta zwraca zestaw zapisany na szansie bez
	zadnej poprawki (stare szanse zachowuja to, co mialy)."""
	if _tekst(producent_nowy) == _tekst(producent_obecny):
		return _tekst(zestaw_obecny)
	return zestaw_dla_producenta(producent_nowy, rodzaj)


MSG_PRODUCENT_PUSTY = "Wybierz producenta."
_TYPY_PRODUCENTA = ("Falownik", "Magazyn energii")
_KATEGORIA_TYPU = {"Falownik": "Falownik", "Magazyn energii": "Magazyn energii"}


@dataclass(frozen=True)
class WalidacjaProducenta:
	"""Wynik `waliduj_producenta`: bledy blokujace i ostrzezenia (informacyjne)."""

	bledy: tuple[str, ...] = ()
	ostrzezenia: tuple[str, ...] = ()


def _odcisk_urzadzen(wiersze: Any) -> list[tuple[str, str]]:
	return sorted(
		(_tekst(_pole(w, "typ")), _tekst(_pole(w, "nazwa")))
		for w in (wiersze or ())
		if _tekst(_pole(w, "typ")) in _TYPY_PRODUCENTA
	)


def _komponent_po_nazwie(komponenty: Any, kategoria: str, nazwa: str) -> Any:
	"""Wiersz katalogu pasujacy po `f"{nazwa} {model}"` (jak `_znajdz_komponent` w umowie)."""
	for k in komponenty or ():
		if k.get("kategoria") != kategoria:
			continue
		if f"{k.get('nazwa') or ''} {k.get('model') or ''}".strip() == nazwa:
			return k
	return None


def waliduj_producenta(
	producent: Any,
	rodzaj: Any,
	wiersze_nowe: Any,
	wiersze_stare: Any,
	komponenty: Any,
	producent_obecny: Any = "",
) -> WalidacjaProducenta:
	"""Spojnosc producenta z wierszami Falownik i Magazyn energii oraz ostrzezenia dodatkow.

	Lustro regul kalkulatora (`ops/crm-kalkulator-bom.py`: falownik i bateria musza miec
	producenta szansy, Pstryk i ladowarka EV tylko Sigenergy, EMS Zeronest tylko
	Hoymiles/Solax/Deye, Solax z magazynem wymaga EMS, licznik nigdy FoxESS).

	Bledem (blokujacym) jest niezgodnosc TYLKO wtedy, gdy zapis zmienia producenta albo
	wiersze Falownik / Magazyn energii; na starej, juz niespojnej szansie, przy zmianie
	samej ceny, ta sama niezgodnosc jest ostrzezeniem. Wiersze niedopasowane do katalogu
	`Volteo Komponent` zawsze daja ostrzezenie. Wejscia nie sa mutowane.
	"""
	wybrany = _tekst(producent)
	obecny = _tekst(producent_obecny)
	zmiana_producenta = wybrany != obecny
	zmiana_urzadzen = _odcisk_urzadzen(wiersze_nowe) != _odcisk_urzadzen(wiersze_stare)
	blokuje = zmiana_producenta or zmiana_urzadzen
	bledy: list[str] = []
	ostrzezenia: list[str] = []

	if zmiana_producenta:
		if not wybrany:
			bledy.append(MSG_PRODUCENT_PUSTY)
		elif wybrany not in producenci_dla_rodzaju(rodzaj):
			if _tekst(rodzaj) == RODZAJ_PV:
				bledy.append(f"Dla rodzaju {RODZAJ_PV} dostępny jest tylko producent {PRODUCENT_PV}.")
			else:
				bledy.append(f'Producent "{wybrany}" nie jest dostępny do wyboru.')

	if wybrany:
		lista = bledy if blokuje else ostrzezenia
		for w in wiersze_nowe or ():
			typ = _tekst(_pole(w, "typ"))
			if typ not in _TYPY_PRODUCENTA:
				continue
			nazwa = _tekst(_pole(w, "nazwa"))
			komp = _komponent_po_nazwie(komponenty, _KATEGORIA_TYPU[typ], nazwa)
			prod_komp = _tekst(komp.get("producent")) if komp else ""
			if not prod_komp:
				ostrzezenia.append(
					f'Pozycja {typ} "{nazwa}" nie została znaleziona w katalogu komponentów '
					"z producentem, zgodność z producentem nie została sprawdzona."
				)
			elif prod_komp != wybrany:
				lista.append(
					f'Pozycja {typ} "{nazwa}" jest producenta {prod_komp}, a wybrany producent to {wybrany}. '
					"Zmień producenta albo pozycję."
				)

	typy_nowe = {_tekst(_pole(w, "typ")) for w in (wiersze_nowe or ())}
	ma_ems = bool(typy_nowe & {"EMS Zeronest", "EMS Breeze"})
	if wybrany and wybrany != "Sigenergy":
		if "Licznik Pstryk" in typy_nowe:
			ostrzezenia.append("Licznik Pstryk jest dostępny tylko z producentem Sigenergy.")
		if "Ladowarka EV" in typy_nowe:
			ostrzezenia.append("Ładowarka EV jest dostępna tylko z producentem Sigenergy.")
	if wybrany in ("Sigenergy", PRODUCENT_PV) and ma_ems:
		ostrzezenia.append(f"EMS Zeronest nie jest dostępny z producentem {wybrany}.")
	if wybrany == "Solax" and _tekst(rodzaj) in RODZAJE_Z_MAGAZYNEM and not ma_ems:
		ostrzezenia.append("Producent Solax z magazynem wymaga pozycji EMS Zeronest.")
	if wybrany == PRODUCENT_PV and "Licznik" in typy_nowe:
		ostrzezenia.append("Dodatkowy licznik nie jest dostępny z producentem FoxESS.")

	return WalidacjaProducenta(tuple(bledy), tuple(dict.fromkeys(ostrzezenia)))
