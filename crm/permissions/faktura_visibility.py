# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Deal-derived visibility scoping for the Volteo Faktura doctype (invoices
attached to a CRM Deal via its `deal` Link field).

Volteo Faktura read access is granted without `if_owner` so that a D2D rep
can see invoices backoffice added on the rep's own deals (backoffice is
usually the owner/creator of the Faktura record, not the rep). Without a
scoping hook, `read=1` + no `if_owner` would let ANY user with the role read
ALL Faktura records across ALL deals via the list/get API -- a confidentiality
leak on financial data.

The rule enforced here: a Volteo Faktura is visible to a user iff its parent
deal is visible to that user. Visibility is never computed independently --
it is entirely delegated to crm.permissions.org_hierarchy, which is the
single source of truth for CRM Deal scoping (owner, subtree, ToDo
assignment). This avoids divergence between deal visibility and Faktura
visibility as org_hierarchy's rules evolve.

Bypass roles (System Manager, Volteo Backend, Volteo Core Admin) see all
Faktura records regardless of deal visibility, mirroring
crm/permissions/contact_visibility.py. Both a permission_query_conditions
hook AND a has_permission hook are registered here for the same reason
org_hierarchy and contact_visibility register both: a
permission_query_conditions hook alone only filters list queries, not direct
single-doc reads.
"""

import frappe

from crm.permissions.org_hierarchy import BYPASS_ROLES, get_deal_permission_query_conditions

# BYPASS_ROLES is defined in org_hierarchy.py (shared with CRM Lead / CRM
# Deal / Contact scoping) so the modules can't drift apart on which roles
# see everything.


def get_faktura_permission_query_conditions(user=None):
	user = user or frappe.session.user

	if user == "Administrator":
		return ""

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return ""

	deal_cond = get_deal_permission_query_conditions(user)

	# Empty condition means the user is unrestricted on CRM Deal (e.g. a
	# Sales Manager outside the hierarchy tree) -- unrestricted on the parent
	# implies unrestricted on the child Faktura too.
	if not deal_cond:
		return ""

	# deal_cond is a bare (unqualified) SQL condition string produced by
	# org_hierarchy's pypika builder -- see get_deal_permission_query_conditions.
	# It is safe to nest here because the subquery's own FROM is
	# `tabCRM Deal`, so deal_cond's unqualified `deal_owner` / `name` column
	# references resolve against that same table with no ambiguity (its
	# correlated subqueries reference their own aliased tables and are
	# self-contained).
	return "`tabVolteo Faktura`.`deal` in (select `name` from `tabCRM Deal` where {})".format(deal_cond)


def has_faktura_permission(doc, ptype, user):
	user = user or frappe.session.user

	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return True

	# Defensive fail-open: no parent deal to check visibility against (e.g.
	# a Faktura mid-creation, or a malformed record). Mirrors
	# contact_visibility's fail-open on a missing custom_opiekun field.
	deal = doc.get("deal") if isinstance(doc, dict) else getattr(doc, "deal", None)
	if not deal:
		return True

	# Defer entirely to org_hierarchy's deal scoping: the rep sees the
	# invoice iff they can read its parent deal.
	return frappe.has_permission("CRM Deal", ptype="read", doc=deal, user=user)
