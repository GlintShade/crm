# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add as assign
from frappe.model.document import Document
from frappe.utils import validate_email_address

from crm.fcrm.doctype.crm_service_level_agreement.utils import get_sla
from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import (
	add_status_change_log,
)
from crm.fcrm.doctype.utils import add_or_remove_lost_reason_section_in_sidepanel
from crm.volteo_lista_szans import FILTER_FIELDS_LEAD, SORT_FIELDS_LEAD


class CRMLead(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from crm.fcrm.doctype.crm_products.crm_products import CRMProducts
		from crm.fcrm.doctype.crm_rolling_response_time.crm_rolling_response_time import (
			CRMRollingResponseTime,
		)
		from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import CRMStatusChangeLog

		annual_revenue: DF.Currency
		communication_status: DF.Link | None
		converted: DF.Check
		email: DF.Data | None
		facebook_form_id: DF.Data | None
		facebook_lead_id: DF.Data | None
		first_name: DF.Data
		first_responded_on: DF.Datetime | None
		first_response_time: DF.Duration | None
		gender: DF.Link | None
		image: DF.AttachImage | None
		industry: DF.Link | None
		job_title: DF.Data | None
		last_name: DF.Data | None
		last_responded_on: DF.Datetime | None
		last_response_time: DF.Duration | None
		lead_name: DF.Data | None
		lead_owner: DF.Link | None
		lost_notes: DF.Text | None
		lost_reason: DF.Link | None
		middle_name: DF.Data | None
		mobile_no: DF.Data | None
		naming_series: DF.Literal["CRM-LEAD-.YYYY.-"]
		net_total: DF.Currency
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		organization: DF.Data | None
		phone: DF.Data | None
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

	def before_validate(self):
		self.set_sla()

	def validate(self):
		self.validate_status()
		self.set_full_name()
		self.set_lead_name()
		self.set_title()
		self.validate_email()
		self.validate_lost_reason()
		if not self.is_new() and self.has_value_changed("lead_owner") and self.lead_owner:
			self.share_with_agent(self.lead_owner)
			self.assign_agent(self.lead_owner)
		if self.has_value_changed("status"):
			add_status_change_log(self)

	def after_insert(self):
		if self.lead_owner:
			if self.lead_owner != frappe.session.user:
				self.share_with_agent(self.lead_owner)
			self.assign_agent(self.lead_owner)

	def before_save(self):
		self.apply_sla()

	def validate_status(self):
		if self.is_new() and not self.status:
			if frappe.db.exists("CRM Lead Status", "New"):
				self.status = "New"
			else:
				self.status = frappe.get_all("CRM Lead Status", {"type": "Open"}, pluck="name")[0]

	def set_full_name(self):
		if self.first_name:
			self.lead_name = " ".join(
				name
				for name in [
					self.salutation,
					self.first_name,
					self.middle_name,
					self.last_name,
				]
				if name
			)

	def set_lead_name(self):
		if not self.lead_name:
			# Check for leads being created through data import
			if not self.organization and not self.email and not self.flags.ignore_mandatory:
				frappe.throw(_("A Lead requires either a person's name or an organization's name"))
			elif self.organization:
				self.lead_name = self.organization
			elif self.email:
				self.lead_name = self.email.split("@")[0]
			else:
				self.lead_name = "Unnamed Lead"

	def set_title(self):
		self.title = self.organization or self.lead_name

	def validate_email(self):
		if self.email:
			if not self.flags.ignore_email_validation:
				validate_email_address(self.email, throw=True)

			if self.email == self.lead_owner:
				frappe.throw(_("Lead Owner cannot be same as the Lead Email Address"))

	def validate_lost_reason(self):
		"""
		Validate the lost reason if the status is set to "Lost".
		"""
		if self.status and frappe.get_cached_value("CRM Lead Status", self.status, "type") == "Lost":
			if not self.lost_reason:
				frappe.throw(_("Please specify a reason for losing the lead."), frappe.ValidationError)
			elif self.lost_reason == "Other" and not self.lost_notes:
				frappe.throw(_("Please specify the reason for losing the lead."), frappe.ValidationError)
		if self.has_value_changed("status"):
			add_or_remove_lost_reason_section_in_sidepanel(self)

	def assign_agent(self, agent):
		if not agent:
			return

		assignees = self.get_assigned_users()
		if assignees:
			for assignee in assignees:
				if agent == assignee:
					# the agent is already set as an assignee
					return

		assign({"assign_to": [agent], "doctype": "CRM Lead", "name": self.name}, ignore_permissions=True)

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
		Find an SLA to apply to the lead.
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

	@staticmethod
	def get_non_filterable_fields():
		return ["converted"]

	# VOLTEO (ops#94): kolejnosc kolumn listy leadow jest doslowna z
	# nagrania wlasciciela (issue ops#94), dopasowana do przeplywu CC,
	# celowo bez maila. Dwie pseudo-kolumny dziela klucz z realnym polem
	# (wzorzec "Szczegoly" z crm_deal.py:default_list_data): "Szczegoly"
	# dzieli `key: "name"`, "Komentarze" dzieli `key: "_comment_count"`,
	# ktore nie jest prawdziwym DocFieldem, wiec `crm.api.doc.get_data`
	# obsluguje je specjalnie (patrz komentarz "VOLTEO (ops#94)" tamze).
	# Render (ikona + licznik, klik otwiera `KomentarzeLeadaModal.vue` bez
	# nawigacji) jest po stronie Vue w `LeadsListView.vue`.
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
				"label": "Komentarze",
				"type": "Data",
				"key": "_comment_count",
				"width": "3.5rem",
			},
			{
				"label": "Zasady",
				"type": "Select",
				"key": "custom_zasady_dotacji",
				"width": "8rem",
			},
			{
				"label": "Telefon",
				"type": "Data",
				"key": "mobile_no",
				"width": "11rem",
			},
			{
				"label": "Status CC",
				"type": "Link",
				"options": "CRM Lead Status",
				"key": "status",
				"width": "12rem",
			},
			{
				"label": "Kolejny kontakt",
				"type": "Date",
				"key": "custom_kolejny_kontakt",
				"width": "11rem",
			},
			{
				"label": "Termin spotkania",
				"type": "Datetime",
				"key": "custom_termin_spotkania",
				"width": "13rem",
			},
			{
				"label": "Obecne produkty",
				"type": "Data",
				"key": "custom_posiadane_produkty",
				"width": "10rem",
			},
			{
				"label": "Przypisany handlowiec",
				"type": "Link",
				"options": "User",
				"key": "lead_owner",
				"width": "10rem",
			},
			{
				# Permlevel 2 (issue ops#89): dla `Volteo D2D Sales` (handlowca)
				# pole przychodzi puste, nie znika z kolumn. `meta.get_field`
				# w `get_data` sprawdza tylko `hidden`, nie permlevel, a
				# `get_permitted_fields` po stronie `frappe.get_list` sam
				# wytnie wartosc z wiersza dla wywolujacego bez odczytu.
				"label": "Przypisany CC",
				"type": "Link",
				"options": "User",
				"key": "custom_cc",
				"width": "10rem",
			},
			{
				"label": "Ulica",
				"type": "Data",
				"key": "custom_install_address",
				"width": "10rem",
			},
			{
				"label": "Nr domu",
				"type": "Data",
				"key": "custom_nr_domu",
				"width": "6rem",
			},
			{
				"label": "Kod pocztowy",
				"type": "Data",
				"key": "custom_install_postal_code",
				"width": "8rem",
			},
			{
				"label": "Miejscowość",
				"type": "Data",
				"key": "custom_install_city",
				"width": "10rem",
			},
			{
				"label": "Województwo",
				"type": "Select",
				"key": "custom_voivodeship",
				"width": "10rem",
			},
			{
				"label": "Powiat",
				"type": "Data",
				"key": "custom_powiat",
				"width": "8rem",
			},
			{
				"label": "Status handlowy",
				"type": "Select",
				"key": "custom_status_handlowy",
				"width": "10rem",
			},
			{
				"label": "Status źródła",
				"type": "Select",
				"key": "custom_status_zrodla",
				"width": "10rem",
			},
			{
				"label": "Źródło",
				"type": "Data",
				"key": "custom_import_source",
				"width": "8rem",
			},
			{
				"label": "Ostatnia zmiana",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"lead_name",
			"_comment_count",
			"custom_zasady_dotacji",
			"mobile_no",
			"status",
			"custom_kolejny_kontakt",
			"custom_termin_spotkania",
			"custom_posiadane_produkty",
			"lead_owner",
			"custom_cc",
			"custom_install_address",
			"custom_nr_domu",
			"custom_install_postal_code",
			"custom_install_city",
			"custom_voivodeship",
			"custom_powiat",
			"custom_status_handlowy",
			"custom_status_zrodla",
			"custom_import_source",
			"modified",
			# Nie sa osobnymi kolumnami, ale karmia awatar w pseudo-kolumnie
			# "Klient" (patrz `Leads.vue::parseRows`, galaz `row == 'lead_name'`).
			"first_name",
			"image",
		]
		return {"columns": columns, "rows": rows}

	# Allowlisty sortowania/filtrowania listy leadow (ops#94): patrz
	# `crm.volteo_lista_szans` dla ksztaltu krotek i uzasadnienia. Odczytywane
	# przez `crm.api.doc.sort_options` / `get_filterable_fields`, ktore
	# sprawdzaja `hasattr(controller, "volteo_sort_fields"/"volteo_filter_fields")`.
	@staticmethod
	def volteo_sort_fields():
		return SORT_FIELDS_LEAD

	@staticmethod
	def volteo_filter_fields():
		return FILTER_FIELDS_LEAD

	@staticmethod
	def default_kanban_settings():
		# VOLTEO: B2C — organization swapped for the install-site city.
		return {
			"column_field": "status",
			"title_field": "lead_name",
			"kanban_fields": '["custom_install_city", "email", "mobile_no", "_assign", "modified"]',
		}
