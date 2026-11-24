# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt

import frappe
from frappe import _
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
from frappe.translate import get_messages_for_boot, get_translated_doctypes
from frappe.utils import cint, get_system_timezone
from frappe.utils.telemetry import capture

from crm.api.oswiadczenie import _wymaga_oswiadczenia

no_cache = 1


def get_context():
	from crm.api import check_app_permission

	if not check_app_permission():
		frappe.throw(_("You do not have permission to access Frappe CRM"), frappe.PermissionError)

	redirect_to_set_password()

	frappe.db.commit()
	context = frappe._dict()
	context.boot = get_boot()
	if frappe.session.user != "Guest":
		capture("active_site", "crm")
	return context


def redirect_to_set_password():
	"""Send a logged in user who has no password to the set password page.

	Issue ops#154, variant B: invited users are logged in straight after
	accepting the invitation and never get a password, so they are locked out
	once the session expires. `needs_password_setup` only fires after the NDA
	is signed (or for users exempt from it), so the NDA screen always comes
	first; the NDA screen itself does a full load of /crm after signing, which
	lands here. This is also the safety net for accounts that already exist
	without a password: every full load of /crm sends them here until they set
	one. The Frappe page logs them in again and returns the default app
	(`/crm`) once the password is saved.

	The redirect uses the relative path of the reset link (`sciezka_wzgledna`):
	Frappe builds the link from `host_name`, which locally drops the port.
	"""
	from crm.api.user import needs_password_setup
	from crm.volteo_haslo import sciezka_wzgledna

	if not needs_password_setup():
		return

	user = frappe.get_doc("User", frappe.session.user)
	link = user._reset_password()

	# GET requests are rolled back, which would take the reset key with them.
	frappe.db.commit()  # nosemgrep

	# Relative path plus query: the absolute link from `get_url` may point at
	# the wrong host or port (locally it drops :8080).
	frappe.local.flags.redirect_location = sciezka_wzgledna(link)

	# 302, not the 301 default: a browser may cache a permanent redirect and
	# keep sending the user to a spent key long after they set a password. Set
	# on the instance so it works whether or not this Frappe version's
	# `Redirect` takes the status code as a constructor argument.
	redirect = frappe.Redirect()
	redirect.http_status_code = 302
	raise redirect


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return get_boot()


def _ukryj_zakladke(pole: str) -> bool:
	from crm.permissions.org_hierarchy import czy_admin_lub_bypass

	user = frappe.session.user
	if czy_admin_lub_bypass(user) or not frappe.get_meta("User").has_field(pole):
		return False
	return bool(cint(frappe.db.get_value("User", user, pole)))


def get_boot():
	from crm.api import volteo_ma_linie, volteo_widzi_prowizje
	from crm.api.user import needs_password_setup
	from crm.permissions.org_hierarchy import _ma_linie_leady

	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": get_default_route(),
			"site_name": frappe.local.site,
			"socketio_port": frappe.conf.socketio_port,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			"sysdefaults": frappe.defaults.get_defaults(),
			"is_demo_site": frappe.conf.get("is_demo_site"),
			"demo_data_created": frappe.db.get_default("crm_demo_data_created") == "1",
			"is_fc_site": is_fc_site(),
			# VOLTEO: this is the upstream marketing banner pointing admins at
			# Frappe's blog post about the CRM permissions model
			# (SalesHierarchyBanner.vue). After importing ~11k leads it would
			# light up for every admin with zero value — always suppressed.
			"show_sales_hierarchy_banner": False,
			# VOLTEO: restored to the upstream permission-gated expression —
			# Leads are no longer hidden globally. The D2D role's read access is
			# granted separately by ops/crm-leady-d2d.py. Since issue #27, the
			# per-user `custom_linia_leady` flag is layered on top of that: a
			# D2D rep without the flag has hide_leads forced True regardless of
			# the role-based `has_permission` check, mirroring the same gate
			# enforced authoritatively in
			# crm.permissions.org_hierarchy.get_lead_permission_query_conditions
			# / has_lead_permission — this boot key only drives client-side UI
			# (sidebar/mobile sidebar `window.hide_leads` checks).
			"hide_leads": not frappe.has_permission("CRM Lead", "read")
			or not _ma_linie_leady(frappe.session.user),
			# VOLTEO: per-user Leady module access switch (issue #27), boot
			# convenience mirroring volteo_linia_oze/volteo_linia_cp below —
			# server-side enforcement is the lead permission hooks, not this.
			"volteo_linia_leady": _ma_linie_leady(frappe.session.user),
			# VOLTEO: expose invoice-add capability so the Faktury tab can hide its add button for reps
			"can_create_faktura": frappe.has_permission("Volteo Faktura", "create"),
			# VOLTEO: restricted D2D rep (used to hide rep-only-forbidden UI affordances)
			"volteo_is_rep": (
				"Volteo D2D Sales" in frappe.get_roles()
				and not (set(frappe.get_roles()) & {"System Manager", "Volteo Core Admin", "Volteo Backend"})
			),
			# VOLTEO: gates the pencil (rename-attachment) icon in AttachmentArea.vue
			# (issue ops#73) — UI convenience only, mirrors the volteo_is_rep pattern
			# above. Authoritative enforcement is the BYPASS_ROLES + has_permission
			# check inside crm.api.volteo_zmien_nazwe_zalacznika.
			"volteo_edytuje_zalaczniki": frappe.session.user == "Administrator"
			or bool(set(frappe.get_roles()) & {"System Manager", "Volteo Core Admin", "Volteo Backend"}),
			# VOLTEO: first-login NDA gate — the SPA shows the signing screen (and
			# blocks the rest of the UI) when this is true. Server-side enforcement
			# for /api/* lives in crm.api.oswiadczenie.before_request; this boot key
			# only drives client-side UI. Fails open on any error (missing schema,
			# etc.) — see _wymaga_oswiadczenia docstring.
			"volteo_wymaga_oswiadczenia": _wymaga_oswiadczenia(frappe.session.user),
			# VOLTEO (ops#154, variant B): True when this user has no password and
			# will be sent to the set password page as soon as the NDA is signed
			# (same predicate as redirect_to_set_password, minus the NDA
			# condition). Oswiadczenie.vue reads it after signing: True means a
			# full load of /crm so the server can redirect, otherwise a plain
			# client-side route to Home. UI convenience only.
			"volteo_wymaga_hasla": needs_password_setup(frappe.session.user, ignore_nda=True),
			# VOLTEO: per-user product-line access switch (issue #16). Bypass-or-flag
			# logic mirrors crm.api.volteo_ma_linie; consumed by the frontend to hide
			# Kalkulator/Dokumenty entries for a line the user is switched off from.
			# Server-side enforcement lives in the API endpoints themselves — these
			# booleans are UI convenience only.
			"volteo_linia_oze": volteo_ma_linie("OZE"),
			"volteo_linia_cp": volteo_ma_linie("Czyste Powietrze"),
			# VOLTEO: per-user commission-visibility switch (issue #48) -- UI
			# convenience only (e.g. hiding the "Informacje dodatkowe" prowizja
			# box up front instead of waiting on a round-trip that would come
			# back empty); the server enforces the real gate in each endpoint
			# (volteo_cp_calc, volteo_prowizja_szansy) via
			# crm.api.volteo_widzi_prowizje. Deliberately no "poziom" boot key --
			# the client never decides how much of the commission breakdown to
			# show, the server trims the payload per volteo_poziom_prowizji.
			"volteo_widzi_prowizje": volteo_widzi_prowizje(frappe.session.user),
			# VOLTEO (ops#425): ukrycie zakladek Umowy / Klienci w menu i na trasach.
			# Menu i trasy tylko; dane zawezaja uprawnienia serwera. Zawsze False dla
			# Administratora i BYPASS_ROLES oraz gdy pola nie ma jeszcze w meta User.
			"volteo_ukryj_umowy": _ukryj_zakladke("custom_ukryj_umowy"),
			"volteo_ukryj_klienci": _ukryj_zakladke("custom_ukryj_klienci"),
			"translated_doctypes": get_translated_doctypes(),
			"translated_messages": get_messages_for_boot(),
			"timezone": {
				"system": get_system_timezone(),
				"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
				or get_system_timezone(),
			},
		}
	)


def get_default_route():
	return "/crm"
