# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from crm.fcrm.doctype.crm_deal.api import get_deal_contacts
from crm.tests import CRMTestCase as FrappeTestCase

TEST_USERS = ("owner@dealapi.test", "outsider@dealapi.test")


class TestGetDealContacts(FrappeTestCase):
	"""
	Regression coverage for ops#31: get_deal_contacts() had no permission
	check on the requested deal, and read Contact rows with frappe.get_doc
	(which ignores permission query conditions), letting any authenticated
	user harvest client PII for any deal name.

	Requires Contact.custom_opiekun (crm/permissions/contact_visibility.py)
	and the Volteo D2D Sales role, both seeded by ops scripts on the
	project's local site rather than shipped as app fixtures -- skipped
	when either is absent (e.g. a bare upstream test site).
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._skip_reason = None
		if not frappe.get_meta("Contact").has_field("custom_opiekun"):
			cls._skip_reason = "Contact.custom_opiekun custom field not present on this site"
			return

		cls._role_created = ensure_role("Volteo D2D Sales")
		make_user("owner@dealapi.test", roles=["Volteo D2D Sales"])
		make_user("outsider@dealapi.test", roles=["Volteo D2D Sales"])
		frappe.db.commit()  # nosemgrep: fixtures must persist across committing after_insert hooks

	@classmethod
	def tearDownClass(cls):
		if not cls._skip_reason:
			delete_test_documents()
			for email in TEST_USERS:
				frappe.delete_doc("User", email, force=True, ignore_permissions=True)
			if cls._role_created:
				frappe.delete_doc("Role", "Volteo D2D Sales", force=True, ignore_permissions=True)
			frappe.db.commit()  # nosemgrep: persist teardown cleanup of committed fixtures
		super().tearDownClass()

	def setUp(self):
		if self._skip_reason:
			self.skipTest(self._skip_reason)

	def tearDown(self):
		frappe.set_user("Administrator")
		delete_test_documents()
		frappe.db.commit()  # nosemgrep: persist per-test cleanup of committed fixtures

	def test_non_owner_outside_hierarchy_cannot_read_deal_contacts(self):
		deal = make_deal("owner@dealapi.test")
		try:
			frappe.set_user("outsider@dealapi.test")
			self.assertRaises(frappe.PermissionError, get_deal_contacts, deal.name)
		finally:
			frappe.set_user("Administrator")

	def test_deal_owner_sees_scoped_contact(self):
		contact = make_contact("owner@dealapi.test")
		deal = make_deal("owner@dealapi.test", contacts=[contact.name])
		try:
			frappe.set_user("owner@dealapi.test")
			result = get_deal_contacts(deal.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(len(result), 1)
		row = result[0]
		self.assertEqual(row["name"], contact.name)
		self.assertEqual(row["full_name"], contact.full_name)
		self.assertEqual(row["email"], "test.contact@dealapi.test")
		self.assertEqual(row["mobile_no"], "500600700")
		self.assertEqual(row["is_primary"], 1)


def delete_test_documents():
	"""Remove deals/contacts created by the test users."""
	frappe.db.delete("CRM Deal", {"deal_owner": ("in", TEST_USERS)})
	frappe.db.delete("Contact", {"custom_opiekun": ("in", TEST_USERS)})


def ensure_role(role_name: str) -> bool:
	if frappe.db.exists("Role", role_name):
		return False
	frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
		ignore_permissions=True
	)
	return True


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


def make_deal(owner_email, contacts=None):
	doc = frappe.get_doc({"doctype": "CRM Deal", "deal_owner": owner_email, "organization": "Test Org"})
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	for contact_name in contacts or []:
		doc.append("contacts", {"contact": contact_name, "is_primary": 1})
	return doc.insert(ignore_permissions=True)


def make_contact(opiekun_email):
	doc = frappe.get_doc(
		{
			"doctype": "Contact",
			"custom_opiekun": opiekun_email,
			"first_name": "Test",
		}
	)
	doc.flags.ignore_mandatory = True
	# email_id/mobile_no are denormalized by Contact.validate() from these
	# child tables (set_primary_email/set_primary) -- setting the flat
	# fields directly gets overwritten with "" when the child rows are empty.
	doc.append("email_ids", {"email_id": "test.contact@dealapi.test", "is_primary": 1})
	doc.append("phone_nos", {"phone": "500600700", "is_primary_mobile_no": 1})
	return doc.insert(ignore_permissions=True)
