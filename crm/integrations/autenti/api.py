import frappe
from frappe import _

from crm.integrations.autenti.client import AutentiClient

RESEND_ELIGIBLE_STATUSES = ("Błąd", "Odrzucona", "Wygasła")
SEND_BLOCKED_STATUSES = ("Wysyłanie", "Wysłana", "Podpisana")
# Confirmed (live sandbox) non-terminal states of an Autenti document process:
# DRAFT -> PROCESSING -> <terminal>. An offer legitimately sits in PROCESSING for
# days while awaiting signature, so these must never be logged as poll errors.
# Kept separate from STATUS_MAP — they intentionally have no CRM status to map to.
PENDING_REMOTE_STATUSES = ("DRAFT", "PROCESSING")


@frappe.whitelist()
def autenti_is_enabled() -> bool:
	"""Check if Autenti integration is enabled."""
	return bool(frappe.db.get_single_value("Volteo Autenti Settings", "enabled"))


@frappe.whitelist()
def autenti_get_ofertas(deal_name: str) -> list:
	"""Return all Volteo Oferta records for a deal (sent or not), newest first."""
	if not frappe.has_permission("CRM Deal", "read", deal_name):
		frappe.throw(_("Brak uprawnień do tej transakcji"), frappe.PermissionError)

	return frappe.get_all(
		"Volteo Oferta",
		filters={"deal": deal_name},
		fields=[
			"name",
			"creation",
			"status",
			"autenti_status",
			"client_name",
			"client_email",
			"signer_name",
			"signer_email",
			"sent_at",
			"signed_at",
			"error_message",
			"autenti_document_id",
			"pdf_file",
			"signed_pdf_file",
		],
		order_by="creation desc",
	)


def _start_oferta_send(oferta_name: str) -> dict:
	"""
	Shared prep for sending/resending an existing Oferta: derive the signer from
	the Oferta's own client fields, stamp status, and enqueue the background job.
	Never mutates the caller's doc in place — always re-fetches and re-saves.
	"""
	oferta = frappe.get_doc("Volteo Oferta", oferta_name)

	if not oferta.client_email:
		frappe.throw(_("Oferta nie ma adresu email klienta"))

	oferta.signer_name = oferta.client_name
	oferta.signer_email = oferta.client_email
	oferta.sent_by = frappe.session.user
	oferta.autenti_status = "Wysyłanie"
	oferta.status = "Wysłana do podpisu"
	oferta.error_message = None
	oferta.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.enqueue(
		"crm.integrations.autenti.api._autenti_send_job",
		oferta_name=oferta.name,
		queue="default",
		timeout=120,
	)

	return {"oferta": oferta.name, "status": "Wysyłanie"}


@frappe.whitelist()
def autenti_send_oferta(oferta_name: str) -> dict:
	"""Send an existing Volteo Oferta (created by the Kalkulator) for e-signature via Autenti."""
	oferta = frappe.get_doc("Volteo Oferta", oferta_name)

	if not frappe.has_permission("CRM Deal", "read", oferta.deal):
		frappe.throw(_("Brak uprawnień do tej transakcji"), frappe.PermissionError)

	if oferta.autenti_status in SEND_BLOCKED_STATUSES:
		frappe.throw(_("Tej oferty nie można wysłać ponownie w obecnym statusie"))

	return _start_oferta_send(oferta_name)


@frappe.whitelist()
def autenti_resend_oferta(oferta_name: str) -> dict:
	"""Resend an oferta that failed or was rejected/expired."""
	oferta = frappe.get_doc("Volteo Oferta", oferta_name)

	if not frappe.has_permission("CRM Deal", "read", oferta.deal):
		frappe.throw(_("Brak uprawnień do tej transakcji"), frappe.PermissionError)

	if oferta.autenti_status not in RESEND_ELIGIBLE_STATUSES:
		frappe.throw(_("Tej oferty nie można wysłać ponownie w obecnym statusie"))

	return _start_oferta_send(oferta_name)


def _get_oferta_pdf_bytes(oferta) -> bytes:
	"""
	Return the exact PDF bytes to send to Autenti for signature.

	The stored oferta.pdf_file is preferred over a fresh frappe.get_print render:
	it is the same document the rep already reviewed and shared with the customer.
	Re-rendering at send time risks the customer signing different bytes than the
	rep saw — e.g. if the print format was edited, or any field on the offer
	changed between generation and sending. For a legally binding e-signature
	flow that silent mismatch must never happen, so DO NOT "simplify" this back
	to a plain get_print call.

	Falls back to a fresh render when there is no stored file, or the stored
	file can't be found/read (older offers predate pdf_file being populated).
	"""
	if oferta.pdf_file:
		try:
			file_names = frappe.get_all("File", filters={"file_url": oferta.pdf_file}, limit=1, pluck="name")
			if file_names:
				return frappe.get_doc("File", file_names[0]).get_content()
			frappe.log_error(
				title="Autenti stored PDF missing",
				message=f"Oferta: {oferta.name}\npdf_file: {oferta.pdf_file}\n"
				"No matching File record found; falling back to a fresh render.",
			)
		except Exception:
			frappe.log_error(
				title="Autenti stored PDF unreadable",
				message=f"Oferta: {oferta.name}\npdf_file: {oferta.pdf_file}\n"
				f"Error: {frappe.get_traceback()}\nFalling back to a fresh render.",
			)

	return frappe.get_print("Volteo Oferta", oferta.name, print_format="Volteo Oferta PDF", as_pdf=True)


def _autenti_send_job(oferta_name: str) -> None:
	"""
	Background job: obtain the Oferta's PDF (preferring the stored file over a
	fresh render — see _get_oferta_pdf_bytes) and talk to Autenti to create +
	send the document process. The PDF is fetched here, not passed through
	enqueue, so a multi-MB payload never has to be serialised into the Redis
	job queue. Not whitelisted.
	"""
	oferta = frappe.get_doc("Volteo Oferta", oferta_name)
	try:
		signature_type = (
			frappe.db.get_single_value("Volteo Autenti Settings", "default_signature_type") or "BASIC"
		)

		pdf_bytes = _get_oferta_pdf_bytes(oferta)

		# Customer-visible: this becomes the PDF filename in the customer's inbox
		# and the Autenti document title, so it must read as the selling entity
		# (ProEnergy) rather than a bare internal docname. Never swap this back.
		document_title = (
			f"Oferta ProEnergy — {oferta.client_name}"
			if oferta.client_name
			else f"Oferta ProEnergy — {oferta.name}"
		)

		client = AutentiClient()
		doc_id = client.create_document_process(title=document_title)

		first_name, _sep, last_name = (oferta.signer_name or "").partition(" ")
		client.add_party(
			doc_id,
			first_name=first_name or oferta.signer_name,
			last_name=last_name,
			email=oferta.signer_email,
			signature_type=signature_type,
		)
		client.upload_file(doc_id, filename=f"{document_title}.pdf", pdf_bytes=pdf_bytes)
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


def _attach_signed_pdf(oferta_name: str, doc_id: str) -> None:
	"""
	Fetch the signed PDF from Autenti and attach it to the Oferta as a private
	File, recording its url on signed_pdf_file. Errors are logged but never
	propagate — losing the attachment must not lose the status transition.
	"""
	try:
		client = AutentiClient()
		file_id = client.get_signed_file_id(doc_id)
		if not file_id:
			frappe.log_error(
				title="Autenti signed file missing",
				message=f"Oferta: {oferta_name}\nDocument process: {doc_id}\nNo signed file found yet.",
			)
			return

		content = client.download_file_content(doc_id, file_id)

		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{oferta_name}-podpisana.pdf",
				"attached_to_doctype": "Volteo Oferta",
				"attached_to_name": oferta_name,
				"is_private": 1,
				"content": content,
			}
		)
		file_doc.insert(ignore_permissions=True)

		oferta = frappe.get_doc("Volteo Oferta", oferta_name)
		oferta.signed_pdf_file = file_doc.file_url
		oferta.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error(
			title="Autenti signed file download failed",
			message=f"Oferta: {oferta_name}\nDocument process: {doc_id}\nError: {frappe.get_traceback()}",
		)
		frappe.db.commit()


def poll_autenti_status() -> None:
	"""Scheduled job (every 10 min, see hooks.py): check status of all 'Wysłana' ofertas via Autenti API."""
	if not frappe.db.get_single_value("Volteo Autenti Settings", "enabled"):
		return

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
				if remote_status in PENDING_REMOTE_STATUSES:
					continue
				frappe.log_error(
					title="Autenti unmapped status",
					message=f"Oferta: {row.name}\nDocument process: {row.autenti_document_id}\n"
					f"Unmapped remote status: {remote_status}",
				)
				continue

			oferta = frappe.get_doc("Volteo Oferta", row.name)
			oferta.autenti_status = new_status
			if new_status == "Podpisana":
				oferta.signed_at = frappe.utils.now_datetime()
			oferta.save(ignore_permissions=True)
			frappe.db.commit()

			if new_status == "Podpisana":
				_attach_signed_pdf(row.name, row.autenti_document_id)
		except Exception:
			frappe.log_error(
				title="Autenti status poll failed",
				message=f"Oferta: {row.name}\nError: {frappe.get_traceback()}",
			)
			frappe.db.commit()
