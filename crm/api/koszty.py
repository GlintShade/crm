"""Whitelisted API edycji "kosztów rzeczywistych" na snapshocie kosztów/marży
(schema v1, `custom_koszty_json`) zapisanym na `CRM Deal` przez
`volteo_cp_create_deal` (`crm/api/czyste_powietrze.py`). Edycja odbywa się z
zakładki Zestaw (panel kosztów na dole zakładki), wyłącznie przez administratorów (`Volteo Core Admin` /
`System Manager`) — rdzeń scalania żyje w `crm/koszty/rdzen.py`
(`scal_snapshot`), frappe-free i testowalny bez tego modułu.

Odczyt snapshotu kosztów (`custom_koszty_json`) idzie ODDZIELNĄ, już istniejącą
ścieżką klienta — `frappe.client.get_value` z zestrippingiem permlevel po
stronie Frappe (ten sam wzorzec co zakładka Zestaw korzystająca z permlevel-2
pól CP, patrz `ops/crm-zestaw-cp.py`) i zostaje WYŁĄCZNIE dla administratorów —
ta ścieżka się nie zmienia. Prowizja handlowa (`custom_cp_prowizja_handlowa`)
ma od 2026-08-19 DRUGĄ, kontrolowaną ścieżkę odczytu: `volteo_prowizja_szansy`
niżej, bo zwykły permlevel jest binarny per-rola i nie potrafi wyrazić "widoczne
dla admina LUB dla opiekuna TEJ KONKRETNEJ szansy" — patrz docstring tej
funkcji po pełne uzasadnienie. Ten moduł dostarcza więc: ścieżkę ZAPISU dla
snapshotu kosztów (`volteo_koszty_zapisz`) i ścieżkę ODCZYTU dla prowizji
handlowej (`volteo_prowizja_szansy`) — dwa różne pola, dwie różne reguły dostępu.

Ostatni zapis wygrywa (last-write-wins) — świadome uproszczenie: grupa
administratorów mogących edytować ten panel jest mała (dwóch core adminów na
produkcji na dziś, patrz CLAUDE.md "Roles"), więc ryzyko równoczesnej kolizji
edycji jest znikome i nie uzasadnia optymistycznej blokady/wersjonowania.
"""

import json
from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import flt

from crm.api.umowa import _sprawdz_dostep_do_szansy
from crm.koszty.rdzen import scal_snapshot

ADMIN_ROLE = {"Volteo Core Admin", "System Manager"}


def _blad_ogolny() -> None:
	frappe.log_error(frappe.get_traceback(), "Volteo Koszty: błąd zapisu kosztów rzeczywistych")
	frappe.throw(_("Wystąpił błąd podczas zapisu kosztów rzeczywistych."))


def _wczytaj_zapisany_snapshot(deal: str) -> dict[str, Any]:
	"""Wczytuje i parsuje `custom_koszty_json` szansy; rzuca czytelny komunikat
	po polsku, jeśli szansa nie ma jeszcze snapshotu (np. utworzona przed
	wdrożeniem tej funkcji) albo jeśli zapisany JSON jest uszkodzony."""
	surowy_json = frappe.db.get_value("CRM Deal", deal, "custom_koszty_json")
	if not surowy_json:
		frappe.throw(_("Brak zapisanego snapshotu kosztów dla tej szansy sprzedaży."))
	try:
		return json.loads(surowy_json)
	except (TypeError, ValueError):
		frappe.log_error(frappe.get_traceback(), "Volteo Koszty: uszkodzony snapshot kosztów")
		frappe.throw(_("Zapisany snapshot kosztów dla tej szansy sprzedaży jest uszkodzony."))


@frappe.whitelist()
@rate_limit(limit=30, seconds=60)
def volteo_koszty_zapisz(
	deal: str, koszty_rzeczywiste: dict[str, Any], dodatkowe: list[dict[str, Any]]
) -> dict[str, Any]:
	"""Nanosi edycję "kosztów rzeczywistych" administratora na zapisany snapshot
	kosztów/marży szansy i utrwala wynik.

	Patrz `crm.koszty.rdzen.scal_snapshot` po dokładną semantykę scalania —
	hostile-payload-proof: pola PLANU przeżywają scalenie bez zmian, wejście
	klienta wpływa wyłącznie na `koszt_rzeczywisty` per linia (mapa
	`koszty_rzeczywiste`, klucz musi pasować do istniejącej linii, `None`
	czyści z powrotem na fallback planu) i na pełne zastąpienie listy
	`dodatkowe`. `ValueError` rzucony przez rdzeń (nieznany klucz, kwota
	ujemna/nieskończona/śmieciowa, pusta/za długa nazwa dodatkowej pozycji) jest
	tu zamieniany na czysty `frappe.throw`, żeby UI dostał zrozumiały komunikat
	zamiast surowego wyjątku frameworka.
	"""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not ADMIN_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	_sprawdz_dostep_do_szansy(deal, "write")

	zapisany = _wczytaj_zapisany_snapshot(deal)

	try:
		nowy = scal_snapshot(
			zapisany,
			koszty_rzeczywiste,
			dodatkowe,
			frappe.utils.now(),
			frappe.session.user,
		)
	except ValueError as blad:
		frappe.throw(str(blad))
	except Exception:
		_blad_ogolny()

	# permlevel-2 (custom_koszty_json, custom_koszty_zysk_rzeczywisty;
	# ops/crm-koszty-montaz.py) -- update_modified=False jest świadome: to zapis
	# panelu administracyjnego z osobnej sekcji (dół zakładki Zestaw), nie edycja formularza
	# szansy, więc nie chcemy dotykać modified/modified_by widocznych na otwartym
	# formularzu CRM Deal i wywoływać fałszywy konflikt "dokument zmieniony w
	# międzyczasie" komuś, kto akurat edytuje szansę w innej karcie.
	frappe.db.set_value(
		"CRM Deal",
		deal,
		{
			"custom_koszty_json": json.dumps(nowy, ensure_ascii=False),
			"custom_koszty_zysk_rzeczywisty": flt(nowy["podsumowanie_rzeczywiste"]["zysk_rzeczywisty"], 2),
		},
		update_modified=False,
	)

	return {"koszty": nowy}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_prowizja_szansy(deal: str) -> dict[str, Any]:
	"""Zwraca prowizję handlową (`custom_cp_prowizja_handlowa`, permlevel 2) tej
	szansy dla dwóch grup uprawnionych: administratorów (`ADMIN_ROLE`) oraz
	opiekuna szansy (`deal_owner == frappe.session.user`).

	Decyzja właściciela (2026-08-19): przedstawiciel prowadzący szansę ma widzieć
	swoją prowizję. Permlevel pola ZOSTAJE nietknięty i pozostaje jedynym
	mechanizmem chroniącym je przed resztą ról (Volteo D2D Sales na CUDZYCH
	szansach, Volteo Backend) — globalne podniesienie permlevela ujawniłoby
	prowizję backoffice'owi i liderom hierarchii na PODWŁADNYCH szansach, czego
	właściciel wprost NIE chciał. Permlevel jest binarny per-rola i nie potrafi
	wyrazić reguły "widoczne dla admina LUB dla opiekuna TEJ JEDNEJ szansy" —
	stąd kontrolowane rozszerzenie dostępu żyje w TYM endpoincie, nie w zmianie
	schematu pola. Liderzy hierarchii sprzedaży świadomie NIE widzą tą ścieżką
	prowizji podwładnych — do ewentualnego rozszerzenia osobną decyzją
	właściciela, nie przy okazji tej zmiany.

	Konsument: pudełko prowizji w `ZestawTab.vue` (dół zakładki Zestaw, obok
	panelu kosztów rzeczywistych administratora zasilanego przez
	`volteo_koszty_zapisz` powyżej).
	"""
	_sprawdz_dostep_do_szansy(deal, "read")

	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	jest_opiekunem_szansy = frappe.db.get_value("CRM Deal", deal, "deal_owner") == frappe.session.user
	if not (ADMIN_ROLE & role_uzytkownika) and not jest_opiekunem_szansy:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	# get_value() świadomie OMIJA permlevel -- to JEST kontrolowana ścieżka
	# ujawnienia opisana w docstringu wyżej, jedyne dodatkowe miejsce (obok
	# volteo_cp_create_deal) uprawnione do czytania tego pola z pominięciem
	# bramki permlevel.
	wartosc = frappe.db.get_value("CRM Deal", deal, "custom_cp_prowizja_handlowa")
	return {"prowizja": flt(wartosc, 2) if wartosc else None}
