# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, cint, now

from crm.api import invite_by_email, resend_invitation
from crm.fcrm.doctype.crm_invitation.crm_invitation import (
	expire_invitations,
	waznosc_zaproszenia_dni,
)
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

	def test_validate_lowercases_email(self):
		"""ops#45: a mixed-case email as typed by the inviting admin must be
		normalized to lowercase on save, so it can never ride into the
		session cookie mixed-case at accept-time (the 2026-08-29 incident)."""
		invitation = self.make_invitation(email="Test.Case.B53@Example.COM")

		self.assertEqual(invitation.email, "test.case.b53@example.com")
		self.assertEqual(
			frappe.db.get_value("CRM Invitation", invitation.name, "email"),
			"test.case.b53@example.com",
		)

	def _set_waznosc_dni(self, wartosc):
		"""Write FCRM Settings.custom_zaproszenie_dni_waznosci and register a
		cleanup that restores whatever value (or absence) was there before."""
		poprzednia = frappe.db.get_singles_dict("FCRM Settings").get("custom_zaproszenie_dni_waznosci")
		frappe.db.set_single_value("FCRM Settings", "custom_zaproszenie_dni_waznosci", wartosc)
		self.addCleanup(
			lambda: frappe.db.set_single_value(
				"FCRM Settings", "custom_zaproszenie_dni_waznosci", poprzednia
			)
		)

	def _backdate(self, invitation, days):
		"""Rewrite `creation` N days into the past and reload the doc."""
		frappe.db.set_value(
			"CRM Invitation",
			invitation.name,
			"creation",
			add_days(now(), -days),
			update_modified=False,
		)
		invitation.reload()
		return invitation

	def test_waznosc_default_when_unset(self):
		"""ops#86: with no Single value at all, or a non-positive one, the
		fallback DOMYSLNA_WAZNOSC_DNI (7) applies; a positive string value is
		coerced with cint."""
		with patch.object(frappe.db, "get_singles_dict", return_value={}):
			self.assertEqual(waznosc_zaproszenia_dni(), 7)

		with patch.object(
			frappe.db,
			"get_singles_dict",
			return_value={"custom_zaproszenie_dni_waznosci": "0"},
		):
			self.assertEqual(waznosc_zaproszenia_dni(), 7)

		with patch.object(
			frappe.db,
			"get_singles_dict",
			return_value={"custom_zaproszenie_dni_waznosci": "14"},
		):
			self.assertEqual(waznosc_zaproszenia_dni(), 14)

	def test_expire_invitations_keeps_six_day_old_pending(self):
		self._set_waznosc_dni(7)
		invitation = self.make_invitation(email="six-day@example.com")
		self._backdate(invitation, 6)

		expire_invitations()

		invitation.reload()
		self.assertEqual(invitation.status, "Pending")

	def test_expire_invitations_expires_eight_day_old(self):
		self._set_waznosc_dni(7)
		invitation = self.make_invitation(email="eight-day@example.com")
		self._backdate(invitation, 8)

		expire_invitations()

		invitation.reload()
		self.assertEqual(invitation.status, "Expired")

	def test_expire_invitations_respects_longer_window(self):
		self._set_waznosc_dni(14)
		invitation = self.make_invitation(email="longer-window@example.com")
		self._backdate(invitation, 8)

		expire_invitations()

		invitation.reload()
		self.assertEqual(invitation.status, "Pending")

	def test_accept_rejects_stale_pending_invitation(self):
		"""ops#86: accept() must not rely solely on the lazy daily scheduler
		to catch a stale Pending invitation, since that scheduler can lag up
		to 24h or be paused entirely."""
		self._set_waznosc_dni(7)
		invitation = self.make_invitation(email="stale-accept@example.com")
		self._backdate(invitation, 8)

		with self.assertRaises(frappe.ValidationError):
			invitation.accept()

		invitation.reload()
		self.assertEqual(invitation.status, "Expired")

	def test_resend_invitation_on_expired_row_creates_new_pending(self):
		"""crm.api.resend_invitation on an Expired row must create a fresh
		Pending row carrying the same email and Volteo fields, and delete
		the old Expired row - a status-only flip would still read as
		expired at accept-time, since expiry is derived from `creation`."""
		old = self.make_invitation(
			email="resend-expired@example.com",
			role="Sales User",
			volteo_role="Volteo D2D Sales",
			first_name="Jan",
			last_name="Testowy",
			mobile_no="+48 111 222 333",
			linia_oze=0,
			linia_cp=1,
			linia_leady=1,
			widzi_prowizje=0,
			poziom_prowizji="Manager",
		)
		old.status = "Expired"
		old.save(ignore_permissions=True)
		old_name = old.name

		with patch.object(frappe, "sendmail"):
			result = resend_invitation(name=old_name)

		self.assertFalse(frappe.db.exists("CRM Invitation", old_name))

		new = frappe.get_doc("CRM Invitation", result["name"])
		self.assertEqual(new.email, "resend-expired@example.com")
		self.assertEqual(new.status, "Pending")
		self.assertTrue(new.key)
		self.assertEqual(new.volteo_role, "Volteo D2D Sales")
		self.assertEqual(new.first_name, "Jan")
		self.assertEqual(new.last_name, "Testowy")
		self.assertEqual(new.mobile_no, "+48 111 222 333")
		self.assertEqual(cint(new.linia_oze), 0)
		self.assertEqual(cint(new.linia_cp), 1)
		self.assertEqual(cint(new.linia_leady), 1)
		self.assertEqual(cint(new.widzi_prowizje), 0)
		self.assertEqual(new.poziom_prowizji, "Manager")

	def test_resend_invitation_on_accepted_row_raises(self):
		"""An Accepted invitation has already produced a User; resending it
		makes no sense and must be refused outright."""
		invitation = self.make_invitation(email="resend-accepted@example.com")
		invitation.accept()

		with self.assertRaises(frappe.ValidationError):
			resend_invitation(name=invitation.name)

	def test_invite_by_email_reinvites_expired_address(self):
		"""crm.api.invite_by_email's duplicate guard must count only Pending
		invitations. An address whose sole invitation is Expired must come
		back in `to_invite`, and afterwards exactly one row (Pending) must
		exist for that email - the prior Expired row is replaced, not kept
		alongside the new one."""
		old = self.make_invitation(email="reinvite-expired@example.com")
		old.status = "Expired"
		old.save(ignore_permissions=True)

		with patch.object(frappe, "sendmail"):
			result = invite_by_email(
				emails="reinvite-expired@example.com",
				role="Sales User",
				first_name="Anna",
				last_name="Nowak",
			)

		self.assertIn("reinvite-expired@example.com", result["to_invite"])

		rows = frappe.db.get_all(
			"CRM Invitation",
			filters={"email": "reinvite-expired@example.com"},
			fields=["name", "status"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].status, "Pending")
