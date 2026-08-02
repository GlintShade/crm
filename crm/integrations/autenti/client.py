import base64
import json

import frappe
import requests


class AutentiClient:
	"""Thin REST wrapper for Autenti Document Process API v2."""

	PRODUCTION_URL = "https://api.autenti.com/api/v2"
	SANDBOX_URL = "https://api.accept.autenti.net/api/v2"
	USER_AGENT = "VolteoCRM/1.0 (Frappe; +https://volteo.pl)"

	def __init__(self):
		"""Read credentials from Volteo Autenti Settings doctype."""
		settings = frappe.get_single("Volteo Autenti Settings")
		if not settings.enabled:
			frappe.throw("Integracja Autenti jest wyłączona")

		self.base_url = self.SANDBOX_URL if settings.environment == "Sandbox" else self.PRODUCTION_URL
		self.client_id = settings.client_id
		self.client_secret = settings.get_password("client_secret")
		self.username = settings.username
		self.password = settings.get_password("password")
		self._token = None

	def _get_token(self):
		"""OAuth2 password grant — get bearer token."""
		if self._token:
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
		)
		resp.raise_for_status()
		self._token = resp.json()["access_token"]
		return self._token

	def _headers(self):
		return {"Authorization": f"Bearer {self._get_token()}", "User-Agent": self.USER_AGENT}

	def _request(self, method, path, **kwargs):
		"""Make an authenticated API request, raising on non-2xx."""
		url = f"{self.base_url}{path}"
		resp = requests.request(method, url, headers=self._headers(), **kwargs)
		resp.raise_for_status()
		return resp

	def create_document_process(self, title: str) -> str:
		"""Create a new document process and return its id."""
		resp = self._request("POST", "/document-processes", json={"title": title})
		return resp.json()["id"]

	def add_party(
		self,
		doc_id: str,
		first_name: str,
		last_name: str,
		email: str,
		role: str = "SIGNER",
		signature_type: str = "BASIC",
	) -> None:
		"""Add a signing party to the document process."""
		body = {
			"party": {
				"firstName": first_name,
				"lastName": last_name,
				"contacts": [{"type": "CONTACT-TYPE:EMAIL", "attributes": {"email": email}}],
				"role": role,
			},
			"constraints": [
				{
					"constrainedActions": ["ACTION:SIGNATURE_APPLICATION"],
					"classifiers": ["CONSTRAINT-UNIQUE_TYPE:SIGNATURE_TYPE"],
					"attributes": {"requiredClassifiers": [f"SIGNATURE_PROVIDER-SIGNATURE_TYPE:{signature_type}"]},
				}
			],
		}
		self._request("POST", f"/document-processes/{doc_id}/parties", json=body)

	def upload_file(self, doc_id: str, filename: str, pdf_bytes: bytes) -> None:
		"""Upload the source PDF file to the document process."""
		files = {
			"fileMeta": (
				None,
				json.dumps({"fileName": filename, "filePurpose": "SOURCE_FILE", "mimeType": "application/pdf"}),
				"application/json",
			),
			"file": (filename, pdf_bytes, "application/pdf"),
		}
		self._request("POST", f"/document-processes/{doc_id}/files", files=files)

	def send(self, doc_id: str) -> None:
		"""Send the document process to its parties."""
		assertion = base64.b64encode(
			json.dumps({"classifiers": ["EVENT_CLASSIFIER-UNIQUE_TYPE:DOCUMENT_SENT"]}).encode("utf-8")
		).decode("ascii")
		headers = {**self._headers(), "X-ASSERTION": assertion}
		resp = requests.post(f"{self.base_url}/document-processes/{doc_id}/actions", headers=headers)
		resp.raise_for_status()

	def get_status(self, doc_id: str) -> dict:
		"""Return the current status of a document process."""
		resp = self._request("GET", f"/document-processes/{doc_id}")
		return resp.json()

	def get_document_files(self, doc_id: str) -> list:
		"""Return the files attached to a document process."""
		resp = self._request("GET", f"/document-processes/{doc_id}/files")
		return resp.json()

	def download_file(self, file_url: str) -> bytes:
		"""Download a file from its absolute URL."""
		resp = requests.get(file_url, headers=self._headers())
		resp.raise_for_status()
		return resp.content
