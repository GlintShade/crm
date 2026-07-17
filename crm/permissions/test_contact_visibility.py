# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import rebuild_tree

from crm.permissions.contact_visibility import (
	get_contact_permission_query_conditions,
	has_contact_permission,
)
from crm.tests import CRMTestCase as FrappeTestCase

TEST_USERS = ("manager@opk.test", "rep1@opk.test", "rep2@opk.test", "outsider@opk.test")


class TestContactVisibility(FrappeTestCase):
	"""
	Hierarchy structure used in tests (opiekun = custom_opiekun on Contact):
	  manager@opk.test  (root)
	  ├── rep1@opk.test
	  └── rep2@opk.test
	  outsider@opk.test  (not in the hierarchy)
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Create test users
		make_user("manager@opk.test", roles=["Sales Manager"])
		make_user("rep1@opk.test", roles=["Sales User"])
		make_user("rep2@opk.test", roles=["Sales User"])
		make_user("outsider@opk.test", roles=["Sales User"])

		# Build hierarchy
		mgr = make_hierarchy_node("manager@opk.test", is_group=1)
		make_hierarchy_node("rep1@opk.test", reports_to=mgr.name)
		make_hierarchy_node("rep2@opk.test", reports_to=mgr.name)
		rebuild_tree("CRM Sales Hierarchy")

		settings = frappe.get_single("FCRM Settings")
		settings.enable_sales_hierarchy = 1
		settings.save(ignore_permissions=True)

		frappe.db.commit()  # nosemgrep: fixtures must persist across committing hooks

	@classmethod
	def tearDownClass(cls):
		delete_test_documents()
		for email in TEST_USERS:
			frappe.db.delete("CRM Sales Hierarchy", {"user": email})
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: persist teardown cleanup of committed fixtures
		super().tearDownClass()

	def tearDown(self):
		delete_test_documents()
		frappe.db.commit()  # nosemgrep: persist per-test cleanup of committed fixtures

	# ------------------------------------------------------------------
	# Contact permissions -- opiekun-based
	# ------------------------------------------------------------------

	def test_opiekun_can_read_own_contact(self):
		contact = make_contact("rep1@opk.test")
		self.assertTrue(has_contact_permission(contact, "read", "rep1@opk.test"))

	def test_manager_can_read_direct_report_contact(self):
		contact = make_contact("rep1@opk.test")
		self.assertTrue(has_contact_permission(contact, "read", "manager@opk.test"))

	def test_manager_can_read_any_report_contact(self):
		contact = make_contact("rep2@opk.test")
		self.assertTrue(has_contact_permission(contact, "read", "manager@opk.test"))

	def test_sibling_cannot_read_peer_contact(self):
		contact = make_contact("rep1@opk.test")
		self.assertFalse(has_contact_permission(contact, "read", "rep2@opk.test"))

	def test_outsider_cannot_read_team_contact(self):
		contact = make_contact("rep1@opk.test")
		self.assertFalse(has_contact_permission(contact, "read", "outsider@opk.test"))

	def test_administrator_always_has_permission(self):
		contact = make_contact("rep1@opk.test")
		self.assertTrue(has_contact_permission(contact, "read", "Administrator"))

	def test_bypass_role_can_read_any_contact(self):
		# Volteo Backend bypasses opiekun scoping entirely
		make_user("backend@opk.test", roles=["Volteo Backend"])
		try:
			contact = make_contact("rep1@opk.test")
			self.assertTrue(has_contact_permission(contact, "read", "backend@opk.test"))
		finally:
			frappe.delete_doc("User", "backend@opk.test", force=True, ignore_permissions=True)
			frappe.db.commit()  # nosemgrep: persist cleanup of committed fixture user

	def test_sales_user_can_create_contact(self):
		new_contact = frappe.get_doc({"doctype": "Contact", "custom_opiekun": "rep1@opk.test"})
		self.assertTrue(has_contact_permission(new_contact, "create", "rep1@opk.test"))

	# ------------------------------------------------------------------
	# Assignment (ToDo) does NOT grant Contact access -- opiekun-only
	# ------------------------------------------------------------------

	def test_assignment_does_not_grant_contact_access(self):
		# Unlike Lead/Deal, Contact visibility ignores ToDo assignment.
		contact = make_contact("rep1@opk.test")
		assign_todo("Contact", contact.name, "outsider@opk.test")
		self.assertFalse(has_contact_permission(contact, "read", "outsider@opk.test"))

	# ------------------------------------------------------------------
	# Permission query conditions
	# ------------------------------------------------------------------

	def test_query_conditions_empty_for_administrator(self):
		self.assertFalse(get_contact_permission_query_conditions("Administrator"))

	def test_query_conditions_empty_for_bypass_role(self):
		make_user("backend@opk.test", roles=["Volteo Backend"])
		try:
			self.assertFalse(get_contact_permission_query_conditions("backend@opk.test"))
		finally:
			frappe.delete_doc("User", "backend@opk.test", force=True, ignore_permissions=True)
			frappe.db.commit()  # nosemgrep: persist cleanup of committed fixture user

	def test_query_conditions_non_empty_for_regular_user(self):
		self.assertTrue(get_contact_permission_query_conditions("rep1@opk.test"))

	# ------------------------------------------------------------------
	# Hierarchy disabled
	# ------------------------------------------------------------------

	def test_hierarchy_disabled_sales_user_still_restricted_to_own(self):
		settings = frappe.get_single("FCRM Settings")
		settings.enable_sales_hierarchy = 0
		settings.save(ignore_permissions=True)
		try:
			contact = make_contact("rep1@opk.test")
			# Sales User default: cannot read another user's contact even when feature is off
			self.assertFalse(has_contact_permission(contact, "read", "outsider@opk.test"))
			# Sales Manager default: sees everything when feature is off
			self.assertTrue(has_contact_permission(contact, "read", "manager@opk.test"))
		finally:
			settings.enable_sales_hierarchy = 1
			settings.save(ignore_permissions=True)


def delete_test_documents():
	"""Remove contacts/assignments created by the test users."""
	frappe.db.delete("ToDo", {"allocated_to": ("in", TEST_USERS)})
	frappe.db.delete("Contact", {"custom_opiekun": ("in", TEST_USERS)})


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


def make_hierarchy_node(user, reports_to=None, is_group=0):
	existing = frappe.db.get_value("CRM Sales Hierarchy", {"user": user}, "name")
	if existing:
		return frappe.get_doc("CRM Sales Hierarchy", existing)
	return frappe.get_doc(
		{
			"doctype": "CRM Sales Hierarchy",
			"user": user,
			"reports_to": reports_to,
			"is_group": is_group,
		}
	).insert(ignore_permissions=True)


def make_contact(opiekun_email):
	doc = frappe.get_doc(
		{"doctype": "Contact", "custom_opiekun": opiekun_email, "first_name": "Test"}
	)
	doc.flags.ignore_mandatory = True
	return doc.insert(ignore_permissions=True)


def assign_todo(doctype, docname, allocated_to, status="Open"):
	return frappe.get_doc(
		{
			"doctype": "ToDo",
			"reference_type": doctype,
			"reference_name": docname,
			"allocated_to": allocated_to,
			"status": status,
			"description": f"Test assignment to {allocated_to}",
		}
	).insert(ignore_permissions=True)
