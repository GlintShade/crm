# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Restrict the `delete` permission to admins only, on the shared CRM record
doctypes (CRM Deal / CRM Lead / FCRM Note / CRM Task / CRM Organization /
Contact).

Reps (Volteo D2D Sales) and backoffice (Volteo Backend) inherit `delete` on
these from the stock `Sales User` / `Sales Manager` roles' DocPerms. Policy:
only Volteo Core Admin + System Manager may delete these records. Rather than
rewrite the shared app DocPerm matrices (migrate-fragile, risks stripping
System Manager), this has_permission controller denies `delete` for anyone who
is not a delete-admin. It is registered LAST in each doctype's has_permission
list so it runs first (Frappe iterates reversed) and short-circuits:
  * ptype != "delete"      -> None  (defer: let read/write scoping hooks run)
  * delete, admin          -> True  (allow; skips the scoping hook for delete)
  * delete, non-admin      -> False (deny)
Returning True never grants beyond role perms (it is ANDed with them); it only
short-circuits so an admin's delete isn't scoped away by org_hierarchy.
"""

import frappe

DELETE_ADMIN_ROLES = {"System Manager", "Volteo Core Admin"}


def block_nonadmin_delete(doc, ptype, user=None):
	if ptype != "delete":
		return None

	user = user or frappe.session.user
	if user == "Administrator":
		return True

	if DELETE_ADMIN_ROLES & set(frappe.get_roles(user)):
		return True

	return False
