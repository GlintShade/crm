"""Whitelisted API zakładek „OSD” i „Dotacja” na szansie OZE (ops#202).

Wzór 1:1: `crm.api.kredyt.volteo_kredyt_status_finansowania` (ops#197). Ten
sam kształt bramki (`BYPASS_ROLES`, nigdy `_sprawdz_role`/`KALKULATOR_ROLE`,
bo ten gate przepuszcza też handlowca), ten sam wzorzec zapisu
(`doc.db_set(..., update_modified=True)`, nigdy `.save()`: `.save()`
dopisałby wiersz `Version`, który czytnik Aktywności renderowałby jako drugą,
czysto etykietową linię obok śladu zapisywanego tu jawnie, czyli duplikat tego
samego zdarzenia w feedzie) i ten sam no-op na tej samej wartości. Różnica: tu
pola żyją wprost na `CRM Deal` (nie na osobnym doctype podrzędnym jak
`Volteo Kredyt`), więc nie ma odczytu/zapisu po `deal_doc.deal`: `deal` z
argumentu wywołania JEST szansą.

Ochrona przed zapisem przez handlowca NIE polega na tej bramce w izolacji.
`frappe.client.set_value` na `custom_status_osd`/`custom_status_dotacja`
ominąłby ten endpoint całkowicie, gdyby nie permlevel 3 na obu polach
(`ops/crm-osd-dotacja.py`, Custom DocPerm read=1/write=0 dla
`Volteo D2D Sales`). Rdzeń Frappe przywraca zapisane wartości pól bez write
na danym permlevel (`validate_higher_perm_levels`), więc handlowiec nie może
wyczyścić statusu nawet przy zapisie INNEGO pola szansy. Ten endpoint jest
wygodną, audytowaną ścieżką dla backoffice/adminów (kolorowy dropdown +
jawny ślad w Aktywności), nie jedynym miejscem egzekwowania uprawnień.

Faza 1: dotyczy wyłącznie szans OZE (`crm.volteo_pipeline.OZE_RODZAJE`).
Czyste Powietrze dostanie te zakładki w fazie 2 bez migracji schematu, bo pola
i permlevel są już wspólne.
"""

from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from crm.api.umowa import _sprawdz_dostep_do_szansy
from crm.permissions.org_hierarchy import BYPASS_ROLES
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad
from crm.volteo_osd_dotacja import POLE, STATUSY, ZAKLADKI
from crm.volteo_pipeline import OZE_RODZAJE


def _sprawdz_rodzaj_oze(deal_doc: "frappe.model.document.Document") -> None:
	"""Zakładki OSD/Dotacja dotyczą wyłącznie linii OZE (Faza 1, patrz docstring
	modułu): `custom_rodzaj_umowy` szansy musi być jedną z wartości
	`crm.volteo_pipeline.OZE_RODZAJE`."""
	if deal_doc.get("custom_rodzaj_umowy") not in OZE_RODZAJE:
		frappe.throw(
			_(
				"Zakładki OSD/Dotacja dotyczą wyłącznie linii OZE (Fotowoltaika, "
				"Fotowoltaika + Magazyn, Magazyn energii). Ustaw „Rodzaj umowy” na "
				"szansie sprzedaży na jedną z tych wartości."
			),
			frappe.ValidationError,
		)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=60, seconds=60)
def ustaw_status(deal: str, zakladka: str, status: str) -> dict[str, Any]:
	"""Zmienia ręczny status zakładki OSD lub Dotacja na szansie. Wyłącznie
	backoffice i admini (`BYPASS_ROLES`), nigdy przedstawiciel.

	`zakladka` musi być `"OSD"` lub `"Dotacja"` (`crm.volteo_osd_dotacja.
	ZAKLADKI`), `status` musi być jedną z wartości dozwolonych dla TEJ
	zakładki (`crm.volteo_osd_dotacja.STATUSY[zakladka]`). Pusty string nie
	jest członkiem żadnej krotki, więc jest odrzucany tą samą kontrolą, bez
	osobnego sprawdzenia „czy puste”.

	Ustawienie tej samej wartości, jaką pole już ma, jest no-opem: bez zapisu
	i bez śladu w Aktywności, bo nie ma tu żadnej zmiany do odnotowania.

	Zwraca `{"status": status}`. Frontend odświeża dokument szansy przez
	`doc.reload()` po sukcesie, bez optymistycznej aktualizacji.
	"""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not BYPASS_ROLES & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	if zakladka not in ZAKLADKI:
		frappe.throw(_("Nieznana zakładka: {0}").format(zakladka), frappe.ValidationError)

	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	if status not in STATUSY[zakladka]:
		frappe.throw(_("Nieznany status: {0}").format(status), frappe.ValidationError)

	fieldname = POLE[zakladka]
	stary = deal_doc.get(fieldname)
	if status == stary:
		return {"status": status}

	deal_doc.db_set(fieldname, status, update_modified=True)

	try:
		zapisz_slad(deal, tekst_sladu("status_zakladki", zakladka=zakladka, stary=stary, nowy=status))
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Volteo OSD/Dotacja: błąd zapisu śladu statusu")

	return {"status": status}
