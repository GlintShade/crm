# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt

import frappe
from frappe import _
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
from frappe.translate import get_messages_for_boot, get_translated_doctypes
from frappe.utils import cint, get_system_timezone
from frappe.utils.telemetry import capture

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
			# VOLTEO: hide the Leads nav for users without CRM Lead read access (e.g. D2D reps)
			"hide_leads": not frappe.has_permission("CRM Lead", "read"),
			# VOLTEO: expose invoice-add capability so the Faktury tab can hide its add button for reps
			"can_create_faktura": frappe.has_permission("Volteo Faktura", "create"),
			# VOLTEO: restricted D2D rep (used to hide rep-only-forbidden UI affordances)
			"volteo_is_rep": (
				"Volteo D2D Sales" in frappe.get_roles()
				and not (set(frappe.get_roles()) & {"System Manager", "Volteo Core Admin", "Volteo Backend"})
			),
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
