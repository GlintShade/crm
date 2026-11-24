# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Rejestracja aplikacji z kodami w oknie logowania (ops#422).

Rdzen Frappe przy pierwszym logowaniu konta objetego drugim skladnikiem wysyla
maila z linkiem do kodu QR. Tu konto w oknie rejestracji (24 h, patrz
`crm/volteo_2fa_rejestracja.py`) dostaje QR na stronie logowania zaraz po
poprawnym hasle. Sesja powstaje dopiero po kodzie, jak w rdzeniu. Po oknie
zachowanie rdzenia.
"""

import os
import time
from base64 import b32encode

import frappe
import frappe.twofactor as tf
import pyotp
from frappe import _
from frappe.utils import escape_html, get_datetime, now_datetime
from frappe.utils.password import encrypt

from crm import volteo_2fa_rejestracja as okno


def _klucz(user: str) -> str:
	return user + okno.KLUCZ_OKNA


def otworz_okno(user: str) -> None:
	tf.set_default(_klucz(user), okno.koniec_okna(time.time()))


def _zarejestrowane(user: str) -> bool:
	return bool(tf.get_default(user + "_otplogin"))


def _qr_w_tym_zadaniu(user: str) -> bool:
	"""Logowanie haslem (bez otp i bez tmp_id, wiec bez powtorki starej sesji) konta w oknie bez aplikacji."""
	req = frappe.local.request
	return bool(
		req
		and (frappe.form_dict.get("cmd") == "login" or req.path == "/api/method/login")
		and not frappe.form_dict.get("otp")
		and not frappe.form_dict.get("tmp_id")
		and tf.get_verification_method() == "OTP App"
		and okno.pokazac_qr(_zarejestrowane(user), tf.get_default(_klucz(user)), time.time())
	)


def _otpsecret_for(user):
	# Nowy sekret przy KAZDYM pokazaniu QR: kto tylko zeskanowal QR i nie wpisal kodu, nie zachowa dzialajacych kodow.
	# authenticate_for_2factor bierze sekret stad i trafia on do cache tmp_id oraz do QR.
	if _qr_w_tym_zadaniu(user):
		nowy = b32encode(os.urandom(10)).decode("utf-8")
		tf.set_default(user + "_otpsecret", encrypt(nowy))
		frappe.db.commit()
		return nowy
	return _otpsecret_for.rdzen(user)


def _verification_obj(user, token, otp_secret):
	if _qr_w_tym_zadaniu(user):
		issuer = frappe.db.get_single_value("System Settings", "otp_issuer_name")
		uri = pyotp.TOTP(otp_secret).provisioning_uri(user, issuer_name=issuer)
		return {
			"method": "OTP App",
			"setup": True,
			"qrcode": tf.get_qr_svg_code(uri).decode(),
			"issuer": issuer,
		}
	return _verification_obj.rdzen(user, token, otp_secret)


def zalozyc_podmiane() -> None:
	"""Idempotentne, wolane przy imporcie `crm.overrides.user` (jedno miejsce).

	Podmiana funkcji modulu `frappe.twofactor`: `get_verification_obj` jest wolane
	wewnatrz `LoginManager` przy `cmd=login`, przed rozdzialem metod whitelist,
	wiec `override_whitelisted_methods` tu nie dziala, a hook `before_request` jest za pozno
	dla pierwszego logowania w swiezym procesie. Poza oknem wola oryginal.
	"""
	if getattr(tf.get_verification_obj, "_volteo_okno", False):
		return
	_otpsecret_for.rdzen = tf.get_otpsecret_for_
	tf.get_otpsecret_for_ = _otpsecret_for
	_verification_obj.rdzen = tf.get_verification_obj
	_verification_obj._volteo_okno = True
	tf.get_verification_obj = _verification_obj


@frappe.whitelist(methods=["POST"])
def reset_otp_secret(user: str):
	wynik = tf.reset_otp_secret(user)
	# okno tylko gdy administrator resetuje CUDZE konto; wlasny reset to sam rdzen (skradziona sesja nie wraca do "samo haslo")
	if frappe.session.user != user:
		otworz_okno(user)
	return wynik


def po_rejestracji(login_manager=None) -> None:
	"""Hook `on_session_creation`: pierwszy poprawny kod po rejestracji zamyka okno i wysyla maila."""
	user = login_manager.user
	if user == "Guest":
		return
	try:
		if not okno.wyslac_mail_po_rejestracji(_zarejestrowane(user), tf.get_default(_klucz(user))):
			return
		tf.clear_default(_klucz(user))
		email = frappe.db.get_value("User", user, "email")
		if not email:
			return
		kiedy = get_datetime(now_datetime()).strftime("%d.%m.%Y %H:%M")
		frappe.sendmail(
			recipients=email,
			subject=_("Do Twojego konta przypisano aplikację z kodami"),
			message=_(
				"<p>Do Twojego konta {0} przypisano aplikację z kodami logowania ({1}).</p>"
				"<p>Jeśli to nie Ty, natychmiast zgłoś to administratorowi.</p>"
			).format(escape_html(user), kiedy),
		)
	except Exception:
		# blad poczty nigdy nie blokuje logowania
		frappe.log_error("ops#422: mail po rejestracji aplikacji z kodami")
