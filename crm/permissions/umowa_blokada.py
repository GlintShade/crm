"""Strażnik blokady formularza umowy (`Volteo Umowa`, ops#371).

Hak `validate` odrzuca KAŻDY zapis przez `Document.save()` (API umowy, ogólne
`frappe.client.set_value`, Desk, skrypty), który zmienia pole formularza umowy,
gdy formularz był zablokowany w chwili sprzed zapisu (`czy_formularz_zablokowany`),
oraz każdy zapis, który zmienia którekolwiek z czterech pól stanu blokady
(`POLA_BLOKADY`): te zmieniają się wyłącznie przez `frappe.db.set_value`
(poller Autenti, wysyłka, odblokowanie), które nie przechodzi przez `validate`.

BEZ obejścia przez `flags.ignore_permissions`: ops#370 ustawia tę flagę dla
przypisanego handlowca, a blokada ma obowiązywać także jego (i administratorów,
którzy najpierw odblokowują, potem edytują). Zapisy bez zmiany pól formularza
(status, PDF, przeliczenia) i wstawienie nowego rekordu przechodzą.
"""

import frappe
from frappe import _

from crm.integrations.autenti.logika import KOMUNIKAT_BLOKADA_FORMULARZA
from crm.volteo_umowa import (
	POLA_BLOKADY,
	POLA_FORMULARZA_CP,
	POLA_FORMULARZA_OZE,
	czy_formularz_zablokowany,
	pola_zmienione,
)

_POLA_FORMULARZA = tuple(dict.fromkeys([*POLA_FORMULARZA_OZE, *POLA_FORMULARZA_CP]))


def _wartosci(dokument: "frappe.model.document.Document", pola: tuple[str, ...]) -> dict[str, object]:
	return {pole: dokument.get(pole) for pole in pola}


def validate(doc: "frappe.model.document.Document", method: str | None = None) -> None:
	"""Hak `validate` dla `Volteo Umowa`; patrz docstring modułu."""
	przed = doc.get_doc_before_save()
	if przed is None:
		return

	pola = (*POLA_BLOKADY, *_POLA_FORMULARZA)
	stare = _wartosci(przed, pola)
	nowe = _wartosci(doc, pola)

	if pola_zmienione(stare, nowe, POLA_BLOKADY):
		frappe.throw(_("Stan blokady formularza umowy zmienia tylko system."), frappe.PermissionError)

	if not czy_formularz_zablokowany(
		przed.get("autenti_status"),
		stare.get("autenti_pierwszy_podpis"),
		stare.get("formularz_odblokowany"),
	):
		return

	if pola_zmienione(stare, nowe, _POLA_FORMULARZA):
		frappe.throw(_(KOMUNIKAT_BLOKADA_FORMULARZA), frappe.ValidationError)
