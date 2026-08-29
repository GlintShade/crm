# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Regression coverage for ops#33: `autenti_send_umowa`/`autenti_send_kredyt`
are STATE-CHANGING actions -- they dispatch a legally binding e-signature
request to the customer's e-mail and flip the document's `autenti_status` to
"Wysyłanie" -- but were gated with `_sprawdz_dostep_do_szansy(deal, "read")`
instead of `"write"`. Any user who could merely READ a deal (e.g. a hierarchy
lead reading a subordinate's deal) could therefore send that customer's
contract for signature. Fixed by gating both send endpoints on `"write"`; the
read-gated status endpoints (`autenti_umowa_status`/`autenti_kredyt_status`)
are unchanged on purpose -- reading status does not mutate anything.

Permission fixture design: rather than reusing the real `Volteo D2D Sales`/
`Volteo Backend`/`Volteo Core Admin` roles (whose CRM Deal DocPerm grants are
applied by `ops/crm-setup.py` on this project's real sites and would give
`write=1` regardless of what this test tries to isolate), this suite defines
two throwaway roles with an explicit, opposite `read`/`write` DocPerm split on
`CRM Deal`, and makes the test user the deal's owner so the org-hierarchy
`has_permission` hook (`crm.permissions.org_hierarchy.has_deal_permission`,
which does not itself distinguish `read` from `write` -- see
`crm/permissions/test_org_hierarchy.py`) passes uniformly for both ptypes.
That isolates the read/write asymmetry to exactly the DocPerm bits this test
controls. `_sprawdz_role()` (the unrelated KALKULATOR_ROLE gate shared with
the PV/CP calculators) is mocked out so it can't mask the gate under test.
"""

from unittest.mock import patch

import frappe
from frappe.permissions import add_permission, update_permission_property

from crm.integrations.autenti.api import autenti_send_kredyt, autenti_send_umowa
from crm.tests import CRMTestCase as FrappeTestCase

READ_ONLY_ROLE = "Test Deal Read Only (ops#33)"
READ_WRITE_ROLE = "Test Deal Read Write (ops#33)"
TEST_ROLES = (READ_ONLY_ROLE, READ_WRITE_ROLE)
TEST_USERS = ("readonly@autenti33.test", "readwrite@autenti33.test")


@patch("crm.integrations.autenti.api._sprawdz_role")
class TestAutentiSendPermissionGate(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._roles_created = [ensure_role(role) for role in TEST_ROLES]
		grant_deal_permission(READ_ONLY_ROLE, read=1, write=0)
		grant_deal_permission(READ_WRITE_ROLE, read=1, write=1)
		make_user("readonly@autenti33.test", roles=[READ_ONLY_ROLE])
		make_user("readwrite@autenti33.test", roles=[READ_WRITE_ROLE])
		frappe.db.commit()  # nosemgrep: fixtures must persist across committing after_insert hooks

	@classmethod
	def tearDownClass(cls):
		delete_test_documents()
		for email in TEST_USERS:
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		for role, created in zip(TEST_ROLES, cls._roles_created, strict=True):
			frappe.db.delete("Custom DocPerm", {"role": role, "parent": "CRM Deal"})
			if created:
				frappe.delete_doc("Role", role, force=True, ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: persist teardown cleanup of committed fixtures
		super().tearDownClass()

	def tearDown(self):
		frappe.set_user("Administrator")
		delete_test_documents()
		frappe.db.commit()  # nosemgrep: persist per-test cleanup of committed fixtures

	def test_read_only_user_cannot_send_umowa(self, _mock_sprawdz_role):
		deal = make_deal("readonly@autenti33.test")
		try:
			frappe.set_user("readonly@autenti33.test")
			self.assertRaises(frappe.PermissionError, autenti_send_umowa, deal.name)
		finally:
			frappe.set_user("Administrator")

		# The permission gate must fire before _wyslij_dokument touches anything --
		# no Volteo Umowa row (and therefore no "Wysyłanie" status) may exist.
		self.assertFalse(frappe.db.exists("Volteo Umowa", deal.name))

	def test_read_only_user_cannot_send_kredyt(self, _mock_sprawdz_role):
		deal = make_deal("readonly@autenti33.test")
		try:
			frappe.set_user("readonly@autenti33.test")
			self.assertRaises(frappe.PermissionError, autenti_send_kredyt, deal.name)
		finally:
			frappe.set_user("Administrator")

		self.assertFalse(frappe.db.exists("Volteo Kredyt", deal.name))

	def test_write_access_user_clears_permission_gate_for_umowa(self, _mock_sprawdz_role):
		# This only proves the deal-access gate itself was cleared -- it does not
		# exercise a real send. _wyslij_dokument fails next, for an unrelated
		# reason (no Volteo Umowa record for this fresh deal), which is expected
		# and must NOT be a PermissionError. Autenti send is production-credentialed
		# and legally binding, so this test never reaches AutentiClient.
		deal = make_deal("readwrite@autenti33.test")
		try:
			frappe.set_user("readwrite@autenti33.test")
			try:
				autenti_send_umowa(deal.name)
			except frappe.PermissionError:
				self.fail(
					"write-access user was blocked by the deal-access permission gate "
					"-- expected to pass it and fail later for an unrelated reason"
				)
			except Exception:
				pass  # expected: fails inside _wyslij_dokument, not at the gate
			else:
				self.fail("expected autenti_send_umowa to fail for a deal with no Volteo Umowa record")
		finally:
			frappe.set_user("Administrator")

	def test_write_access_user_clears_permission_gate_for_kredyt(self, _mock_sprawdz_role):
		deal = make_deal("readwrite@autenti33.test")
		try:
			frappe.set_user("readwrite@autenti33.test")
			try:
				autenti_send_kredyt(deal.name)
			except frappe.PermissionError:
				self.fail(
					"write-access user was blocked by the deal-access permission gate "
					"-- expected to pass it and fail later for an unrelated reason"
				)
			except Exception:
				pass  # expected: fails at _sprawdz_rodzaj_oze or _wyslij_dokument, not the gate
			else:
				self.fail("expected autenti_send_kredyt to fail for a deal with no Volteo Kredyt record")
		finally:
			frappe.set_user("Administrator")


def delete_test_documents():
	"""Remove deals created by the test users."""
	frappe.db.delete("CRM Deal", {"deal_owner": ("in", TEST_USERS)})


def ensure_role(role_name: str) -> bool:
	if frappe.db.exists("Role", role_name):
		return False
	frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
		ignore_permissions=True
	)
	return True


def grant_deal_permission(role: str, *, read: int, write: int) -> None:
	"""Sets an explicit, isolated CRM Deal DocPerm (permlevel 0) for a throwaway
	test role -- deliberately not reusing Volteo D2D Sales/Backend/Core Admin,
	whose real CRM Deal grants (from ops/crm-setup.py) would make read/write
	inseparable on this project's actual sites. See module docstring."""
	add_permission("CRM Deal", role, 0)
	update_permission_property("CRM Deal", role, 0, "read", read)
	update_permission_property("CRM Deal", role, 0, "write", write)


def make_user(email, roles=None):
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)
	u = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
		}
	).insert(ignore_permissions=True)
	for role in roles or []:
		u.add_roles(role)
	return u


def make_deal(owner_email):
	"""Creates a CRM Deal owned by `owner_email`. Ownership is what satisfies the
	org-hierarchy `has_permission` hook uniformly for both `read` and `write`
	(see module docstring) so the only remaining variable is this test's own
	DocPerm split."""
	doc = frappe.get_doc(
		{"doctype": "CRM Deal", "deal_owner": owner_email, "organization": "Test Org (ops#33)"}
	)
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	return doc.insert(ignore_permissions=True)
