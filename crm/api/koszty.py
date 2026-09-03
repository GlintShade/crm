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

from crm.api import volteo_poziom_prowizji, volteo_widzi_prowizje
from crm.api.umowa import _sprawdz_dostep_do_szansy
from crm.koszty.rdzen import scal_snapshot
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad

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

	# Ślad aktywności (ops#67) -- WYŁĄCZNIE liczniki, nigdy kwota/nazwa/marża
	# (model tajemnicy kosztów). Awaria zapisu śladu nie może ubić zapisu
	# kosztów, który już się powiódł -- log_error zamiast throw.
	try:
		zapisz_slad(
			deal,
			tekst_sladu("koszty", pozycje=len(nowy["linie"]), dodatkowe=len(dodatkowe)),
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Volteo Koszty: błąd zapisu śladu aktywności")

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

	Issue #48 (schema ops#46, rdzeń ops#47) dodaje DRUGĄ bramkę, ORTOGONALNĄ do
	powyższej: `custom_widzi_prowizje` na `User`, ten sam flip-bit sprawdzany
	przez `crm.api.czyste_powietrze.volteo_cp_calc`. Sprawdzana TU DODATKOWO
	(nie zamiast) reguły admin-lub-opiekun i NIE dotyczy administratorów --
	`ADMIN_ROLE` zawsze przechodzi. Wyłączona flaga zwraca ciche
	``{"prowizja": None, "prowizje": None}`` zamiast rzucać: ten endpoint jest
	odpytywany w tle przez `ZestawTab.vue`, więc brak uprawnień ma wyglądać jak
	brak danych, ten sam wzorzec co `onError` w tym komponencie -- nie jak błąd.

	`custom_cp_nadprowizja_manager` / `custom_cp_nadprowizja_partner`
	(permlevel 2, schema ops#46) mają swój JEDYNY kontrolowany odczyt właśnie
	tutaj, z tym samym uzasadnieniem jak dla `custom_cp_prowizja_handlowa`
	wyżej: permlevel jest binarny per-rola i nie wyraża "widoczne dla admina
	LUB opiekuna, ale tylko do jego poziomu prowizyjnego". Zwracany blok
	"prowizje" jest przycięty POZIOMEM WYWOŁUJĄCEGO (`volteo_poziom_prowizji`),
	NIE poziomem opiekuna szansy -- Handlowiec widzi tylko swoją bazę, Manager
	bazę + swoją nadprowizję + sumę tych dwóch (BEZ nadprowizji Partnera),
	Partner i administrator widzą pełny 4-kluczowy rozkład (`handlowiec`,
	`nadprowizja_manager`, `nadprowizja_partner`, `suma`).

	Konsument: pudełko prowizji w `ZestawTab.vue` (dół zakładki Zestaw, obok
	panelu kosztów rzeczywistych administratora zasilanego przez
	`volteo_koszty_zapisz` powyżej).
	"""
	_sprawdz_dostep_do_szansy(deal, "read")

	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	jest_admin = bool(ADMIN_ROLE & role_uzytkownika)
	jest_opiekunem_szansy = frappe.db.get_value("CRM Deal", deal, "deal_owner") == frappe.session.user
	if not jest_admin and not jest_opiekunem_szansy:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	# Druga, ortogonalna bramka (issue #48): flaga per-user wygrywa nawet dla
	# opiekuna szansy. Admini ją zawsze mijają (patrz volteo_widzi_prowizje).
	# Ciche zdegradowanie, nie throw -- ten endpoint jest odpytywany w tle.
	if not jest_admin and not volteo_widzi_prowizje():
		return {"prowizja": None, "prowizje": None}

	# get_value() świadomie OMIJA permlevel -- to JEST kontrolowana ścieżka
	# ujawnienia opisana w docstringu wyżej, jedyne dodatkowe miejsce (obok
	# volteo_cp_create_deal) uprawnione do czytania tych trzech pól z
	# pominięciem bramki permlevel. NULL (szansa sprzed ops#46, albo nigdy nie
	# zasilona nadprowizją) traktowany jak 0 przez flt().
	handlowiec, nadprowizja_manager, nadprowizja_partner = frappe.db.get_value(
		"CRM Deal",
		deal,
		["custom_cp_prowizja_handlowa", "custom_cp_nadprowizja_manager", "custom_cp_nadprowizja_partner"],
	)
	handlowiec = flt(handlowiec, 2)
	nadprowizja_manager = flt(nadprowizja_manager, 2)
	nadprowizja_partner = flt(nadprowizja_partner, 2)

	# Admin zawsze na pełnym rozkładzie niezależnie od WŁASNEGO
	# custom_poziom_prowizji (mógłby mieć zaseedowane "Handlowiec") -- tylko
	# Partner spośród zwykłych poziomów widzi to samo.
	poziom = "Partner" if jest_admin else volteo_poziom_prowizji()
	if poziom == "Manager":
		prowizje = {
			"handlowiec": handlowiec,
			"nadprowizja_manager": nadprowizja_manager,
			"suma": flt(handlowiec + nadprowizja_manager, 2),
		}
	elif poziom == "Partner":
		prowizje = {
			"handlowiec": handlowiec,
			"nadprowizja_manager": nadprowizja_manager,
			"nadprowizja_partner": nadprowizja_partner,
			"suma": flt(handlowiec + nadprowizja_manager + nadprowizja_partner, 2),
		}
	else:  # "Handlowiec" -- fail-safe domyślne, celowo bez klucza "suma"
		prowizje = {"handlowiec": handlowiec}

	# "prowizja" (legacy) zachowuje dotychczasową semantykę: None gdy baza jest
	# zerowa/pusta, niezależnie od tego, że "prowizje" może dalej nieść zera --
	# front i tak chowa wiersze zerowe.
	return {"prowizja": handlowiec if handlowiec else None, "prowizje": prowizje}
