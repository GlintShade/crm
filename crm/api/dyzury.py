# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Panel grafiku dyżurów SMS (ops#313): CRUD dla Ustawienia -> Dyżury SMS.

Wiersze `Volteo Dyzur SMS` (dzień tygodnia, od, do, użytkownik, aktywny) mówią,
komu `crm.api.sms_dyzur.powiadom_dyzurnego` wyśle SMS po leadzie z Facebooka.
Dostęp wyłącznie dla `Volteo Core Admin` / `System Manager` (`frappe.only_for` jako
pierwsza instrukcja każdej metody, wzorzec `crm.api.automatyzacje`). Zapisy idą przez
`doc.save()`, żeby zadziałał hook `validate_dyzur` i powstał `Version`.
"""

from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_url, now_datetime
from frappe.utils.password import get_decrypted_password

from crm.volteo_dyzury import (
	DANE_PRZYKLADOWE_DYZUR,
	dyzurni_w_chwili,
	normalizuj_numer_pl,
	waliduj_limit_dyzur,
	waliduj_tresc_dyzur,
	waliduj_wiersz,
	zbuduj_tresc_dyzur,
)
from crm.volteo_sms import numer_do_smsapi

DOCTYPE = "Volteo Dyzur SMS"
DOCTYPE_USTAWIEN = "Volteo SMS Ustawienia"
DOPUSZCZONE_ROLE_WOLAJACEGO = ["Volteo Core Admin", "System Manager"]
ROLE_DYZURNYCH = ("Volteo Backend", "Volteo Core Admin", "System Manager")


def validate_dyzur(doc: "frappe.model.document.Document", method: str | None = None) -> None:
	"""Hook `validate` na `Volteo Dyzur SMS` (działa też przy zapisie z Desk)."""
	komunikat = waliduj_wiersz(doc.get("dzien_tygodnia"), doc.get("od"), doc.get("do"))
	if komunikat:
		frappe.throw(_(komunikat))


def _godzina(wartosc: Any) -> str:
	if isinstance(wartosc, timedelta):
		sek = int(wartosc.total_seconds())
		return f"{sek // 3600:02d}:{(sek % 3600) // 60:02d}:{sek % 60:02d}"
	return str(wartosc or "")


def _wiersze() -> list[dict[str, Any]]:
	wiersze = frappe.get_all(
		DOCTYPE,
		fields=["name", "dzien_tygodnia", "od", "do", "uzytkownik", "aktywny"],
		order_by="creation asc",
		limit_page_length=500,
	)
	return [
		{**w, "od": _godzina(w["od"]), "do": _godzina(w["do"]), "aktywny": cint(w["aktywny"])}
		for w in wiersze
	]


def _uzytkownicy() -> list[dict[str, Any]]:
	nazwy = frappe.get_all(
		"Has Role",
		filters={"role": ["in", list(ROLE_DYZURNYCH)], "parenttype": "User"},
		pluck="parent",
		distinct=True,
		limit_page_length=500,
	)
	nazwy = [n for n in nazwy if n not in ("Administrator", "Guest")]
	if not nazwy:
		return []
	wiersze = frappe.get_all(
		"User",
		filters={"name": ["in", nazwy], "enabled": 1},
		fields=["name", "full_name", "mobile_no"],
		order_by="full_name asc",
		limit_page_length=500,
	)
	return [
		{
			"name": u["name"],
			"full_name": u["full_name"] or u["name"],
			"mobile_no": u["mobile_no"] or "",
			"ma_numer": bool(numer_do_smsapi(u["mobile_no"])),
		}
		for u in wiersze
	]


@frappe.whitelist()
def volteo_dyzury_lista() -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	wiersze = _wiersze()
	ustawienia = frappe.db.get_singles_dict(DOCTYPE_USTAWIEN) or {}
	token = get_decrypted_password(DOCTYPE_USTAWIEN, DOCTYPE_USTAWIEN, "token_api", raise_exception=False)
	limit_surowy = ustawienia.get("limit_dzienny_dyzur")
	return {
		"wiersze": wiersze,
		"uzytkownicy": _uzytkownicy(),
		"dyzur_wlaczone": cint(ustawienia.get("dyzur_wlaczone")),
		"tresc_dyzur": ustawienia.get("tresc_dyzur") or "",
		"limit_dzienny_dyzur": cint(limit_surowy) if limit_surowy not in (None, "") else 0,
		"nadawca": ustawienia.get("nadawca") or "",
		"tryb_testowy": cint(ustawienia.get("tryb_testowy")),
		"token_ustawiony": bool(token),
		"dyzurni_teraz": dyzurni_w_chwili([w for w in wiersze if w["aktywny"]], now_datetime()),
	}


@frappe.whitelist()
def volteo_dyzury_ustawienia_zapisz(tresc_dyzur: str, limit_dzienny_dyzur: int) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	komunikat = waliduj_tresc_dyzur(tresc_dyzur) or waliduj_limit_dyzur(limit_dzienny_dyzur)
	if komunikat:
		frappe.throw(_(komunikat))
	tresc = tresc_dyzur.strip()
	limit = cint(limit_dzienny_dyzur)
	frappe.db.set_single_value(DOCTYPE_USTAWIEN, "tresc_dyzur", tresc)
	frappe.db.set_single_value(DOCTYPE_USTAWIEN, "limit_dzienny_dyzur", limit)
	return {"tresc_dyzur": tresc, "limit_dzienny_dyzur": limit}


@frappe.whitelist()
def volteo_dyzur_podglad_tresci(tresc_dyzur: str) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	dane = {**DANE_PRZYKLADOWE_DYZUR, "link": get_url("/crm/leads/CRM-LEAD-2026-00001")}
	tresc, ostrzezenie = zbuduj_tresc_dyzur(tresc_dyzur, dane)
	return {"tresc": tresc, "znaki": len(tresc), "ostrzezenie": ostrzezenie}


@frappe.whitelist()
def volteo_dyzur_zapisz(
	name: str | None,
	dzien_tygodnia: str,
	od: str,
	do: str,
	uzytkownik: str,
	aktywny: int = 1,
) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	if not frappe.db.exists("User", uzytkownik):
		frappe.throw(_("Nie ma takiego użytkownika."))
	dane = {
		"dzien_tygodnia": dzien_tygodnia,
		"od": od,
		"do": do,
		"uzytkownik": uzytkownik,
		"aktywny": 1 if cint(aktywny) else 0,
	}
	if name:
		doc = frappe.get_doc(DOCTYPE, name)
		doc.update(dane)
	else:
		doc = frappe.get_doc({"doctype": DOCTYPE, **dane})
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def volteo_dyzur_usun(name: str) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	frappe.delete_doc(DOCTYPE, name)
	return {"name": name}


@frappe.whitelist()
def volteo_dyzury_przelacznik(dyzur_wlaczone: int) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	wartosc = 1 if cint(dyzur_wlaczone) else 0
	frappe.db.set_single_value(DOCTYPE_USTAWIEN, "dyzur_wlaczone", wartosc)
	return {"dyzur_wlaczone": wartosc}


@frappe.whitelist()
def volteo_dyzur_telefon_zapisz(uzytkownik: str, mobile_no: str) -> dict[str, Any]:
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	if not frappe.has_permission("User", "write", uzytkownik):
		frappe.throw(_("Brak uprawnień do edycji tego użytkownika."), frappe.PermissionError)
	surowy = (mobile_no or "").strip()
	if surowy:
		numer = normalizuj_numer_pl(surowy)
		if not numer:
			frappe.throw(
				_(
					"Numer telefonu musi mieć 9 cyfr (komórkowy w Polsce), np. 500 100 200 albo +48 500 100 200."
				)
			)
		surowy = numer
	frappe.db.set_value("User", uzytkownik, "mobile_no", surowy)
	return {"uzytkownik": uzytkownik, "mobile_no": surowy, "ma_numer": bool(surowy)}
