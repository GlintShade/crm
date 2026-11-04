# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""SMS do zaproszonego użytkownika CRM: zadanie w tle.

`zakolejkuj(zaproszenie)` woła `CRMInvitation.invite_via_email` zaraz po wysłaniu maila
z zaproszeniem (także przy ponownym wysłaniu, bo resend tworzy nowy rekord). Zadanie
`wyslij_sms_zaproszenia` rusza po commicie, w kolejce "short". Nie jest metodą
whitelisted: woła ją tylko worker po ścieżce kropkowej.

Warunki wysyłki: zaproszenie nadal `Pending`, ma numer telefonu, przełącznik
`zaproszenie_wlaczone` w `Volteo SMS Ustawienia` nie jest jawnie wyłączony (brak pola
oznacza włączony, patrz `crm.volteo_sms_zaproszenie.czy_kanal_wlaczony`). Token,
nadawca i tryb testowy są wspólne z SMS powitalnym i dyżurowym.

Wynik ląduje w komentarzu na `CRM Invitation` (widoczny w Desk), a błąd także w Error
Log. Ani komentarz, ani log nie niosą numeru telefonu ani tokenu. Funkcja łapie każdy
wyjątek i nigdy nie rzuca: SMS jest dodatkiem do maila i nie może go zablokować.
"""

import frappe
from frappe.utils.password import get_decrypted_password

from crm.api.sms_dyzur import wyslij_sms_do_numeru
from crm.api.sms_powitalny import DOCTYPE_USTAWIEN
from crm.volteo_sms_zaproszenie import czy_kanal_wlaczony, numer_zaproszonego, zbuduj_tresc_zaproszenia

DOCTYPE_ZAPROSZENIA = "CRM Invitation"
TYTUL_BLEDU = "SMS zaproszenia"


def _notatka(zaproszenie: str, tekst: str) -> None:
	try:
		frappe.get_doc(DOCTYPE_ZAPROSZENIA, zaproszenie).add_comment("Info", tekst)
	except Exception:
		frappe.log_error(title=TYTUL_BLEDU, message=f"{zaproszenie}: nie udało się zapisać komentarza")


def _blad(zaproszenie: str, powod: str) -> None:
	_notatka(zaproszenie, f"SMS o zaproszeniu nie został wysłany: {powod}")
	frappe.log_error(title=TYTUL_BLEDU, message=f"{zaproszenie}: {powod}")


def wyslij_sms_zaproszenia(zaproszenie: str) -> None:
	try:
		ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
		if not czy_kanal_wlaczony(ustawienia):
			return

		dane = frappe.db.get_value(
			DOCTYPE_ZAPROSZENIA, zaproszenie, ["email", "mobile_no", "status"], as_dict=True
		)
		if not dane or dane.status != "Pending" or not (dane.mobile_no or "").strip():
			return

		numer = numer_zaproszonego(dane.mobile_no)
		if not numer:
			_blad(zaproszenie, "numer telefonu nie jest poprawnym polskim numerem komórkowym.")
			return

		token = get_decrypted_password(DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False)
		if not token:
			_blad(zaproszenie, "brak tokenu SMSAPI w Volteo SMS Ustawienia.")
			return

		ok, powod, tryb_testowy = wyslij_sms_do_numeru(
			numer, zbuduj_tresc_zaproszenia(dane.email), ustawienia, token
		)
		if not ok:
			_blad(zaproszenie, powod)
			return
		_notatka(
			zaproszenie,
			"SMS o zaproszeniu: tryb testowy SMSAPI, nic nie wyszło do odbiorcy."
			if tryb_testowy
			else "SMS o zaproszeniu wysłany.",
		)
	except Exception:
		frappe.log_error(title=TYTUL_BLEDU, message=f"{zaproszenie}\n{frappe.get_traceback()}")


def zakolejkuj(zaproszenie: str) -> None:
	"""Kolejkuje SMS po commicie zaproszenia (wzorzec `crm.api.leady_webhook._zakolejkuj_sms_powitalny`).

	Własny callback `after_commit` z try/except zamiast `enqueue_after_commit=True`: błąd
	Redis przy kolejkowaniu nie może wywrócić już zapisanego zaproszenia ani maila.
	"""

	def _enqueue() -> None:
		try:
			frappe.enqueue(
				"crm.api.sms_zaproszenie.wyslij_sms_zaproszenia", queue="short", zaproszenie=zaproszenie
			)
		except Exception:
			frappe.log_error(
				title=TYTUL_BLEDU,
				message=f"{zaproszenie}: nie udało się zakolejkować\n{frappe.get_traceback()}",
			)

	try:
		frappe.db.after_commit.add(_enqueue)
	except Exception:
		frappe.log_error(
			title=TYTUL_BLEDU,
			message=f"{zaproszenie}: nie udało się zarejestrować callbacku\n{frappe.get_traceback()}",
		)
