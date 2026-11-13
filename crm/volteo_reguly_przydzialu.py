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

import json
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


# --- Adapter API reguł (ops#346): logika czysta ---------------------------------

LIMIT_KANDYDATOW_SRODKA: int = 20
MIN_ZNAKOW_SZUKANIA: int = 2


def grupuj_kandydatow_srodka(
	wiersze: Iterable[Mapping[str, Any]], limit: int = LIMIT_KANDYDATOW_SRODKA
) -> list[dict[str, Any]]:
	"""Kandydaci środka z wierszy `Postal Code`: jeden na parę miejscowość i powiat.

	Z każdej pary zostaje wiersz o najniższym kodzie. Wiersze bez miejscowości albo
	bez współrzędnych odpadają. Wynik posortowany po miejscowości, kodzie; maks. `limit`.
	Pola: kod, miejscowosc, powiat, wojewodztwo, lat, lng.
	"""
	najlepsze: dict[tuple[str, str], dict[str, Any]] = {}
	for wiersz in wiersze:
		miejscowosc = _tekst(wiersz.get("miejscowosc"))
		kod = _tekst(wiersz.get("kod"))
		if not miejscowosc or not kod or not ma_wspolrzedne(wiersz.get("lat"), wiersz.get("lng")):
			continue
		powiat = _tekst(wiersz.get("powiat"))
		klucz = (miejscowosc.casefold(), powiat.casefold())
		aktualny = najlepsze.get(klucz)
		if aktualny is not None and aktualny["kod"] <= kod:
			continue
		najlepsze[klucz] = {
			"kod": kod,
			"miejscowosc": miejscowosc,
			"powiat": powiat,
			"wojewodztwo": _tekst(wiersz.get("wojewodztwo")),
			"lat": float(_liczba(wiersz.get("lat"))),  # type: ignore[arg-type]
			"lng": float(_liczba(wiersz.get("lng"))),  # type: ignore[arg-type]
		}
	wynik = sorted(najlepsze.values(), key=lambda k: (k["miejscowosc"].casefold(), k["kod"]))
	return wynik[: max(0, int(limit))]


def policz_leady_w_promieniu(
	reguly: Iterable[Regula], wspolrzedne_leadow: Iterable[tuple[Any, Any]]
) -> dict[str, int]:
	"""Dla każdej reguły (po `name`) liczba punktów w jej promieniu od środka.

	Reguła bez współrzędnych środka albo z promieniem <= 0 dostaje 0. Punkty bez
	poprawnych współrzędnych są pomijane. Nieaktywne reguły też są liczone (podgląd).
	"""
	punkty = [
		(float(_liczba(lat)), float(_liczba(lng)))  # type: ignore[arg-type]
		for lat, lng in wspolrzedne_leadow
		if ma_wspolrzedne(lat, lng)
	]
	wynik: dict[str, int] = {}
	for regula in reguly:
		licznik = 0
		if regula.promien_km > 0 and ma_wspolrzedne(regula.srodek_lat, regula.srodek_lng):
			for lat, lng in punkty:
				if odleglosc_km(lat, lng, regula.srodek_lat, regula.srodek_lng) <= regula.promien_km:  # type: ignore[arg-type]
					licznik += 1
		wynik[regula.name] = licznik
	return wynik


def ostrzezenia_reguly(
	konto: Mapping[str, Any] | None, ma_rola_d2d: bool, ma_linie_leady: bool, ma_numer: bool
) -> list[str]:
	"""Ostrzeżenia o handlowcu reguły (teksty po polsku, kolejność stała)."""
	if konto is None:
		return ["Konto nie istnieje"]
	ostrzezenia: list[str] = []
	if not konto.get("enabled"):
		ostrzezenia.append("Konto wyłączone")
	if not ma_rola_d2d:
		ostrzezenia.append("Brak roli handlowca")
	if not ma_linie_leady:
		ostrzezenia.append("Brak dostępu do Leadów")
	if not ma_numer:
		ostrzezenia.append("Brak numeru telefonu")
	return ostrzezenia


def _wpis_reguly(regula: Regula, odleglosc: float, nazwy: Mapping[str, str]) -> dict[str, Any]:
	return {
		"kolejnosc": regula.kolejnosc,
		"handlowiec_nazwa": nazwy.get(regula.handlowiec) or regula.handlowiec,
		"srodek_nazwa": regula.srodek_nazwa,
		"odleglosc_km": round(odleglosc),
	}


def zbuduj_wynik_sprawdzenia(
	kod: str,
	dane_kodu: Mapping[str, Any] | None,
	dopasowanie: Dopasowanie | None,
	najblizsza: tuple[Regula, float] | None,
	nazwy_handlowcow: Mapping[str, str],
) -> dict[str, Any]:
	"""Słownik odpowiedzi `sprawdz_kod` z obiektów rdzenia (bez I/O).

	`dane_kodu` None oznacza kod nieznany albo bez współrzędnych: wynik "cc".
	Odpowiedź nie zawiera numeru telefonu ani tożsamości CC.
	"""
	znany = dane_kodu is not None
	wynik: dict[str, Any] = {
		"kod": kod,
		"znany": znany,
		"miejscowosc": _tekst(dane_kodu.get("miejscowosc")) if dane_kodu else "",
		"wojewodztwo": _tekst(dane_kodu.get("wojewodztwo")) if dane_kodu else "",
		"wynik": "cc",
		"regula": None,
		"odleglosc_km": None,
		"inne_pasujace": [],
		"najblizsza": None,
	}
	if dopasowanie is not None:
		r = dopasowanie.regula
		wynik["wynik"] = "regula"
		wynik["regula"] = {
			"name": r.name,
			"kolejnosc": r.kolejnosc,
			"handlowiec_nazwa": nazwy_handlowcow.get(r.handlowiec) or r.handlowiec,
			"srodek_nazwa": r.srodek_nazwa,
			"promien_km": r.promien_km,
		}
		wynik["odleglosc_km"] = round(dopasowanie.odleglosc_km)
		wynik["inne_pasujace"] = [
			_wpis_reguly(inna, odl, nazwy_handlowcow) for inna, odl in dopasowanie.inne_pasujace
		]
	elif najblizsza is not None:
		r, odl = najblizsza
		wpis = _wpis_reguly(r, odl, nazwy_handlowcow)
		wpis.pop("handlowiec_nazwa")
		wynik["najblizsza"] = wpis
	return wynik


# --- Webhook i SMS do handlowca o leadzie (ops#347): logika czysta --------------

TTL_LICZNIKA_SEK: int = 2 * 24 * 3600
TTL_REZERWACJI_SEK: int = 24 * 3600
TTL_ODROCZONYCH_SEK: int = 2 * 24 * 3600
TTL_ALERTU_SEK: int = 2 * 24 * 3600
POLE_ZNACZNIKA: str = "custom_przydzial_bezposredni"


def klucz_alertu_limitu(data: date | datetime) -> str:
	"""Klucz Redis alertu "limit wyczerpany": jeden wpis w Error Log na dobę."""
	return f"{PREFIKS_KLUCZA}alert:limit:{_dzien(data)}"


def czy_znacznik(wartosc: Any) -> bool:
	"""Znacznik `custom_przydzial_bezposredni` z bazy (0, 1, "0", "1", None)."""
	liczba = _liczba(wartosc)
	return liczba is not None and liczba != 0


def czy_ponowne_do_handlowca(znacznik: Any, wlasciciel: Any) -> bool:
	"""Ponowne zgłoszenie tego samego numeru idzie do handlowca tylko dla leada przydzielonego
	regułą (znacznik 1) i z niepustym właścicielem; inaczej do dyżurnego jak dotąd."""
	return czy_znacznik(znacznik) and bool(_tekst(wlasciciel))


def czy_wyslac_odroczone(wpis_wlasciciel: Any, wlasciciel: Any, znacznik: Any) -> bool:
	"""Po ciszy nocnej wysyłamy tylko, gdy lead ma nadal tego samego właściciela i znacznik 1."""
	biezacy = _tekst(wlasciciel)
	return bool(biezacy) and biezacy == _tekst(wpis_wlasciciel) and czy_znacznik(znacznik)


def limit_dzienny_lead(ustawienia: Mapping[str, Any]) -> int:
	"""`limit_dzienny_lead_bezposredni`; brak albo nieliczbowy = domyślny, ujemny = 0."""
	wartosc = ustawienia.get(POLE_LIMITU)
	if wartosc in (None, ""):
		return LIMIT_DZIENNY_DOMYSLNY
	try:
		return max(0, int(float(wartosc)))
	except (TypeError, ValueError):
		return LIMIT_DZIENNY_DOMYSLNY


def szablon_lead_bezposredni(ustawienia: Mapping[str, Any], ponowne: bool = False) -> str:
	"""Szablon SMS: zapisany (niepusty) albo domyślny; przy ponownym zgłoszeniu z `PREFIKS_PONOWNE`."""
	zapisany = ustawienia.get(POLE_TRESCI)
	szablon = zapisany if isinstance(zapisany, str) and zapisany.strip() else TRESC_LEAD_BEZPOSREDNI_DOMYSLNA
	return f"{PREFIKS_PONOWNE}{szablon}" if ponowne else szablon


def zakoduj_odroczenie_lead(ponowne: bool, wlasciciel: str) -> str:
	"""Wartość w `KLUCZ_ODROCZONYCH`: czy ponowne zgłoszenie i właściciel z chwili odroczenia (JSON)."""
	return json.dumps({"ponowne": bool(ponowne), "wlasciciel": _tekst(wlasciciel)})


def odkoduj_odroczenie_lead(tekst: Any) -> tuple[bool, str] | None:
	"""(ponowne, właściciel) z wartości kolejki odroczonych (str albo bytes); None dla nieczytelnej."""
	if isinstance(tekst, bytes):
		tekst = tekst.decode("utf-8", "replace")
	try:
		dane = json.loads(_tekst(tekst))
	except (ValueError, TypeError):
		return None
	if not isinstance(dane, dict) or not isinstance(dane.get("ponowne"), bool):
		return None
	return dane["ponowne"], _tekst(dane.get("wlasciciel"))
