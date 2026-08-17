# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import rebuild_tree

from crm.permissions.child_visibility import (
	get_note_permission_query_conditions,
	get_task_permission_query_conditions,
	has_note_permission,
	has_task_permission,
)
from crm.permissions.delete_lockdown import block_nonadmin_delete
from crm.tests import CRMTestCase as FrappeTestCase

TEST_USERS = (
	"manager@child.test",
	"rep1@child.test",
	"rep2@child.test",
	"outsider@child.test",
	"backend@child.test",
)


class TestChildVisibility(FrappeTestCase):
	"""
	Hierarchy structure used in tests:
	  manager@child.test  (root)
	  ├── rep1@child.test
	  └── rep2@child.test
	  outsider@child.test  (not in the hierarchy)
	  backend@child.test   (Volteo Backend -- bypass role, not in the hierarchy)

	FCRM Note / CRM Task are attached via reference_doctype +
	reference_docname (confirmed against fcrm_note.json / crm_task.json).
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Volteo Backend is normally seeded by ops/crm-setup.py, but a fresh
		# test site won't have it yet.
		cls._role_created = ensure_role("Volteo Backend")

		make_user("manager@child.test", roles=["Sales Manager"])
		make_user("rep1@child.test", roles=["Sales User"])
		make_user("rep2@child.test", roles=["Sales User"])
		make_user("outsider@child.test", roles=["Sales User"])
		make_user("backend@child.test", roles=["Volteo Backend"])

		mgr = make_hierarchy_node("manager@child.test", is_group=1)
		make_hierarchy_node("rep1@child.test", reports_to=mgr.name)
		make_hierarchy_node("rep2@child.test", reports_to=mgr.name)
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
		if cls._role_created:
			frappe.delete_doc("Role", "Volteo Backend", force=True, ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: persist teardown cleanup of committed fixtures
		super().tearDownClass()

	def tearDown(self):
		delete_test_documents()
		frappe.db.commit()  # nosemgrep: persist per-test cleanup of committed fixtures

	# ------------------------------------------------------------------
	# FCRM Note -- scoped via reference to CRM Deal
	# ------------------------------------------------------------------

	def test_owner_can_read_note_on_own_deal(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertTrue(has_note_permission(note, "read", "rep1@child.test"))

	def test_manager_can_read_note_on_report_deal(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertTrue(has_note_permission(note, "read", "manager@child.test"))

	def test_sibling_cannot_read_note_on_peer_deal(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertFalse(has_note_permission(note, "read", "rep2@child.test"))

	def test_outsider_cannot_read_note_on_foreign_deal(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertFalse(has_note_permission(note, "read", "outsider@child.test"))

	def test_bypass_role_reads_note_on_any_deal(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertTrue(has_note_permission(note, "read", "backend@child.test"))

	def test_administrator_always_reads_note(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertTrue(has_note_permission(note, "read", "Administrator"))

	# ------------------------------------------------------------------
	# CRM Task -- scoped via reference to CRM Lead
	# ------------------------------------------------------------------

	def test_owner_can_read_task_on_own_lead(self):
		lead = make_lead("rep1@child.test")
		task = make_task("CRM Lead", lead.name)
		self.assertTrue(has_task_permission(task, "read", "rep1@child.test"))

	def test_manager_can_read_task_on_report_lead(self):
		lead = make_lead("rep2@child.test")
		task = make_task("CRM Lead", lead.name)
		self.assertTrue(has_task_permission(task, "read", "manager@child.test"))

	def test_outsider_cannot_read_task_on_foreign_lead(self):
		lead = make_lead("rep1@child.test")
		task = make_task("CRM Lead", lead.name)
		self.assertFalse(has_task_permission(task, "read", "outsider@child.test"))

	def test_bypass_role_reads_task_on_any_lead(self):
		lead = make_lead("rep1@child.test")
		task = make_task("CRM Lead", lead.name)
		self.assertTrue(has_task_permission(task, "read", "backend@child.test"))

	# ------------------------------------------------------------------
	# Fail-closed on a malformed / inaccessible scoped reference
	# ------------------------------------------------------------------

	def test_note_with_missing_docname_on_scoped_type_fails_closed(self):
		# reference_doctype is a scoped type but reference_docname is empty --
		# must NOT fall back to open access.
		note = make_note("CRM Deal", None)
		self.assertFalse(has_note_permission(note, "read", "rep1@child.test"))
		self.assertFalse(has_note_permission(note, "read", "outsider@child.test"))

	# ------------------------------------------------------------------
	# Fallback for a reference that is neither CRM Deal nor CRM Lead --
	# own / assigned only, matching org_hierarchy's Sales User default.
	# ------------------------------------------------------------------

	def test_owner_can_read_note_with_no_reference(self):
		note = make_note(None, None, owner="rep1@child.test")
		self.assertTrue(has_note_permission(note, "read", "rep1@child.test"))

	def test_non_owner_cannot_read_note_with_no_reference(self):
		note = make_note(None, None, owner="rep1@child.test")
		self.assertFalse(has_note_permission(note, "read", "outsider@child.test"))

	def test_assignee_can_read_task_with_unrelated_reference(self):
		# reference_doctype is neither CRM Deal nor CRM Lead: falls back to
		# own/assigned. assigned_to is a direct Link field on CRM Task.
		task = make_task("Contact", "does-not-matter", owner="rep2@child.test", assigned_to="rep1@child.test")
		self.assertTrue(has_task_permission(task, "read", "rep1@child.test"))

	def test_non_owner_non_assignee_cannot_read_task_with_unrelated_reference(self):
		task = make_task("Contact", "does-not-matter", owner="rep2@child.test", assigned_to="rep1@child.test")
		self.assertFalse(has_task_permission(task, "read", "outsider@child.test"))

	# ------------------------------------------------------------------
	# Permission query conditions
	# ------------------------------------------------------------------

	def test_query_conditions_empty_for_administrator(self):
		self.assertFalse(get_note_permission_query_conditions("Administrator"))
		self.assertFalse(get_task_permission_query_conditions("Administrator"))

	def test_query_conditions_empty_for_bypass_role(self):
		self.assertFalse(get_note_permission_query_conditions("backend@child.test"))
		self.assertFalse(get_task_permission_query_conditions("backend@child.test"))

	def test_query_conditions_non_empty_for_regular_user(self):
		self.assertTrue(get_note_permission_query_conditions("rep1@child.test"))
		self.assertTrue(get_task_permission_query_conditions("rep1@child.test"))

	# ------------------------------------------------------------------
	# Delete stays admin-only regardless of read visibility (delete_lockdown
	# is registered alongside has_note_permission / has_task_permission in
	# crm/hooks.py, and must run last / win for ptype="delete").
	# ------------------------------------------------------------------

	def test_delete_blocked_for_owner_non_admin(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertFalse(block_nonadmin_delete(note, "delete", "rep1@child.test"))

	def test_delete_allowed_for_core_admin(self):
		deal = make_deal("rep1@child.test")
		note = make_note("CRM Deal", deal.name)
		self.assertTrue(block_nonadmin_delete(note, "delete", "Administrator"))


def delete_test_documents():
	"""Remove notes/tasks/deals/leads created by the test users."""
	frappe.db.delete("FCRM Note", {"reference_docname": ("in", _deal_and_lead_names())})
	frappe.db.delete("CRM Task", {"reference_docname": ("in", _deal_and_lead_names())})
	frappe.db.delete("FCRM Note", {"owner": ("in", TEST_USERS)})
	frappe.db.delete("CRM Task", {"owner": ("in", TEST_USERS)})
	frappe.db.delete("CRM Deal", {"deal_owner": ("in", TEST_USERS)})
	frappe.db.delete("CRM Lead", {"lead_owner": ("in", TEST_USERS)})


def _deal_and_lead_names():
	names = frappe.get_all("CRM Deal", filters={"deal_owner": ("in", TEST_USERS)}, pluck="name")
	names += frappe.get_all("CRM Lead", filters={"lead_owner": ("in", TEST_USERS)}, pluck="name")
	return names or [""]


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


def make_deal(owner_email):
	doc = frappe.get_doc({"doctype": "CRM Deal", "deal_owner": owner_email, "organization": "Test Org"})
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	return doc.insert(ignore_permissions=True)


def make_lead(owner_email):
	doc = frappe.get_doc({"doctype": "CRM Lead", "lead_owner": owner_email, "first_name": "Test"})
	doc.flags.ignore_mandatory = True
	return doc.insert(ignore_permissions=True)


def make_note(reference_doctype, reference_docname, owner=None):
	doc = frappe.get_doc(
		{
			"doctype": "FCRM Note",
			"title": "Test note",
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
		}
	)
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
	if owner:
		frappe.db.set_value("FCRM Note", doc.name, "owner", owner, update_modified=False)
		doc.reload()
	return doc


def make_task(reference_doctype, reference_docname, owner=None, assigned_to=None):
	doc = frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": "Test task",
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
			"assigned_to": assigned_to,
		}
	)
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
	if owner:
		frappe.db.set_value("CRM Task", doc.name, "owner", owner, update_modified=False)
		doc.reload()
	return doc
