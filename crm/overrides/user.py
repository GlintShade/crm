# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

from frappe.core.doctype.user.user import User

from crm.api.volteo_2fa_rejestracja import zalozyc_podmiane


class CustomUser(User):
	"""Bez zmian zachowania. Rdzen laduje klase User przy kazdym logowaniu, ZANIM zapyta o kod
	(`should_run_2fa`), wiec import tego modulu to pewny moment na podmiane twofactor (ops#422)."""


zalozyc_podmiane()
