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

from crm.permissions.org_hierarchy import _in_hierarchy, _team_mem_query, hierarchy_enabled

OPIEKUN_FIELD = "custom_opiekun"

# Volteo Backend / Volteo Core Admin sit atop the Sales Hierarchy tree, but
# demo clients are all owned by Administrator -- who is NOT a tree node -- so
# subtree membership alone would hide those contacts from them. Bypass by
# role instead, same as System Manager. Administrator itself is handled
# explicitly below, matching org_hierarchy.
BYPASS_ROLES = {"System Manager", "Volteo Backend", "Volteo Core Admin"}


def _conditions(user: str | None):
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return ""

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return ""

	# Defensive fail-open: fresh site before the custom_opiekun field exists.
	if not frappe.get_meta("Contact").has_field(OPIEKUN_FIELD):
		return ""

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

	# Defensive fail-open: fresh site before the custom_opiekun field exists.
	if not frappe.get_meta("Contact").has_field(OPIEKUN_FIELD):
		return True

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
