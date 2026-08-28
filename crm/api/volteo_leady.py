# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Leady D2D — statystyki, przydział i mapa (b52, ops#24)
======================================================================

Trzecia noga cyklu leadów D2D, po `ops/crm-leady-pola.py` (issue #19, pola
adresowe/importowe na `CRM Lead`) i `ops/crm-leady-d2d.py` (issue #18,
uprawnienia D2D na `CRM Lead` + słownik siedmiu statusów: Nowy, W kontakcie,
Umówione spotkanie, Nie odbiera, Odmowa, Błędny numer, Skonwertowany). Ten
moduł jest jedyną ścieżką, przez którą admin czyta stan puli leadów i
przydziela paczki repom, oraz przez którą front renderuje mapę.

Frontend musi wołać te metody PEŁNĄ ścieżką kropkowaną
`crm.api.volteo_leady.<metoda>` — gołą nazwą tylko Server Script potrafi się
rozwiązać (patrz `AGENT-PLAYBOOK.md`); to samo dałoby zielone bramki lokalnie
i HTTP 417 w runtime.

Typy statusów, nigdy nazwy
------------------------------
`CRM Lead Status.type` (Open/Ongoing/On Hold/Won/Lost) jest jedynym źródłem
semantyki — nazwy (`lead_status`) to UI i mogą się zmienić bez ostrzeżenia.
Każda funkcja tu buduje mapę nazwa->type raz i rozstrzyga po niej; żadna nie
ma zaszytego literału `"Nowy"` / `"Skonwertowany"` w warunku SQL.

Definicje (zgodne z `ops/crm-leady-d2d.py`, docstring SEKCJI 2)
------------------------------------------------------------------------
- **nietknięty** (globalnie, w puli) = status typu Open AND
  `ifnull(lead_owner, '') = ''`.
- **nietknięty** (per rep, w `statystyki`) = lead PRZYDZIELONY temu repowi
  (`lead_owner = rep`), którego status wciąż jest typu Open — rep go
  jeszcze nie ruszył.
- **przerobiony** = status typu Won LUB Lost, LUB `converted = 1`.
- **w toku** = status typu Ongoing.
- **skonwertowany** = `converted = 1`.

Model uprawnień
----------------
`statystyki` i `przydziel` — wyłącznie `System Manager` / `Volteo Core
Admin` (ten sam zestaw co `crm.api.volteo_uzytkownicy`), bramkowane
`frappe.only_for` jako pierwsza instrukcja. `mapa` jest dla każdego
zalogowanego z prawem odczytu `CRM Lead` — i dlatego MUSI wołać
`frappe.get_list`, nie `frappe.get_all`: `get_list` przepuszcza wynik przez
`crm/permissions/org_hierarchy.py` (permission query conditions już
podpięte w `hooks.py` dla `CRM Lead`), więc rep dostaje tylko swoje/mu
przypisane leady, a admin/backend (bypass w `org_hierarchy.py`) widzi
wszystkie. `get_all` ignoruje uprawnienia i byłby wyciekiem całej bazy
leadów do każdego repa D2D.

Pułapka None-vs-0 na `custom_lat`/`custom_lng`
------------------------------------------------------------------------
Kolumna Float jest `NOT NULL DEFAULT 0` — nieustawiona współrzędna czyta się
jako `0.0`, nie `None` (patrz `ops/crm-leady-pola.py`, sekcja "Pułapka
None-vs-0"). `mapa()` filtruje `custom_lat != 0`, więc leady bez geokodu po
prostu nie trafiają na mapę zamiast renderować się w (0, 0).

`przydziel` — bramka flagi `custom_linia_leady` (issue #27)
------------------------------------------------------------------------
Od issue #27 `przydziel` odrzuca przydział, gdy docelowy handlowiec nie ma
flagi `custom_linia_leady` na koncie (analogicznie do
`custom_linia_oze`/`custom_linia_cp` z b51,
`crm.api.volteo_ma_linie`). Sprawdzenie idzie przez współdzielony helper
`crm.permissions.org_hierarchy._ma_linie_leady` — ten sam, który bramkuje
`get_lead_permission_query_conditions`/`has_lead_permission` — żeby "kto
może zostać przydzielony" i "kto widzi przydzielone leady" nigdy nie
rozjechały się w dwóch osobnych implementacjach tej samej reguły. Bramka
stoi tuż po walidacji roli `Volteo D2D Sales` poniżej: bez roli D2D handlowiec
i tak nie mógłby zobaczyć leada, więc kolejność (rola najpierw, potem linia)
daje czytelniejszy komunikat błędu.

Wzorzec zaczerpnięty z `crm.api.volteo_uzytkownicy` / `crm.api.volteo_panele`
--------------------------------------------------------------------------------
Bramka wejścia (`frappe.only_for`) jako pierwsza instrukcja, komunikaty
błędów po polsku przez `frappe.throw`, adnotacje typów na każdym parametrze
(wymóg `require_type_annotated_api_methods`). Parametry liczbowe (`ilosc`)
przychodzą jako stringi przy wywołaniu HTTP form-encoded — adnotacja `int`
sama NIE rzutuje, więc `cint()` jawnie w ciele funkcji, tak jak
`volteo_panele` robi dla wartości liczbowych karty.
"""

import frappe
from frappe import _
from frappe.utils import cint

from crm.permissions.org_hierarchy import _ma_linie_leady

DOPUSZCZONE_ROLE_WOLAJACEGO = ("System Manager", "Volteo Core Admin")
ROLA_D2D = "Volteo D2D Sales"

ILOSC_MIN = 1
ILOSC_MAX = 100
ILOSC_DOMYSLNA = 20


def _mapa_typow_statusow() -> dict[str, str]:
	"""Nazwa statusu -> type ('Open'/'Ongoing'/'On Hold'/'Won'/'Lost'), zbudowana
	raz na wywołanie. Jedyne miejsce, które czyta `CRM Lead Status.type` dla
	tego modułu — każda funkcja poniżej rozstrzyga semantykę przez to, nigdy
	po nazwie statusu."""
	return {
		row.name: row.type
		for row in frappe.get_all("CRM Lead Status", fields=["name", "type"])
	}


def _nazwy_statusow_typu(status_type_map: dict[str, str], typ: str) -> list[str]:
	return [name for name, t in status_type_map.items() if t == typ]


def _aktywni_d2d_reprezentanci() -> list[dict]:
	"""Userzy `enabled=1` z rolą `Volteo D2D Sales`, posortowani po nazwisku."""
	nazwy = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": ROLA_D2D},
		pluck="parent",
	)
	if not nazwy:
		return []
	return frappe.get_all(
		"User",
		filters={"name": ["in", nazwy], "enabled": 1},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)


@frappe.whitelist()
def statystyki() -> dict:
	"""Per-rep liczniki (przydzielone/nietknięte/w_toku/przerobione/skonwertowane)
	dla każdego aktywnego handlowca D2D, plus pula nieprzydzielonych nietkniętych
	leadów z rozkładem per województwo/powiat. Admin-only."""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	status_type_map = _mapa_typow_statusow()
	reprezentanci = _aktywni_d2d_reprezentanci()
	rep_names = [r.name for r in reprezentanci]

	liczniki = {
		name: {
			"przydzielone": 0,
			"nietkniete": 0,
			"w_toku": 0,
			"przerobione": 0,
			"skonwertowane": 0,
		}
		for name in rep_names
	}

	if rep_names:
		leady_reprezentantow = frappe.get_all(
			"CRM Lead",
			filters={"lead_owner": ["in", rep_names]},
			fields=["lead_owner", "status", "converted"],
		)
		for lead in leady_reprezentantow:
			bucket = liczniki[lead.lead_owner]
			bucket["przydzielone"] += 1
			typ = status_type_map.get(lead.status)
			skonwertowany = bool(cint(lead.converted))
			if typ == "Open":
				bucket["nietkniete"] += 1
			if typ == "Ongoing":
				bucket["w_toku"] += 1
			if typ in ("Won", "Lost") or skonwertowany:
				bucket["przerobione"] += 1
			if skonwertowany:
				bucket["skonwertowane"] += 1

	handlowcy = [
		{
			"user": r.name,
			"full_name": r.full_name,
			**liczniki[r.name],
		}
		for r in reprezentanci
	]

	# Pula: nietknięte leady bez ownera, wg tej samej definicji co
	# ops/crm-leady-d2d.py — status typu Open AND ifnull(lead_owner,'')=''.
	open_status_names = _nazwy_statusow_typu(status_type_map, "Open")
	pula_wiersze = (
		frappe.db.sql(
			"""
			select custom_voivodeship as wojewodztwo, custom_powiat as powiat
			from `tabCRM Lead`
			where status in %(statuses)s
			  and ifnull(lead_owner, '') = ''
			""",
			{"statuses": open_status_names},
			as_dict=True,
		)
		if open_status_names
		else []
	)

	per_wojewodztwo: dict[str, int] = {}
	per_powiat: dict[str, int] = {}
	for wiersz in pula_wiersze:
		woj = wiersz.wojewodztwo or "(brak)"
		pow_ = wiersz.powiat or "(brak)"
		per_wojewodztwo[woj] = per_wojewodztwo.get(woj, 0) + 1
		per_powiat[pow_] = per_powiat.get(pow_, 0) + 1

	return {
		"handlowcy": handlowcy,
		"pula": {
			"razem": len(pula_wiersze),
			"wojewodztwa": per_wojewodztwo,
			"powiaty": per_powiat,
		},
	}


@frappe.whitelist()
def przydziel(
	handlowiec: str,
	ilosc: int = ILOSC_DOMYSLNA,
	wojewodztwo: str | None = None,
	powiat: str | None = None,
	miasto: str | None = None,
) -> dict:
	"""Przydziela paczkę geograficznie zwartych, nietkniętych leadów jednemu
	handlowcowi D2D. `ilosc` jest rzutowana i przycinana do 1..100 (parametry
	HTTP przychodzą jako stringi). Admin-only. Zapis idzie przez
	`doc.save(ignore_permissions=True)` na każdym leadzie z osobna, żeby
	kontroler (`crm/fcrm/doctype/crm_lead/crm_lead.py:86-96`) odpalił
	`assign_agent`/`share_with_agent` — to jedyny sposób, żeby rep dostał
	widoczność (ToDo + share) bez pisania nowego kodu uprawnień tutaj."""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	handlowiec = (handlowiec or "").strip()
	if not handlowiec:
		frappe.throw(_("Handlowiec jest wymagany."))
	if not frappe.db.exists("User", handlowiec):
		frappe.throw(_("Użytkownik {0} nie istnieje.").format(handlowiec))
	if not frappe.db.get_value("User", handlowiec, "enabled"):
		frappe.throw(_("Konto {0} jest wyłączone.").format(handlowiec))
	if not frappe.db.exists(
		"Has Role", {"parent": handlowiec, "parenttype": "User", "role": ROLA_D2D}
	):
		frappe.throw(
			_("Użytkownik {0} nie ma roli {1}.").format(handlowiec, ROLA_D2D)
		)
	# Bramka flagi custom_linia_leady (issue #27) — patrz docstring modułu
	# "przydziel — bramka flagi custom_linia_leady". Współdzielony helper z
	# crm.permissions.org_hierarchy, ta sama reguła, która bramkuje widoczność
	# leadów dla tego handlowca.
	if not _ma_linie_leady(handlowiec):
		frappe.throw(
			_(
				"Użytkownik {0} nie ma dostępu do modułu Leady — włącz linię "
				"Leady w Ustawienia → Użytkownicy przed przydzieleniem."
			).format(handlowiec)
		)

	ilosc = cint(ilosc)
	if ilosc < ILOSC_MIN:
		ilosc = ILOSC_MIN
	elif ilosc > ILOSC_MAX:
		ilosc = ILOSC_MAX

	status_type_map = _mapa_typow_statusow()
	open_status_names = _nazwy_statusow_typu(status_type_map, "Open")
	if not open_status_names:
		frappe.throw(
			_("Brak statusu leada typu Open — nie można wyznaczyć puli nieprzydzielonych.")
		)

	warunki = ["status in %(statuses)s", "converted = 0", "ifnull(lead_owner, '') = ''"]
	wartosci = {"statuses": open_status_names}

	wojewodztwo = (wojewodztwo or "").strip()
	if wojewodztwo:
		warunki.append("custom_voivodeship = %(wojewodztwo)s")
		wartosci["wojewodztwo"] = wojewodztwo

	powiat = (powiat or "").strip()
	if powiat:
		warunki.append("custom_powiat = %(powiat)s")
		wartosci["powiat"] = powiat

	miasto = (miasto or "").strip()
	if miasto:
		warunki.append("custom_install_city = %(miasto)s")
		wartosci["miasto"] = miasto

	gdzie = " and ".join(warunki)

	# Paczka ma być geograficznie ZWARTA (sąsiednie kody pocztowe), nie
	# losowa próbka z całego województwa/powiatu. Dwustopniowy order by:
	# MariaDB sortuje NULL/'' PRZED wszystkim w ASC, więc bez pierwszego
	# klucza leady bez kodu pocztowego (~810 na produkcyjnym imporcie)
	# zawsze wygrywałyby paczkę jako pierwsze mimo bycia geograficznie
	# bezużyteczne — pierwszy klucz spycha puste/NULL kody na koniec,
	# drugi sortuje właściwe kody rosnąco jak dotychczas.
	kandydaci = frappe.db.sql(
		f"""
		select name
		from `tabCRM Lead`
		where {gdzie}
		order by (custom_install_postal_code is null or custom_install_postal_code = '') asc,
		         custom_install_postal_code asc
		limit %(limit)s
		""",
		{**wartosci, "limit": ilosc},
		pluck=True,
	)

	przydzielone_nazwy = []
	for nazwa_leada in kandydaci:
		doc = frappe.get_doc("CRM Lead", nazwa_leada)
		doc.lead_owner = handlowiec
		doc.save(ignore_permissions=True)
		przydzielone_nazwy.append(nazwa_leada)

	pozostalo_w_puli = frappe.db.sql(
		f"""
		select count(*) as cnt
		from `tabCRM Lead`
		where {gdzie}
		""",
		wartosci,
		as_dict=True,
	)[0].cnt

	return {
		"przydzielono": len(przydzielone_nazwy),
		"leady": przydzielone_nazwy,
		"pozostalo_w_puli": pozostalo_w_puli,
	}


@frappe.whitelist()
def mapa() -> list[dict]:
	"""Leady z geokodem dla widoku mapy. `frappe.get_list` (NIGDY `get_all` —
	patrz docstring modułu) przepuszcza wynik przez scoping z
	`crm/permissions/org_hierarchy.py`: rep dostaje tylko swoje/przypisane
	leady, admin/backend wszystkie. `custom_lat != 0` odcina leady bez
	geokodu (kolumna NOT NULL DEFAULT 0 — 0 znaczy "nie ustawiono", nie
	prawdziwą współrzędną)."""
	return frappe.get_list(
		"CRM Lead",
		fields=[
			"name",
			"lead_name",
			"status",
			"custom_lat",
			"custom_lng",
			"lead_owner",
			"custom_install_city",
		],
		filters={"custom_lat": ["!=", 0]},
		limit_page_length=0,
	)
