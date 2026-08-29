# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Regression coverage for ops#35 ("[SEC][HIGH] Read-gated writes"): five
whitelisted endpoints checked `read` permission on the underlying `CRM Deal`
for an action that actually mutates state -- letting any user with mere read
access to a deal generate/replace a legally-relevant PDF (and, for the umowa
one, advance the deal's pipeline status), or push a Czyste Powietrze audit
through its review workflow:

- `crm.api.umowa.volteo_umowa_pdf`               (was `read`, now `write`)
- `crm.api.kredyt.volteo_kredyt_pdf`              (was `read`, now `write`)
- `crm.api.audyt_cp.volteo_audyt_cp_submit`       (was `read`, now `write`)
- `crm.api.audyt_cp.volteo_audyt_cp_set_status`   (was `read`, now `write`)
- `crm.api.audyt_cp.volteo_audyt_cp_set_verdict`  (was `read`, now `write`)

Style follows `crm/fcrm/doctype/crm_deal/test_api.py` (ops#31): `FrappeTestCase`
(via `crm.tests.CRMTestCase`), fixture users/roles created once per class,
`frappe.set_user` scoped around the call under test.

`frappe.has_permission` is mocked, but ONLY for `doctype == "CRM Deal"` and
ONLY for the duration of the single call under test (a `with` block) -- every
other doctype/ptype check, including ones Frappe itself makes while loading
unrelated documents during setup/teardown, falls through unchanged to the
real implementation. This isolates exactly the bug that was fixed (does the
endpoint ask `has_permission` for `"read"` or `"write"` on the deal) without
depending on the fine print of org-hierarchy/DocShare permission resolution,
which already has its own coverage in `crm/permissions/test_org_hierarchy.py`.
Real roles are still used for the checks these endpoints keep unchanged
(`_sprawdz_role`'s calculator-role check in umowa/kredyt, `_is_reviewer`/owner
in audyt_cp) so the tests exercise the actual, un-mocked authorization layers
that sit alongside the fixed gate.

For the three `audyt_cp` deny tests specifically, the "denied" caller is
REVIEWER (`Volteo Backend`, passes `_is_reviewer()`), not a plain D2D user.
`volteo_audyt_cp_submit`/`_set_status`/`_set_verdict` throw `PermissionError`
from TWO independent places: the deal write gate (the thing ops#35 fixed) and
`_is_reviewer()`/owner (unchanged, checked right after). A plain D2D user
fails both, so if the deal gate ever regressed back to `read`, the call would
still raise `PermissionError` from `_is_reviewer()` alone and the test would
stay green through the exact regression it exists to catch. Forcing REVIEWER
(who clears `_is_reviewer()`) with `_deal_permission_forced({"read"})` leaves
the deal write gate as the ONLY possible source of `PermissionError`, so a
read-gate regression flips the test red (the call would instead proceed past
both layers and fail later with a non-`PermissionError`, e.g. a missing
`Volteo Audyt CP` record). The umowa/kredyt PDF deny tests don't need this --
neither endpoint has a second, independent `PermissionError` source past the
deal gate -- so READONLY (plain `Volteo D2D Sales`) is unambiguous there.

None of `Volteo Umowa` / `Volteo Kredyt` / `Volteo Audyt CP` ship as doctype
fixtures in this fork -- they are created by ops scripts against a live site.
On a bare test site the functions under test will fail past the permission
gate (missing doctype/record) with something other than `frappe.PermissionError`;
that is expected and is exactly what the "authorized path is reached" tests
assert (anything but `frappe.PermissionError` proves the gate itself let the
call through).
"""

from contextlib import contextmanager
from unittest import mock

import frappe

from crm.api.audyt_cp import (
	volteo_audyt_cp_set_status,
	volteo_audyt_cp_set_verdict,
	volteo_audyt_cp_submit,
)
from crm.api.kredyt import volteo_kredyt_pdf
from crm.api.umowa import volteo_umowa_pdf
from crm.tests import CRMTestCase as FrappeTestCase

OWNER = "owner@sec35.test"
READONLY = "readonly@sec35.test"
REVIEWER = "reviewer@sec35.test"
TEST_USERS = (OWNER, READONLY, REVIEWER)

D2D_ROLE = "Volteo D2D Sales"  # in KALKULATOR_ROLE, NOT in BYPASS_ROLES/REVIEWER_ROLES
BACKEND_ROLE = "Volteo Backend"  # in REVIEWER_ROLES (== BYPASS_ROLES) for audyt_cp


@contextmanager
def _deal_permission_forced(allowed_ptypes):
	"""Patch `frappe.has_permission` so that, for `doctype == "CRM Deal"` only,
	`ptype` is granted iff it is in `allowed_ptypes`. Every other doctype/ptype
	check (including ones Frappe itself makes elsewhere in the call) is passed
	through unchanged to the real, un-mocked implementation.
	"""
	original = frappe.has_permission

	def _fake(doctype=None, ptype="read", doc=None, *args, **kwargs):
		if doctype == "CRM Deal":
			return ptype in allowed_ptypes
		return original(doctype, ptype, doc, *args, **kwargs)

	with mock.patch("frappe.has_permission", side_effect=_fake):
		yield


class TestUmowaKredytAudytWriteGates(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._d2d_role_created = _ensure_role(D2D_ROLE)
		cls._backend_role_created = _ensure_role(BACKEND_ROLE)
		_make_user(OWNER, roles=[D2D_ROLE])
		_make_user(READONLY, roles=[D2D_ROLE])
		_make_user(REVIEWER, roles=[BACKEND_ROLE])
		frappe.db.commit()  # nosemgrep: fixtures must persist across committing after_insert hooks

	@classmethod
	def tearDownClass(cls):
		_delete_test_documents()
		for email in TEST_USERS:
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)
		if cls._d2d_role_created:
			frappe.delete_doc("Role", D2D_ROLE, force=True, ignore_permissions=True)
		if cls._backend_role_created:
			frappe.delete_doc("Role", BACKEND_ROLE, force=True, ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: persist teardown cleanup of committed fixtures
		super().tearDownClass()

	def tearDown(self):
		frappe.set_user("Administrator")
		_delete_test_documents()
		frappe.db.commit()  # nosemgrep: persist per-test cleanup of committed fixtures

	def _assert_gate_reached_without_permission_error(self, fn, *args):
		"""Calls `fn(*args)` and fails only if it raises `frappe.PermissionError`.

		Any other outcome (success, or a downstream error from missing
		Volteo Umowa/Kredyt/Audyt CP setup on this test site) proves the
		CRM Deal permission gate itself let the call through.
		"""
		try:
			fn(*args)
		except frappe.PermissionError:
			self.fail(f"{fn.__name__}: write-authorized user was blocked by the CRM Deal permission gate")
		except Exception:
			pass

	# -- crm.api.umowa.volteo_umowa_pdf --------------------------------------

	def test_umowa_pdf_denies_read_only_user(self):
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(READONLY)
			with _deal_permission_forced({"read"}):
				self.assertRaises(frappe.PermissionError, volteo_umowa_pdf, deal.name)
		finally:
			frappe.set_user("Administrator")

	def test_umowa_pdf_reaches_body_for_write_user(self):
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(OWNER)
			with _deal_permission_forced({"read", "write"}):
				self._assert_gate_reached_without_permission_error(volteo_umowa_pdf, deal.name)
		finally:
			frappe.set_user("Administrator")

	# -- crm.api.kredyt.volteo_kredyt_pdf ------------------------------------

	def test_kredyt_pdf_denies_read_only_user(self):
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(READONLY)
			with _deal_permission_forced({"read"}):
				self.assertRaises(frappe.PermissionError, volteo_kredyt_pdf, deal.name)
		finally:
			frappe.set_user("Administrator")

	def test_kredyt_pdf_reaches_body_for_write_user(self):
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(OWNER)
			with _deal_permission_forced({"read", "write"}):
				self._assert_gate_reached_without_permission_error(volteo_kredyt_pdf, deal.name)
		finally:
			frappe.set_user("Administrator")

	# -- crm.api.audyt_cp.volteo_audyt_cp_submit -----------------------------

	def test_audyt_cp_submit_denies_reviewer_without_deal_write(self):
		# REVIEWER (not READONLY): _is_reviewer() must pass so the deal write
		# gate is the ONLY possible source of PermissionError here -- see the
		# module docstring for why a plain D2D user can't isolate the gate.
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(REVIEWER)
			with _deal_permission_forced({"read"}):
				self.assertRaises(frappe.PermissionError, volteo_audyt_cp_submit, deal.name)
		finally:
			frappe.set_user("Administrator")

	def test_audyt_cp_submit_reaches_body_for_reviewer(self):
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(REVIEWER)
			with _deal_permission_forced({"read", "write"}):
				self._assert_gate_reached_without_permission_error(volteo_audyt_cp_submit, deal.name)
		finally:
			frappe.set_user("Administrator")

	# -- crm.api.audyt_cp.volteo_audyt_cp_set_status -------------------------

	def test_audyt_cp_set_status_denies_reviewer_without_deal_write(self):
		# REVIEWER (not READONLY) -- see test_audyt_cp_submit_denies_reviewer_without_deal_write.
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(REVIEWER)
			with _deal_permission_forced({"read"}):
				self.assertRaises(frappe.PermissionError, volteo_audyt_cp_set_status, deal.name, "Zatwierdzony")
		finally:
			frappe.set_user("Administrator")

	def test_audyt_cp_set_status_reaches_body_for_reviewer(self):
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(REVIEWER)
			with _deal_permission_forced({"read", "write"}):
				self._assert_gate_reached_without_permission_error(
					volteo_audyt_cp_set_status, deal.name, "Zatwierdzony"
				)
		finally:
			frappe.set_user("Administrator")

	# -- crm.api.audyt_cp.volteo_audyt_cp_set_verdict ------------------------

	def test_audyt_cp_set_verdict_denies_reviewer_without_deal_write(self):
		# REVIEWER (not READONLY) -- see test_audyt_cp_submit_denies_reviewer_without_deal_write.
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(REVIEWER)
			with _deal_permission_forced({"read"}):
				self.assertRaises(
					frappe.PermissionError, volteo_audyt_cp_set_verdict, deal.name, "some_key", "accepted", None
				)
		finally:
			frappe.set_user("Administrator")

	def test_audyt_cp_set_verdict_reaches_body_for_reviewer(self):
		deal = _make_deal(OWNER)
		try:
			frappe.set_user(REVIEWER)
			with _deal_permission_forced({"read", "write"}):
				self._assert_gate_reached_without_permission_error(
					volteo_audyt_cp_set_verdict, deal.name, "some_key", "accepted", None
				)
		finally:
			frappe.set_user("Administrator")


def _delete_test_documents():
	"""Remove deals created by the test users."""
	frappe.db.delete("CRM Deal", {"deal_owner": ("in", TEST_USERS)})


def _ensure_role(role_name: str) -> bool:
	if frappe.db.exists("Role", role_name):
		return False
	frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
		ignore_permissions=True
	)
	return True


def _make_user(email, roles=None):
	if frappe.db.exists("User", email):
		u = frappe.get_doc("User", email)
	else:
		u = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	for role in roles or []:
		u.add_roles(role)
	return u


def _make_deal(owner_email):
	doc = frappe.get_doc({"doctype": "CRM Deal", "deal_owner": owner_email, "organization": "Test Org SEC35"})
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	return doc.insert(ignore_permissions=True)
