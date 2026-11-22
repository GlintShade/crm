# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kategorie handlowców i kategoria leada (ops#393): logika czysta.

Administracja nadaje handlowcowi kategorię, teren (środek i promień w km) i okręg
kampanii FB. Kategoria leada nie jest zapisywana: liczy się przy odczycie z terenów.
Moduł celowo nie importuje ``frappe`` (precedens `crm/volteo_reguly_przydzialu.py`).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from crm.volteo_dyzury import _ODWZOROWANIE_POLSKICH_ZNAKOW, OKREGI_KAMPANII, okreg_z_kampanii
from crm.volteo_reguly_przydzialu import (
	DLUGOSC_MAX,
	DLUGOSC_MIN,
	PROMIEN_MAX_KM,
	PROMIEN_MIN_KM,
	SZEROKOSC_MAX,
	SZEROKOSC_MIN,
	_liczba,
	_tekst,
	ma_wspolrzedne,
	odleglosc_km,
)

KATEGORIE: tuple[str, ...] = ("Priorytet", "Standard", "Nie umawiać")
"""Kolejność = ranga (pierwsza wygrywa)."""

NIE_UMAWIAC: str = "Nie umawiać"

ROLE_KATEGORII: frozenset[str] = frozenset(
	{"System Manager", "Volteo Core Admin", "Volteo Backend", "Volteo Call Center"}
)
ROLE_ZAPISU: frozenset[str] = frozenset({"System Manager", "Volteo Core Admin"})

OKREGI: tuple[str, ...] = tuple(nazwa for _, nazwa in OKREGI_KAMPANII)


def moze_widziec(roles: Iterable[str]) -> bool:
	return not ROLE_KATEGORII.isdisjoint(roles)


def moze_zapisac(roles: Iterable[str]) -> bool:
	return not ROLE_ZAPISU.isdisjoint(roles)


def okreg_kampanii(tekst: Any) -> str:
	"""Okręg z pola `custom_kampania_fb`: układ `[..][WROCŁAW][..]`, skrót `Wrocław, 27.10`
	albo prosty tekst typu `GORZÓW` / `Trójmiasto 3.11` (porównanie bez polskich znaków)."""
	if not isinstance(tekst, str):
		return ""
	znaleziony = okreg_z_kampanii(tekst)
	if znaleziony:
		return znaleziony
	normalny = tekst.translate(_ODWZOROWANIE_POLSKICH_ZNAKOW).upper()
	for slowo, nazwa in OKREGI_KAMPANII:
		if slowo in normalny:
			return nazwa
	return ""


@dataclass(frozen=True)
class Teren:
	handlowiec: str
	nazwa_handlowca: str
	kategoria: str
	lat: float | None
	lng: float | None
	promien_km: int
	okreg: str


def teren_z_wiersza(wiersz: Mapping[str, Any]) -> Teren | None:
	"""Teren z wiersza `User`; bez kategorii z listy daje None. 0/0 to brak środka."""
	kategoria = _tekst(wiersz.get("custom_kategoria_handlowca"))
	if kategoria not in KATEGORIE:
		return None
	lat = _liczba(wiersz.get("custom_teren_lat"))
	lng = _liczba(wiersz.get("custom_teren_lng"))
	if not ma_wspolrzedne(lat, lng):
		lat = lng = None
	promien = _liczba(wiersz.get("custom_teren_promien_km"))
	return Teren(
		handlowiec=_tekst(wiersz.get("name")),
		nazwa_handlowca=_tekst(wiersz.get("full_name")),
		kategoria=kategoria,
		lat=lat,
		lng=lng,
		promien_km=int(promien) if promien is not None else 0,
		okreg=_tekst(wiersz.get("custom_okreg_kampanii")),
	)


def kategorie_leada(
	lat: Any,
	lng: Any,
	kampania: Any,
	wlasciciel: Any,
	tereny: Iterable[Teren],
) -> dict[str, str]:
	"""`{kategoria: handlowiec}` w kolejności rangi (pierwszy klucz = kategoria główna).

	Lead należy do KAŻDEJ kategorii, której teren (promień albo okręg kampanii) go obejmuje
	(ops#406). W kategorii wygrywa bliższy środek (teren bez środka jest najdalej), potem
	nazwa konta (stabilny wynik). Właściciel z kategorią `Nie umawiać` wygrywa zawsze i
	wyklucza pozostałe.
	"""
	tereny = list(tereny)
	wlasciciel_txt = _tekst(wlasciciel)
	for t in tereny:
		if t.handlowiec == wlasciciel_txt and t.kategoria == NIE_UMAWIAC:
			return {NIE_UMAWIAC: t.handlowiec}
	okreg = okreg_kampanii(kampania)
	szer, dlug = _liczba(lat), _liczba(lng)
	maja_wsp = ma_wspolrzedne(szer, dlug)
	najlepsi: dict[str, tuple[float, str]] = {}
	for t in tereny:
		odl = float("inf")
		wsrodku = False
		if maja_wsp and t.lat is not None and t.lng is not None and t.promien_km > 0:
			odl = odleglosc_km(szer, dlug, t.lat, t.lng)  # type: ignore[arg-type]
			wsrodku = odl <= t.promien_km
		if not (wsrodku or (okreg and t.okreg == okreg)):
			continue
		kandydat = (odl, t.handlowiec)
		if t.kategoria not in najlepsi or kandydat < najlepsi[t.kategoria]:
			najlepsi[t.kategoria] = kandydat
	return {k: najlepsi[k][1] for k in KATEGORIE if k in najlepsi}


def kategoria_leada(
	lat: Any,
	lng: Any,
	kampania: Any,
	wlasciciel: Any,
	tereny: Iterable[Teren],
) -> tuple[str, str] | None:
	"""Kategoria główna leada: `(kategoria, handlowiec)` albo None, gdy nic nie pasuje."""
	wszystkie = kategorie_leada(lat, lng, kampania, wlasciciel, tereny)
	return next(iter(wszystkie.items()), None)


def kategorie_leadow(
	leady: Iterable[Mapping[str, Any]], tereny: Iterable[Teren]
) -> dict[str, dict[str, str]]:
	"""`name` leada -> `{kategoria: handlowiec}` (kolejność rangi); leady bez kategorii pomijane."""
	tereny = list(tereny)
	wynik: dict[str, dict[str, str]] = {}
	for lead in leady:
		k = kategorie_leada(
			lead.get("custom_lat"),
			lead.get("custom_lng"),
			lead.get("custom_kampania_fb"),
			lead.get("lead_owner"),
			tereny,
		)
		if k:
			wynik[_tekst(lead.get("name"))] = k
	return wynik


def sortuj_handlowcow(wpisy: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
	"""Kolejność handlowców w kalendarzu: Priorytet, Standard, Nie umawiać, bez kategorii;
	w grupie po `full_name` (bez rozróżniania wielkości liter). Wpis ma klucze `kategoria`
	(`""` gdy brak) i `full_name`."""

	def klucz(w: Mapping[str, Any]) -> tuple[int, str]:
		k = _tekst(w.get("kategoria"))
		ranga = KATEGORIE.index(k) if k in KATEGORIE else len(KATEGORIE)
		return (ranga, _tekst(w.get("full_name")).casefold())

	return sorted(wpisy, key=klucz)


def waliduj_teren(dane: Mapping[str, Any]) -> list[str]:
	"""Lista komunikatów po polsku; pusta, gdy ustawienia są poprawne."""
	bledy: list[str] = []
	kategoria = _tekst(dane.get("kategoria"))
	if kategoria and kategoria not in KATEGORIE:
		bledy.append("Wybierz kategorię z listy: " + ", ".join(KATEGORIE) + ".")
	okreg = _tekst(dane.get("okreg"))
	if okreg and okreg not in OKREGI:
		bledy.append("Wybierz okręg kampanii z listy: " + ", ".join(OKREGI) + ".")
	lat, lng = _liczba(dane.get("teren_lat")), _liczba(dane.get("teren_lng"))
	if ma_wspolrzedne(lat, lng):
		if not (SZEROKOSC_MIN <= lat <= SZEROKOSC_MAX and DLUGOSC_MIN <= lng <= DLUGOSC_MAX):  # type: ignore[operator]
			bledy.append("Środek terenu musi leżeć w granicach Polski.")
		promien = _liczba(dane.get("promien_km"))
		if promien is None or promien != int(promien) or not PROMIEN_MIN_KM <= promien <= PROMIEN_MAX_KM:
			bledy.append(f"Promień musi być liczbą całkowitą od {PROMIEN_MIN_KM} do {PROMIEN_MAX_KM} km.")
	return bledy
