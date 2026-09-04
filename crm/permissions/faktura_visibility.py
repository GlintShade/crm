# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Deal-derived visibility scoping for doctypes that link a `CRM Deal` through
their own `deal` Link field: `Volteo Faktura` (invoices attached to a deal)
and `Volteo Trify Update` (Trify process log entries on a Czyste Powietrze
deal, ops#75).

Volteo Faktura read access is granted without `if_owner` so that a D2D rep
can see invoices backoffice added on the rep's own deals (backoffice is
usually the owner/creator of the Faktura record, not the rep). Without a
scoping hook, `read=1` + no `if_owner` would let ANY user with the role read
ALL Faktura records across ALL deals via the list/get API -- a confidentiality
leak on financial data.

Volteo Trify Update follows the same owner decision (ops#75): whoever can see
a deal sees ALL of its Trify entries, not just their own -- D2D and Backend
both add entries on the same deal, and hiding entries by author would defeat
the point of a shared process log. DocPerm (set up by `ops/crm-trify.py`)
already narrows D2D to read+create with no write/delete; this hook is the
deal-scoping layer underneath that, not a substitute for it.

The rule enforced here, for both doctypes: a record is visible to a user iff
its parent deal is visible to that user. Visibility is never computed
independently -- it is entirely delegated to crm.permissions.org_hierarchy,
which is the single source of truth for CRM Deal scoping (owner, subtree,
ToDo assignment). This avoids divergence between deal visibility and
Faktura/Trify visibility as org_hierarchy's rules evolve.

Bypass roles (System Manager, Volteo Backend, Volteo Core Admin) see all
records for both doctypes regardless of deal visibility, mirroring
crm/permissions/contact_visibility.py. Both a permission_query_conditions
hook AND a has_permission hook are registered here for each doctype, for the
same reason org_hierarchy and contact_visibility register both: a
permission_query_conditions hook alone only filters list queries, not direct
single-doc reads.

The two doctypes differ in one respect, deliberately preserved: when a record
has no `deal` yet, Faktura fails OPEN (`True` -- a defensive default that
predates Trify and is left untouched here, ops#39 revisits Faktura's write
semantics separately) while Trify fails CLOSED (`False` -- a Trify Update is
only ever created via `frappe.client.insert` with `deal` populated up front,
so a record with no `deal` is malformed, not mid-creation).
"""

import frappe

from crm.permissions.org_hierarchy import BYPASS_ROLES, get_deal_permission_query_conditions

# BYPASS_ROLES is defined in org_hierarchy.py (shared with CRM Lead / CRM
# Deal / Contact scoping) so the modules can't drift apart on which roles
# see everything.


def _deal_scoped_query_conditions(doctype: str, user: str) -> str:
	"""Generyczne ciało `permission_query_conditions` dla doctype'u linkującego
	`CRM Deal` przez własne pole `deal` -- widoczność rekordu równa się
	widoczności jego szansy nadrzędnej. Wspólne dla Volteo Faktura i
	Volteo Trify Update.
	"""
	if user == "Administrator":
		return ""

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return ""

	deal_cond = get_deal_permission_query_conditions(user)

	# Empty condition means the user is unrestricted on CRM Deal (e.g. a
	# Sales Manager outside the hierarchy tree) -- unrestricted on the parent
	# implies unrestricted on the child record too.
	if not deal_cond:
		return ""

	# deal_cond is a bare (unqualified) SQL condition string produced by
	# org_hierarchy's pypika builder -- see get_deal_permission_query_conditions.
	# It is safe to nest here because the subquery's own FROM is
	# `tabCRM Deal`, so deal_cond's unqualified `deal_owner` / `name` column
	# references resolve against that same table with no ambiguity (its
	# correlated subqueries reference their own aliased tables and are
	# self-contained).
	# Trust boundary: deal_cond MUST remain a server-derived condition (built by
	# org_hierarchy's pypika builder from frappe.session.user), never client input.
	# If a future change routes user-supplied data into get_deal_permission_query_conditions,
	# this string interpolation becomes an injection sink -- keep that function pypika-only.
	assert isinstance(deal_cond, str), "deal_cond must be a pypika-rendered SQL string"
	return "`tab{0}`.`deal` in (select `name` from `tabCRM Deal` where {1})".format(doctype, deal_cond)


def _has_deal_scoped_permission(doc, ptype: str, user: str, fail_open: bool) -> bool:
	"""Generyczne ciało `has_permission` dla doctype'u linkującego `CRM Deal`
	przez własne pole `deal`. `fail_open` decyduje, co zwrócić, gdy rekord
	(jeszcze) nie ma wypełnionego pola `deal` -- patrz docstring modułu.
	"""
	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return True

	deal = doc.get("deal") if isinstance(doc, dict) else getattr(doc, "deal", None)
	if not deal:
		return fail_open

	# Defer entirely to org_hierarchy's deal scoping: the user gets `ptype`
	# access to the child record iff they have the equivalent access to its
	# parent deal. Any create/write/delete on the child maps to a "write"
	# check on the deal -- there is no meaningful "delete the deal" access
	# level to check separately.
	tryb = "read" if ptype == "read" else "write"
	try:
		return frappe.has_permission("CRM Deal", ptype=tryb, doc=deal, user=user)
	except frappe.DoesNotExistError:
		return False


def get_faktura_permission_query_conditions(user=None):
	return _deal_scoped_query_conditions("Volteo Faktura", user or frappe.session.user)


def has_faktura_permission(doc, ptype, user):
	user = user or frappe.session.user

	# Faktura's long-standing behaviour, unchanged: whatever `ptype` was
	# actually requested on the Faktura, the check against the parent deal is
	# always "read" -- an invoice's visibility tracks whether the user can
	# *see* the deal, never whether they can *edit* it. ops#39 revisits
	# Faktura's write semantics separately; not touched here.
	return _has_deal_scoped_permission(doc, "read", user, fail_open=True)


def get_trify_permission_query_conditions(user=None):
	return _deal_scoped_query_conditions("Volteo Trify Update", user or frappe.session.user)


def has_trify_permission(doc, ptype, user):
	user = user or frappe.session.user

	# Unlike Faktura, Trify's requested `ptype` matters: read maps to a read
	# check on the deal, create/write/delete map to a write check. DocPerm
	# already narrows D2D to read+create with no write/delete -- this is the
	# deal-scoping layer underneath that, not a substitute for it.
	return _has_deal_scoped_permission(doc, ptype, user, fail_open=False)
