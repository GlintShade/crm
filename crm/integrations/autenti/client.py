import base64
import json
import time
import urllib.parse

import frappe
import requests
from frappe import _

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
UPLOAD_READ_TIMEOUT = 120


class AutentiClient:
	"""Thin REST wrapper for Autenti Document Process API v2."""

	PRODUCTION_URL = "https://api.autenti.com/api/v2"
	SANDBOX_URL = "https://api.accept.autenti.net/api/v2"
	USER_AGENT = "VolteoCRM/1.0 (Frappe; +https://volteo.pl)"
	DEFAULT_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)
	UPLOAD_TIMEOUT = (CONNECT_TIMEOUT, UPLOAD_READ_TIMEOUT)

	TOKEN_FALLBACK_EXPIRY = 3600
	TOKEN_EXPIRY_MARGIN = 60

	def __init__(self):
		"""Read credentials from Volteo Autenti Settings doctype."""
		settings = frappe.get_single("Volteo Autenti Settings")
		if not settings.enabled:
			frappe.throw(_("Integracja Autenti jest wyłączona"))

		# Fail-safe direction: unset/None `environment` (e.g. a half-configured Single —
		# Frappe's DocField `default=` never seeds stored Single data, so "unset" is a
		# real, reachable state, not just a theoretical one) must resolve to SANDBOX,
		# never PRODUCTION. Production is used only on an explicit "Production" value.
		self.base_url = self.PRODUCTION_URL if settings.environment == "Production" else self.SANDBOX_URL
		self.client_id = settings.client_id
		self.client_secret = settings.get_password("client_secret")
		self.username = settings.username
		self.password = settings.get_password("password")
		self._token = None
		self._token_expires_at = 0.0

	def _get_token(self):
		"""OAuth2 password grant — get bearer token."""
		if self._token and time.monotonic() < self._token_expires_at:
			return self._token
		resp = requests.post(
			f"{self.base_url}/auth/token",
			data={
				"grant_type": "password",
				"client_id": self.client_id,
				"client_secret": self.client_secret,
				"username": self.username,
				"password": self.password,
			},
			headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": self.USER_AGENT},
			timeout=self.DEFAULT_TIMEOUT,
		)
		resp.raise_for_status()
		token_data = resp.json()
		if not isinstance(token_data, dict) or "access_token" not in token_data:
			frappe.throw(_("Autenti token request failed: expected an access_token in the response"))
		self._token = token_data["access_token"]
		try:
			expires_in = int(token_data.get("expires_in", self.TOKEN_FALLBACK_EXPIRY))
		except (TypeError, ValueError):
			expires_in = self.TOKEN_FALLBACK_EXPIRY
		self._token_expires_at = time.monotonic() + expires_in - self.TOKEN_EXPIRY_MARGIN
		return self._token

	def _headers(self):
		return {"Authorization": f"Bearer {self._get_token()}", "User-Agent": self.USER_AGENT}

	def _request(self, method, path, timeout=DEFAULT_TIMEOUT, **kwargs):
		"""Make an authenticated API request, raising on non-2xx."""
		url = f"{self.base_url}{path}"
		resp = requests.request(method, url, headers=self._headers(), timeout=timeout, **kwargs)
		resp.raise_for_status()
		return resp

	def create_document_process(self, title: str) -> str:
		"""Create a new document process and return its id."""
		resp = self._request("POST", "/document-processes", json={"title": title, "processLanguage": "pl"})
		response_data = resp.json()
		if not isinstance(response_data, dict) or "id" not in response_data:
			frappe.throw(_("Autenti create_document_process failed: expected an id in the response"))
		return response_data["id"]

	def add_party(
		self,
		doc_id: str,
		first_name: str,
		last_name: str,
		email: str,
		role: str = "SIGNER",
		signature_type: str = "BASIC",
	) -> None:
		"""Add a party (signer or viewer) to the document process.

		The `constraints` block pins the signature type for `ACTION:SIGNATURE_APPLICATION`
		and only makes sense for a party that actually signs. It is included only when
		`role == "SIGNER"` — sending it for a VIEWER risks a 400, since a viewer never
		performs that action. SIGNER behavior is byte-identical to before.
		"""
		body = {
			"party": {
				"firstName": first_name,
				"lastName": last_name,
				"contacts": [{"type": "CONTACT-TYPE:EMAIL", "attributes": {"email": email}}],
			},
			"role": role,
		}
		if role == "SIGNER":
			body["constraints"] = [
				{
					"constrainedActions": ["ACTION:SIGNATURE_APPLICATION"],
					"classifiers": ["CONSTRAINT-UNIQUE_TYPE:SIGNATURE_TYPE"],
					"attributes": {
						"requiredClassifiers": [f"SIGNATURE_PROVIDER-SIGNATURE_TYPE:{signature_type}"]
					},
				}
			]
		self._request("POST", f"/document-processes/{doc_id}/parties", json=body)

	def upload_file(self, doc_id: str, filename: str, pdf_bytes: bytes) -> None:
		"""Upload the source PDF file to the document process."""
		files = {
			"fileMeta": (
				None,
				json.dumps(
					{"filename": filename, "filePurpose": "SOURCE_FILE", "mimeType": "application/pdf"}
				),
				"application/json",
			),
			"file": (filename, pdf_bytes, "application/pdf"),
		}
		self._request("POST", f"/document-processes/{doc_id}/files", files=files, timeout=self.UPLOAD_TIMEOUT)

	def _perform_action(self, doc_id: str, event_classifier: str) -> list:
		"""
		Perform a document process action (send/withdraw) via the challenge/response
		assertion protocol: the X-ASSERTION header answers the action-selection
		challenge by naming the desired event classifier. No request body is sent.
		"""
		assertion = base64.b64encode(
			json.dumps(
				{
					"classifiers": [
						"CHALLENGE_CLASSIFIER-UNIQUE_TYPE:ACTION_SELECTION",
						"CHALLENGE_CLASSIFIER-USER_INTERACTION_TYPE:SELECTION",
					],
					"attributes": {"selectedIds": [event_classifier]},
				}
			).encode("utf-8")
		).decode("ascii")
		headers = {**self._headers(), "X-ASSERTION": assertion}
		resp = requests.post(
			f"{self.base_url}/document-processes/{doc_id}/actions",
			headers=headers,
			timeout=self.DEFAULT_TIMEOUT,
		)
		resp.raise_for_status()
		return resp.json()

	def send(self, doc_id: str) -> list:
		"""Send the document process to its parties."""
		return self._perform_action(doc_id, "EVENT_CLASSIFIER-UNIQUE_TYPE:DOCUMENT_SENT")

	def withdraw(self, doc_id: str) -> list:
		"""Withdraw the document process."""
		return self._perform_action(doc_id, "EVENT_CLASSIFIER-UNIQUE_TYPE:DOCUMENT_WITHDRAWAL")

	def get_status(self, doc_id: str) -> dict:
		"""Return the current status of a document process."""
		resp = self._request("GET", f"/document-processes/{doc_id}")
		return resp.json()

	def get_document_files(self, doc_id: str) -> list:
		"""
		Return the files attached to a document process. The API responds with
		newline-delimited JSON (Content-Type: application/stream+json), not a
		JSON array, so it must be parsed line by line.
		"""
		resp = self._request("GET", f"/document-processes/{doc_id}/files")
		return [json.loads(line) for line in resp.text.splitlines() if line.strip()]

	def get_signed_file_id(self, doc_id: str) -> str | None:
		"""
		Return the id of the signed output file for a document process, if any.
		Prefers a fully SIGNED_CONTENT_FILE, falls back to a
		PARTIALLY_SIGNED_CONTENT_FILE, then to any other non-source file that
		is verifiably a PDF (via mimeType, or the filename extension when
		mimeType is missing).

		CONTENT_ARCHIVE is a ZIP bundle, not a PDF, and must never be picked
		by the fallback — doing so would silently save a ZIP as
		"<oferta>-podpisana.pdf". This filePurpose only materialises once a
		document process reaches COMPLETED, so it is invisible during
		pre-signature testing and can't be caught by testing earlier stages.

		Returns None when no qualifying file exists yet; the caller already
		handles None by logging and leaving the status transition intact.
		"""

		def _is_pdf(file_entry: dict) -> bool:
			mime_type = file_entry.get("mimeType")
			if mime_type is not None:
				return mime_type == "application/pdf"
			filename = file_entry.get("filename") or ""
			return filename.lower().endswith(".pdf")

		files = self.get_document_files(doc_id)
		candidates = [f for f in files if f.get("filePurpose") != "SOURCE_FILE"]
		if not candidates:
			return None

		signed = next((f for f in candidates if f.get("filePurpose") == "SIGNED_CONTENT_FILE"), None)
		if signed:
			return signed.get("id")

		partially_signed = next(
			(f for f in candidates if f.get("filePurpose") == "PARTIALLY_SIGNED_CONTENT_FILE"), None
		)
		if partially_signed:
			return partially_signed.get("id")

		pdf_fallback = next((f for f in candidates if _is_pdf(f)), None)
		return pdf_fallback.get("id") if pdf_fallback else None

	def download_file_content(self, doc_id: str, file_id: str) -> bytes:
		"""
		Download a file's raw bytes by its id. File ids may contain '/'
		(e.g. "FILE-DTBS:.../DTBS"), so the id must be percent-encoded before
		being placed in the URL path.
		"""
		encoded_file_id = urllib.parse.quote(file_id, safe="")
		resp = self._request(
			"GET",
			f"/document-processes/{doc_id}/files/{encoded_file_id}/content",
			timeout=self.UPLOAD_TIMEOUT,
		)
		return resp.content
