# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""
Ustawienia automatyzacji rurociągu — CRUD dla panelu admina
======================================================================

Wiersze `Volteo Automatyzacja` (jedna reguła = jeden klucz automatyzacji,
np. `umowa_wygenerowana`, `umowa_podpisana`) są SEEDOWANE wyłącznie skryptem
ops — ten moduł może je włączać/wyłączać i edytować odbiorców/kanały, ale
nigdy nie tworzy nowego wiersza. Sama logika przesuwania statusu i wysyłki
powiadomień żyje w `crm.api.pipeline` (`advance_deal_status`,
`dispatch_notification`); ten moduł tylko obsługuje panel konfiguracji.

Model uprawnień
----------------
Dostęp wyłącznie dla `Volteo Core Admin` / `System Manager` — wzorzec
zaczerpnięty 1:1 z `crm.api.volteo_panele` (`frappe.only_for` jako pierwsza
instrukcja każdej metody, ta sama para ról).
"""

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

DOCTYPE = "Volteo Automatyzacja"

# Kto może wołać którąkolwiek funkcję tego modułu — identyczny zestaw co
# crm.api.volteo_panele / crm.api.volteo_uzytkownicy.
DOPUSZCZONE_ROLE_WOLAJACEGO = ["Volteo Core Admin", "System Manager"]

_POLA_LISTY = (
	"klucz",
	"typ",
	"opis",
	"wlaczona",
	"odbiorca_handlowiec",
	"kanal_bell",
	"kanal_email",
	"kanal_sms",
)


def _wiersz_do_dict(doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Kształt jednej reguły zwracany przez listę i zapis — te same klucze co
	`_POLA_LISTY` plus `odbiorcy` (lista e-maili z tabeli podrzędnej)."""
	wynik = {pole: doc.get(pole) for pole in _POLA_LISTY}
	wynik["odbiorcy"] = [wiersz.uzytkownik for wiersz in (doc.get("odbiorcy") or [])]
	return wynik


@frappe.whitelist()
def volteo_automatyzacje_lista() -> list[dict[str, Any]]:
	"""Zwraca wszystkie reguły automatyzacji, posortowane po `typ`, potem `klucz`.

	Zwraca listę pustą, gdy doctype jeszcze nie istnieje (świeży dev-site,
	zanim odpowiedni skrypt ops go założy) — panel admina ma wtedy po prostu
	nic do pokazania, zamiast wywalać się błędem 500.
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	if not frappe.db.table_exists(DOCTYPE):
		return []

	nazwy = frappe.get_all(DOCTYPE, pluck="name", order_by="typ asc, klucz asc")
	return [_wiersz_do_dict(frappe.get_doc(DOCTYPE, nazwa)) for nazwa in nazwy]


@frappe.whitelist()
def volteo_automatyzacja_zapisz(
	klucz: str,
	wlaczona: int = 0,
	odbiorcy: str | None = None,
	odbiorca_handlowiec: int = 0,
	kanal_bell: int = 1,
	kanal_email: int = 0,
	kanal_sms: int = 0,
) -> dict[str, Any]:
	"""Aktualizuje istniejącą regułę automatyzacji (flagi kanałów, odbiorca
	handlowiec, lista odbiorców-użytkowników). NIGDY nie tworzy nowego wiersza —
	nieznany `klucz` jest błędem, reguły są seedowane wyłącznie skryptem ops.

	`odbiorcy` przychodzi jako string JSON (lista adresów e-mail użytkowników) —
	tak wysyła go frontend (`createResource`/`fetch` z ciałem JSON zagnieżdżonym
	w formularzu); parsowane i walidowane tutaj, PRZED jakimkolwiek zapisem.
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	klucz = (klucz or "").strip()
	if not klucz:
		frappe.throw(_("Klucz automatyzacji jest wymagany."))
	if not frappe.db.exists(DOCTYPE, klucz):
		frappe.throw(_("Reguła automatyzacji „{0}” nie istnieje — reguły zakłada wyłącznie skrypt ops.").format(klucz))

	lista_odbiorcow = _sparsuj_odbiorcow(odbiorcy)

	doc = frappe.get_doc(DOCTYPE, klucz)
	doc.wlaczona = cint(wlaczona)
	doc.odbiorca_handlowiec = cint(odbiorca_handlowiec)
	doc.kanal_bell = cint(kanal_bell)
	doc.kanal_email = cint(kanal_email)
	doc.kanal_sms = cint(kanal_sms)

	doc.set("odbiorcy", [])
	for email in lista_odbiorcow:
		doc.append("odbiorcy", {"uzytkownik": email})

	doc.save(ignore_permissions=True)

	return _wiersz_do_dict(doc)


def _sparsuj_odbiorcow(odbiorcy: str | None) -> list[str]:
	"""Parsuje i waliduje `odbiorcy` (string JSON — lista adresów e-mail).

	Puste/brakujące wejście daje pustą listę (dozwolone: reguła bez wyznaczonych
	odbiorców-użytkowników, np. gdy jedynym adresatem ma być właściciel deala
	przez `odbiorca_handlowiec`). Każdy nierozpoznany adres (brak konta `User`
	o tym e-mailu) odrzuca cały zapis z jedną, zbiorczą listą nieznanych adresów
	— żeby administrator poprawił literówkę zamiast dostawać błąd na pierwszym
	trafieniu i zgadywać, ile ich jeszcze zostało.
	"""
	if not odbiorcy:
		return []

	try:
		wartosc = json.loads(odbiorcy)
	except (TypeError, ValueError):
		frappe.throw(_("Nieprawidłowy format listy odbiorców."))

	if not isinstance(wartosc, list) or not all(isinstance(pozycja, str) for pozycja in wartosc):
		frappe.throw(_("Lista odbiorców musi być listą adresów e-mail."))

	nieznani = [email for email in wartosc if not frappe.db.exists("User", email)]
	if nieznani:
		frappe.throw(_("Nieznani użytkownicy: {0}").format(", ".join(nieznani)))

	return wartosc
