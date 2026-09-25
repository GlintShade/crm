# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Restrict the `delete` permission to admins only, on the shared CRM record
doctypes (CRM Deal / CRM Lead / FCRM Note / CRM Task / CRM Organization /
Contact), with one deliberate exception: backoffice (Volteo Backend) may
delete CRM Deal (szanse), after a strong client-side warning (see
`frontend/src/utils/usuwanieSzansy.js`). Reps (Volteo D2D Sales) still cannot
delete any of the six.

Reps and backoffice inherit `delete` on these from the stock `Sales User` /
`Sales Manager` roles' DocPerms. Policy: only Volteo Core Admin + System
Manager may delete five of the six; backoffice is additionally allowed on
CRM Deal. Rather than rewrite the shared app DocPerm matrices (migrate-fragile,
risks stripping System Manager), this has_permission controller denies
`delete` for anyone the policy in `crm.volteo_usuwanie` does not allow. It is
registered LAST in each doctype's has_permission list so it runs first
(Frappe iterates reversed) and short-circuits:
  * ptype != "delete"          -> None  (defer: let read/write scoping hooks run)
  * delete, allowed by policy  -> True  (allow; skips the scoping hook for delete)
  * delete, not allowed        -> False (deny)
Returning True never grants beyond role perms (it is ANDed with them); it only
short-circuits so an allowed delete isn't scoped away by org_hierarchy. The
role/doctype matrix and its tests live in the frappe-free `crm.volteo_usuwanie`
module; this stays the thin adapter Frappe actually calls, and keeps its
public names (DELETE_ADMIN_ROLES, LOCKED_DELETE_DOCTYPES, is_delete_admin,
block_nonadmin_delete) because `crm/hooks.py`, `crm/api/doc.py` and
`crm/permissions/test_child_visibility.py` import them directly.
"""

import frappe

from crm.volteo_usuwanie import DOCTYPY_ZABLOKOWANE, ROLE_ADMIN_USUWANIA, czy_wolno_usunac

DELETE_ADMIN_ROLES = set(ROLE_ADMIN_USUWANIA)

LOCKED_DELETE_DOCTYPES = set(DOCTYPY_ZABLOKOWANE)


def is_delete_admin(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(ROLE_ADMIN_USUWANIA & set(frappe.get_roles(user)))


def block_nonadmin_delete(doc, ptype, user=None):
	if ptype != "delete":
		return None

	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return czy_wolno_usunac(doc.doctype, roles, user)
