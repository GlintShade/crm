"""Whitelisted API integracji Autenti dla podpisu elektronicznego UMOWY (`Volteo Umowa`).

`Volteo Umowa` jest 1:1 z `CRM Deal` (`autoname: field:deal`), więc nazwa
dokumentu `Volteo Umowa` jest tożsama z nazwą szansy — `deal` i `umowa_name`
poniżej to zawsze ten sam string, ale sygnatury funkcji trzymają je osobno dla
czytelności i zgodności z odpowiednikiem tego kodu dla `Volteo Oferta`.

Wysyłka do podpisu wysyła DOKŁADNIE te bajty PDF-u, które rep już wygenerował
i przejrzał przez `volteo_umowa_pdf` (`crm/api/umowa.py`) — NIGDY świeżo
wyrenderowane w tle. Klient musi podpisać to samo, co przedstawiciel widział.

Statusy zapisujemy przez `frappe.db.set_value`, nie przez `doc.save()` — żeby
odpytywanie w tle (`poll_autenti_status`) i wysyłka nigdy nie ścigały się
z równoległym zapisem formularza umowy przez przedstawiciela w przeglądarce.
"""

from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from crm.api.umowa import (
	DOCTYPE,
	_dane_kontaktu,
	_pobierz_umowe,
	_podstawowy_kontakt,
	_sprawdz_dostep_do_szansy,
	_sprawdz_role,
)
from crm.integrations.autenti import logika
from crm.integrations.autenti.client import AutentiClient


def _autenti_ustawienia() -> dict[str, Any]:
	"""Odczyt Single `Volteo Autenti Settings` przez `get_singles_dict`.

	`get_single_value` kłamie o nieustawionym polu (zwraca 0/"" zamiast None dla
	Single, który nigdy nie był zapisany) — dlatego tu świadomie NIE jest używany.
	"""
	return frappe.db.get_singles_dict("Volteo Autenti Settings") or {}


def _wlaczone() -> bool:
	return bool(_autenti_ustawienia().get("enabled"))


def _pdf_istnieje(deal: str) -> bool:
	"""Czy istnieje wygenerowany PDF umowy (niepodpisanej) tej szansy — dokładnie ten plik,
	który `volteo_umowa_pdf` zapisuje pod nazwą z `logika.nazwa_pliku_umowy`."""
	return bool(
		frappe.db.exists(
			"File",
			{
				"attached_to_doctype": "CRM Deal",
				"attached_to_name": deal,
				"file_name": logika.nazwa_pliku_umowy(deal),
			},
		)
	)


def _pdf_umowy_plik(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca rekord `File` PDF-u umowy (niepodpisanej) tej szansy, albo `None`, gdy go brak."""
	nazwy = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"file_name": logika.nazwa_pliku_umowy(deal),
		},
		pluck="name",
		limit=1,
	)
	if not nazwy:
		return None
	return frappe.get_doc("File", nazwy[0])


def _identyfikacja_podpisujacego(deal_doc: "frappe.model.document.Document") -> dict[str, Any] | None:
	"""Dane podstawowego kontaktu szansy do podpisu Autenti: imię, nazwisko, pełne imię
	i nazwisko, e-mail. Używa dokładnie tych samych helperów co `volteo_umowa_pdf`
	(`_podstawowy_kontakt` + `_dane_kontaktu`), żeby podpisujący na dokumencie Autenti
	nigdy nie mógł się rozjechać z klientem widocznym na samej umowie.

	Zwraca `None` TYLKO gdy szansa nie ma podstawowego kontaktu — brak e-maila jest
	dozwolonym stanem do wyświetlenia (podglądu w `autenti_umowa_status`), blokuje
	dopiero samą wysyłkę (`autenti_send_umowa` sprawdza `email` osobno).
	"""
	kontakt = _podstawowy_kontakt(deal_doc)
	if not kontakt:
		return None

	# `_dane_kontaktu` zwraca "" (nigdy None) dla brakujących pól — to poprawne dla
	# `prefill` formularza, ale kontrakt tej funkcji to `str | None`, więc email jest
	# tu jawnie sprowadzany do None, gdy pusty.
	dane = _dane_kontaktu(kontakt)
	first_name = (dane.get("first_name") or "").strip()
	last_name = (dane.get("last_name") or "").strip()
	full_name = f"{first_name} {last_name}".strip()
	email = dane.get("email") or None

	return {"first_name": first_name, "last_name": last_name, "full_name": full_name, "email": email}


@frappe.whitelist()
def autenti_is_enabled() -> dict[str, Any]:
	"""Tani, bezstanowy check widoczności funkcji podpisu w UI. Bez gate'u dostępu do
	szansy — to globalny stan integracji, nie dane konkretnej umowy."""
	ustawienia = _autenti_ustawienia()
	return {"enabled": bool(ustawienia.get("enabled")), "environment": ustawienia.get("environment")}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def autenti_umowa_status(deal: str) -> dict[str, Any]:
	"""Zwraca pełny stan podpisu Autenti dla umowy tej szansy. Obsługuje zarówno
	pierwsze wczytanie zakładki, jak i odpytywanie co 30 s przez frontend — to
	jeden, tani endpoint, żeby te dwa przypadki nigdy się nie rozjechały."""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	ustawienia = _autenti_ustawienia()
	if not ustawienia.get("enabled"):
		return {"enabled": False}

	umowa_doc = _pobierz_umowe(deal)
	deal_doc = frappe.get_doc("CRM Deal", deal)
	identyfikacja = _identyfikacja_podpisujacego(deal_doc)

	return {
		"enabled": True,
		"environment": ustawienia.get("environment"),
		"umowa_exists": umowa_doc is not None,
		"pdf_exists": _pdf_istnieje(deal),
		"autenti_status": umowa_doc.get("autenti_status") if umowa_doc else None,
		"signer_name": umowa_doc.get("signer_name") if umowa_doc else None,
		"signer_email": umowa_doc.get("signer_email") if umowa_doc else None,
		"sent_at": umowa_doc.get("sent_at") if umowa_doc else None,
		"signed_at": umowa_doc.get("signed_at") if umowa_doc else None,
		"error_message": umowa_doc.get("error_message") if umowa_doc else None,
		"signed_pdf_file": umowa_doc.get("signed_pdf_file") if umowa_doc else None,
		"proposed_signer": (
			{"full_name": identyfikacja["full_name"], "email": identyfikacja["email"]}
			if identyfikacja
			else None
		),
	}


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def autenti_send_umowa(deal: str) -> dict[str, Any]:
	"""Wysyła PDF umowy tej szansy do podpisu przez Autenti (asynchronicznie —
	kolejkuje `_autenti_send_umowa_job` i wraca natychmiast)."""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	if not _wlaczone():
		frappe.throw(_("Integracja Autenti jest wyłączona."))

	umowa_doc = _pobierz_umowe(deal)
	if umowa_doc is None:
		frappe.throw(_("Najpierw wygeneruj umowę dla tej szansy sprzedaży."))

	if not _pdf_istnieje(deal):
		frappe.throw(_("Najpierw wygeneruj PDF umowy."))

	if not logika.mozna_wyslac(umowa_doc.get("autenti_status")):
		frappe.throw(_("Umowa jest już w trakcie podpisywania lub podpisana."))

	deal_doc = frappe.get_doc("CRM Deal", deal)
	podpisujacy = _identyfikacja_podpisujacego(deal_doc)
	if not podpisujacy or not podpisujacy["email"]:
		frappe.throw(_("Kontakt szansy nie ma adresu e-mail — uzupełnij go w CRM."))

	# `frappe.db.set_value` zamiast `doc.save()` — nie ryzykujemy ścigania się
	# z równoległym zapisem formularza umowy przez przedstawiciela w przeglądarce.
	frappe.db.set_value(
		DOCTYPE,
		deal,
		{
			"autenti_status": "Wysyłanie",
			"signer_name": podpisujacy["full_name"],
			"signer_email": podpisujacy["email"],
			"sent_by": frappe.session.user,
			"error_message": None,
		},
		update_modified=False,
	)
	frappe.db.commit()

	frappe.enqueue(
		"crm.integrations.autenti.api._autenti_send_umowa_job",
		queue="default",
		timeout=300,
		deal=deal,
	)

	return {"autenti_status": "Wysyłanie"}


def _autenti_send_umowa_job(deal: str) -> None:
	"""Zadanie w tle: pobiera zapisany PDF umowy (NIGDY świeży render — patrz docstring
	modułu) i wywołuje Autenti, żeby utworzyć proces dokumentu, dodać podpisującego,
	wgrać plik i wysłać. Nie jest whitelisted — wywoływane wyłącznie przez
	`frappe.enqueue` z `autenti_send_umowa`.
	"""
	umowa_doc = _pobierz_umowe(deal)
	if umowa_doc is None:
		# Rekord zniknął między enqueue a wykonaniem joba — nie powinno się zdarzyć
		# (formularz umowy się nie usuwa), ale nie ma gdzie zapisać stanu błędu.
		frappe.log_error(
			title="Autenti: brak Volteo Umowa w jobie wysyłki",
			message=f"Szansa: {deal}",
		)
		return

	try:
		plik = _pdf_umowy_plik(deal)
		if plik is None:
			frappe.db.set_value(
				DOCTYPE,
				deal,
				{"autenti_status": "Błąd", "error_message": "PDF umowy zniknął przed wysyłką."},
				update_modified=False,
			)
			frappe.db.commit()
			return
		pdf_bytes = plik.get_content()

		deal_doc = frappe.get_doc("CRM Deal", deal)
		podpisujacy = _identyfikacja_podpisujacego(deal_doc)
		if not podpisujacy or not podpisujacy["email"]:
			frappe.db.set_value(
				DOCTYPE,
				deal,
				{"autenti_status": "Błąd", "error_message": "Kontakt szansy nie ma adresu e-mail."},
				update_modified=False,
			)
			frappe.db.commit()
			return

		signature_type = _autenti_ustawienia().get("default_signature_type") or "BASIC"
		tytul = logika.tytul_dokumentu(podpisujacy["full_name"])

		client = AutentiClient()
		doc_id = client.create_document_process(title=tytul)
		client.add_party(
			doc_id,
			# first_name/last_name pochodzą osobno z helpera kontaktu, nigdy z rozbicia
			# pełnego imienia i nazwiska po spacji (zawodzi dla nazwisk wieloczłonowych).
			first_name=podpisujacy["first_name"] or podpisujacy["full_name"],
			last_name=podpisujacy["last_name"],
			email=podpisujacy["email"],
			signature_type=signature_type,
		)
		client.upload_file(doc_id, filename=logika.nazwa_pliku_umowy(deal), pdf_bytes=pdf_bytes)
		client.send(doc_id)

		frappe.db.set_value(
			DOCTYPE,
			deal,
			{
				"autenti_status": "Wysłana",
				"autenti_document_id": doc_id,
				"sent_at": frappe.utils.now(),
				"error_message": None,
			},
			update_modified=False,
		)
		frappe.db.commit()
	except Exception as exc:
		frappe.log_error(
			title="Autenti: wysyłka umowy nie powiodła się",
			message=f"Szansa: {deal}\n{frappe.get_traceback()}",
		)
		frappe.db.set_value(
			DOCTYPE,
			deal,
			{"autenti_status": "Błąd", "error_message": str(exc)[:500]},
			update_modified=False,
		)
		frappe.db.commit()


def _attach_signed_pdf(deal: str, umowa_name: str, doc_id: str) -> None:
	"""Pobiera podpisany PDF z Autenti i podpina go jako prywatny `File` do rekordu
	`Volteo Umowa`, zapisując jego url w `signed_pdf_file`. `deal` i `umowa_name` są
	zawsze tym samym stringiem (`Volteo Umowa` jest 1:1 z `CRM Deal`, `autoname:
	field:deal`) — trzymane osobno dla czytelności, na wzór odpowiednika dla oferty.

	Cały błąd jest łapany i logowany, nigdy nie propaguje — utrata samego załącznika
	nie może cofnąć już zapisanego przejścia statusu na „Podpisana”.
	"""
	try:
		client = AutentiClient()
		file_id = client.get_signed_file_id(doc_id)
		if not file_id:
			frappe.log_error(
				title="Autenti: brak podpisanego pliku",
				message=f"Umowa: {umowa_name}\nProces dokumentu: {doc_id}\nBrak jeszcze pliku podpisanego.",
			)
			return

		content = client.download_file_content(doc_id, file_id)

		plik = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": logika.nazwa_pliku_podpisanego(deal),
				"attached_to_doctype": DOCTYPE,
				"attached_to_name": umowa_name,
				"is_private": 1,
				"content": content,
			}
		)
		plik.insert(ignore_permissions=True)

		frappe.db.set_value(DOCTYPE, umowa_name, "signed_pdf_file", plik.file_url, update_modified=False)
		frappe.db.commit()
	except Exception:
		frappe.log_error(
			title="Autenti: pobranie podpisanego pliku nie powiodło się",
			message=f"Umowa: {umowa_name}\nProces dokumentu: {doc_id}\n{frappe.get_traceback()}",
		)
		frappe.db.commit()


def poll_autenti_status() -> None:
	"""Zadanie harmonogramu (co 10 min, patrz `hooks.py`): sprawdza status wszystkich
	umów w stanie „Wysłana” przez API Autenti i aktualizuje `Volteo Umowa`."""
	if not _wlaczone():
		return

	wiersze = frappe.get_all(
		DOCTYPE,
		filters={"autenti_status": "Wysłana", "autenti_document_id": ["is", "set"]},
		fields=["name", "autenti_document_id"],
	)
	if not wiersze:
		return

	client = AutentiClient()
	for wiersz in wiersze:
		try:
			zdalny = client.get_status(wiersz.autenti_document_id)
			zdalny_status = zdalny.get("status")
			nowy_status = logika.STATUS_MAP.get(zdalny_status)
			if not nowy_status:
				if zdalny_status in logika.PENDING_REMOTE_STATUSES:
					# Nieterminalny stan zdalny — umowa zasadnie czeka na podpis dni,
					# więc NIGDY nie logujemy tego jako błąd (zalałoby Error Log).
					continue
				frappe.log_error(
					title="Autenti: nierozpoznany status",
					message=f"Umowa: {wiersz.name}\nProces dokumentu: {wiersz.autenti_document_id}\n"
					f"Nierozpoznany zdalny status: {zdalny_status}",
				)
				continue

			aktualizacja: dict[str, Any] = {"autenti_status": nowy_status}
			if nowy_status == "Podpisana":
				aktualizacja["signed_at"] = frappe.utils.now()
			frappe.db.set_value(DOCTYPE, wiersz.name, aktualizacja, update_modified=False)
			frappe.db.commit()

			if nowy_status == "Podpisana":
				_attach_signed_pdf(wiersz.name, wiersz.name, wiersz.autenti_document_id)
		except Exception:
			frappe.log_error(
				title="Autenti: odpytanie statusu nie powiodło się",
				message=f"Umowa: {wiersz.name}\n{frappe.get_traceback()}",
			)
			frappe.db.commit()
