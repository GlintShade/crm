# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Deal/Lead-derived visibility scoping for FCRM Note and CRM Task -- the two
polymorphic "child record" doctypes attached to a parent via
`reference_doctype` + `reference_docname` (a Link to DocType plus a Dynamic
Link, confirmed against crm/fcrm/doctype/fcrm_note/fcrm_note.json and
crm/fcrm/doctype/crm_task/crm_task.json; both doctypes use identical field
names).

Neither doctype had a permission_query_conditions hook before this module:
any user holding the stock `Sales User` role (which both grant read=1 with no
if_owner, same as Contact/Volteo Faktura before their fixes) could read every
Note/Task in the system via the generic list/get API, including ones attached
to a Deal or Lead the Sales-Hierarchy scoping in org_hierarchy.py would
otherwise hide from them. Notes and Tasks routinely carry internal free-text
about a specific customer -- this was a straight bypass of the parent's
confidentiality boundary.

The rule enforced here mirrors crm/permissions/faktura_visibility.py (itself
delegating to org_hierarchy.py as the single source of truth for CRM
Deal/Lead scoping, to avoid ever diverging from it):

  * A Note/Task whose reference_doctype is "CRM Deal" is visible iff that
    deal is visible to the user (get_deal_permission_query_conditions).
  * A Note/Task whose reference_doctype is "CRM Lead" is visible iff that
    lead is visible to the user (get_lead_permission_query_conditions).
  * Both branches FAIL CLOSED: a row that names a Deal/Lead the user cannot
    see is hidden, and a malformed row (reference_doctype is "CRM Deal" or
    "CRM Lead" but reference_docname is empty) is hidden too -- it does NOT
    get faktura_visibility's fail-*open* treatment, because a missing target
    there meant "record mid-creation" on a single, non-polymorphic field,
    whereas here it would silently un-scope an otherwise-restricted row.
  * In this app Notes/Tasks are only ever created against CRM Deal or CRM
    Lead (see crm/api/doc.py's get_linked_notes_and_tasks / crm/api/todo.py),
    so a third reference_doctype is a theoretical edge, not a real path. For
    that edge -- and for a genuinely unreferenced row (reference_doctype is
    NULL) -- this module does not silently widen (leaving it open to
    everyone with the role, the pre-fix bug) nor over-restrict (hiding a
    user's own records outright). Instead it falls back to the same default
    org_hierarchy.py applies to a Sales User with no Sales-Hierarchy node:
    the row is visible if the user owns it (`owner`), and for CRM Task only,
    also if it is directly assigned to them (`assigned_to`, a plain Link
    field on CRM Task -- distinct from the ToDo-based assignment org_hierarchy
    uses for CRM Lead/CRM Deal, which Note/Task do not have).

Bypass roles (System Manager, Volteo Backend, Volteo Core Admin) see every
Note/Task regardless of reference, mirroring every other scoping module in
this package. Both a permission_query_conditions hook AND a has_permission
hook are registered (in crm/hooks.py) for the same reason org_hierarchy /
contact_visibility / faktura_visibility register both: the query-conditions
hook alone only filters list queries, not direct single-doc reads.
"""

import frappe

from crm.permissions.org_hierarchy import (
	BYPASS_ROLES,
	get_deal_permission_query_conditions,
	get_lead_permission_query_conditions,
)

# BYPASS_ROLES is defined in org_hierarchy.py (shared with CRM Lead / CRM
# Deal / Contact / Volteo Faktura scoping) so the modules can't drift apart
# on which roles see everything.

_REFERENCE_DOCTYPE_FIELD = "reference_doctype"
_REFERENCE_DOCNAME_FIELD = "reference_docname"

_SCOPED_REFERENCE_QUERY_CONDITIONS = {
	"CRM Deal": get_deal_permission_query_conditions,
	"CRM Lead": get_lead_permission_query_conditions,
}


def _fallback_condition(doctype: str, user: str):
	"""Pypika condition for rows whose reference is neither CRM Deal nor CRM
	Lead (including no reference at all): own records, plus direct
	assignment for CRM Task. See module docstring for why this is the
	fallback rather than leaving such rows unscoped."""
	DT = frappe.qb.DocType(doctype)
	cond = DT.owner == user
	if doctype == "CRM Task":
		cond = cond | (DT.assigned_to == user)
	return cond


def _get_child_permission_query_conditions(doctype: str, user=None):
	user = user or frappe.session.user

	if user == "Administrator":
		return ""

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return ""

	table = f"`tab{doctype}`"

	branches = []
	for reference_doctype, get_conditions in _SCOPED_REFERENCE_QUERY_CONDITIONS.items():
		parent_cond = get_conditions(user)
		# Trust boundary: parent_cond MUST remain a server-derived condition
		# (built by org_hierarchy's pypika builder from frappe.session.user),
		# never client input -- mirrors faktura_visibility's identical
		# assertion, since this is nested via string interpolation below.
		assert isinstance(parent_cond, str), "parent_cond must be a pypika-rendered SQL string"

		parent_table = "tabCRM Deal" if reference_doctype == "CRM Deal" else "tabCRM Lead"
		subquery = f"select `name` from `{parent_table}`"
		if parent_cond:
			subquery += f" where {parent_cond}"

		branches.append(
			"({table}.`{ref_dt}` = '{reference_doctype}' and {table}.`{ref_name}` in ({subquery}))".format(
				table=table,
				ref_dt=_REFERENCE_DOCTYPE_FIELD,
				ref_name=_REFERENCE_DOCNAME_FIELD,
				reference_doctype=reference_doctype,
				subquery=subquery,
			)
		)

	fallback_cond = _fallback_condition(doctype, user)
	fallback_sql = fallback_cond.get_sql(quote_char="`", secondary_quote_char="'")
	branches.append(
		"(({table}.`{ref_dt}` is null or {table}.`{ref_dt}` not in ('CRM Deal', 'CRM Lead')) "
		"and ({fallback_sql}))".format(
			table=table,
			ref_dt=_REFERENCE_DOCTYPE_FIELD,
			fallback_sql=fallback_sql,
		)
	)

	return " or ".join(branches)


def get_note_permission_query_conditions(user=None):
	return _get_child_permission_query_conditions("FCRM Note", user)


def get_task_permission_query_conditions(user=None):
	return _get_child_permission_query_conditions("CRM Task", user)


def _has_child_permission(doc, ptype, user, doctype: str) -> bool:
	user = user or frappe.session.user

	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return True

	if ptype == "create" or not doc.name:
		return True

	reference_doctype = doc.get(_REFERENCE_DOCTYPE_FIELD) if isinstance(doc, dict) else getattr(
		doc, _REFERENCE_DOCTYPE_FIELD, None
	)
	reference_docname = doc.get(_REFERENCE_DOCNAME_FIELD) if isinstance(doc, dict) else getattr(
		doc, _REFERENCE_DOCNAME_FIELD, None
	)

	if reference_doctype in _SCOPED_REFERENCE_QUERY_CONDITIONS:
		# Fail closed: a scoped reference without a target is malformed data,
		# not evidence the row is safe to show -- mirrors the query-condition
		# branch above, where the same row would match neither the deal/lead
		# branch (empty docname) nor the fallback branch (reference_doctype
		# is one of the scoped types, so it's excluded from that branch too).
		if not reference_docname:
			return False
		return bool(frappe.has_permission(reference_doctype, ptype="read", doc=reference_docname, user=user))

	# reference_doctype is neither CRM Deal nor CRM Lead (including None) --
	# fall back to own/assigned, consistent with the query-conditions branch.
	owner = doc.get("owner") if isinstance(doc, dict) else getattr(doc, "owner", None)
	if owner == user:
		return True
	if doctype == "CRM Task":
		assigned_to = doc.get("assigned_to") if isinstance(doc, dict) else getattr(doc, "assigned_to", None)
		if assigned_to == user:
			return True
	return False


def has_note_permission(doc, ptype, user=None):
	return _has_child_permission(doc, ptype, user, "FCRM Note")


def has_task_permission(doc, ptype, user=None):
	return _has_child_permission(doc, ptype, user, "CRM Task")
