# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
#
# Ported from upstream frappe/crm (d9f1d1c9b, c7fdb2161, dcf73bc0f) and adapted
# to ops#154 variant B: the password is only forced once the NDA is signed.
# Bench only (needs a real Frappe site).

from unittest.mock import patch

import frappe
from frappe.utils.data import sha256_hash
from frappe.utils.password import update_password

from crm.api.user import has_password, needs_password_setup
from crm.tests import CRMTestCase
from crm.www.crm import get_boot, get_context, redirect_to_set_password

STRONG_PASSWORD = "Qx7#mLp2vT9!"

# needs_password_setup imports the NDA predicate lazily from this module, so
# patching the module attribute is what the function sees.
NDA = "crm.api.oswiadczenie._wymaga_oswiadczenia"


def make_user(email, roles=None):
	"""A user created the way CRM Invitation and scripts create one: no password."""
	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, ignore_permissions=True, force=True)

	user = frappe.get_doc(
		doctype="User",
		user_type="System User",
		email=email,
		first_name=email.split("@")[0].title(),
		send_welcome_email=0,
	).insert(ignore_permissions=True)

	if roles:
		user.append_roles(*roles)
		user.save(ignore_permissions=True)

	return user


class TestPasswordSetup(CRMTestCase):
	def setUp(self):
		# NDA signed (or exempt) by default; tests that need the NDA pending
		# patch it to True themselves.
		nda = patch(NDA, return_value=False)
		self.nda = nda.start()
		self.addCleanup(nda.stop)

		self.user = make_user("no-password@example.com", roles=["System Manager"])
		frappe.set_user(self.user.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.flags.redirect_location = None
		frappe.local.flags.commit = False
		frappe.local.system_settings = None
		frappe.db.rollback()

	def make_sso_user(self):
		frappe.set_user("Administrator")
		self.user.append("social_logins", {"provider": "google", "userid": "1234567890"})
		self.user.save(ignore_permissions=True)
		frappe.set_user(self.user.name)

	# ---- needs_password_setup ----

	def test_needs_setup_for_user_without_password(self):
		self.assertFalse(has_password(self.user.name))
		self.assertTrue(needs_password_setup())

	def test_does_not_need_setup_once_password_exists(self):
		update_password(user=self.user.name, pwd=STRONG_PASSWORD)

		self.assertTrue(has_password(self.user.name))
		self.assertFalse(needs_password_setup())
		self.assertFalse(needs_password_setup(ignore_nda=True))

	def test_does_not_need_setup_while_nda_is_pending(self):
		"""Variant B: the NDA comes first, the password right after it."""
		self.nda.return_value = True

		self.assertFalse(needs_password_setup())
		# the boot flag ignores the NDA: this user will be sent there after signing
		self.assertTrue(needs_password_setup(ignore_nda=True))

	def test_does_not_need_setup_for_sso_user(self):
		"""No password is the correct state for someone who signs in via SSO."""
		self.make_sso_user()

		self.assertFalse(needs_password_setup())

	def test_does_not_need_setup_for_ldap_user(self):
		frappe.db.set_single_value("LDAP Settings", "enabled", 1)

		self.assertFalse(needs_password_setup())

	def test_does_not_need_setup_when_password_login_is_disabled(self):
		# not change_settings: it saves the doc, and validating System Settings
		# fails on a bare site that has no language or time zone set
		frappe.db.set_single_value("System Settings", "disable_user_pass_login", 1)
		frappe.local.system_settings = None

		self.assertFalse(needs_password_setup())

	def test_technical_accounts_never_need_setup(self):
		self.assertFalse(needs_password_setup("Administrator"))
		self.assertFalse(needs_password_setup("Guest"))

	def test_fails_open_on_error(self):
		with patch("crm.api.user.has_password", side_effect=RuntimeError("boom")):
			self.assertFalse(needs_password_setup())

	# ---- redirect ----

	def test_redirects_to_set_password_page_with_a_working_key(self):
		with patch.object(frappe.db.__class__, "commit") as commit:
			with self.assertRaises(frappe.Redirect) as raised:
				redirect_to_set_password()

			# the reset key is written on a GET, which is rolled back otherwise
			self.assertTrue(commit.called)

		# a 301 would be cached by the browser and outlive the key it points at
		self.assertEqual(raised.exception.http_status_code, 302)

		link = frappe.local.flags.redirect_location
		self.assertIn("/update-password?key=", link)

		key = link.split("key=")[1]
		self.assertEqual(frappe.db.get_value("User", self.user.name, "reset_password_key"), sha256_hash(key))

	def test_no_redirect_for_user_who_has_a_password(self):
		update_password(user=self.user.name, pwd=STRONG_PASSWORD)

		redirect_to_set_password()

		self.assertIsNone(frappe.local.flags.redirect_location)

	def test_no_redirect_while_nda_is_pending(self):
		self.nda.return_value = True

		redirect_to_set_password()

		self.assertIsNone(frappe.local.flags.redirect_location)

	def test_no_redirect_for_sso_user(self):
		self.make_sso_user()

		redirect_to_set_password()

		self.assertIsNone(frappe.local.flags.redirect_location)

	def test_crm_page_load_redirects_a_user_without_a_password(self):
		"""The redirect is wired into the page the user actually opens."""
		with patch.object(frappe.db.__class__, "commit"):
			with self.assertRaises(frappe.Redirect):
				get_context()

		self.assertIn("/update-password?key=", frappe.local.flags.redirect_location)

	# ---- boot flag ----

	def test_boot_flag_set_for_user_without_password(self):
		self.nda.return_value = True

		self.assertTrue(get_boot().volteo_wymaga_hasla)

	def test_boot_flag_clear_for_user_with_password(self):
		update_password(user=self.user.name, pwd=STRONG_PASSWORD)

		self.assertFalse(get_boot().volteo_wymaga_hasla)
