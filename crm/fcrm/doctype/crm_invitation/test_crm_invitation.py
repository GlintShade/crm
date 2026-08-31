# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import cint

from crm.tests import CRMTestCase as FrappeTestCase


class TestCRMInvitation(FrappeTestCase):
	def make_invitation(self, email="invitee@example.com", role="Sales User", **kwargs):
		"""Create a Pending invitation without actually sending an email."""
		with patch.object(frappe, "sendmail"):
			return frappe.get_doc(
				doctype="CRM Invitation",
				email=email,
				role=role,
				**kwargs,
			).insert(ignore_permissions=True)

	def test_new_invitation_is_pending_with_key(self):
		invitation = self.make_invitation()
		self.assertEqual(invitation.status, "Pending")
		self.assertTrue(invitation.key)
		self.assertEqual(invitation.invited_by, frappe.session.user)

	def test_accept_pending_invitation(self):
		invitation = self.make_invitation()

		invitation.accept()

		self.assertEqual(invitation.status, "Accepted")
		self.assertTrue(invitation.accepted_at)
		self.assertTrue(frappe.db.exists("User", invitation.email))

	def test_accept_clears_key(self):
		"""The key is wiped after acceptance so the invite link cannot be reused."""
		invitation = self.make_invitation()

		invitation.accept()

		self.assertIsNone(invitation.key)
		self.assertFalse(frappe.db.get_value("CRM Invitation", invitation.name, "key"))

	def test_accept_already_accepted_raises(self):
		"""An already-accepted invitation cannot be accepted again."""
		invitation = self.make_invitation()
		invitation.accept()

		invitation.reload()
		with self.assertRaises(frappe.ValidationError):
			invitation.accept()

	def test_accept_expired_invitation_raises(self):
		invitation = self.make_invitation()
		invitation.status = "Expired"
		invitation.save(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			invitation.accept()

	def test_accept_grants_role_to_user(self):
		invitation = self.make_invitation(email="manager@example.com", role="Sales Manager")

		invitation.accept()

		user = frappe.get_doc("User", invitation.email)
		user_roles = {r.role for r in user.roles}
		self.assertIn("Sales Manager", user_roles)
		self.assertIn("Sales User", user_roles)

	def test_accept_with_phone_and_cp_only(self):
		"""Issue #17: phone lands on mobile_no; an explicit CP-only selection
		grants custom_linia_cp but withholds custom_linia_oze."""
		invitation = self.make_invitation(
			email="cp-rep@example.com",
			mobile_no="+48 123 456 789",
			linia_oze=0,
			linia_cp=1,
		)

		invitation.accept()

		user = frappe.get_doc("User", invitation.email)
		self.assertEqual(user.mobile_no, "+48 123 456 789")
		self.assertEqual(cint(user.custom_linia_oze), 0)
		self.assertEqual(cint(user.custom_linia_cp), 1)

	def test_accept_with_fields_unset_defaults_to_both_lines(self):
		"""A Pending invitation predating ops/crm-invitation-linie-telefon.py
		has nothing in linia_oze/linia_cp — accept() must not crash and must
		default the new user to both product lines (the pre-#17 behaviour)."""
		invitation = self.make_invitation(email="legacy-invite@example.com")

		invitation.accept()

		user = frappe.get_doc("User", invitation.email)
		self.assertEqual(cint(user.custom_linia_oze), 1)
		self.assertEqual(cint(user.custom_linia_cp), 1)

	def test_accept_with_commission_flag_off_and_manager_tier(self):
		"""Issue #51: an invitation with widzi_prowizje=0 and poziom_prowizji
		"Manager" copies both onto the new User's custom_widzi_prowizje /
		custom_poziom_prowizji."""
		invitation = self.make_invitation(
			email="manager-rep@example.com",
			widzi_prowizje=0,
			poziom_prowizji="Manager",
		)

		invitation.accept()

		user = frappe.get_doc("User", invitation.email)
		self.assertEqual(cint(user.custom_widzi_prowizje), 0)
		self.assertEqual(user.custom_poziom_prowizji, "Manager")

	def test_accept_with_commission_fields_unset_defaults_to_visible_handlowiec(self):
		"""A Pending invitation predating ops/crm-prowizje-uzytkownik.py has
		nothing in widzi_prowizje/poziom_prowizji — accept() must not crash and
		must default the new user to visible commission at the base tier
		(matching the field's own schema defaults, Check default 1 / Select
		default "Handlowiec")."""
		invitation = self.make_invitation(email="legacy-prowizje-invite@example.com")

		invitation.accept()

		user = frappe.get_doc("User", invitation.email)
		self.assertEqual(cint(user.custom_widzi_prowizje), 1)
		self.assertEqual(user.custom_poziom_prowizji, "Handlowiec")

	def test_accept_with_garbage_poziom_prowizji_falls_back_to_handlowiec(self):
		"""An invitation carrying a poziom_prowizji value outside the closed
		set (e.g. a stale/hand-crafted request) must fall back to the
		narrowest tier "Handlowiec" rather than store the garbage value or
		crash accept()."""
		invitation = self.make_invitation(
			email="garbage-poziom@example.com",
			poziom_prowizji="Wlasciciel",
		)

		invitation.accept()

		user = frappe.get_doc("User", invitation.email)
		self.assertEqual(user.custom_poziom_prowizji, "Handlowiec")
