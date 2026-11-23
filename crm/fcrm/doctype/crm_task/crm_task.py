# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as assign
from frappe.desk.form.assign_to import remove as unassign
from frappe.model.document import Document

from crm.volteo_powiadomienia_zadan import (
	ZNACZNIK_ZADANIA_AUTOMATYCZNEGO,
	autor_wzmiankowany,
	czy_zadanie_automatyczne,
	etykieta_statusu,
	nowo_dodani,
	tekst_powiadomienia,
	wybierz_odbiorcow,
	wyczysc_do_wiadomosci,
	wykryj_zdarzenia,
)
from crm.volteo_zadania_tresc import (
	POLA_TRESCI,
	czy_zmiana_tresci_dozwolona,
	wartosci_do_zapisu,
)

POLE_DW = "custom_do_wiadomosci"
"""Table MultiSelect "Do wiadomosci" (ops#411): Custom Field z ops, wiersze `Volteo Zadanie DW`."""


class CRMTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		assigned_to: DF.Link | None
		description: DF.TextEditor | None
		due_date: DF.Datetime | None
		name: DF.Int | None
		priority: DF.Literal["Low", "Medium", "High"]
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		start_date: DF.Date | None
		status: DF.Literal["Todo", "In Progress", "Done", "Canceled"]
		title: DF.Data
	# end: auto-generated types

	def after_insert(self):
		self.assign_to()
		if self.flags.get("volteo_zadanie_automatyczne"):
			self.zapisz_znacznik_automatycznego()
		# ops#411: jeden dzwonek "Dodano Cie do wiadomosci" dla kazdej osoby z nowego zadania.
		self.powiadom_dodanych(nowo_dodani([], _do_wiadomosci(self)))

	def powiadom_dodanych(self, nowi: list[str]):
		if not nowi:
			return
		try:
			powiadom_o_zdarzeniu(self, "dw", tylko=nowi)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "CRM Task: powiadomienie Do wiadomosci")

	def zapisz_znacznik_automatycznego(self):
		"""Trwaly znacznik zadania automatycznego (ops#360): `Comment` typu `Info`.
		Nie jest wpisem rozmowy (ta czyta tylko `comment_type = Comment`). Blad nie
		cofa zapisu zadania."""
		try:
			from crm.volteo_aktywnosc import zapisz_slad

			zapisz_slad(str(self.name), ZNACZNIK_ZADANIA_AUTOMATYCZNEGO, doctype="CRM Task")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "CRM Task: znacznik zadania automatycznego")

	def on_update(self):
		"""Dzwonek dla autora zadania o zmianie statusu, terminu lub wykonawcy
		dokonanej przez kogos innego (ops#360). Nigdy nie cofa zapisu."""
		try:
			przed = self.get_doc_before_save()
			if not przed:
				return
			pola = ("status", "due_date", "assigned_to")
			zdarzenia = wykryj_zdarzenia(
				{pole: przed.get(pole) for pole in pola}, {pole: self.get(pole) for pole in pola}
			)
			# Nowy wykonawca (i poprzedni) dostaja juz dzwonek przypisania z ToDo.
			# Dotyczy tylko zdarzenia "wykonawca"; przy statusie i terminie
			# wykonawca dostaje dzwonek jak kazdy odbiorca.
			zmiana_wykonawcy = {przed.get("assigned_to"), self.get("assigned_to")} - {None, ""}
			for zdarzenie in zdarzenia:
				pomin = zmiana_wykonawcy if zdarzenie == "wykonawca" else None
				powiadom_o_zdarzeniu(self, zdarzenie, pomin=pomin)
			self.powiadom_dodanych(
				nowo_dodani([w.user for w in przed.get(POLE_DW) or []], _do_wiadomosci(self))
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "CRM Task: powiadomienie autora zadania")

	def before_validate(self):
		# Status "Backlog" usuniety 2026-11-16; stary frontend w cache moze go jeszcze wyslac.
		if self.status == "Backlog":
			self.status = "Todo"

	def validate(self):
		self.pilnuj_autora_tresci()
		self.pilnuj_do_wiadomosci()
		if self.is_new() or not self.assigned_to:
			return

		if self.get_doc_before_save().assigned_to != self.assigned_to:
			self.unassign_from_previous_user(self.get_doc_before_save().assigned_to)
			self.assign_to()

	def pilnuj_do_wiadomosci(self):
		"""ops#411: ta sama osoba nie jest naraz odpowiedzialna i "Do wiadomosci", a lista
		nie ma duplikatow: serwer cicho usuwa nadmiar, bez bledu. Pole jeszcze nie istnieje
		(skrypt ops nie ruszyl), wiec `get` daje None: nic do zrobienia."""
		wiersze = self.get(POLE_DW)
		if wiersze is None:
			return
		osoby = [w.user for w in wiersze]
		czyste = wyczysc_do_wiadomosci(osoby, self.assigned_to)
		if czyste != osoby:
			self.set(POLE_DW, [{"user": u} for u in czyste])

	def pilnuj_autora_tresci(self):
		"""ops#412: tytul i opis istniejacego zadania zmienia tylko autor. Caly zapis
		jest odrzucany. Kod wewnetrzny przechodzi flaga `volteo_tresc_systemowa`."""
		przed = None if self.is_new() else self.get_doc_before_save()
		if not przed or self.flags.get("volteo_tresc_systemowa"):
			return
		stare = {pole: przed.get(pole) for pole in POLA_TRESCI}
		nowe = {pole: self.get(pole) for pole in POLA_TRESCI}
		if not czy_zmiana_tresci_dozwolona(przed.owner, frappe.session.user, stare, nowe):
			frappe.throw(_("Tytuł i opis zadania może zmienić tylko autor zadania."), frappe.PermissionError)
		for pole, wartosc in wartosci_do_zapisu(przed.owner, frappe.session.user, stare, nowe).items():
			self.set(pole, wartosc)

	def unassign_from_previous_user(self, user: str | None):
		if user:
			unassign(self.doctype, self.name, user)

	def assign_to(self):
		if self.assigned_to:
			assign(
				{
					"assign_to": [self.assigned_to],
					"doctype": self.doctype,
					"name": self.name,
					"description": self.title or self.description,
				}
			)

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Title",
				"type": "Data",
				"key": "title",
				"width": "16rem",
			},
			{
				"label": "Klient",
				"type": "Data",
				"key": "_klient",
				"width": "11.5rem",
			},
			{
				"label": "Status",
				"type": "Select",
				"key": "status",
				"width": "8rem",
			},
			{
				"label": "Priority",
				"type": "Select",
				"key": "priority",
				"width": "8rem",
			},
			{
				"label": "Due Date",
				"type": "Date",
				"key": "due_date",
				"width": "8rem",
			},
			{
				"label": "Osoba odpowiedzialna",
				"type": "Link",
				"key": "assigned_to",
				"width": "10rem",
			},
			{
				"label": "Do wiadomości",
				"type": "Data",
				"key": "_dw",
				"width": "11rem",
			},
			{
				"label": "Szansa",
				"type": "Dynamic Link",
				"key": "reference_docname",
				"options": "reference_doctype",
				"width": "10rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]

		rows = [
			"name",
			"title",
			"description",
			"assigned_to",
			"due_date",
			"status",
			"priority",
			"reference_doctype",
			"reference_docname",
			"modified",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "title",
			"kanban_fields": '["description", "priority", "creation"]',
		}


def _czy_automatyczne(zadanie) -> bool:
	ma_znacznik = bool(
		frappe.db.exists(
			"Comment",
			{
				"reference_doctype": "CRM Task",
				"reference_name": str(zadanie.name),
				"comment_type": "Info",
				"content": ZNACZNIK_ZADANIA_AUTOMATYCZNEGO,
			},
		)
	)
	return czy_zadanie_automatyczne(ma_znacznik, zadanie.get("title"), zadanie.get("reference_doctype"))


def _wykonawcy(zadanie) -> list[str]:
	"""`assigned_to` oraz osoby z otwartym ToDo na zadaniu."""
	todo = frappe.get_all(
		"ToDo",
		filters={"reference_type": "CRM Task", "reference_name": str(zadanie.name), "status": "Open"},
		pluck="allocated_to",
	)
	return [zadanie.get("assigned_to"), *todo]


def _do_wiadomosci(zadanie) -> list[str]:
	"""Osoby z listy "Do wiadomosci" zadania (ops#411); pusta lista, gdy pole nie istnieje."""
	return [w.user for w in zadanie.get(POLE_DW) or [] if w.user]


def powiadom_o_zdarzeniu(
	zadanie,
	zdarzenie: str,
	tresc_wpisu: str | None = None,
	pomin: set[str] | None = None,
	tylko: list[str] | None = None,
) -> None:
	"""Wstawia po jednym `CRM Notification` dla kazdego odbiorcy zdarzenia
	`zdarzenie` (wpis, status, termin, wykonawca) dokonanego przez biezacego
	uzytkownika: autora zadania (`owner`, tylko zadanie reczne) i wykonawcow
	(`crm.volteo_powiadomienia_zadan.wybierz_odbiorcow`). Wzmianka odbiorcy we wpisie
	wygrywa (powiadomi go `crm.api.comment.notify_mentions`). Maskowanie CC per
	odbiorca jak w `crm.api.todo.notify_assigned_user`. Wstawia wiersz bezposrednio,
	a nie przez `notify_user`, bo jego dedup po tresci gubilby powtorzone, rownie
	brzmiace zdarzenia (np. dwa razy "Wykonane"). Osoby "Do wiadomosci" (ops#411) dostaja
	te same zdarzenia co wykonawca. `tylko` (zdarzenie `dw`): dzwonek dostaja wylacznie te
	osoby, czyli swiezo dodane."""
	from crm.permissions.org_hierarchy import BYPASS_ROLES, czy_autor_ma_role_cc
	from crm.volteo_aktywnosc import czy_dokument_maskuje_cc
	from crm.volteo_powiadomienia import nazwa_przydzielajacego

	aktor = frappe.session.user
	wykonawcy = _wykonawcy(zadanie)
	dw = _do_wiadomosci(zadanie)
	kandydaci = {zadanie.owner, *wykonawcy, *dw, *(tylko or [])} - {None, ""}
	aktywni = {u for u in kandydaci if frappe.db.get_value("User", u, "enabled")}
	if tylko is not None:
		odbiorcy = wybierz_odbiorcow(None, tylko, aktor, aktywni, False)
	else:
		odbiorcy = wybierz_odbiorcow(
			zadanie.owner, wykonawcy, aktor, aktywni, _czy_automatyczne(zadanie), pomin, dw
		)

	nowa_wartosc = None
	if zdarzenie == "status":
		nowa_wartosc = etykieta_statusu(zadanie.get("status"))
	elif zdarzenie == "termin":
		nowa_wartosc = str(zadanie.get("due_date") or "")[:16] or "brak terminu"
	elif zdarzenie == "wykonawca":
		nowy = zadanie.get("assigned_to")
		nowa_wartosc = (frappe.get_cached_value("User", nowy, "full_name") or nowy) if nowy else "brak"

	for odbiorca in odbiorcy:
		try:
			if zdarzenie == "wpis" and autor_wzmiankowany(tresc_wpisu, odbiorca):
				continue
			odbiorca_widzi_cc = odbiorca == "Administrator" or bool(
				set(frappe.get_roles(odbiorca)) & BYPASS_ROLES
			)
			maskuj = (
				czy_autor_ma_role_cc(aktor)
				and not odbiorca_widzi_cc
				and czy_dokument_maskuje_cc("CRM Task", zadanie.get("reference_doctype"))
			)
			aktor_nazwa = nazwa_przydzielajacego(
				frappe.get_cached_value("User", aktor, "full_name"), maskuj=maskuj
			)
			frappe.get_doc(
				{
					"doctype": "CRM Notification",
					"from_user": aktor,
					"to_user": odbiorca,
					"type": "Task",
					"message": zadanie.get("title") or "",
					"notification_text": tekst_powiadomienia(
						zdarzenie, aktor_nazwa, zadanie.get("title"), nowa_wartosc
					),
					"notification_type_doctype": "CRM Task",
					"notification_type_doc": str(zadanie.name),
					"reference_doctype": "CRM Task",
					"reference_name": str(zadanie.name),
				}
			).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "CRM Task: powiadomienie o zdarzeniu")
