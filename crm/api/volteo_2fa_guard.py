# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Strażnik drugiego składnika: bez wejścia przez skrzynkę mailową (ops#420).

Frappe pyta o kod z aplikacji tylko przy logowaniu hasłem. Dwie drogi przez
maila wpuszczają konto objęte drugim składnikiem BEZ kodu: logowanie linkiem
(`login_via_key`) i reset hasła linkiem (`update_password` z `key`, który
loguje po zapisie hasła). Wrappery mają sygnatury rdzenia, delegują do niego
i zamykają te dwie drogi tylko dla kont, dla których `should_run_2fa` jest
prawdą. Pozostałe konta i wyłączony drugi składnik: zachowanie rdzenia.
"""

import frappe
from frappe import _
from frappe.core.doctype.user.user import update_password as _rdzen_update_password
from frappe.twofactor import should_run_2fa
from frappe.www.login import login_via_key as _rdzen_login_via_key


def _konto_objete(user: str | None) -> bool:
	# should_run_2fa robi get_doc("User"), więc dla nieistniejącego adresu rzuca
	return bool(user) and frappe.db.exists("User", user) and bool(should_run_2fa(user))


@frappe.whitelist(allow_guest=True, methods=["GET"])
def login_via_key(key: str):
	cache_key = f"one_time_login_key:{key}"
	if _konto_objete(frappe.cache.get_value(cache_key)):
		frappe.cache.delete_value(cache_key)
		return frappe.respond_as_web_page(
			_("Logowanie linkiem wyłączone"),
			_("Dla tego konta logowanie linkiem z e-maila jest wyłączone. Zaloguj się hasłem i kodem z aplikacji."),
			http_status_code=403,
			indicator_color="red",
		)
	return _rdzen_login_via_key(key)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(
	new_password: str, logout_all_sessions: int = 0, key: str | None = None, old_password: str | None = None
):
	wynik = _rdzen_update_password(new_password, logout_all_sessions, key, old_password)
	if (
		key
		and frappe.local.response.get("http_status_code") != 410
		and frappe.session.user != "Guest"
		and _konto_objete(frappe.session.user)
	):
		# rdzeń zalogował konto po resecie: kończymy tę sesję, wejście tylko hasłem i kodem
		frappe.local.login_manager.logout()
		return "/login"
	return wynik
