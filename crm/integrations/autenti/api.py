import frappe
from frappe import _

from crm.integrations.autenti.client import AutentiClient


@frappe.whitelist()
def autenti_is_enabled() -> bool:
	"""Check if Autenti integration is enabled."""
	return bool(frappe.db.get_single_value("Volteo Autenti Settings", "enabled"))


@frappe.whitelist()
def autenti_send_oferta(deal_name: str) -> dict:
	"""
	Create a Volteo Oferta, render its PDF, and enqueue the Autenti send job.
	"""
	if not frappe.has_permission("CRM Deal", "read", deal_name):
		frappe.throw(_("Brak uprawnień do tej transakcji"), frappe.PermissionError)

	deal = frappe.get_doc("CRM Deal", deal_name)

	primary_row = next((row for row in deal.contacts if row.is_primary), None)
	if not primary_row:
		frappe.throw(_("Transakcja nie ma głównego kontaktu"))

	contact = frappe.get_doc("Contact", primary_row.contact)
	first_name = contact.first_name or ""
	last_name = contact.last_name or ""
	email = contact.email_id or primary_row.email

	if not email:
		frappe.throw(_("Klient nie ma adresu email"))

	oferta = frappe.get_doc(
		{
			"doctype": "Volteo Oferta",
			"deal": deal_name,
			"status": "Wysłana do podpisu",
			"autenti_status": "Wysyłanie",
			"signer_name": f"{first_name} {last_name}".strip(),
			"signer_email": email,
			"sent_by": frappe.session.user,
		}
	)
	oferta.insert(ignore_permissions=True)
	frappe.db.commit()

	pdf_bytes = frappe.get_print("Volteo Oferta", oferta.name, print_format="Volteo Oferta PDF", as_pdf=True)

	frappe.enqueue(
		"crm.integrations.autenti.api._autenti_send_job",
		oferta_name=oferta.name,
		pdf_bytes=pdf_bytes,
		queue="default",
		timeout=120,
	)

	return {"oferta": oferta.name, "status": "Wysyłanie"}


def _autenti_send_job(oferta_name: str, pdf_bytes: bytes) -> None:
	"""Background job: talk to Autenti to create + send the document process. Not whitelisted."""
	oferta = frappe.get_doc("Volteo Oferta", oferta_name)
	try:
		client = AutentiClient()
		doc_id = client.create_document_process(title=oferta.name)

		first_name, _sep, last_name = (oferta.signer_name or "").partition(" ")
		client.add_party(
			doc_id,
			first_name=first_name or oferta.signer_name,
			last_name=last_name,
			email=oferta.signer_email,
		)
		client.upload_file(doc_id, filename=f"{oferta.name}.pdf", pdf_bytes=pdf_bytes)
		client.send(doc_id)

		oferta.autenti_status = "Wysłana"
		oferta.autenti_document_id = doc_id
		oferta.sent_at = frappe.utils.now_datetime()
		oferta.error_message = None
	except Exception as exc:
		frappe.log_error(
			title="Autenti send failed",
			message=f"Oferta: {oferta_name}\nError: {frappe.get_traceback()}",
		)
		oferta.autenti_status = "Błąd"
		oferta.error_message = str(exc)
	finally:
		oferta.save(ignore_permissions=True)
		frappe.db.commit()


@frappe.whitelist()
def autenti_get_ofertas(deal_name: str) -> list:
	"""Return all Volteo Oferta records for a deal with their Autenti status."""
	if not frappe.has_permission("CRM Deal", "read", deal_name):
		frappe.throw(_("Brak uprawnień do tej transakcji"), frappe.PermissionError)

	return frappe.get_all(
		"Volteo Oferta",
		filters={"deal": deal_name},
		fields=[
			"name",
			"autenti_status",
			"signer_name",
			"signer_email",
			"sent_at",
			"signed_at",
			"error_message",
			"autenti_document_id",
		],
		order_by="creation desc",
	)


@frappe.whitelist()
def autenti_resend_oferta(oferta_name: str) -> dict:
	"""Resend an oferta that failed or was rejected/expired."""
	oferta = frappe.get_doc("Volteo Oferta", oferta_name)

	if not frappe.has_permission("CRM Deal", "read", oferta.deal):
		frappe.throw(_("Brak uprawnień do tej transakcji"), frappe.PermissionError)

	if oferta.autenti_status not in ("Błąd", "Odrzucona", "Wygasła"):
		frappe.throw(_("Tej oferty nie można wysłać ponownie w obecnym statusie"))

	pdf_bytes = frappe.get_print("Volteo Oferta", oferta.name, print_format="Volteo Oferta PDF", as_pdf=True)

	oferta.autenti_status = "Wysyłanie"
	oferta.error_message = None
	oferta.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.enqueue(
		"crm.integrations.autenti.api._autenti_send_job",
		oferta_name=oferta.name,
		pdf_bytes=pdf_bytes,
		queue="default",
		timeout=120,
	)

	return {"oferta": oferta.name, "status": "Wysyłanie"}


def poll_autenti_status() -> None:
	"""Scheduled job (every 10 min, see hooks.py): check status of all 'Wysłana' ofertas via Autenti API."""
	STATUS_MAP = {
		"COMPLETED": "Podpisana",
		"REJECTED": "Odrzucona",
		"EXPIRED": "Wygasła",
		"WITHDRAWN": "Wycofana",
	}

	ofertas = frappe.get_all(
		"Volteo Oferta",
		filters={"autenti_status": "Wysłana", "autenti_document_id": ["is", "set"]},
		fields=["name", "autenti_document_id"],
	)
	if not ofertas:
		return

	client = AutentiClient()
	for row in ofertas:
		try:
			remote = client.get_status(row.autenti_document_id)
			remote_status = remote.get("status")
			new_status = STATUS_MAP.get(remote_status)
			if not new_status:
				continue

			oferta = frappe.get_doc("Volteo Oferta", row.name)
			oferta.autenti_status = new_status
			if new_status == "Podpisana":
				oferta.signed_at = frappe.utils.now_datetime()
			oferta.save(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			frappe.log_error(
				title="Autenti status poll failed",
				message=f"Oferta: {row.name}\nError: {frappe.get_traceback()}",
			)
			frappe.db.commit()
