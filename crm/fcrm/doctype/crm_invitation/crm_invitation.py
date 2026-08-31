# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


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

		# Product-line access (issue #17, ops/crm-invitation-linie-telefon.py):
		# thread the inviter's OZE / Czyste Powietrze selection onto the new
		# User's `custom_linia_oze` / `custom_linia_cp` flags (issue #16).
		# Resolution defaults to 1 (both lines granted) when the invitation
		# carries no value — Pending invitations created before this script
		# ran have nothing in these columns, and the pre-#17 behaviour was
		# unrestricted product-line access, so "missing" must resolve the
		# same way "both checked" would.
		user.custom_linia_oze = self._resolve_linia_flag("linia_oze")
		user.custom_linia_cp = self._resolve_linia_flag("linia_cp")
		# Leady module access (issue #27, ops/crm-linia-leady.py): same
		# resolution mechanism, but default=0 rather than 1 — unlike
		# OZE/CP there is no pre-existing "everyone already had it"
		# behaviour to preserve; the owner's safe-rollout default is off
		# until explicitly granted, matching both the ops backfill default
		# and the CRM Invitation field's own schema default of "0" (see
		# ops/crm-linia-leady.py docstring).
		user.custom_linia_leady = self._resolve_linia_flag("linia_leady", default=0)

		# Commission visibility/tier (issue #51, schema: #46/ops#46): same
		# `.get()`-then-resolve shape as the linia_* flags above, so a
		# Pending invitation created before ops/crm-prowizje-uzytkownik.py
		# ran (fields don't exist yet) doesn't crash `accept()`.
		user.custom_widzi_prowizje = self._resolve_linia_flag("widzi_prowizje", default=1)
		# Not imported from `crm.api.VOLTEO_POZIOMY_PROWIZJI` here: crm.api's
		# package __init__ imports this doctype module indirectly through
		# other API submodules at load time, and importing it back from here
		# would risk a circular import for no real benefit — this is a tiny,
		# closed, effectively-frozen set. Keep it in sync with
		# `crm.api.VOLTEO_POZIOMY_PROWIZJI` if that set ever changes.
		_POZIOMY_PROWIZJI = {"Handlowiec", "Manager", "Partner"}
		raw_poziom = self.get("poziom_prowizji")
		user.custom_poziom_prowizji = raw_poziom if raw_poziom in _POZIOMY_PROWIZJI else "Handlowiec"

		# One save covers the stock role(s) above, the Volteo role, the
		# product-line flags, and the commission visibility/tier.
		user.save(ignore_permissions=True)

		# Place the new user in the Sales Hierarchy tree whenever the
		# invite carried a Volteo role, whether or not a parent node was
		# picked (issue #15): an empty hierarchy_parent means the node goes
		# straight under management at the tree root (reports_to = None) —
		# the same position the existing backoffice leaves already sit at,
		# so it is no longer treated as "unplaced". Skipped only if a node
		# for this user already exists. accept() runs allow_guest (see
		# accept_invitation), so this insert must ignore permissions
		# explicitly. A failure here is deliberately NOT swallowed: it
		# propagates so the invitation stays Pending and the accept can be
		# retried, rather than silently leaving the new rep unplaced in the
		# hierarchy.
		if volteo_role and not frappe.db.exists("CRM Sales Hierarchy", {"user": self.email}):
			hierarchy_parent = self.get("hierarchy_parent")
			full_name = user.full_name or self.email
			frappe.get_doc(
				doctype="CRM Sales Hierarchy",
				full_name=full_name,
				user=self.email,
				reports_to=hierarchy_parent or None,
				is_group=0,
			).insert(ignore_permissions=True)

		self.status = "Accepted"
		self.accepted_at = frappe.utils.now()
		self.key = None
		self.save(ignore_permissions=True)

	def _resolve_linia_flag(self, fieldname, default=1):
		"""Resolve a product-line/module-access flag (`linia_oze` / `linia_cp` /
		`linia_leady`) to 0/1.

		`.get()`, not attribute access — same reasoning as `volteo_role`
		above: on a site where the relevant ops script hasn't run yet, the
		field doesn't exist and `.get()` returns None instead of raising.
		None/missing resolves to `default` — see the docstrings on the two
		call sites in `accept()`: `linia_oze`/`linia_cp` pass no `default`
		(so it stays 1, "both lines granted", preserving pre-#17 behaviour),
		while `linia_leady` explicitly passes `default=0` (issue #27's
		safe-rollout default — there is no pre-existing behaviour to
		preserve there). A value that IS set may arrive as a string
		("0"/"1") depending on read path, so coerce deliberately with
		`cint` rather than relying on Python truthiness of the raw value.
		"""
		raw = self.get(fieldname)
		if raw is None or raw == "":
			return default
		return 1 if cint(raw) else 0

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
			# `mobile_no` is optional (issue #17, ops/crm-invitation-linie-telefon.py)
			# and only ever set on the brand-new User — the existing-User branch
			# below deliberately never overwrites an established identity, phone
			# included.
			user = frappe.get_doc(
				doctype="User",
				user_type="System User",
				email=self.email,
				send_welcome_email=0,
				first_name=first_name,
				last_name=last_name,
				mobile_no=self.get("mobile_no") or None,
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
