# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS powitalny po leadzie z Facebooka (ops#305): zadanie w tle.

`wyslij_sms_powitalny(lead)` jest kolejkowane z `crm.api.leady_webhook.przyjmij`
wylacznie po udanym insercie nowego leada (`enqueue_after_commit=True`, kolejka
"short"). Nie jest metoda whitelisted: wola je tylko worker po sciezce kropkowej.

Ustawienia siedza w Single `Volteo SMS Ustawienia` (edytowane w Desk przez
System Manager i Volteo Core Admin). Flage `wlaczone` czytamy zawsze przez
`cint(get_singles_dict(...))`, bo Single zwraca stringi. Token (Password) tylko
przez `get_decrypted_password`, nigdy w logu, sladzie ani polu leada.

Wynik ladujemy w dwoch polach tylko do odczytu na leadzie
(`custom_sms_powitalny_status` i `_info`, `update_modified=False`) oraz w sladzie
Aktywnosci. Blad SMS nigdy nie cofa ani nie blokuje leada ani odpowiedzi webhooka:
cala funkcja lapie wyjatki i zapisuje je w Error Log bez tokenu.

Cala logika decyzji i interpretacji odpowiedzi jest w `crm/volteo_sms.py` (bez `frappe`).
"""

import frappe
import requests
from frappe.utils import cint, now_datetime

from crm.volteo_aktywnosc import zapisz_slad
from crm.volteo_sms import STATUS_WYSLANY, data_z_info, przetworz

DOCTYPE_USTAWIEN = "Volteo SMS Ustawienia"
TIMEOUT_SEKUND = 15
TYTUL_BLEDU = "SMS powitalny"


def _http_post(url: str, dane: dict, naglowki: dict):
	"""Jedna proba, timeout 15 s; wyjatek `requests` leci do rdzenia, ktory go opisuje bez tresci."""
	odp = requests.post(url, data=dane, headers=naglowki, timeout=TIMEOUT_SEKUND)
	try:
		tresc = odp.json()
	except ValueError:
		tresc = None
	return odp.status_code, tresc


def _daty_innych_wyslanych(lead: str, mobile_no: str | None) -> list:
	"""Daty z info innych leadow z tym samym numerem i statusem Wysłany."""
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


def _zapisz_wynik(lead: str, status: str, info: str) -> None:
	frappe.db.set_value(
		"CRM Lead",
		lead,
		{"custom_sms_powitalny_status": status, "custom_sms_powitalny_info": info},
		update_modified=False,
	)


def wyslij_sms_powitalny(lead: str) -> None:
	"""Zadanie w tle: patrz docstring modulu. Nigdy nie rzuca."""
	try:
		ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
		token = frappe.utils.password.get_decrypted_password(
			DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False
		)
		dane_leada = frappe.db.get_value(
			"CRM Lead", lead, ["mobile_no", "custom_sms_powitalny_status"], as_dict=True
		)
		if not dane_leada:
			return

		wynik = przetworz(
			wlaczone=bool(cint(ustawienia.get("wlaczone"))),
			token=token,
			nadawca=ustawienia.get("nadawca") or "ProEnergy",
			tresc_surowa=ustawienia.get("tresc_powitalna") or "",
			tryb_testowy=bool(cint(ustawienia.get("tryb_testowy"))),
			mobile_no=dane_leada.mobile_no,
			status_leada=dane_leada.custom_sms_powitalny_status,
			daty_innych_wyslanych=_daty_innych_wyslanych(lead, dane_leada.mobile_no),
			teraz=now_datetime(),
			http_post=_http_post,
		)

		_zapisz_wynik(lead, wynik.status, wynik.info)
		zapisz_slad(lead, wynik.slad, doctype="CRM Lead")
		if wynik.blad_do_logu:
			frappe.log_error(title=TYTUL_BLEDU, message=f"Lead {lead}: {wynik.blad_do_logu}")
		frappe.db.commit()
	except Exception:
		# Traceback nie niesie tokenu (jest tylko lokalna zmienna, nie argument wywolania w tekscie).
		frappe.log_error(title=TYTUL_BLEDU, message=f"Lead {lead}: nieoczekiwany wyjatek\n{frappe.get_traceback()}")
