# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Reguły bezpośredniego przydziału leadów (ops#345): logika czysta.

Lead z Facebooka, którego kod pocztowy leży w obszarze reguły (środek plus promień
w km), trafia od razu do handlowca z reguły. Ten moduł odpowiada za wszystko poza
I/O: odległość, wybór reguły, walidację wiersza, link do mapy, stałe SMS do
handlowca o nowym leadzie, decyzję o wysyłce i teksty śladów.

Moduł celowo nie importuje ``frappe`` (precedens `crm/volteo_dyzury.py`).
Tożsamość osoby CC nigdy nie wchodzi do SMS ani do śladów.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

PROMIEN_ZIEMI_KM: float = 6371.0

PROMIEN_MIN_KM: int = 1
PROMIEN_MAX_KM: int = 300

SZEROKOSC_MIN: float = 48.5
SZEROKOSC_MAX: float = 55.5
DLUGOSC_MIN: float = 13.5
DLUGOSC_MAX: float = 24.5

TRESC_LEAD_BEZPOSREDNI_DOMYSLNA: str = (
	"Nowy lead dla Ciebie: {klient}, tel. {telefon}, {kod}, PV: {ma_pv}. Mapa: {mapa}"
)
"""Seed `tresc_lead_bezposredni` i fallback."""

PREFIKS_PONOWNE: str = "Ponownie: "
"""Przedrostek treści, gdy ten sam numer zgłasza się ponownie."""

PLACEHOLDERY_LEAD_BEZPOSREDNI: tuple[str, ...] = (
	"klient",
	"telefon",
	"kod",
	"miejscowosc",
	"ma_pv",
	"zasady",
	"link",
	"mapa",
)

DANE_PRZYKLADOWE_LEAD_BEZPOSREDNI: Mapping[str, str] = {
	"klient": "Jan Kowalski",
	"telefon": "600100200",
	"kod": "66-300",
	"miejscowosc": "Międzyrzecz",
	"ma_pv": "nie",
	"zasady": "brak",
	"link": "https://crm.proenergy.pro/crm/leads/CRM-LEAD-2026-00001",
	"mapa": "https://maps.google.com/?q=52.4447,15.5780",
}
"""Dane do podglądu i SMS testowego."""

POLE_WLACZONE: str = "lead_bezposredni_wlaczone"
POLE_TRESCI: str = "tresc_lead_bezposredni"
POLE_LIMITU: str = "limit_dzienny_lead_bezposredni"
LIMIT_DZIENNY_DOMYSLNY: int = 100

PREFIKS_KLUCZA: str = "volteo:sms_lead_bezposredni:"
KLUCZ_ODROCZONYCH: str = f"{PREFIKS_KLUCZA}odroczone"

WYNIK_WYSLIJ: str = "wyslij"
WYNIK_WYLACZONE: str = "wylaczone"
WYNIK_BRAK_NUMERU: str = "brak_numeru"
WYNIK_ODLOZ: str = "odloz"
WYNIK_LIMIT: str = "limit"
WYNIK_BLAD: str = "blad"


def _liczba(wartosc: Any) -> float | None:
	"""Skończona liczba z liczby albo napisu; None dla reszty (bool też odpada)."""
	if wartosc is None or isinstance(wartosc, bool):
		return None
	try:
		wynik = float(str(wartosc).strip().replace(",", ".")) if isinstance(wartosc, str) else float(wartosc)
	except (TypeError, ValueError):
		return None
	return wynik if math.isfinite(wynik) else None


def _tekst(wartosc: Any) -> str:
	return "" if wartosc is None else str(wartosc).strip()


def odleglosc_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
	"""Odległość po kuli (haversine, promień 6371 km)."""
	f1, f2 = math.radians(lat1), math.radians(lat2)
	df = f2 - f1
	dl = math.radians(lng2 - lng1)
	a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
	return 2 * PROMIEN_ZIEMI_KM * math.asin(min(1.0, math.sqrt(a)))


def ma_wspolrzedne(lat: Any, lng: Any) -> bool:
	"""Prawda dla pary liczb skończonych, innej niż 0/0 (nieustawiony Float we Frappe to 0)."""
	a, b = _liczba(lat), _liczba(lng)
	if a is None or b is None:
		return False
	return not (a == 0 and b == 0)


@dataclass(frozen=True)
class Regula:
	name: str
	handlowiec: str
	srodek_nazwa: str
	srodek_kod: str
	srodek_lat: float | None
	srodek_lng: float | None
	promien_km: int
	aktywna: bool
	kolejnosc: int


def _aktywna(wartosc: Any) -> bool:
	if isinstance(wartosc, str):
		return wartosc.strip().lower() not in ("", "0", "false", "nie", "none")
	return bool(wartosc)


def regula_z_wiersza(wiersz: Mapping[str, Any]) -> Regula:
	"""Reguła z wiersza bazy; tolerancyjna wobec napisów i None."""
	promien = _liczba(wiersz.get("promien_km"))
	kolejnosc = _liczba(wiersz.get("kolejnosc"))
	lat = _liczba(wiersz.get("srodek_lat"))
	lng = _liczba(wiersz.get("srodek_lng"))
	return Regula(
		name=_tekst(wiersz.get("name")),
		handlowiec=_tekst(wiersz.get("handlowiec")),
		srodek_nazwa=_tekst(wiersz.get("srodek_nazwa")),
		srodek_kod=_tekst(wiersz.get("srodek_kod")),
		srodek_lat=lat,
		srodek_lng=lng,
		promien_km=int(promien) if promien is not None else 0,
		aktywna=_aktywna(wiersz.get("aktywna")),
		kolejnosc=int(kolejnosc) if kolejnosc is not None else 0,
	)


def uporzadkuj(reguly: Iterable[Regula]) -> list[Regula]:
	"""Rosnąco po `kolejnosc`, przy remisie po `name`; wejście bez zmian."""
	return sorted(reguly, key=lambda r: (r.kolejnosc, r.name))


@dataclass(frozen=True)
class Dopasowanie:
	regula: Regula
	odleglosc_km: float
	inne_pasujace: list[tuple[Regula, float]]


def _odleglosc_do_srodka(lat: float, lng: float, regula: Regula) -> float | None:
	if not ma_wspolrzedne(regula.srodek_lat, regula.srodek_lng):
		return None
	return odleglosc_km(lat, lng, regula.srodek_lat, regula.srodek_lng)  # type: ignore[arg-type]


def dopasuj_regule(
	lat: Any,
	lng: Any,
	reguly: Iterable[Regula],
	dozwoleni_handlowcy: Iterable[str] | None = None,
) -> Dopasowanie | None:
	"""Pierwsza pasująca reguła wg `uporzadkuj` (odległość <= promień) albo None.

	Pomija reguły nieaktywne, bez współrzędnych, z promieniem <= 0 i takie, których
	handlowiec nie należy do `dozwoleni_handlowcy` (gdy zbiór podany).
	"""
	if not ma_wspolrzedne(lat, lng):
		return None
	szer, dlug = float(_liczba(lat)), float(_liczba(lng))  # type: ignore[arg-type]
	dozwoleni = None if dozwoleni_handlowcy is None else frozenset(dozwoleni_handlowcy)
	pasujace: list[tuple[Regula, float]] = []
	for regula in uporzadkuj(reguly):
		if not regula.aktywna or regula.promien_km <= 0:
			continue
		if dozwoleni is not None and regula.handlowiec not in dozwoleni:
			continue
		odl = _odleglosc_do_srodka(szer, dlug, regula)
		if odl is not None and odl <= regula.promien_km:
			pasujace.append((regula, odl))
	if not pasujace:
		return None
	pierwsza, odl = pasujace[0]
	return Dopasowanie(regula=pierwsza, odleglosc_km=odl, inne_pasujace=list(pasujace[1:]))


def najblizsza_regula(lat: Any, lng: Any, reguly: Iterable[Regula]) -> tuple[Regula, float] | None:
	"""Aktywna reguła ze współrzędnymi, najbliższa środkiem (do komunikatu "Najbliżej: ...")."""
	if not ma_wspolrzedne(lat, lng):
		return None
	szer, dlug = float(_liczba(lat)), float(_liczba(lng))  # type: ignore[arg-type]
	najlepsza: tuple[Regula, float] | None = None
	for regula in uporzadkuj(reguly):
		if not regula.aktywna:
			continue
		odl = _odleglosc_do_srodka(szer, dlug, regula)
		if odl is not None and (najlepsza is None or odl < najlepsza[1]):
			najlepsza = (regula, odl)
	return najlepsza


def waliduj_regule(dane: Mapping[str, Any]) -> list[str]:
	"""Lista komunikatów po polsku; pusta, gdy reguła jest poprawna."""
	bledy: list[str] = []
	if not _tekst(dane.get("handlowiec")):
		bledy.append("Wybierz handlowca.")
	promien = dane.get("promien_km")
	liczba = _liczba(promien)
	if liczba is None or liczba != int(liczba) or not PROMIEN_MIN_KM <= liczba <= PROMIEN_MAX_KM:
		bledy.append(f"Promień musi być liczbą całkowitą od {PROMIEN_MIN_KM} do {PROMIEN_MAX_KM} km.")
	lat, lng = dane.get("srodek_lat"), dane.get("srodek_lng")
	if not ma_wspolrzedne(lat, lng):
		bledy.append("Brak współrzędnych środka obszaru.")
	else:
		szer, dlug = float(_liczba(lat)), float(_liczba(lng))  # type: ignore[arg-type]
		if not (SZEROKOSC_MIN <= szer <= SZEROKOSC_MAX and DLUGOSC_MIN <= dlug <= DLUGOSC_MAX):
			bledy.append("Środek obszaru leży poza Polską.")
	return bledy


def opis_obszaru(regula: Regula) -> str:
	"""`70 km, środek: Gorzów Wielkopolski` (nazwa miejscowości bez odmiany)."""
	return f"{regula.promien_km} km, środek: {regula.srodek_nazwa}"


def link_mapy(lat: Any, lng: Any) -> str:
	"""Link do Map Google z czterema miejscami po przecinku; pusty string bez współrzędnych."""
	if not ma_wspolrzedne(lat, lng):
		return ""
	return f"https://maps.google.com/?q={float(_liczba(lat)):.4f},{float(_liczba(lng)):.4f}"


def _dzien(data: date | datetime) -> str:
	return data.strftime("%Y-%m-%d")


def klucz_licznika_dnia(data: date | datetime) -> str:
	"""Klucz Redis dziennego licznika wysłanych SMS (prefiks site dokłada adapter)."""
	return f"{PREFIKS_KLUCZA}{_dzien(data)}"


def klucz_rezerwacji(lead: str) -> str:
	"""Klucz Redis rezerwacji SMS dla leada (jeden SMS na lead)."""
	return f"{PREFIKS_KLUCZA}rezerwacja:{lead}"


def zdecyduj_sms(wlaczone: Any, numer_ok: Any, w_ciszy: Any, wyslane_dzis: int, limit: int) -> str:
	"""`wyslij`, `wylaczone`, `brak_numeru`, `limit` albo `odloz`.

	Kolejność: wyłączone, brak numeru, limit (limit 0 blokuje), cisza.
	"""
	if not wlaczone:
		return WYNIK_WYLACZONE
	if not numer_ok:
		return WYNIK_BRAK_NUMERU
	if limit <= 0 or wyslane_dzis >= limit:
		return WYNIK_LIMIT
	if w_ciszy:
		return WYNIK_ODLOZ
	return WYNIK_WYSLIJ


def tekst_sladu_przydzialu(
	handlowiec_nazwa: str, srodek_nazwa: str, promien_km: int, odleglosc_km: float
) -> str:
	"""Ślad w Aktywności leada; bez tożsamości CC."""
	return (
		f"Lead przydzielony bezpośrednio: {handlowiec_nazwa} "
		f"(reguła: {promien_km} km, środek: {srodek_nazwa}; odległość {round(odleglosc_km)} km)"
	)


def tekst_sladu_sms(wynik: str, handlowiec_nazwa: str) -> str:
	"""Ślad o SMS do handlowca dla każdego wyniku `zdecyduj_sms` oraz błędu wysyłki."""
	teksty = {
		WYNIK_WYSLIJ: f"SMS o nowym leadzie wysłany do: {handlowiec_nazwa}",
		WYNIK_WYLACZONE: f"SMS do handlowca ({handlowiec_nazwa}) nie wysłany: wysyłka wyłączona",
		WYNIK_BRAK_NUMERU: f"SMS do handlowca ({handlowiec_nazwa}) nie wysłany: brak poprawnego numeru telefonu",
		WYNIK_ODLOZ: f"SMS do handlowca ({handlowiec_nazwa}) odłożony: godziny ciszy nocnej",
		WYNIK_LIMIT: f"SMS do handlowca ({handlowiec_nazwa}) nie wysłany: dzienny limit wyczerpany",
		WYNIK_BLAD: f"SMS do handlowca ({handlowiec_nazwa}) nie wysłany: błąd wysyłki",
	}
	return teksty.get(wynik, f"SMS do handlowca ({handlowiec_nazwa}): {wynik}")
