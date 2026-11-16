# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""ops#338: deal-scoped visibility and author/deal_owner write rule for
`Volteo Audyt` and `Volteo Audyt CP` (`crm/permissions/audyt_visibility.py`).
Bench-only (needs frappe), like test_kredyt_visibility.py; the doctypes are
created by ops scripts, so the Audyt side of the join is a dict stub."""

import frappe
from frappe.utils.nestedset import rebuild_tree

from crm.permissions.audyt_visibility import (
	czy_autor_lub_doradca,
	get_audyt_permission_query_conditions,
	has_audyt_cp_permission,
	has_audyt_permission,
)
from crm.tests import CRMTestCase as FrappeTestCase

TEST_USERS = (
	"manager@audytvis.test",
	"rep1@audytvis.test",
	"outsider@audytvis.test",
	"backend@audytvis.test",
)
BYPASS_TEST_ROLES = ("Volteo Backend",)


class TestAudytVisibility(FrappeTestCase):
	"""
	Hierarchy structure used in tests:
	  manager@audytvis.test  (root)
	  └── rep1@audytvis.test
	  outsider@audytvis.test  (not in the hierarchy, owns a stranger's deal)
	  backend@audytvis.test   (Volteo Backend, BYPASS_ROLES)
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._roles_created = [ensure_role(role) for role in BYPASS_TEST_ROLES]

		make_user("manager@audytvis.test", roles=["Sales Manager"])
		make_user("rep1@audytvis.test", roles=["Sales User"])
		make_user("outsider@audytvis.test", roles=["Sales User"])
		make_user("backend@audytvis.test", roles=["Volteo Backend"])

		mgr = make_hierarchy_node("manager@audytvis.test", is_group=1)
		make_hierarchy_node("rep1@audytvis.test", reports_to=mgr.name)
		rebuild_tree("CRM Sales Hierarchy")

		settings = frappe.get_single("FCRM Settings")
		settings.enable_sales_hierarchy = 1
		settings.save(ignore_permissions=True)

		# rep1's own deal (a colleague/backoffice-created Audyt on it must
		# be visible to rep1) and a stranger's deal entirely outside rep1's
		# subtree (a Audyt on it must stay hidden from rep1).
		cls.rep_deal = make_deal("rep1@audytvis.test")
		cls.stranger_deal = make_deal("outsider@audytvis.test")

		# Fixtures must persist across the committing after_insert hooks
		# CRM Deal triggers (assign/share), same as test_org_hierarchy.py.
		frappe.db.commit()  # nosemgrep: fixtures must persist across committing after_insert hooks

	@classmethod
	def tearDownClass(cls):
		delete_test_documents()
		for email in TEST_USERS:
			frappe.db.delete("CRM Sales Hierarchy", {"user": email})
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		for role, created in zip(BYPASS_TEST_ROLES, cls._roles_created, strict=True):
			if created:
				frappe.delete_doc("Role", role, force=True, ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: persist teardown cleanup of committed fixtures
		super().tearDownClass()

	def test_pure_rule(self):
		self.assertTrue(czy_autor_lub_doradca("a", "a", "b"))
		self.assertTrue(czy_autor_lub_doradca("b", "a", "b"))
		self.assertTrue(czy_autor_lub_doradca("a", None, "b"))
		self.assertFalse(czy_autor_lub_doradca("c", "a", "b"))
		self.assertFalse(czy_autor_lub_doradca("c", "a", None))

	def test_deal_owner_reads_and_writes_audit_authored_by_someone_else(self):
		stub = {"deal": self.rep_deal.name, "owner": "backend@audytvis.test"}
		self.assertTrue(has_audyt_permission(stub, "read", "rep1@audytvis.test"))
		self.assertTrue(has_audyt_permission(stub, "write", "rep1@audytvis.test"))
		self.assertTrue(has_audyt_cp_permission(stub, "write", "rep1@audytvis.test"))

	def test_supervisor_reads_but_does_not_write(self):
		stub = {"deal": self.rep_deal.name, "owner": "backend@audytvis.test"}
		self.assertTrue(has_audyt_permission(stub, "read", "manager@audytvis.test"))
		self.assertFalse(has_audyt_permission(stub, "write", "manager@audytvis.test"))

	def test_foreign_rep_sees_nothing(self):
		stub = {"deal": self.stranger_deal.name, "owner": "outsider@audytvis.test"}
		self.assertFalse(has_audyt_permission(stub, "read", "rep1@audytvis.test"))
		self.assertFalse(has_audyt_permission(stub, "write", "rep1@audytvis.test"))

	def test_no_deal_fails_closed(self):
		stub = {"deal": None, "owner": "rep1@audytvis.test"}
		self.assertFalse(has_audyt_permission(stub, "read", "rep1@audytvis.test"))

	def test_bypass_roles(self):
		stub = {"deal": self.stranger_deal.name, "owner": "outsider@audytvis.test"}
		self.assertTrue(has_audyt_permission(stub, "write", "backend@audytvis.test"))
		self.assertTrue(has_audyt_permission(stub, "write", "Administrator"))

	def test_query_conditions(self):
		self.assertIn(
			"`tabVolteo Audyt`.`deal` in", get_audyt_permission_query_conditions("rep1@audytvis.test")
		)
		self.assertFalse(get_audyt_permission_query_conditions("backend@audytvis.test"))
		self.assertFalse(get_audyt_permission_query_conditions("Administrator"))


def delete_test_documents():
	"""Remove deals created by the test users."""
	frappe.db.delete("CRM Deal", {"deal_owner": ("in", TEST_USERS)})


def ensure_role(role_name: str) -> bool:
	"""Create `role_name` if missing. Returns True iff this call created it,
	so the caller only tears down roles it actually created."""
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
	doc = frappe.get_doc(
		{"doctype": "CRM Deal", "deal_owner": owner_email, "organization": "Test Org Audyt Vis"}
	)
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	return doc.insert(ignore_permissions=True)
