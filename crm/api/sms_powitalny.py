# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS powitalny po leadzie z Facebooka (ops#305): zadanie w tle.

`wyslij_sms_powitalny(lead)` jest kolejkowane z `crm.api.leady_webhook.przyjmij`
wyłącznie po udanym insercie nowego leada, przez callback `after_commit`
(kolejka "short"). To JEDYNA ścieżka wyzwalająca SMS: lead dodany ręcznie,
importem arkusza czy innym API nie wysyła nic. Nie jest metodą whitelisted: woła
ją tylko worker po ścieżce kropkowej.

Ustawienia siedzą w Single `Volteo SMS Ustawienia` (edytowane w Desk przez
System Manager i Volteo Core Admin). Flagę `wlaczone` czytamy zawsze przez
`cint(get_singles_dict(...))`, bo Single zwraca stringi. Token (Password) tylko
przez `get_decrypted_password`, nigdy w logu, śladzie ani polu leada.

Przy wyłączonym kanale funkcja kończy się od razu: bez odczytu tokenu, bez zapisu
pól leada, bez śladu, bez commita. W pozostałych przypadkach wynik ląduje w dwóch
polach tylko do odczytu na leadzie (`custom_sms_powitalny_status` i `_info`,
`update_modified=False`) oraz w śladzie Aktywności. Błąd SMS nigdy nie cofa ani nie
blokuje leada ani odpowiedzi webhooka: cała funkcja łapie wyjątki i zapisuje je
w Error Log bez tokenu.

Dedupe numeru ma dwie warstwy: atomowa rezerwacja w Redis (`SET NX EX 86400`,
klucz z prefiksem site; potrzebna, bo produkcja ma dwa workery konsumujące kolejkę
short) oraz zapytanie do bazy o inne leady z tym samym numerem. Gdy Redis jest
niedostępny, SMS idzie (fail open), a w Error Log ląduje wpis. Dzienny limit realnie
wysłanych SMS (pole `limit_dzienny`) jest hamulcem na wyciek klucza integracji.

Cała logika decyzji i interpretacji odpowiedzi jest w `crm/volteo_sms.py` (bez `frappe`).
"""

import frappe
import redis
import requests
from frappe.utils import cint, now_datetime
from frappe.utils.password import get_decrypted_password

from crm.volteo_aktywnosc import zapisz_slad
from crm.volteo_sms import (
	NADAWCA_DOMYSLNY,
	STATUS_WYSLANY,
	TTL_REZERWACJI_SEK,
	data_z_info,
	klucz_rezerwacji_numeru,
	przetworz,
	wzor_info_dnia,
)

DOCTYPE_USTAWIEN = "Volteo SMS Ustawienia"
TIMEOUT_SEKUND = 15
TYTUL_BLEDU = "SMS powitalny"


def _http_post(url: str, dane: dict, naglowki: dict):
	"""Jedna próba, timeout 15 s; wyjątek `requests` leci do rdzenia, który go opisuje bez treści."""
	odp = requests.post(url, data=dane, headers=naglowki, timeout=TIMEOUT_SEKUND)
	try:
		tresc = odp.json()
	except ValueError:
		tresc = None
	return odp.status_code, tresc


def _rezerwuj(numer: str) -> bool | None:
	"""Atomowa rezerwacja numeru na 24 h; None gdy Redis niedostępny (fail open)."""
	cache = frappe.cache()
	try:
		return bool(cache.set(cache.make_key(klucz_rezerwacji_numeru(numer)), "1", nx=True, ex=TTL_REZERWACJI_SEK))
	except redis.exceptions.RedisError:
		return None


def _zwolnij(numer: str) -> None:
	cache = frappe.cache()
	try:
		cache.delete(cache.make_key(klucz_rezerwacji_numeru(numer)))
	except redis.exceptions.RedisError:
		pass


def _daty_innych_wyslanych(lead: str, mobile_no: str | None) -> list:
	"""Daty z info innych leadów z tym samym numerem i statusem Wysłany."""
	if not mobile_no:
		return []
	wiersze = frappe.get_all(
		"CRM Lead",
		filters={
			"mobile_no": mobile_no,
			"name": ["!=", lead],
			"custom_sms_powitalny_status": STATUS_WYSLANY,
		},
		fields=["custom_sms_powitalny_info"],
		limit_page_length=50,
	)
	return [d for d in (data_z_info(w.custom_sms_powitalny_info) for w in wiersze) if d]


def _wyslane_dzis(teraz) -> int:
	"""Liczba SMS realnie wysłanych w dobie serwera (z daty w polu info)."""
	return frappe.db.count(
		"CRM Lead",
		{
			"custom_sms_powitalny_status": STATUS_WYSLANY,
			"custom_sms_powitalny_info": ["like", wzor_info_dnia(teraz)],
		},
	)


def _zapisz_wynik(lead: str, status: str, info: str) -> None:
	frappe.db.set_value(
		"CRM Lead",
		lead,
		{"custom_sms_powitalny_status": status, "custom_sms_powitalny_info": info},
		update_modified=False,
	)


def wyslij_sms_powitalny(lead: str) -> None:
	"""Zadanie w tle: patrz docstring modułu. Nigdy nie rzuca."""
	try:
		ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
		if not cint(ustawienia.get("wlaczone")):
			return  # kanał wyłączony: nic nie czytamy i nic nie zapisujemy
		token = get_decrypted_password(DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False)
		dane_leada = frappe.db.get_value("CRM Lead", lead, ["mobile_no", "custom_sms_powitalny_status"], as_dict=True)
		if not dane_leada:
			return

		teraz = now_datetime()
		wynik = przetworz(
			wlaczone=True,
			token=token,
			nadawca=ustawienia.get("nadawca") or NADAWCA_DOMYSLNY,
			tresc_surowa=ustawienia.get("tresc_powitalna") or "",
			tryb_testowy=bool(cint(ustawienia.get("tryb_testowy"))),
			mobile_no=dane_leada.mobile_no,
			status_leada=dane_leada.custom_sms_powitalny_status,
			daty_innych_wyslanych=_daty_innych_wyslanych(lead, dane_leada.mobile_no),
			teraz=teraz,
			http_post=_http_post,
			rezerwuj=_rezerwuj,
			zwolnij=_zwolnij,
			limit_dzienny=cint(ustawienia.get("limit_dzienny")),
			wyslane_dzis=_wyslane_dzis(teraz),
		)
		if not wynik.zapisz:
			return

		_zapisz_wynik(lead, wynik.status, wynik.info)
		zapisz_slad(lead, wynik.slad, doctype="CRM Lead")
		if wynik.blad_do_logu:
			frappe.log_error(title=TYTUL_BLEDU, message=f"Lead {lead}: {wynik.blad_do_logu}")
		if wynik.ostrzezenie:
			frappe.log_error(
				title="SMS powitalny: treść dłuższa niż 1 część", message=f"Lead {lead}: {wynik.ostrzezenie}"
			)
		if wynik.redis_niedostepny:
			frappe.log_error(
				title=TYTUL_BLEDU, message=f"Lead {lead}: Redis cache niedostępny, dedupe tylko po bazie"
			)
		if wynik.limit_wyczerpany:
			frappe.log_error(
				title="SMS powitalny: limit dzienny",
				message=f"Lead {lead}: wyczerpany limit dzienny SMS powitalnych, SMS nie wysłany",
			)
		frappe.db.commit()
	except Exception:
		# Traceback nie niesie tokenu (jest tylko lokalną zmienną, nie argumentem wywołania w tekście).
		frappe.log_error(title=TYTUL_BLEDU, message=f"Lead {lead}: nieoczekiwany wyjątek\n{frappe.get_traceback()}")
