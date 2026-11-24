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
from frappe.twofactor import get_default as get_2fa_default
from frappe.twofactor import should_run_2fa
from frappe.utils.data import sha256_hash
from frappe.www.login import login_via_key as _rdzen_login_via_key


def _konto_objete(user: str | None) -> bool:
	# should_run_2fa robi get_doc("User"), więc dla nieistniejącego adresu rzuca
	return bool(user) and frappe.db.exists("User", user) and bool(should_run_2fa(user))


def _pierwsze_haslo_konta_objetego(key: str | None) -> str | None:
	"""Konto z klucza resetu, jesli jest objete 2FA, nie ma hasla i nie ma aplikacji z kodami."""
	if not key:
		return None
	user = frappe.db.get_value("User", {"reset_password_key": sha256_hash(key)}, "name")
	if not user or not _konto_objete(user):
		return None
	from crm.api.user import has_password
	from crm.volteo_2fa_rejestracja import pierwsze_haslo_otwiera_okno

	zarejestrowane = bool(get_2fa_default(user + "_otplogin"))
	return user if pierwsze_haslo_otwiera_okno(True, has_password(user), zarejestrowane) else None


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
	pierwsze_haslo = _pierwsze_haslo_konta_objetego(key)
	wynik = _rdzen_update_password(new_password, logout_all_sessions, key, old_password)
	if pierwsze_haslo and frappe.local.response.get("http_status_code") != 410:
		# ops#422: nowe konto objete 2FA ustawilo PIERWSZE haslo: otwieramy okno rejestracji aplikacji
		from crm.api.volteo_2fa_rejestracja import otworz_okno

		otworz_okno(pierwsze_haslo)
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
