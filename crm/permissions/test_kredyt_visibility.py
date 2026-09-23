# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Regression coverage for issue #161: `Volteo Kredyt` closes the REVISIT.md
A-6/K7 gap (owner decision #4 from the 2026-09-16 credit/contract/Autenti
audit) by wiring the same deal-scoped visibility hook
`crm/permissions/faktura_visibility.py` already uses for `Volteo Faktura` and
`Volteo Trify Update`, through the existing generic
`_deal_scoped_query_conditions` / `_has_deal_scoped_permission` functions --
no new generic machinery is written for Kredyt, per the issue's explicit
instruction.

`Volteo Kredyt` is not a doctype fixture in this fork -- it is created only
by ops scripts against a live site (see `crm/api/test_umowa_kredyt_audyt_perms.py`'s
module docstring for the same caveat about Kredyt/Umowa/Audyt CP). A bare
test site therefore has no `Volteo Kredyt` doctype at all, so this suite
cannot insert real `Volteo Kredyt` documents the way
`crm/permissions/test_org_hierarchy.py` inserts real `CRM Lead`/`CRM Deal`
records. Instead it drives the reusable generic functions, plus the two thin
`Volteo Kredyt` wrappers (`get_kredyt_permission_query_conditions`,
`has_kredyt_permission`), against plain dict stub docs shaped like
`{"deal": <real CRM Deal name>}`. `CRM Deal` and `CRM Sales Hierarchy` fixtures
ARE real, inserted doctypes here, so the parent-deal half of the scoping is
exercised against genuine org_hierarchy resolution, not a mock -- only the
Kredyt side of the join is a stub, because there is no Kredyt doctype to
insert into.

Needs bench/live frappe (`crm.tests.CRMTestCase`); this module does NOT run
under plain `python3 -m unittest` locally (no `frappe` package installed
outside a bench environment -- see WORKSHOP.md's verification matrix). It
would run under `bench --site <site> run-tests --module crm.permissions.test_kredyt_visibility`
or a full `bench --site <site> run-tests --app crm` sweep.
"""

import frappe
from frappe.utils.nestedset import rebuild_tree

from crm.permissions.faktura_visibility import (
	get_kredyt_permission_query_conditions,
	has_faktura_permission,
	has_kredyt_permission,
)
from crm.tests import CRMTestCase as FrappeTestCase

TEST_USERS = (
	"manager@kredytvis.test",
	"rep1@kredytvis.test",
	"outsider@kredytvis.test",
	"backend@kredytvis.test",
)

# Bypass role under test. Created in setUpClass (guarded) and removed in
# tearDownClass, matching crm/permissions/test_org_hierarchy.py's pattern for
# a site where ops/crm-setup.py has not already seeded it.
BYPASS_TEST_ROLES = ("Volteo Backend",)


class TestKredytVisibility(FrappeTestCase):
	"""
	Hierarchy structure used in tests:
	  manager@kredytvis.test  (root)
	  └── rep1@kredytvis.test
	  outsider@kredytvis.test  (not in the hierarchy, owns a stranger's deal)
	  backend@kredytvis.test   (Volteo Backend, BYPASS_ROLES)
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._roles_created = [ensure_role(role) for role in BYPASS_TEST_ROLES]

		make_user("manager@kredytvis.test", roles=["Sales Manager"])
		make_user("rep1@kredytvis.test", roles=["Sales User"])
		make_user("outsider@kredytvis.test", roles=["Sales User"])
		make_user("backend@kredytvis.test", roles=["Volteo Backend"])

		mgr = make_hierarchy_node("manager@kredytvis.test", is_group=1)
		make_hierarchy_node("rep1@kredytvis.test", reports_to=mgr.name)
		rebuild_tree("CRM Sales Hierarchy")

		settings = frappe.get_single("FCRM Settings")
		settings.enable_sales_hierarchy = 1
		settings.save(ignore_permissions=True)

		# rep1's own deal (a colleague/backoffice-created Kredyt on it must
		# be visible to rep1) and a stranger's deal entirely outside rep1's
		# subtree (a Kredyt on it must stay hidden from rep1).
		cls.rep_deal = make_deal("rep1@kredytvis.test")
		cls.stranger_deal = make_deal("outsider@kredytvis.test")

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

	# ------------------------------------------------------------------
	# Acceptance criterion 1: rep sees a Kredyt form created by backoffice
	# on the rep's OWN deal. The stub doc's owner/creator is irrelevant here
	# on purpose -- this hook scopes by parent deal, never by who inserted
	# the Kredyt row, mirroring how DocPerm (A1) deliberately dropped
	# `if_owner`.
	# ------------------------------------------------------------------

	def test_rep_sees_kredyt_stub_on_own_deal(self):
		stub = {"deal": self.rep_deal.name}
		self.assertTrue(has_kredyt_permission(stub, "read", "rep1@kredytvis.test"))

	def test_manager_sees_kredyt_stub_on_report_deal(self):
		stub = {"deal": self.rep_deal.name}
		self.assertTrue(has_kredyt_permission(stub, "read", "manager@kredytvis.test"))

	# ------------------------------------------------------------------
	# Acceptance criterion 2: same rep does NOT see a Kredyt on a stranger's
	# deal outside their sales-hierarchy subtree.
	# ------------------------------------------------------------------

	def test_rep_does_not_see_kredyt_stub_on_strangers_deal(self):
		stub = {"deal": self.stranger_deal.name}
		self.assertFalse(has_kredyt_permission(stub, "read", "rep1@kredytvis.test"))

	def test_rep_cannot_write_kredyt_stub_on_strangers_deal(self):
		stub = {"deal": self.stranger_deal.name}
		self.assertFalse(has_kredyt_permission(stub, "write", "rep1@kredytvis.test"))

	# ------------------------------------------------------------------
	# Backoffice/BYPASS_ROLES sees everything regardless.
	# ------------------------------------------------------------------

	def test_backend_sees_kredyt_stub_on_strangers_deal(self):
		stub = {"deal": self.stranger_deal.name}
		self.assertTrue(has_kredyt_permission(stub, "read", "backend@kredytvis.test"))

	def test_administrator_sees_kredyt_stub_on_strangers_deal(self):
		stub = {"deal": self.stranger_deal.name}
		self.assertTrue(has_kredyt_permission(stub, "read", "Administrator"))

	# ------------------------------------------------------------------
	# Acceptance criterion 3, and the core regression this issue is about:
	# a record whose parent deal is unresolved/deleted/inaccessible (here,
	# simply absent -- `deal` empty) fails CLOSED, hiding the row, in
	# explicit contrast to Faktura's fail-open default for the identical
	# stub shape and user.
	# ------------------------------------------------------------------

	def test_kredyt_stub_with_no_deal_fails_closed(self):
		stub = {"deal": None}
		self.assertFalse(has_kredyt_permission(stub, "read", "rep1@kredytvis.test"))
		self.assertFalse(has_kredyt_permission(stub, "write", "rep1@kredytvis.test"))

	def test_kredyt_fail_closed_contrasts_with_faktura_fail_open(self):
		# Same stub, same user, same ptype -- Kredyt hides the row, Faktura
		# would have shown it. This is the deliberate divergence issue #161
		# calls out, asserted explicitly rather than left implicit.
		stub = {"deal": None}
		self.assertFalse(has_kredyt_permission(stub, "read", "rep1@kredytvis.test"))
		self.assertTrue(has_faktura_permission(stub, "read", "rep1@kredytvis.test"))

	def test_kredyt_stub_with_no_deal_fails_closed_even_for_bypass_role(self):
		# Bypass roles short-circuit before the empty-deal branch is ever
		# reached, so this stays True -- confirms the fail-closed default
		# only matters for non-bypass users, not a contradiction.
		stub = {"deal": None}
		self.assertTrue(has_kredyt_permission(stub, "read", "backend@kredytvis.test"))

	# ------------------------------------------------------------------
	# permission_query_conditions wiring (list-view scoping): same generic
	# subquery shape Trify/Faktura already use, now for Volteo Kredyt.
	# ------------------------------------------------------------------

	def test_query_conditions_scope_kredyt_by_deal_for_plain_rep(self):
		cond = get_kredyt_permission_query_conditions("rep1@kredytvis.test")
		self.assertIn("`tabVolteo Kredyt`.`deal` in", cond)

	def test_query_conditions_empty_for_bypass_role(self):
		self.assertFalse(get_kredyt_permission_query_conditions("backend@kredytvis.test"))

	def test_query_conditions_empty_for_administrator(self):
		self.assertFalse(get_kredyt_permission_query_conditions("Administrator"))


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
		{"doctype": "CRM Deal", "deal_owner": owner_email, "organization": "Test Org Kredyt Vis"}
	)
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	return doc.insert(ignore_permissions=True)
