# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Hierarchy-aware visibility scoping for the Contact doctype ("Klienci" in the
Volteo CRM UI).

A Volteo D2D Sales rep should only see clients where they are the account
manager (`custom_opiekun`), plus anyone below them in the Sales Hierarchy
subtree. Bypass roles (System Manager, Volteo Backend, Volteo Core Admin) see
all contacts regardless of opiekun.

This mirrors crm/permissions/org_hierarchy.py (which does the equivalent for
CRM Deal / CRM Lead, keyed on deal_owner / lead_owner) and reuses its
hierarchy helpers directly to avoid divergence. Both a
permission_query_conditions hook AND a has_permission hook are registered
here for the same reason org_hierarchy registers both: a
permission_query_conditions hook alone only filters list queries, not direct
single-doc reads.
"""

import frappe

from crm.permissions.org_hierarchy import BYPASS_ROLES, _in_hierarchy, _team_mem_query, hierarchy_enabled

OPIEKUN_FIELD = "custom_opiekun"

# BYPASS_ROLES is defined in org_hierarchy.py (shared with CRM Lead / CRM
# Deal scoping) so the two modules can't drift apart on which roles see
# everything.


def _conditions(user: str | None):
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return ""

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return ""

	# Fail closed: if custom_opiekun is absent (deleted field, or an
	# ops-schema-before-image deploy-order violation), scoping cannot be
	# evaluated. Hide all rows for non-bypass users rather than leak every
	# contact org-wide, and log so the schema drift is visible. The never-match
	# condition is built on `name` (always present, NOT NULL) rather than
	# OPIEKUN_FIELD, since referencing the missing column would itself raise
	# an "unknown column" SQL error instead of failing closed.
	if not frappe.get_meta("Contact").has_field(OPIEKUN_FIELD):
		frappe.log_error(
			title="contact_visibility: custom_opiekun missing",
			message="Fail-closed: Contact.custom_opiekun field absent; scoping cannot be evaluated.",
		)
		return frappe.qb.DocType("Contact").name.isnull()

	in_tree = hierarchy_enabled() and _in_hierarchy(user)

	# Sales Manager outside the tree retains the default ie sees everything
	if "Sales Manager" in roles and not in_tree:
		return ""

	Contact = frappe.qb.DocType("Contact")

	if in_tree:
		return (Contact[OPIEKUN_FIELD] == user) | Contact[OPIEKUN_FIELD].isin(_team_mem_query(user))

	return Contact[OPIEKUN_FIELD] == user


def get_contact_permission_query_conditions(user=None):
	cond = _conditions(user)
	return cond.get_sql(quote_char="`", secondary_quote_char="'") if cond else ""


def has_contact_permission(doc, ptype, user):
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return True

	if ptype == "create" or not doc.name:
		return True

	# Fail closed: if custom_opiekun is absent (deleted field, or an
	# ops-schema-before-image deploy-order violation), scoping cannot be
	# evaluated. Deny access for non-bypass users rather than leak every
	# contact org-wide, and log so the schema drift is visible.
	if not frappe.get_meta("Contact").has_field(OPIEKUN_FIELD):
		frappe.log_error(
			title="contact_visibility: custom_opiekun missing",
			message="Fail-closed: Contact.custom_opiekun field absent; scoping cannot be evaluated.",
		)
		return False

	in_tree = hierarchy_enabled() and _in_hierarchy(user)
	if "Sales Manager" in roles and not in_tree:
		return True

	conditions = _conditions(user)
	Contact = frappe.qb.DocType("Contact")
	return bool(
		frappe.qb.from_(Contact)
		.select(Contact.name)
		.where(Contact.name == doc.name)
		.where(conditions)
		.limit(1)
		.run()
	)
