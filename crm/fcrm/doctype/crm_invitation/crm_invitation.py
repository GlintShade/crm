# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CRMInvitation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accepted_at: DF.Datetime | None
		email: DF.Data
		email_sent_at: DF.Datetime | None
		invited_by: DF.Link | None
		key: DF.Data | None
		role: DF.Literal["", "Sales User", "Sales Manager", "System Manager"]
		status: DF.Literal["", "Pending", "Accepted", "Expired"]
	# end: auto-generated types

	def before_insert(self):
		frappe.utils.validate_email_address(self.email, True)

		self.key = frappe.generate_hash()
		self.invited_by = frappe.session.user
		self.status = "Pending"

	def after_insert(self):
		self.invite_via_email()

	def invite_via_email(self):
		# A guest GET on the accept-invitation API endpoint 403s: that
		# endpoint is deliberately POST-only (b47 audit hardening — see
		# ops/crm-invitation-hardening.py — and must stay that way). The
		# emailed link instead points at a website page that does the POST
		# from a button (crm/www/zaproszenie.py).
		invite_link = frappe.utils.get_url(f"/zaproszenie?key={self.key}")
		if frappe.local.dev_server:
			print(f"Invite link for {self.email}: {invite_link}")  # nosemgrep

		# User-facing branding is ProEnergy (see CLAUDE.md) even though the
		# app/doctype namespace stays "Volteo"/"CRM" internally.
		title = "CRM ProEnergy"
		template = "crm_invitation"

		frappe.sendmail(
			recipients=self.email,
			subject=_("You have been invited to join {0}").format(title),
			template=template,
			args={"title": title, "invite_link": invite_link},
			now=True,
		)
		self.db_set("email_sent_at", frappe.utils.now())

	@frappe.whitelist()
	def accept_invitation(self):
		frappe.only_for(["System Manager", "Sales Manager"], True)
		self.accept()

	def accept(self):
		if self.status != "Pending":
			frappe.throw(_("Invalid or expired key"))

		user = self.create_user_if_not_exists()
		user.append_roles(self.role)
		if self.role == "System Manager":
			user.append_roles("Sales Manager", "Sales User")
		elif self.role == "Sales Manager":
			user.append_roles("Sales User")
		if self.role == "Sales User":
			self.update_module_in_user(user, "FCRM")
		# Volteo-specific role. Read via `.get()`, not attribute access: the
		# `volteo_role` Custom Field only exists once
		# ops/crm-invitation-volteo.py has run on this site, and `.get()` on
		# a Document returns None for an undefined field instead of raising
		# — same reasoning as `hierarchy_parent` below.
		volteo_role = self.get("volteo_role")
		if volteo_role:
			user.append_roles(volteo_role)
		# One save covers the stock role(s) above and the Volteo role.
		user.save(ignore_permissions=True)

		# Place the new user in the Sales Hierarchy tree under the chosen
		# parent, if one was picked at invite time and no node exists for
		# this user yet. accept() runs allow_guest (see accept_invitation),
		# so this insert must ignore permissions explicitly. A failure here
		# is deliberately NOT swallowed: it propagates so the invitation
		# stays Pending and the accept can be retried, rather than silently
		# leaving the new rep unplaced in the hierarchy.
		hierarchy_parent = self.get("hierarchy_parent")
		if hierarchy_parent and not frappe.db.exists("CRM Sales Hierarchy", {"user": self.email}):
			full_name = user.full_name or self.email
			frappe.get_doc(
				doctype="CRM Sales Hierarchy",
				full_name=full_name,
				user=self.email,
				reports_to=hierarchy_parent,
				is_group=0,
			).insert(ignore_permissions=True)

		self.status = "Accepted"
		self.accepted_at = frappe.utils.now()
		self.key = None
		self.save(ignore_permissions=True)

	def update_module_in_user(self, user, module):
		block_modules = frappe.get_all(
			"Module Def",
			fields=["name as module"],
			filters={"name": ["!=", module]},
		)

		if block_modules:
			user.set("block_modules", block_modules)

	def create_user_if_not_exists(self):
		if not frappe.db.exists("User", self.email):
			# `first_name`/`last_name` are Custom Fields (issue #14,
			# ops/crm-invitation-dane.py) supplied by the inviter, not the
			# invitee — they feed User.full_name, which the NDA gate compares
			# the signer's typed name against (see
			# crm.api.oswiadczenie._pelne_imie_i_nazwisko). Read via `.get()`,
			# not attribute access: on a site where the ops script hasn't run
			# yet, the field doesn't exist and `.get()` returns None instead
			# of raising (same reasoning as `volteo_role`/`hierarchy_parent`
			# above). Fall back to the local-part-derived name only for
			# invitations that predate this field.
			first_name = self.get("first_name") or self.email.split("@")[0].title()
			last_name = self.get("last_name") or ""
			user = frappe.get_doc(
				doctype="User",
				user_type="System User",
				email=self.email,
				send_welcome_email=0,
				first_name=first_name,
				last_name=last_name,
			).insert(ignore_permissions=True)
		else:
			# Existing User: never overwrite an established identity with
			# whatever the inviter typed this time around.
			user = frappe.get_doc("User", self.email)
		return user


def expire_invitations():
	"""expire invitations after 3 days"""
	from frappe.utils import add_days, now

	days = 3
	invitations_to_expire = frappe.db.get_all(
		"CRM Invitation", filters={"status": "Pending", "creation": ["<", add_days(now(), -days)]}
	)
	for invitation in invitations_to_expire:
		invitation = frappe.get_doc("CRM Invitation", invitation.name)
		invitation.status = "Expired"
		invitation.save(ignore_permissions=True)
