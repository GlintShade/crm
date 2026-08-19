# Copyright (c) 2026, ProEnergy and contributors
# GNU GPLv3 License. See license.txt

"""
Guest-accessible landing page for the emailed invitation link.

Why this page exists
---------------------
`crm.api.accept_invitation` is deliberately POST-only + allow_guest (b47
audit hardening, see ops/crm-invitation-hardening.py — it must stay that
way: a GET-able accept endpoint was the escalation vector that hardening
closed). A plain emailed `<a href>` can only ever do a GET, so hitting the
API endpoint directly 403s for a guest. This page is the fix: a guest-GET
website page at a human link (`/zaproszenie?key=...`) that renders a button
which fires the actual POST via fetch() client-side.

Privacy
-------
Only `frappe.db.exists(...)` is used to check the key — never
`frappe.get_doc`/`frappe.get_all` with extra fields. An unauthenticated
visitor must never learn the invitee's email or any other field of a
pending invitation from this page, valid key or not; the page only ever
renders a boolean-driven Polish message.
"""

import json

import frappe

no_cache = 1


def _js_string(value):
	"""JSON-encode a value for safe embedding inside an inline <script> tag.

	Escaping "</" defends against a key value that happens to contain a
	literal "</script>" sequence prematurely closing the script block --
	moot in practice (see get_context: the script block only renders when
	`wazne` is True, which requires the key to match a real, randomly
	generated CRM Invitation.key), but cheap and worth keeping as
	defense-in-depth.
	"""
	return json.dumps(value or "").replace("</", "<\\/")


def get_context(context):
	context.no_cache = 1

	key = frappe.form_dict.get("key")
	context.klucz = key
	context.wazne = bool(key) and bool(
		frappe.db.exists("CRM Invitation", {"key": key, "status": "Pending"})
	)

	if context.wazne:
		context.klucz_json = _js_string(key)
		context.csrf_token_json = _js_string(frappe.sessions.get_csrf_token())
