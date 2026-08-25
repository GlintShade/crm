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
	from crm.api import volteo_ma_linie

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
			"show_sales_hierarchy_banner": frappe.db.count("CRM Lead") > 0,
			# VOLTEO: leads are unused in the current D2D-only phase and the Ecom line
			# is not in use, so the Leads tab is hidden globally for everyone — including
			# Administrator and System Manager, who bypass permission checks and would
			# otherwise still see it. Restoring the tab means editing this line and
			# rebuilding the image.
			"hide_leads": True,
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
