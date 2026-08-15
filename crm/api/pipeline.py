# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Warstwa frappe-owa nad `crm.volteo_pipeline` — pasek postępu rurociągu na
szansie sprzedaży, automatyczne przesuwanie statusu i dyspozytor powiadomień.

KSZTAŁT rurociągu (kolejność kroków, notatki „co dalej”) żyje wyłącznie w
`crm.volteo_pipeline` (frappe-free, testowalne bez frappe zainstalowanego
lokalnie). Ten moduł tylko odczytuje/zapisuje dokumenty `CRM Deal` i tworzy
powiadomienia — żadnej wiedzy o KOLEJNOŚCI statusów tu nie ma.

Frontend woła `volteo_pipeline_get` po PEŁNEJ, kropkowanej ścieżce
`crm.api.pipeline.volteo_pipeline_get` — gołe nazwy metod działają wyłącznie
dla Server Scriptów; skopiowanie wzorca wywołania z innej zakładki (bez
pełnej ścieżki) daje w runtime HTTP 417 mimo zielonych bramek lokalnych
(patrz `crm.api.umowa` i historia z `AudytTab.vue`).
"""

from typing import Any

import frappe
from frappe import _

from crm.volteo_pipeline import is_forward, notatka_for, pipeline_for, step_index


def _sprawdz_dostep_do_szansy(deal: str) -> None:
	"""Sprawdza istnienie szansy i uprawnienie `read` wywołującego do niej."""
	if not deal or not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Szansa sprzedaży nie istnieje."), frappe.DoesNotExistError)
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)


@frappe.whitelist()
def volteo_pipeline_get(deal: str) -> dict[str, Any]:
	"""Zwraca kształt paska rurociągu dla szansy: kroki, indeks bieżącego statusu,
	czy szansa jest POZA rurociągiem (przegrana/wygrana) i notatkę „co dalej”.

	Pusty `steps` (rodzaj umowy szansy bez rurociągu — np. nieustawiony) jest
	poprawną odpowiedzią, nie błędem: frontend ukrywa wtedy pasek zamiast go
	renderować pusty.
	"""
	_sprawdz_dostep_do_szansy(deal)

	rodzaj, status = frappe.db.get_value("CRM Deal", deal, ["custom_rodzaj_umowy", "status"])

	rurociag = pipeline_for(rodzaj)
	kroki = [{"status": nazwa, "index": indeks} for indeks, nazwa in enumerate(rurociag or ())]
	biezacy_indeks = step_index(rodzaj, status)

	poza_rurociagiem = bool(rurociag) and biezacy_indeks == -1
	typ_poza_rurociagiem = None
	if poza_rurociagiem:
		typ_statusu = frappe.db.get_value("CRM Deal Status", status, "type")
		typ_poza_rurociagiem = typ_statusu if typ_statusu in ("Lost", "Won") else None

	return {
		"rodzaj": rodzaj,
		"status": status,
		"steps": kroki,
		"current_index": biezacy_indeks,
		"off_pipeline": poza_rurociagiem,
		"off_pipeline_type": typ_poza_rurociagiem,
		"note": notatka_for(rodzaj, status),
	}


def advance_deal_status(deal: str, target_status: str, automation_key: str) -> bool:
	"""Automatycznie przesuwa status szansy do przodu w jej rurociągu, jeśli
	automatyzacja `automation_key` jest włączona i przejście jest do przodu.

	Wołane z punktów zaczepienia (generowanie PDF-u umowy, odebranie statusu
	„Podpisana” z Autenti) — NIGDY nie wolno jej pozwolić rzucić wyjątkiem:
	nieudana automatyzacja statusu nie może zepsuć operacji, która ją wywołała
	(wygenerowanie PDF-u / odpytanie Autenti). Stąd całe ciało w try/except.
	Zwraca `True`, jeśli status faktycznie został przesunięty, inaczej `False`
	(automatyzacja wyłączona/brak wiersza, przejście nie jest do przodu, albo
	dowolny inny błąd — zalogowany, nigdy niepodniesiony).
	"""
	try:
		# Fail-closed: brakujący wiersz (doctype może jeszcze nie istnieć na
		# świeżym dev-site — zakłada go dopiero skrypt ops) albo `wlaczona=0`
		# dają `None`/`0`, oba traktowane jako „nie uruchamiaj”.
		if not frappe.db.get_value("Volteo Automatyzacja", automation_key, "wlaczona"):
			return False

		doc = frappe.get_doc("CRM Deal", deal)
		if not is_forward(doc.custom_rodzaj_umowy, doc.status, target_status):
			return False

		# Celowo `doc.save()`, NIE `frappe.db.set_value` — tylko `.save()`
		# przechodzi przez `add_status_change_log` na kontrolerze `CRMDeal`,
		# więc automatyczne przejście zostaje odnotowane tak samo jak ręczne.
		doc.status = target_status
		doc.save(ignore_permissions=True)
		return True
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Volteo Pipeline: automatyzacja {automation_key} nie powiodła się")
		return False


_KANALY_STUB_DOKUMENTACJA = (
	"Scaffolding pod przyszłe kanały — nic tu jeszcze nie wysyła. E-mail czeka na "
	"własny silnik domenowy, SMS na integrację SMSAPI.pl (patrz REVISIT.md)."
)


def _wyslij_email_stub(recipient: str, deal: str, tekst_html: str) -> None:
	"""Zaślepka kanału e-mail. Integracja jeszcze nieistniejąca — patrz moduł, przypis
	`_KANALY_STUB_DOKUMENTACJA`. Świadomy no-op, nie błąd."""
	return


def _wyslij_sms_stub(recipient: str, deal: str, tekst_html: str) -> None:
	"""Zaślepka kanału SMS (SMSAPI.pl, planowane). Świadomy no-op, nie błąd —
	patrz moduł, przypis `_KANALY_STUB_DOKUMENTACJA`."""
	return


def _bell_notification(recipient: str, deal: str, tekst_html: str) -> None:
	"""Tworzy dzwoneczek `CRM Notification` dla jednego odbiorcy — wzorzec
	1:1 z `crm.fcrm.doctype.crm_notification.crm_notification.notify_user`
	i jego użyciem w `crm.api.todo.notify_assigned_user`, z tym że tu nadawcą
	jest zawsze bieżąca sesja (wołający joba/hooka), a nie właściciel dokumentu.
	Deduplikacja przez `frappe.db.exists` na tym samym zestawie wartości, żeby
	powtórne wywołanie tej samej automatyzacji (np. dwukrotny poll Autenti)
	nie zasypało odbiorcy identycznymi powiadomieniami.
	"""
	wartosci = frappe._dict(
		doctype="CRM Notification",
		from_user=frappe.session.user,
		to_user=recipient,
		type="Assignment",
		message=tekst_html,
		notification_text=tekst_html,
		notification_type_doctype="CRM Deal",
		notification_type_doc=deal,
		reference_doctype="CRM Deal",
		reference_name=deal,
	)
	if frappe.db.exists("CRM Notification", wartosci):
		return
	frappe.get_doc(wartosci).insert(ignore_permissions=True)


_KANALY = {
	"kanal_bell": _bell_notification,
	"kanal_email": _wyslij_email_stub,
	"kanal_sms": _wyslij_sms_stub,
}
"""Rejestr kanałów, klucz = nazwa flagi na `Volteo Automatyzacja`. Pluggable
scaffolding: dodanie realnego kanału e-mail/SMS to podmiana jednej wartości
w tym dict, bez zmiany `dispatch_notification`."""


def dispatch_notification(rule_key: str, deal: str, tekst_html: str) -> None:
	"""Wysyła powiadomienie o automatycznym zdarzeniu na rurociągu do odbiorców
	reguły `rule_key` (wiersz `Volteo Automatyzacja`), przez włączone kanały.

	Tak samo jak `advance_deal_status`, NIGDY nie rzuca — brak/wyłączona reguła,
	brak odbiorców i błąd pojedynczego kanału są po cichu pomijane/logowane, bo
	wołający (hook generowania PDF-u / poll Autenti) nie może zostać przerwany
	przez usterkę samego powiadomienia.
	"""
	try:
		regula = frappe.db.get_value(
			"Volteo Automatyzacja",
			rule_key,
			["wlaczona", "odbiorca_handlowiec", "kanal_bell", "kanal_email", "kanal_sms"],
			as_dict=True,
		)
		if not regula or not regula.wlaczona:
			return

		odbiorcy = set(
			frappe.get_all(
				"Volteo Automatyzacja Odbiorca",
				filters={"parent": rule_key, "parenttype": "Volteo Automatyzacja"},
				pluck="uzytkownik",
			)
		)
		if regula.odbiorca_handlowiec:
			wlasciciel = frappe.db.get_value("CRM Deal", deal, "deal_owner")
			if wlasciciel:
				odbiorcy.add(wlasciciel)

		# Bez samego wywołującego (np. handlowiec, który właśnie sam podpisał
		# akcję wyzwalającą automatyzację, nie musi dostać dzwoneczka o niej)
		# i bez pustych/`None` wpisów.
		odbiorcy = {o for o in odbiorcy if o and o != frappe.session.user}
		if not odbiorcy:
			return

		for flaga, kanal in _KANALY.items():
			if not regula.get(flaga):
				continue
			for odbiorca in odbiorcy:
				kanal(odbiorca, deal, tekst_html)
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Volteo Pipeline: dyspozytor powiadomień {rule_key} nie powiódł się")
