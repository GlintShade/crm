# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add as assign
from frappe.model.document import Document

from crm.api.exchange_rate import get_exchange_rate
from crm.fcrm.doctype.crm_service_level_agreement.utils import get_sla
from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import add_status_change_log
from crm.fcrm.doctype.utils import add_or_remove_lost_reason_section_in_sidepanel
from crm.permissions.org_hierarchy import BYPASS_ROLES
from crm.volteo_pipeline import grupa_for, pipeline_for


class CRMDeal(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from crm.fcrm.doctype.crm_contacts.crm_contacts import CRMContacts
		from crm.fcrm.doctype.crm_products.crm_products import CRMProducts
		from crm.fcrm.doctype.crm_rolling_response_time.crm_rolling_response_time import (
			CRMRollingResponseTime,
		)
		from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import CRMStatusChangeLog

		annual_revenue: DF.Currency
		closed_date: DF.Date | None
		communication_status: DF.Link | None
		contact: DF.Link | None
		contacts: DF.Table[CRMContacts]
		currency: DF.Link | None
		deal_owner: DF.Link | None
		deal_value: DF.Currency
		email: DF.Data | None
		exchange_rate: DF.Float
		expected_closure_date: DF.Date | None
		expected_deal_value: DF.Currency
		first_name: DF.Data | None
		first_responded_on: DF.Datetime | None
		first_response_time: DF.Duration | None
		gender: DF.Link | None
		industry: DF.Link | None
		job_title: DF.Data | None
		last_name: DF.Data | None
		last_responded_on: DF.Datetime | None
		last_response_time: DF.Duration | None
		lead: DF.Link | None
		lead_name: DF.Data | None
		lost_notes: DF.Text | None
		lost_reason: DF.Link | None
		mobile_no: DF.Data | None
		naming_series: DF.Literal["CRM-DEAL-.YYYY.-"]
		net_total: DF.Currency
		next_step: DF.Data | None
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		organization: DF.Link | None
		organization_name: DF.Data | None
		phone: DF.Data | None
		probability: DF.Percent
		products: DF.Table[CRMProducts]
		response_by: DF.Datetime | None
		rolling_responses: DF.Table[CRMRollingResponseTime]
		salutation: DF.Link | None
		sla: DF.Link | None
		sla_creation: DF.Datetime | None
		sla_status: DF.Literal["", "First Response Due", "Rolling Response Due", "Failed", "Fulfilled"]
		source: DF.Link | None
		status: DF.Link
		status_change_log: DF.Table[CRMStatusChangeLog]
		territory: DF.Link | None
		total: DF.Currency
		website: DF.Data | None
	# end: auto-generated types

	def autoname(self):
		# Licznik `PRO-UMOWA-` jest wspólny dla wszystkich rodzajów umowy (jeden wiersz
		# tabSeries) i NIE resetuje się rocznie — numer porządkowy jest więc globalnie
		# unikalny na zawsze, a rok w nazwie jest wyłącznie informacyjny. Po 9999
		# `getseries` naturalnie przechodzi na 5 cyfr. Nieudany insert zostawia dziurę
		# w numeracji — to standardowe zachowanie `getseries`, nie obchodzimy go.
		from frappe.model.naming import getseries

		from crm.volteo_naming import SERIES_DIGITS, SERIES_KEY, code_for, format_deal_name

		self.name = format_deal_name(
			code_for(self.get("custom_rodzaj_umowy")),
			frappe.utils.nowdate()[2:4],
			getseries(SERIES_KEY, SERIES_DIGITS),
		)

	def before_validate(self):
		self.set_sla()

	def validate(self):
		self.validate_status()
		self.set_primary_contact()
		self.set_primary_email_mobile_no()
		if not self.is_new() and self.has_value_changed("deal_owner") and self.deal_owner:
			self.share_with_agent(self.deal_owner)
			self.assign_agent(self.deal_owner)
		if self.has_value_changed("status"):
			add_status_change_log(self)
			if frappe.db.get_value("CRM Deal Status", self.status, "type") == "Won":
				self.closed_date = frappe.utils.nowdate()
		self.validate_forecasting_fields()
		self.validate_lost_reason()
		self.update_exchange_rate()

	def after_insert(self):
		if self.deal_owner:
			if self.deal_owner != frappe.session.user:
				self.share_with_agent(self.deal_owner)
			self.assign_agent(self.deal_owner)

	def before_save(self):
		self.apply_sla()

	def validate_status(self):
		if self.is_new() and not self.status:
			if frappe.db.exists("CRM Deal Status", "Qualification"):
				self.status = "Qualification"
			else:
				self.status = frappe.get_all("CRM Deal Status", {"type": "Open"}, pluck="name")[0]

	def set_primary_contact(self, contact=None):
		if not self.contacts:
			return

		if not contact and len(self.contacts) == 1:
			self.contacts[0].is_primary = 1
		elif contact:
			for d in self.contacts:
				if d.contact == contact:
					d.is_primary = 1
				else:
					d.is_primary = 0

	def set_primary_email_mobile_no(self):
		if not self.contacts:
			self.email = ""
			self.mobile_no = ""
			self.phone = ""
			return

		if len([contact for contact in self.contacts if contact.is_primary]) > 1:
			frappe.throw(_("Only one {0} can be set as primary.").format(frappe.bold("Contact")))

		primary_contact_exists = False
		for d in self.contacts:
			if d.is_primary == 1:
				primary_contact_exists = True
				self.email = d.email.strip() if d.email else ""
				self.mobile_no = d.mobile_no.strip() if d.mobile_no else ""
				self.phone = d.phone.strip() if d.phone else ""
				break

		if not primary_contact_exists:
			self.email = ""
			self.mobile_no = ""
			self.phone = ""

	def assign_agent(self, agent):
		if not agent:
			return

		assignees = self.get_assigned_users()
		if assignees:
			for assignee in assignees:
				if agent == assignee:
					# the agent is already set as an assignee
					return

		assign({"assign_to": [agent], "doctype": "CRM Deal", "name": self.name}, ignore_permissions=True)

	def share_with_agent(self, agent):
		if not agent:
			return

		docshares = frappe.get_all(
			"DocShare",
			filters={"share_name": self.name, "share_doctype": self.doctype},
			fields=["name", "user"],
		)

		shared_with = [d.user for d in docshares] + [agent]

		for user in shared_with:
			if user == agent and not frappe.db.exists(
				"DocShare",
				{"user": agent, "share_name": self.name, "share_doctype": self.doctype},
			):
				frappe.share.add_docshare(
					self.doctype,
					self.name,
					agent,
					write=1,
					flags={"ignore_share_permission": True},
				)
			elif user != agent:
				frappe.share.remove(
					self.doctype,
					self.name,
					user,
					flags={"ignore_share_permission": True, "ignore_permissions": True},
				)

	def set_sla(self):
		"""
		Find an SLA to apply to the deal.
		"""
		if self.sla:
			return

		sla = get_sla(self)
		if not sla:
			self.first_responded_on = None
			self.first_response_time = None
			return
		self.sla = sla.name

	def apply_sla(self):
		"""
		Apply SLA if set.
		"""
		if not self.sla:
			return
		sla = frappe.get_last_doc("CRM Service Level Agreement", {"name": self.sla})
		if sla:
			sla.apply(self)

	def update_closed_date(self):
		"""
		Update the closed date based on the "Won" status.
		"""
		if self.status == "Won" and not self.closed_date:
			self.closed_date = frappe.utils.nowdate()

	def update_default_probability(self):
		"""
		Update the default probability based on the status.
		"""
		if not self.probability or self.probability == 0:
			self.probability = frappe.db.get_value("CRM Deal Status", self.status, "probability") or 0

	def update_expected_deal_value(self):
		"""
		Update the expected deal value based on the net total or total.
		"""
		if (
			frappe.db.get_single_value("FCRM Settings", "auto_update_expected_deal_value")
			and (self.net_total or self.total)
			and self.expected_deal_value
		):
			self.expected_deal_value = self.net_total or self.total

	def validate_forecasting_fields(self):
		self.update_closed_date()
		self.update_default_probability()
		self.update_expected_deal_value()
		if frappe.db.get_single_value("FCRM Settings", "enable_forecasting"):
			if not self.expected_deal_value or self.expected_deal_value == 0:
				frappe.throw(_("Expected deal value is required."), frappe.MandatoryError)
			if not self.expected_closure_date:
				frappe.throw(_("Expected closure date is required."), frappe.MandatoryError)

	def validate_lost_reason(self):
		"""
		Validate the lost reason if the status is set to "Lost".
		"""
		if self.status and frappe.get_cached_value("CRM Deal Status", self.status, "type") == "Lost":
			if not self.lost_reason:
				frappe.throw(_("Please specify a reason for losing the deal."), frappe.ValidationError)
			elif self.lost_reason == "Other" and not self.lost_notes:
				frappe.throw(_("Please specify the reason for losing the deal."), frappe.ValidationError)
		if self.has_value_changed("status"):
			add_or_remove_lost_reason_section_in_sidepanel(self)

	def update_exchange_rate(self):
		if self.has_value_changed("currency") or not self.exchange_rate:
			system_currency = frappe.db.get_single_value("FCRM Settings", "currency") or "USD"
			exchange_rate = 1
			if self.currency and self.currency != system_currency:
				exchange_rate = get_exchange_rate(self.currency, system_currency)

			self.db_set("exchange_rate", exchange_rate)

	# Domyślny widok listy szans dostosowany do B2C (klienci to osoby fizyczne, nie firmy).
	# `organization` zniknęło z kolumn: jest ukryte (hidden=1) i puste w każdej szansie,
	# a `crm/api/doc.py:365-368` i tak wyrzuca ukryte kolumny w locie.
	#
	# Kolumny "Szczegóły" i "Szansa" celowo dzielą `key: "name"`. Powód: pętla w
	# `crm/api/doc.py:356-358` dopisuje każdy klucz kolumny do listy pól SQL (`rows`),
	# więc pseudo-klucz bez odpowiadającego pola w bazie wywaliłby zapytanie — przycisk
	# "Szczegóły" (render po stronie Vue, osobne zadanie) musi więc siedzieć na
	# realnym polu, a `name` jest identyfikatorem, do którego przycisk i tak nawiguje.
	# Weryfikacja braku kolizji: `rows` już zawiera "name", więc obie kolumny trafiają
	# w warunek `if column.get("key") not in rows` jako "already present" i klucz nie
	# dubluje się w zapytaniu; `meta.get_field("name")` zwraca None (to nie DocField,
	# tylko klucz główny), więc żadna z dwóch kolumn nie zostaje usunięta jako ukryta.
	# Rozróżnienie renderowania obu kolumn robi etykieta, po stronie Vue.
	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Szczegóły",
				"type": "Data",
				"key": "name",
				"width": "7rem",
			},
			{
				"label": "Klient",
				"type": "Data",
				"key": "lead_name",
				"width": "11rem",
			},
			{
				"label": "Szansa",
				"type": "Data",
				"key": "name",
				"width": "10rem",
			},
			{
				"label": "Doradca",
				"type": "Link",
				"key": "deal_owner",
				"options": "User",
				"width": "10rem",
			},
			{
				"label": "Status",
				"type": "Link",
				"options": "CRM Deal Status",
				"key": "status",
				"width": "10rem",
			},
			{
				"label": "Telefon",
				"type": "Data",
				"key": "mobile_no",
				"width": "11rem",
			},
			{
				"label": "Mail",
				"type": "Data",
				"key": "email",
				"width": "12rem",
			},
			{
				"label": "Rodzaj",
				"type": "Select",
				"key": "custom_rodzaj_umowy",
				"width": "10rem",
			},
		]
		rows = [
			"name",
			"organization",
			"deal_value",
			"status",
			"custom_rodzaj_umowy",
			"email",
			"currency",
			"mobile_no",
			"deal_owner",
			"sla_status",
			"response_by",
			"first_response_time",
			"first_responded_on",
			"modified",
			"_assign",
			"lead_name",
			"first_name",
			"last_name",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "lead_name",
			"kanban_fields": '["deal_value", "email", "mobile_no", "_assign", "modified"]',
		}


@frappe.whitelist()
def add_contact(deal: str, contact: str):
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Not allowed to add contact to Deal"), frappe.PermissionError)

	deal = frappe.get_cached_doc("CRM Deal", deal)
	deal.append("contacts", {"contact": contact})
	deal.save()
	return True


@frappe.whitelist()
def remove_contact(deal: str, contact: str):
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Not allowed to remove contact from Deal"), frappe.PermissionError)

	deal = frappe.get_cached_doc("CRM Deal", deal)
	deal.contacts = [d for d in deal.contacts if d.contact != contact]
	deal.save()
	return True


@frappe.whitelist()
def set_primary_contact(deal: str, contact: str):
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Not allowed to set primary contact for Deal"), frappe.PermissionError)

	deal = frappe.get_cached_doc("CRM Deal", deal)
	deal.set_primary_contact(contact)
	deal.save()
	return True


def create_organization(doc):
	if not doc.get("organization_name"):
		return

	existing_organization = frappe.db.exists(
		"CRM Organization", {"organization_name": doc.get("organization_name")}
	)
	if existing_organization:
		return existing_organization

	organization = frappe.new_doc("CRM Organization")
	organization.update(
		{
			"organization_name": doc.get("organization_name"),
			"website": doc.get("website"),
			"territory": doc.get("territory"),
			"industry": doc.get("industry"),
			"annual_revenue": doc.get("annual_revenue"),
		}
	)
	organization.insert(ignore_permissions=True)
	return organization.name


def contact_exists(doc):
	email_exist = frappe.db.exists("Contact Email", {"email_id": doc.get("email")})
	mobile_exist = frappe.db.exists("Contact Phone", {"phone": doc.get("mobile_no")})

	doctype = "Contact Email" if email_exist else "Contact Phone"
	name = email_exist or mobile_exist

	if name:
		return frappe.db.get_value(doctype, name, "parent")

	return False


def create_contact(doc):
	existing_contact = contact_exists(doc)
	if existing_contact:
		return existing_contact

	contact = frappe.new_doc("Contact")
	contact.update(
		{
			"first_name": doc.get("first_name"),
			"last_name": doc.get("last_name"),
			"salutation": doc.get("salutation"),
			"company_name": doc.get("organization") or doc.get("organization_name"),
			"gender": doc.get("gender"),
		}
	)

	if doc.get("email"):
		contact.append("email_ids", {"email_id": doc.get("email"), "is_primary": 1})

	if doc.get("mobile_no"):
		contact.append("phone_nos", {"phone": doc.get("mobile_no"), "is_primary_mobile_no": 1})

	contact.insert(ignore_permissions=True)
	contact.reload()  # load changes by hooks on contact

	return contact.name


_ALWAYS_DROPPED_DEAL_KEYS = {
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"doctype",
	"idx",
	"naming_series",
}
"""System/identity keys a caller-supplied deal payload must never control, regardless of role."""


def _is_deal_input_bypass(user: str | None = None) -> bool:
	"""True when `user` (default: current session) is exempt from deal-input sanitization --
	Administrator or a role in `BYPASS_ROLES`. Shared between `sanitize_deal_input` and the two
	deal-creation call sites (`create_deal` here, `CRMLead.create_deal`) that need the same
	decision to gate whether a caller-supplied `deal_owner` may be trusted after insert.
	"""
	if not user:
		user = frappe.session.user
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)) & BYPASS_ROLES)


def sanitize_deal_input(doc: dict) -> dict:
	"""Return a sanitized COPY of a caller-controlled CRM Deal payload (`doc` is never mutated).

	Always drops: keys starting with `_`, and the identity/system keys in
	`_ALWAYS_DROPPED_DEAL_KEYS`. Also drops any key that is not an actual CRM Deal fieldname
	(per `frappe.get_meta`, which already includes `contacts`, a Table field). This closes the
	attribute-clobbering hole a caller could otherwise reach by naming an arbitrary Document
	attribute (e.g. `flags`) in the payload.

	For a non-bypass caller (see `_is_deal_input_bypass`), also drops every field the DocType
	meta marks `permlevel > 0` -- this is what stops a `Volteo D2D Sales` rep from spoofing
	`deal_owner` (permlevel 1, ops/crm-setup.py reassign lock) or the CP commission-secrecy
	fields (permlevel 2, ops/crm-koszty-montaz.py -- present in live meta, not in
	crm_deal.json, so only `frappe.get_meta` sees them; deliberately meta-driven rather than a
	hardcoded field list so it never drifts from what ops actually locks down). And rewrites
	`status` to the first step of the product line's pipeline (`crm.volteo_pipeline`) whenever
	the caller's status is not a member of that line's group -- prevents e.g. a Czyste Powietrze
	deal being created sitting on an OZE-only status. A deal whose `custom_rodzaj_umowy` has no
	known pipeline (unset/unrecognised) is left with whatever status the caller sent; Link
	validation on `status` covers existence.
	"""
	if not isinstance(doc, dict):
		frappe.throw(_("Invalid deal payload: expected an object of field values."))

	meta = frappe.get_meta("CRM Deal")
	valid_fieldnames = {df.fieldname for df in meta.fields}

	new_dict = {}
	for key, value in doc.items():
		if key.startswith("_") or key in _ALWAYS_DROPPED_DEAL_KEYS:
			continue
		if key not in valid_fieldnames:
			continue
		new_dict[key] = value

	if _is_deal_input_bypass():
		return new_dict

	high_permlevel_fields = {df.fieldname for df in meta.fields if (df.permlevel or 0) > 0}
	new_dict = {k: v for k, v in new_dict.items() if k not in high_permlevel_fields}

	rodzaj = new_dict.get("custom_rodzaj_umowy")
	grupa = grupa_for(rodzaj)
	if grupa is not None and new_dict.get("status") not in grupa:
		new_dict["status"] = pipeline_for(rodzaj)[0]

	return new_dict


@frappe.whitelist()
def create_deal(doc: dict):
	dane = sanitize_deal_input(doc)

	deal = frappe.new_doc("CRM Deal")

	# create_contact/create_organization read fields (first_name, email, website, ...) that are
	# not CRM Deal meta fields, so they deliberately keep reading the raw, unsanitized `doc` --
	# their own ignore_permissions=True inserts are out of scope for this fix.
	contact = doc.get("contact")
	if not contact and (
		doc.get("first_name") or doc.get("last_name") or doc.get("email") or doc.get("mobile_no")
	):
		contact = create_contact(doc)

	deal.update(
		{
			"organization": doc.get("organization") or create_organization(doc),
			"contacts": [{"contact": contact, "is_primary": 1}] if contact else [],
		}
	)

	dane.pop("organization", None)

	deal.update(dane)

	# Normal permission enforcement is the primary control here (no more
	# ignore_permissions=True): a Volteo D2D Sales rep has create rights on CRM Deal
	# (ops/crm-setup.py GRANTS), so insert() succeeds, but permlevel>0 fields (deal_owner,
	# the CP secrecy fields) get silently stripped for them at insert time -- sanitize_deal_input
	# already removed them too, this is belt-and-suspenders on the same mechanism.
	deal.insert()

	# deal_owner is permlevel 1: insert() strips a caller-supplied value for a non-privileged
	# creator, so it must be applied explicitly with db_set() afterwards, same pattern as
	# crm/api/czyste_powietrze.py's volteo_cp_create_deal. Only a bypass caller's requested
	# owner is honored -- the frontend always sends deal_owner = current user for reps anyway,
	# so this changes nothing for legitimate use.
	requested_owner = doc.get("deal_owner")
	owner = requested_owner if (_is_deal_input_bypass() and requested_owner) else frappe.session.user
	deal.db_set("deal_owner", owner)

	# db_set() does not run validate()/after_insert(), so CRMDeal.after_insert's own
	# share_with_agent + assign_agent (triggered when deal_owner is already set going into
	# insert()) never fires here -- deal_owner is only known after db_set. Replicate it
	# explicitly; both helpers are idempotent (assign_agent no-ops if already an assignee,
	# share_with_agent checks DocShare existence), so this is safe to call unconditionally,
	# including for a bypass caller for whom after_insert may already have run.
	if owner != frappe.session.user:
		deal.share_with_agent(owner)
	deal.assign_agent(owner)

	return deal.name
