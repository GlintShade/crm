# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""
API reguł bezpośredniego przydziału leadów (ops#346)
====================================================

Zarządzanie regułami `Volteo Regula Przydzialu` (środek obszaru, promień w km,
handlowiec) i sprawdzenie, do kogo trafi lead z danego kodu pocztowego. Używa go
zakładka Ustawienia, "Przydział leadów" (tryb "Reguły bezpośrednie"), a funkcje
wewnętrzne (`wczytaj_reguly`, `dozwoleni_handlowcy`, `wspolrzedne_kodu`) importuje
webhook leadów, dzięki czemu `sprawdz_kod` i webhook podejmują tę samą decyzję.

Dostęp: każda metoda whitelisted zaczyna od `frappe.only_for` dla `System Manager`
i `Volteo Core Admin`. Odpowiedzi nigdy nie zawierają numeru telefonu handlowca
ani pola `custom_cc`. Współrzędne środka reguły czyta serwer z `Postal Code`,
nigdy od klienta. Logika czysta jest w `crm/volteo_reguly_przydzialu.py`.
"""

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime

from crm.api.sms_powitalny import DOCTYPE_USTAWIEN
from crm.api.volteo_leady import ROLA_D2D, _aktywni_d2d_reprezentanci, _waliduj_handlowca
from crm.permissions.org_hierarchy import _ma_linie_leady
from crm.volteo_dyzury import normalizuj_numer_pl
from crm.volteo_kod_pocztowy import normalizuj_kod
from crm.volteo_leady_kontakt import czy_lead_z_webhooka
from crm.volteo_reguly_przydzialu import (
	MIN_ZNAKOW_SZUKANIA,
	POLE_WLACZONE,
	Regula,
	dopasuj_regule,
	grupuj_kandydatow_srodka,
	ma_wspolrzedne,
	najblizsza_regula,
	ostrzezenia_reguly,
	policz_leady_w_promieniu,
	regula_z_wiersza,
	uporzadkuj,
	waliduj_regule,
	zbuduj_wynik_sprawdzenia,
)
from crm.volteo_sms import numer_do_smsapi

DOCTYPE = "Volteo Regula Przydzialu"
DOCTYPE_KODOW = "Postal Code"
DOPUSZCZONE_ROLE_WOLAJACEGO = ["System Manager", "Volteo Core Admin"]
OKNO_LEADOW_DNI = 30

_POLA_REGULY = (
	"name",
	"handlowiec",
	"srodek_nazwa",
	"srodek_kod",
	"srodek_lat",
	"srodek_lng",
	"promien_km",
	"aktywna",
	"kolejnosc",
)
_POLA_KODU = ("kod", "miejscowosc", "powiat", "wojewodztwo", "lat", "lng")


# --- Funkcje wewnętrzne (importuje je webhook) --------------------------------


def wczytaj_reguly() -> list[Regula]:
	"""Wszystkie reguły jako obiekty rdzenia; pusta lista, gdy doctype nie istnieje."""
	if not frappe.db.table_exists(DOCTYPE):
		return []
	wiersze = frappe.get_all(DOCTYPE, fields=list(_POLA_REGULY))
	return [regula_z_wiersza(w) for w in wiersze]


def dozwoleni_handlowcy() -> set[str]:
	"""Aktywne konta `Volteo D2D Sales` z włączoną linią Leady.

	`_aktywni_d2d_reprezentanci` już filtruje po `custom_linia_leady`, a
	`_ma_linie_leady` dodatkowo pilnuje reguły bramki (BYPASS_ROLES, brak pola).
	"""
	return {r.name for r in _aktywni_d2d_reprezentanci() if _ma_linie_leady(r.name)}


def wspolrzedne_kodu(kod: str) -> dict[str, Any] | None:
	"""Wiersz `Postal Code` (kod, miejscowosc, powiat, wojewodztwo, lat, lng) z lokalnej tabeli.

	Bez zewnętrznego API. `None`, gdy kod jest niepoprawny, nie ma go w tabeli
	albo ma lat/lng równe 0.
	"""
	znormalizowany = normalizuj_kod(kod)
	if not znormalizowany:
		return None
	wiersz = frappe.db.get_value(DOCTYPE_KODOW, {"kod": znormalizowany}, list(_POLA_KODU), as_dict=True)
	if not wiersz or not ma_wspolrzedne(wiersz.get("lat"), wiersz.get("lng")):
		return None
	return dict(wiersz)


# --- Pomocnicze ----------------------------------------------------------------


def _dostep() -> None:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)


def _wspolrzedne_leadow_z_webhooka() -> list[tuple[Any, Any]]:
	"""Współrzędne leadów z webhooka utworzonych w ostatnich 30 dniach (jedno zapytanie)."""
	od = add_days(now_datetime(), -OKNO_LEADOW_DNI)
	wiersze = frappe.get_all(
		"CRM Lead",
		filters={"creation": [">=", od], "custom_lat": ["!=", 0]},
		or_filters=[["source", "=", "Facebook"], ["custom_import_source", "like", "%FB%"]],
		fields=["custom_lat", "custom_lng", "source", "custom_import_source"],
		limit_page_length=0,
	)
	return [
		(w.custom_lat, w.custom_lng) for w in wiersze if czy_lead_z_webhooka(w.source, w.custom_import_source)
	]


def _konta(nazwy: list[str]) -> dict[str, dict[str, Any]]:
	"""`User` -> enabled, full_name, ma_numer, ma_rola_d2d, ma_linie_leady (bez numeru telefonu)."""
	if not nazwy:
		return {}
	wiersze = frappe.get_all(
		"User",
		filters={"name": ["in", nazwy]},
		fields=["name", "full_name", "enabled", "mobile_no"],
	)
	z_rola = set(
		frappe.get_all(
			"Has Role",
			filters={"parenttype": "User", "role": ROLA_D2D, "parent": ["in", nazwy]},
			pluck="parent",
		)
	)
	return {
		w.name: {
			"full_name": w.full_name or w.name,
			"enabled": cint(w.enabled),
			"ma_numer": bool(numer_do_smsapi(normalizuj_numer_pl(w.mobile_no))),
			"ma_rola_d2d": w.name in z_rola,
			"ma_linie_leady": bool(_ma_linie_leady(w.name)),
		}
		for w in wiersze
	}


def _sms_wlaczony() -> bool:
	"""Przełącznik SMS do handlowca o leadzie bezpośrednim; brak pola albo doctype to fałsz."""
	try:
		return bool(cint((frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}).get(POLE_WLACZONE)))
	except Exception:
		return False


def _lista() -> dict[str, Any]:
	reguly = uporzadkuj(wczytaj_reguly())
	konta = _konta(sorted({r.handlowiec for r in reguly if r.handlowiec}))
	liczniki = policz_leady_w_promieniu(reguly, _wspolrzedne_leadow_z_webhooka())
	wynik_regul = []
	for r in reguly:
		konto = konta.get(r.handlowiec)
		wynik_regul.append(
			{
				"name": r.name,
				"handlowiec": r.handlowiec,
				"handlowiec_nazwa": konto["full_name"] if konto else r.handlowiec,
				"srodek_nazwa": r.srodek_nazwa,
				"srodek_kod": r.srodek_kod,
				"srodek_lat": r.srodek_lat,
				"srodek_lng": r.srodek_lng,
				"promien_km": r.promien_km,
				"aktywna": 1 if r.aktywna else 0,
				"kolejnosc": r.kolejnosc,
				"leady_30_dni": liczniki.get(r.name, 0),
				"ostrzezenia": ostrzezenia_reguly(
					konto,
					bool(konto and konto["ma_rola_d2d"]),
					bool(konto and konto["ma_linie_leady"]),
					bool(konto and konto["ma_numer"]),
				),
			}
		)
	aktywni = [r.name for r in _aktywni_d2d_reprezentanci()]
	konta_handlowcow = _konta(aktywni)
	handlowcy = [
		{
			"user": nazwa,
			"full_name": k["full_name"],
			"ma_numer": k["ma_numer"],
			"ma_linie_leady": k["ma_linie_leady"],
		}
		for nazwa, k in konta_handlowcow.items()
	]
	handlowcy.sort(key=lambda h: h["full_name"].casefold())
	return {"reguly": wynik_regul, "handlowcy": handlowcy, "sms_wlaczony": _sms_wlaczony()}


def _srodek_z_kodu(srodek_kod: str) -> dict[str, Any]:
	dane = wspolrzedne_kodu(srodek_kod)
	if not dane:
		frappe.throw(_("Nie znaleziono współrzędnych dla kodu pocztowego {0}.").format(srodek_kod))
	return dane


def _sprawdz_dane_reguly(handlowiec: str, srodek: dict[str, Any], promien_km: int, aktywna: bool) -> None:
	bledy = waliduj_regule(
		{
			"handlowiec": handlowiec,
			"promien_km": promien_km,
			"srodek_lat": srodek.get("lat"),
			"srodek_lng": srodek.get("lng"),
		}
	)
	if bledy:
		frappe.throw(_(bledy[0]))
	if aktywna:
		_waliduj_handlowca(handlowiec)
	elif not frappe.db.exists("User", handlowiec):
		frappe.throw(_("Użytkownik {0} nie istnieje.").format(handlowiec))


def _dokument(name: str) -> "frappe.model.document.Document":
	if not name or not frappe.db.exists(DOCTYPE, name):
		frappe.throw(_("Reguła {0} nie istnieje.").format(name))
	return frappe.get_doc(DOCTYPE, name)


# --- Metody whitelisted --------------------------------------------------------


@frappe.whitelist()
def lista() -> dict:
	"""Reguły i handlowcy do wyboru.

	Zwraca `{"reguly": [...], "handlowcy": [...], "sms_wlaczony": bool}`
	(`sms_wlaczony`: przełącznik `lead_bezposredni_wlaczone` w `Volteo SMS Ustawienia`). Reguła: `name, handlowiec,
	handlowiec_nazwa, srodek_nazwa, srodek_kod, srodek_lat, srodek_lng, promien_km,
	aktywna, kolejnosc, leady_30_dni, ostrzezenia` (lista tekstów: konto wyłączone,
	brak roli D2D, brak dostępu do Leadów, brak numeru telefonu), posortowane po
	`kolejnosc`. Handlowiec: `user, full_name, ma_numer, ma_linie_leady`. Numer
	telefonu nigdy nie jest zwracany.
	"""
	_dostep()
	return _lista()


@frappe.whitelist()
def szukaj_srodka(q: str) -> list[dict]:
	"""Kandydaci środka obszaru po kodzie pocztowym albo początku nazwy miejscowości.

	`q` ma min. 2 znaki. Zwraca listę (maks. 20) słowników `{kod, miejscowosc,
	powiat, wojewodztwo, lat, lng}`: jeden na parę miejscowość i powiat (najniższy
	kod), tylko wiersze ze współrzędnymi. Krótsze `q` daje pustą listę.
	"""
	_dostep()
	fraza = (q or "").strip()
	if len(fraza) < MIN_ZNAKOW_SZUKANIA:
		return []
	kod = normalizuj_kod(fraza)
	if kod:
		filtry: dict[str, Any] = {"kod": kod}
	elif fraza[0].isdigit():
		filtry = {"kod": ["like", f"{fraza}%"]}
	else:
		filtry = {"miejscowosc": ["like", f"{fraza}%"]}
	wiersze = frappe.get_all(
		DOCTYPE_KODOW,
		filters=filtry,
		fields=list(_POLA_KODU),
		order_by="kod asc",
		limit_page_length=2000,
	)
	return grupuj_kandydatow_srodka(wiersze)


@frappe.whitelist()
def zapisz(
	handlowiec: str,
	srodek_kod: str,
	promien_km: int,
	aktywna: int = 1,
	name: str | None = None,
	srodek_nazwa: str | None = None,
) -> dict:
	"""Tworzy (bez `name`) albo aktualizuje regułę; zwraca świeże `lista()`.

	Współrzędne środka czyta serwer z `Postal Code` po `srodek_kod`.
	`srodek_nazwa` domyślnie to miejscowość z tabeli. Nowa reguła dostaje
	`kolejnosc` = max + 1. Aktywnej reguły nie da się zapisać dla handlowca bez
	dostępu do Leadów (komunikat po polsku).
	"""
	_dostep()
	kod = normalizuj_kod(srodek_kod) or (srodek_kod or "").strip()
	srodek = _srodek_z_kodu(kod)
	promien = cint(promien_km)
	czy_aktywna = bool(cint(aktywna))
	_sprawdz_dane_reguly(handlowiec, srodek, promien, czy_aktywna)
	nazwa_srodka = (srodek_nazwa or "").strip() or srodek.get("miejscowosc") or ""
	if name:
		doc = _dokument(name)
	else:
		doc = frappe.new_doc(DOCTYPE)
		maks = max((r.kolejnosc for r in wczytaj_reguly()), default=0)
		doc.kolejnosc = maks + 1
	doc.handlowiec = handlowiec
	doc.srodek_kod = srodek["kod"]
	doc.srodek_nazwa = nazwa_srodka
	doc.srodek_lat = float(srodek["lat"])
	doc.srodek_lng = float(srodek["lng"])
	doc.promien_km = promien
	doc.aktywna = 1 if czy_aktywna else 0
	doc.save()
	return _lista()


@frappe.whitelist()
def ustaw_kolejnosc(nazwy: str) -> dict:
	"""Ustawia kolejność reguł; `nazwy` to JSON lista WSZYSTKICH `name` w nowej kolejności.

	Odrzuca listę niepełną, z duplikatem albo z nieznaną nazwą. Zapisuje
	`kolejnosc` 1..N. Zwraca świeże `lista()`.
	"""
	_dostep()
	try:
		kolejka = json.loads(nazwy) if isinstance(nazwy, str) else nazwy
	except ValueError:
		frappe.throw(_("Nieprawidłowa lista reguł."))
	if not isinstance(kolejka, list) or not all(isinstance(n, str) for n in kolejka):
		frappe.throw(_("Nieprawidłowa lista reguł."))
	istniejace = set(frappe.get_all(DOCTYPE, pluck="name"))
	if len(kolejka) != len(set(kolejka)) or set(kolejka) != istniejace:
		frappe.throw(_("Lista musi zawierać wszystkie reguły, każdą dokładnie raz."))
	for pozycja, nazwa in enumerate(kolejka, start=1):
		doc = frappe.get_doc(DOCTYPE, nazwa)
		if cint(doc.kolejnosc) != pozycja:
			doc.kolejnosc = pozycja
			doc.save()
	return _lista()


@frappe.whitelist()
def przelacz(name: str, aktywna: int) -> dict:
	"""Włącza (`aktywna` 1) albo wyłącza (0) regułę; zwraca świeże `lista()`.

	Włączenie wymaga tych samych warunków co `zapisz` (handlowiec z dostępem do Leadów).
	"""
	_dostep()
	doc = _dokument(name)
	czy_aktywna = bool(cint(aktywna))
	if czy_aktywna:
		_waliduj_handlowca(doc.handlowiec)
	doc.aktywna = 1 if czy_aktywna else 0
	doc.save()
	return _lista()


@frappe.whitelist()
def usun(name: str) -> dict:
	"""Usuwa regułę; zwraca świeże `lista()`. Kolejność pozostałych nie jest zmieniana."""
	_dostep()
	_dokument(name)
	frappe.delete_doc(DOCTYPE, name)
	return _lista()


@frappe.whitelist()
def podglad_obszaru(srodek_kod: str, promien_km: int) -> dict:
	"""Podgląd obszaru przed zapisem reguły.

	Zwraca `{"leady_30_dni": int, "srodek": {kod, miejscowosc, powiat,
	wojewodztwo, lat, lng}}`: liczba leadów z webhooka z ostatnich 30 dni w promieniu.
	"""
	_dostep()
	kod = normalizuj_kod(srodek_kod) or (srodek_kod or "").strip()
	srodek = _srodek_z_kodu(kod)
	probna = Regula(
		name="podglad",
		handlowiec="",
		srodek_nazwa=srodek.get("miejscowosc") or "",
		srodek_kod=srodek["kod"],
		srodek_lat=float(srodek["lat"]),
		srodek_lng=float(srodek["lng"]),
		promien_km=cint(promien_km),
		aktywna=True,
		kolejnosc=0,
	)
	liczniki = policz_leady_w_promieniu([probna], _wspolrzedne_leadow_z_webhooka())
	return {"leady_30_dni": liczniki["podglad"], "srodek": srodek}


@frappe.whitelist()
def sprawdz_kod(kod: str) -> dict:
	"""Do kogo trafi lead z danego kodu pocztowego (nic nie zapisuje).

	Zwraca `{kod, znany, miejscowosc, wojewodztwo, lat, lng (float albo None
	dla kodu nieznanego), wynik: "regula" | "cc",
	regula: {name, kolejnosc, handlowiec_nazwa, srodek_nazwa, promien_km} | None,
	odleglosc_km: int | None, inne_pasujace: [{kolejnosc, handlowiec_nazwa,
	srodek_nazwa, odleglosc_km}], najblizsza: {kolejnosc, srodek_nazwa,
	odleglosc_km} | None}`. Decyzja jest ta sama co w webhooku
	(`dopasuj_regule` z `dozwoleni_handlowcy()`).
	"""
	_dostep()
	znormalizowany = normalizuj_kod(kod) or (kod or "").strip()
	dane = wspolrzedne_kodu(znormalizowany)
	reguly = wczytaj_reguly()
	dopasowanie = None
	najblizsza = None
	if dane:
		dopasowanie = dopasuj_regule(dane["lat"], dane["lng"], reguly, dozwoleni_handlowcy())
		if dopasowanie is None:
			najblizsza = najblizsza_regula(dane["lat"], dane["lng"], reguly)
	nazwy = {r.handlowiec: "" for r in reguly if r.handlowiec}
	for nazwa, konto in _konta(sorted(nazwy)).items():
		nazwy[nazwa] = konto["full_name"]
	return zbuduj_wynik_sprawdzenia(znormalizowany, dane, dopasowanie, najblizsza, nazwy)
