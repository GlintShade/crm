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

	frappe.db.commit()
	context = frappe._dict()
	context.boot = get_boot()
	if frappe.session.user != "Guest":
		capture("active_site", "crm")
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return get_boot()


def get_boot():
	from crm.api import volteo_ma_linie, volteo_widzi_prowizje
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
			# VOLTEO: first-login NDA gate — the SPA shows the signing screen (and
			# blocks the rest of the UI) when this is true. Server-side enforcement
			# for /api/* lives in crm.api.oswiadczenie.before_request; this boot key
			# only drives client-side UI. Fails open on any error (missing schema,
			# etc.) — see _wymaga_oswiadczenia docstring.
			"volteo_wymaga_oswiadczenia": _wymaga_oswiadczenia(frappe.session.user),
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
