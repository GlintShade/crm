# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet, update_nsm


class CRMSalesHierarchy(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		full_name: DF.Data | None
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		reports_to: DF.Link | None
		rgt: DF.Int
		user: DF.Link | None
	# end: auto-generated types

	nsm_parent_field = "reports_to"

	def on_update(self):
		update_nsm(self)
		frappe.cache.delete_value("crm_sales_hierarchy_subtree")

	def validate(self):
		if self.user:
			# Ensure the same user is not mapped to two different nodes
			existing = frappe.db.get_value(
				"CRM Sales Hierarchy",
				{"user": self.user, "name": ["!=", self.name]},
				"name",
			)
			if existing:
				frappe.throw(
					frappe._("User {0} is already mapped to hierarchy node {1}.").format(self.user, existing)
				)

		# A node with reports_to becomes a child so its parent must be a group
		if self.reports_to and not frappe.db.get_value("CRM Sales Hierarchy", self.reports_to, "is_group"):
			frappe.db.set_value("CRM Sales Hierarchy", self.reports_to, "is_group", 1)

	def on_trash(self):
		# ops#87: CRM Invitation.hierarchy_parent is a Custom Field (Link to CRM
		# Sales Hierarchy) added by ops/crm-invitation-volteo.py, not part of this
		# doctype's own schema. accept() reads it once to place a new user's node
		# under the invited parent, then never clears it, so an Accepted or Expired
		# invitation keeps pointing at a node that later gets deleted and the delete
		# fails with LinkExistsError.
		#
		# frappe/model/delete_doc.py runs doc.run_method("on_trash") BEFORE
		# check_if_doc_is_linked(doc), so unlinking here still lets the link check
		# pass afterwards, for every delete path (UI, crm.api.user, bench).
		#
		# We deliberately do NOT set ignore_links_on_delete in hooks.py: that flag
		# is global to the doctype and would also waive the link check for Pending
		# invitations (whose addressee has not registered yet, so the parent they
		# were promised must not vanish under them) and for any other link CRM
		# Invitation may hold. The owner's decision is that the hierarchy must stay
		# editable independently of what an invitation once said: hierarchy_parent
		# only records the starting position, so once an invitation is Accepted or
		# Expired that value is history and can be cleared, but a Pending one still
		# needs the node to exist and must block the delete with a clear message.
		#
		# The has_field guard covers a site where the ops script that adds
		# hierarchy_parent has never run: without it this controller would crash on
		# every hierarchy delete instead of degrading to a no-op.
		frappe.cache.delete_value("crm_sales_hierarchy_subtree")

		if not frappe.get_meta("CRM Invitation").has_field("hierarchy_parent"):
			return

		linked_invitations = frappe.get_all(
			"CRM Invitation",
			filters={"hierarchy_parent": self.name},
			fields=["name", "email", "status"],
		)

		pending_emails = sorted(
			row.email for row in linked_invitations if row.status == "Pending"
		)
		if pending_emails:
			frappe.throw(
				_(
					"Cannot remove hierarchy node {0}: pending invitation(s) for {1} still"
					" point to it. Cancel them first or wait until they are accepted."
				).format(self.full_name or self.name, ", ".join(pending_emails)),
				frappe.LinkExistsError,
			)

		for row in linked_invitations:
			frappe.db.set_value(
				"CRM Invitation", row.name, "hierarchy_parent", None, update_modified=False
			)


def on_doctype_update():
	frappe.db.add_index("CRM Sales Hierarchy", ["lft", "rgt"])
	frappe.db.add_index("CRM Sales Hierarchy", ["user"])
