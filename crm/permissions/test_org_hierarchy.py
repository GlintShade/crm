# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import rebuild_tree

from crm.permissions.org_hierarchy import (
	get_lead_permission_query_conditions,
	has_deal_permission,
	has_lead_permission,
	hierarchy_enabled,
)
from crm.tests import CRMTestCase as FrappeTestCase

TEST_USERS = (
	"manager@hier.test",
	"rep1@hier.test",
	"rep2@hier.test",
	"outsider@hier.test",
	"backend@hier.test",
	"backendintree@hier.test",
	"coreadmin@hier.test",
	"coreadminintree@hier.test",
	"cc@hier.test",
)

# Bypass roles under test. Created in setUpClass (guarded) and removed in
# tearDownClass so the suite is self-cleaning on a fresh site as well as one
# where ops/crm-setup.py has already seeded them.
BYPASS_TEST_ROLES = ("Volteo Backend", "Volteo Core Admin")

# Non-bypass Volteo role under test (issue #88, L01) -- created/removed the
# same guarded way as BYPASS_TEST_ROLES above.
CC_TEST_ROLE = "Volteo Call Center"


class TestOrgHierarchy(FrappeTestCase):
	"""
	Hierarchy structure used in tests:
	  manager@hier.test  (root)
	  ├── rep1@hier.test
	  ├── rep2@hier.test
	  ├── backendintree@hier.test    (Volteo Backend, leaf)
	  └── coreadminintree@hier.test  (Volteo Core Admin, leaf)
	  outsider@hier.test    (not in the hierarchy)
	  backend@hier.test     (Volteo Backend, not in the hierarchy)
	  coreadmin@hier.test   (Volteo Core Admin, not in the hierarchy)
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Volteo Backend / Volteo Core Admin are normally seeded by
		# ops/crm-setup.py, but a fresh test site won't have them yet.
		cls._roles_created = [ensure_role(role) for role in BYPASS_TEST_ROLES]
		# Volteo Call Center (issue #88, L01) -- non-bypass role, same
		# guarded create/cleanup as the bypass roles above.
		cls._cc_role_created = ensure_role(CC_TEST_ROLE)

		# custom_cc (CRM Lead) and custom_linia_leady (User) are normally
		# created by ops scripts (ops/crm-leady-call-center.py,
		# ops/crm-linia-leady.py) that run against a real site, not by any
		# fixture bundled with the app -- a fresh test site needs them
		# created here so the CC permission-query branch (guarded on
		# has_field in org_hierarchy.py) is actually exercised.
		cls._cc_field_created = ensure_custom_field("CRM Lead", "custom_cc", "Link", options="User")
		cls._linia_leady_field_created = ensure_custom_field("User", "custom_linia_leady", "Check")

		# Create test users
		make_user("manager@hier.test", roles=["Sales Manager"])
		make_user("rep1@hier.test", roles=["Sales User"])
		make_user("rep2@hier.test", roles=["Sales User"])
		make_user("outsider@hier.test", roles=["Sales User"])
		make_user("backend@hier.test", roles=["Volteo Backend"])
		make_user("backendintree@hier.test", roles=["Volteo Backend"])
		make_user("coreadmin@hier.test", roles=["Volteo Core Admin"])
		make_user("coreadminintree@hier.test", roles=["Volteo Core Admin"])
		make_user("cc@hier.test", roles=[CC_TEST_ROLE])
		# Every non-bypass test user needs the custom_linia_leady flag (issue
		# #27's gate, unchanged by issue #88 -- WORKSHOP.md: "CC musi mieć
		# flagę Leady w Ustawienia -> Użytkownicy") set explicitly: it is a
		# fresh Custom Field on this test site (see ensure_custom_field call
		# above), so every dynamically-created test user reads back
		# None/0 -- i.e. denied -- unless set here. BYPASS_ROLES users don't
		# need it (their _ma_linie_leady short-circuits on role), but setting
		# it is harmless for them too.
		for _user in TEST_USERS:
			frappe.db.set_value("User", _user, "custom_linia_leady", 1, update_modified=False)

		# Build hierarchy
		mgr = make_hierarchy_node("manager@hier.test", is_group=1)
		make_hierarchy_node("rep1@hier.test", reports_to=mgr.name)
		make_hierarchy_node("rep2@hier.test", reports_to=mgr.name)
		make_hierarchy_node("backendintree@hier.test", reports_to=mgr.name)
		make_hierarchy_node("coreadminintree@hier.test", reports_to=mgr.name)
		rebuild_tree("CRM Sales Hierarchy")

		settings = frappe.get_single("FCRM Settings")
		settings.enable_sales_hierarchy = 1
		settings.save(ignore_permissions=True)

		# Persist the fixtures as a baseline. Inserting CRM Lead/Deal commits
		# (after_insert assigns/shares the record), so per-test isolation relies
		# on explicit cleanup rather than a rollback.
		frappe.db.commit()  # nosemgrep: fixtures must persist across the committing after_insert hooks

	@classmethod
	def tearDownClass(cls):
		delete_test_documents()
		for email in TEST_USERS:
			frappe.db.delete("CRM Sales Hierarchy", {"user": email})
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		for role, created in zip(BYPASS_TEST_ROLES, cls._roles_created, strict=True):
			if created:
				frappe.delete_doc("Role", role, force=True, ignore_permissions=True)
		if cls._cc_role_created:
			frappe.delete_doc("Role", CC_TEST_ROLE, force=True, ignore_permissions=True)
		if cls._cc_field_created:
			frappe.delete_doc(
				"Custom Field", "CRM Lead-custom_cc", force=True, ignore_permissions=True
			)
		if cls._linia_leady_field_created:
			frappe.delete_doc(
				"Custom Field", "User-custom_linia_leady", force=True, ignore_permissions=True
			)
		frappe.db.commit()  # nosemgrep: persist teardown cleanup of committed fixtures
		frappe.clear_cache(doctype="CRM Lead")
		frappe.clear_cache(doctype="User")
		super().tearDownClass()

	def tearDown(self):
		delete_test_documents()
		frappe.db.commit()  # nosemgrep: persist per-test cleanup of committed fixtures

	# ------------------------------------------------------------------
	# hierarchy_enabled
	# ------------------------------------------------------------------

	def test_hierarchy_is_enabled(self):
		self.assertTrue(hierarchy_enabled())

	# ------------------------------------------------------------------
	# Lead permissions -- owner-based
	# ------------------------------------------------------------------

	def test_owner_can_read_own_lead(self):
		lead = make_lead("rep1@hier.test")
		self.assertTrue(has_lead_permission(lead, "read", "rep1@hier.test"))

	def test_manager_can_read_direct_report_lead(self):
		lead = make_lead("rep1@hier.test")
		self.assertTrue(has_lead_permission(lead, "read", "manager@hier.test"))

	def test_manager_can_read_any_report_lead(self):
		lead = make_lead("rep2@hier.test")
		self.assertTrue(has_lead_permission(lead, "read", "manager@hier.test"))

	def test_sibling_cannot_read_peer_lead(self):
		lead = make_lead("rep1@hier.test")
		self.assertFalse(has_lead_permission(lead, "read", "rep2@hier.test"))

	def test_outsider_cannot_read_team_lead(self):
		lead = make_lead("rep1@hier.test")
		self.assertFalse(has_lead_permission(lead, "read", "outsider@hier.test"))

	def test_administrator_always_has_permission(self):
		lead = make_lead("rep1@hier.test")
		self.assertTrue(has_lead_permission(lead, "read", "Administrator"))

	def test_sales_user_can_create_lead(self):
		new_lead = frappe.get_doc({"doctype": "CRM Lead", "lead_owner": "rep1@hier.test"})
		self.assertTrue(has_lead_permission(new_lead, "create", "rep1@hier.test"))

	# ------------------------------------------------------------------
	# Lead permissions -- ToDo-based
	# ------------------------------------------------------------------

	def test_direct_assignee_can_read_lead(self):
		lead = make_lead("rep1@hier.test")
		assign_todo("CRM Lead", lead.name, "outsider@hier.test")
		self.assertTrue(has_lead_permission(lead, "read", "outsider@hier.test"))

	def test_cancelled_todo_does_not_grant_access(self):
		lead = make_lead("rep1@hier.test")
		assign_todo("CRM Lead", lead.name, "outsider@hier.test", status="Cancelled")
		self.assertFalse(has_lead_permission(lead, "read", "outsider@hier.test"))

	def test_manager_can_read_lead_assigned_to_report(self):
		lead = make_lead("outsider@hier.test")
		assign_todo("CRM Lead", lead.name, "rep1@hier.test")
		self.assertTrue(has_lead_permission(lead, "read", "manager@hier.test"))

	# ------------------------------------------------------------------
	# Lead permissions -- custom_cc (issue #88, L01)
	# ------------------------------------------------------------------

	def test_cc_can_read_lead_assigned_via_custom_cc(self):
		# The lead is owned by outsider (outside cc's tree entirely -- cc has
		# no tree node at all) and never assigned via ToDo: only custom_cc
		# grants access here.
		lead = make_lead("outsider@hier.test")
		frappe.db.set_value("CRM Lead", lead.name, "custom_cc", "cc@hier.test", update_modified=False)
		self.assertTrue(has_lead_permission(lead, "read", "cc@hier.test"))
		self.assertTrue(has_lead_permission(lead, "write", "cc@hier.test"))

	def test_cc_cannot_read_lead_not_assigned_to_them(self):
		lead = make_lead("outsider@hier.test")
		# custom_cc left unset -- no ownership, no assignment, no CC grant.
		self.assertFalse(has_lead_permission(lead, "read", "cc@hier.test"))

	def test_cc_cannot_read_lead_assigned_to_a_different_cc(self):
		lead = make_lead("outsider@hier.test")
		frappe.db.set_value("CRM Lead", lead.name, "custom_cc", "manager@hier.test", update_modified=False)
		self.assertFalse(has_lead_permission(lead, "read", "cc@hier.test"))

	def test_query_conditions_for_cc_reference_custom_cc(self):
		# The permission-query branch (used for list views) must reference the
		# custom_cc column, not just the single-doc has_permission path.
		cond = get_lead_permission_query_conditions("cc@hier.test")
		self.assertIn("custom_cc", cond)

	def test_query_conditions_for_plain_rep_also_reference_custom_cc(self):
		# custom_cc is OR'd into every non-bypass user's query, whether or not
		# they hold the CC role -- any user COULD in principle be someone's
		# custom_cc. It only ever MATCHES rows where custom_cc equals that
		# specific user, so this doesn't widen a plain rep's actual access
		# (the D2D-facing sibling/outsider tests above already prove that in
		# practice); this only confirms the SQL fragment is always emitted
		# once the field exists on the site.
		cond = get_lead_permission_query_conditions("rep1@hier.test")
		self.assertIn("custom_cc", cond)

	# ------------------------------------------------------------------
	# Deal permissions
	# ------------------------------------------------------------------

	def test_manager_can_read_report_deal(self):
		deal = make_deal("rep2@hier.test")
		self.assertTrue(has_deal_permission(deal, "read", "manager@hier.test"))

	def test_peer_cannot_read_sibling_deal(self):
		deal = make_deal("rep2@hier.test")
		self.assertFalse(has_deal_permission(deal, "read", "rep1@hier.test"))

	# ------------------------------------------------------------------
	# Bypass roles (Volteo Backend / Volteo Core Admin) -- production bug:
	# backend@demo.volteo.pl saw only 13 of 16 CRM Deals because the 3
	# invisible ones were owned by Administrator, who has no tree node.
	# ------------------------------------------------------------------

	def test_backend_outside_tree_sees_deal_owned_by_unrelated_user(self):
		# Exact shape of the production hole: a backoffice user with no node
		# in the Sales Hierarchy must still see a deal owned by someone they
		# have no tree relationship with at all.
		deal = make_deal("outsider@hier.test")
		self.assertTrue(has_deal_permission(deal, "read", "backend@hier.test"))

	def test_backend_in_tree_still_sees_deal_outside_subtree(self):
		# backendintree is a leaf under manager, alongside rep1/rep2. The
		# deal owner (outsider) is outside that subtree entirely -- subtree
		# scoping alone would hide it. The role bypass must win regardless.
		deal = make_deal("outsider@hier.test")
		self.assertTrue(has_deal_permission(deal, "read", "backendintree@hier.test"))

	def test_coreadmin_outside_tree_sees_deal_owned_by_unrelated_user(self):
		deal = make_deal("outsider@hier.test")
		self.assertTrue(has_deal_permission(deal, "read", "coreadmin@hier.test"))

	def test_coreadmin_in_tree_still_sees_deal_outside_subtree(self):
		deal = make_deal("outsider@hier.test")
		self.assertTrue(has_deal_permission(deal, "read", "coreadminintree@hier.test"))

	def test_bypass_role_sees_lead_not_owned_by_them(self):
		# Covers the single-doc path (has_lead_permission), not just the
		# list query -- a bypass user must be able to open the record, not
		# merely see it listed.
		lead = make_lead("outsider@hier.test")
		self.assertTrue(has_lead_permission(lead, "read", "backend@hier.test"))
		self.assertTrue(has_lead_permission(lead, "read", "coreadmin@hier.test"))

	def test_bypass_role_sees_deal_not_owned_by_them(self):
		deal = make_deal("outsider@hier.test")
		self.assertTrue(has_deal_permission(deal, "read", "backend@hier.test"))
		self.assertTrue(has_deal_permission(deal, "read", "coreadmin@hier.test"))

	def test_query_conditions_empty_for_bypass_role(self):
		self.assertFalse(get_lead_permission_query_conditions("backend@hier.test"))
		self.assertFalse(get_lead_permission_query_conditions("coreadmin@hier.test"))

	def test_regression_plain_sales_user_in_tree_still_scoped_to_subtree(self):
		# Guard against a future BYPASS_ROLES change accidentally widening
		# who sees everything: an ordinary Sales User rep who happens to be
		# in the tree must still be blind to a deal owned outside their
		# subtree.
		deal = make_deal("outsider@hier.test")
		self.assertFalse(has_deal_permission(deal, "read", "rep1@hier.test"))

	# ------------------------------------------------------------------
	# Permission query conditions
	# ------------------------------------------------------------------

	def test_query_conditions_empty_for_administrator(self):
		self.assertFalse(get_lead_permission_query_conditions("Administrator"))

	def test_query_conditions_non_empty_for_regular_user(self):
		self.assertTrue(get_lead_permission_query_conditions("rep1@hier.test"))

	# ------------------------------------------------------------------
	# Hierarchy disabled
	# ------------------------------------------------------------------

	def test_hierarchy_disabled_sales_user_still_restricted_to_own(self):
		settings = frappe.get_single("FCRM Settings")
		settings.enable_sales_hierarchy = 0
		settings.save(ignore_permissions=True)
		try:
			lead = make_lead("rep1@hier.test")
			# Sales User default: cannot read another user's lead even when feature is off
			self.assertFalse(has_lead_permission(lead, "read", "outsider@hier.test"))
			# Sales Manager default: sees everything when feature is off
			self.assertTrue(has_lead_permission(lead, "read", "manager@hier.test"))
		finally:
			settings.enable_sales_hierarchy = 1
			settings.save(ignore_permissions=True)

	def test_query_conditions_when_hierarchy_disabled(self):
		settings = frappe.get_single("FCRM Settings")
		settings.enable_sales_hierarchy = 0
		settings.save(ignore_permissions=True)
		try:
			# Sales User still gets a filter (own + assigned)
			self.assertTrue(get_lead_permission_query_conditions("rep1@hier.test"))
			# Sales Manager has no filter (sees everything)
			self.assertFalse(get_lead_permission_query_conditions("manager@hier.test"))
		finally:
			settings.enable_sales_hierarchy = 1
			settings.save(ignore_permissions=True)


def delete_test_documents():
	"""Remove leads/deals/assignments created by the test users."""
	frappe.db.delete("ToDo", {"allocated_to": ("in", TEST_USERS)})
	frappe.db.delete("CRM Deal", {"deal_owner": ("in", TEST_USERS)})
	frappe.db.delete("CRM Lead", {"lead_owner": ("in", TEST_USERS)})


def ensure_role(role_name: str) -> bool:
	"""Create `role_name` if missing (matching ops/crm-setup.py's ROLES
	convention: desk_access=1). Returns True iff this call created it, so
	the caller only tears down roles it actually created."""
	if frappe.db.exists("Role", role_name):
		return False
	frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
		ignore_permissions=True
	)
	return True


def ensure_custom_field(doctype: str, fieldname: str, fieldtype: str, options: str | None = None) -> bool:
	"""Create a bare `Custom Field` if missing. Mirrors `ensure_role` above: returns
	True iff this call created it, so the caller only tears down what it created.

	custom_cc / custom_linia_leady are normally seeded by ops scripts
	(ops/crm-leady-call-center.py, ops/crm-linia-leady.py) that run against a real
	site, not by any fixture bundled with the app -- a fresh test site has neither,
	so the org_hierarchy.py `has_field` guard would otherwise skip the branch this
	suite exists to exercise."""
	name = f"{doctype}-{fieldname}"
	if frappe.db.exists("Custom Field", name):
		return False
	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": doctype,
			"fieldname": fieldname,
			"fieldtype": fieldtype,
			"options": options,
			"label": fieldname,
		}
	).insert(ignore_permissions=True)
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


def make_lead(owner_email):
	doc = frappe.get_doc({"doctype": "CRM Lead", "lead_owner": owner_email, "first_name": "Test"})
	doc.flags.ignore_mandatory = True
	return doc.insert(ignore_permissions=True)


def make_deal(owner_email):
	doc = frappe.get_doc({"doctype": "CRM Deal", "deal_owner": owner_email, "organization": "Test Org"})
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
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
