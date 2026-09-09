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
ma zaszytego literału `"Nowy"` / `"Umówiony"` w warunku SQL.

Definicje (zgodne z `ops/crm-leady-d2d.py`, docstring SEKCJI 2)
------------------------------------------------------------------------
- **nietknięty** (globalnie, w puli) = status typu Open AND
  `ifnull(lead_owner, '') = ''`.
- **nietknięty** (per rep, w `statystyki`) = lead PRZYDZIELONY temu repowi
  (`lead_owner = rep`), którego status wciąż jest typu Open — rep go
  jeszcze nie ruszył.
- **przerobiony** = status typu Won LUB Lost, LUB `converted = 1` (`converted`
  jest historycznym znacznikiem konwersji leada na szansę, funkcja usunięta
  w issue #115 -- pole zostaje na leadach sprzed tej zmiany).
- **w toku** = status typu Ongoing.

Model uprawnień
----------------
`statystyki`, `przydziel` i `przydziel_cc`: wyłącznie `System Manager` /
`Volteo Core Admin` (ten sam zestaw co `crm.api.volteo_uzytkownicy`),
bramkowane `frappe.only_for` jako pierwsza instrukcja. `mapa` jest dla
każdego zalogowanego z prawem odczytu `CRM Lead`, i dlatego MUSI wołać
`frappe.get_list`, nie `frappe.get_all`: `get_list` przepuszcza wynik przez
`crm/permissions/org_hierarchy.py` (permission query conditions już
podpięte w `hooks.py` dla `CRM Lead`), więc rep dostaje tylko swoje/mu
przypisane leady, a admin/backend (bypass w `org_hierarchy.py`) widzi
wszystkie. `get_all` ignoruje uprawnienia i byłby wyciekiem całej bazy
leadów do każdego repa D2D.

Statystyki per CC i kaskada powiatu (issue #104)
------------------------------------------------------------------------
`statystyki` zwraca teraz też klucz `cc`: per aktywna osoba CC liczniki
`przydzielone` (wszystkie leady z `custom_cc = ta osoba`), `obdzwonione`
(status inny niż typu Open, czyli inny niż jedyny status "Nowy" -- patrz
"Typy statusów, nigdy nazwy" powyżej), `umowione` (status typu Won, czyli
"Umówiony", jedyny status tego typu od issue #121) i `przekazane` (lead ma
już niepuste `lead_owner`). Jedno zapytanie `frappe.get_all` grupujące po
`custom_cc`, bez N+1 -- ten sam wzorzec co pętla `handlowcy` obok.

`powiaty(wojewodztwo)` daje frontowi (`LeadyPrzydzial.vue`) kaskadę selecta
Powiat od wybranego województwa: bez tego endpointu select powiatu byłby
albo niezależną globalną agregacją (stary stan, patrz komentarz w
`LeadyPrzydzial.vue`), albo front musiałby wołać strażnikowany
`frappe.client.get_list`/`get_count` z filtrem po `custom_voivodeship`, co
strażnik (`crm.api.volteo_filtry_guard`) i tak by przepuścił (pole jest na
allowliście), ale to dodatkowy niepotrzebny endpoint ogólnego przeznaczenia
zamiast wąskiego, celowego.

Dwupoziomowy przydział CC->handlowiec (ops#93, issue #88)
------------------------------------------------------------------------
`przekaz_handlowcowi` (detal, jeden lead na wywołanie) jest dostępny dla
Administratora/`BYPASS_ROLES` ORAZ dla CC (rola `Volteo Call Center`)
ustawionego jako `custom_cc` na TYM konkretnym leadzie, nie dla dowolnego
CC. `custom_cc` NIE jest zmieniane przy przekazaniu: CC zachowuje
widoczność leada (decyzja właściciela). `handlowcy` daje CC listę
handlowców D2D do wyboru w UI, bo `widoczni_uzytkownicy` (poddrzewo
hierarchii) dałby CC spoza hierarchii pustą listę. Oba zapisy (`przydziel_cc`,
`przekaz_handlowcowi`) wołają `crm.volteo_aktywnosc.zapisz_slad(...,
doctype="CRM Lead")`, żeby przydział/przekazanie zostawiały ślad w zakładce
Aktywność leada. `crm.api.activities.get_lead_activities` maskuje tożsamość
CC dla roli `Volteo D2D Sales` (patrz `crm.volteo_aktywnosc.tekst_widoczny_dla`),
bo handlowiec nie ma widzieć pola „Przypisany CC”.

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

from crm.api.doc import _sprawdz_filtry
from crm.permissions.org_hierarchy import BYPASS_ROLES, _ma_linie_leady
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad

DOPUSZCZONE_ROLE_WOLAJACEGO = ("System Manager", "Volteo Core Admin")
ROLA_D2D = "Volteo D2D Sales"
ROLA_CC = "Volteo Call Center"

ILOSC_MIN = 1
ILOSC_MAX = 100
ILOSC_DOMYSLNA = 20

#: Limit liczby leadów przydzielanych JEDNYM wywołaniem przydziel_cc (ops#93).
#: Wyższy niż ILOSC_MAX z przydziel powyżej, bo zapis idzie przez db.set_value
#: (bez doc.save) -- kontroler CRMLead nie ma tu nic do zrobienia dla custom_cc,
#: w odróżnieniu od lead_owner (share_with_agent/assign_agent w validate()).
LIMIT_PRZYDZIAL_CC = 2000


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
	"""Per-rep liczniki (przydzielone/nietknięte/w_toku/przerobione) dla każdego
	aktywnego handlowca D2D, per-CC liczniki (przydzielone/obdzwonione/umowione/
	przekazane, issue #104) dla każdej aktywnej osoby CC, plus pula nieprzydzielonych
	nietkniętych leadów z rozkładem per województwo/powiat. Admin-only."""
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
			if typ == "Open":
				bucket["nietkniete"] += 1
			# ops#93 / L04 (issue #89): "Odłożony" (On Hold, wprowadzony w
			# migracji statusów CC) liczy się jako w toku, tak samo jak
			# Ongoing -- lead na tym statusie nie jest ani porzucony, ani
			# przerobiony, wciąż czeka na kolejny kontakt/spotkanie.
			if typ in ("Ongoing", "On Hold"):
				bucket["w_toku"] += 1
			# `converted = 1` przetrwa jako historyczny znacznik (issue #115),
			# leady sprzed usunięcia konwersji mogą go jeszcze nosić.
			if typ in ("Won", "Lost") or cint(lead.converted):
				bucket["przerobione"] += 1

	handlowcy = [
		{
			"user": r.name,
			"full_name": r.full_name,
			**liczniki[r.name],
		}
		for r in reprezentanci
	]

	# Statystyki per CC (issue #104), lustro pętli handlowców powyżej. Jedno
	# zapytanie frappe.get_all grupujące po custom_cc, bez N+1 -- patrz
	# docstring modułu "Statystyki per CC i kaskada powiatu".
	cc_reprezentanci = _aktywni_cc_reprezentanci()
	cc_names = [r.name for r in cc_reprezentanci]

	cc_liczniki = {
		name: {
			"przydzielone": 0,
			"obdzwonione": 0,
			"umowione": 0,
			"przekazane": 0,
		}
		for name in cc_names
	}

	if cc_names:
		leady_cc = frappe.get_all(
			"CRM Lead",
			filters={"custom_cc": ["in", cc_names]},
			fields=["custom_cc", "status", "lead_owner"],
		)
		for lead in leady_cc:
			bucket = cc_liczniki[lead.custom_cc]
			bucket["przydzielone"] += 1
			typ = status_type_map.get(lead.status)
			# "obdzwonione" = status INNY niż typu Open (jedyny status typu
			# Open to "Nowy") -- rozstrzygane po type, nigdy po literale, tak
			# jak reszta tego modułu (patrz "Typy statusów, nigdy nazwy").
			if typ != "Open":
				bucket["obdzwonione"] += 1
			# "umowione" = status typu Won (jedyny taki status to "Umówiony"
			# od issue #121, patrz ops/crm-leady-call-center.py sekcja VERIFY).
			if typ == "Won":
				bucket["umowione"] += 1
			if (lead.lead_owner or "").strip():
				bucket["przekazane"] += 1

	cc = [
		{
			"user": r.name,
			"full_name": r.full_name,
			**cc_liczniki[r.name],
		}
		for r in cc_reprezentanci
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
		"cc": cc,
		"pula": {
			"razem": len(pula_wiersze),
			"wojewodztwa": per_wojewodztwo,
			"powiaty": per_powiat,
		},
	}


@frappe.whitelist()
def powiaty(wojewodztwo: str) -> list[str]:
	"""Lista unikalnych powiatów występujących wśród leadów danego województwa,
	posortowana rosnąco -- kaskada selecta Powiat w `LeadyPrzydzial.vue` (issue
	#104), niezależna od globalnej agregacji `statystyki().pula.powiaty` (patrz
	docstring modułu "Statystyki per CC i kaskada powiatu"). Admin-only, jak
	pozostałe funkcje w tym module poza `mapa`/`przekaz_handlowcowi`/`handlowcy`.

	Pusty `wojewodztwo` zwraca pustą listę -- front wtedy pokazuje niezawężoną
	pulę powiatów zamiast pustego selecta (patrz `powiatOptions` w
	`LeadyPrzydzial.vue`)."""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	wojewodztwo = (wojewodztwo or "").strip()
	if not wojewodztwo:
		return []

	return frappe.get_list(
		"CRM Lead",
		filters={"custom_voivodeship": wojewodztwo, "custom_powiat": ["is", "set"]},
		pluck="custom_powiat",
		distinct=True,
		order_by="custom_powiat asc",
		limit_page_length=0,
	)


def _waliduj_handlowca(handlowiec: str) -> None:
	"""Waliduje, że `handlowiec` to istniejące, włączone konto z rolą `Volteo D2D
	Sales` i dostępem do modułu Leady (`custom_linia_leady`). Wydzielone z `przydziel`
	(ops#93), żeby `przydziel` i `przekaz_handlowcowi` rzucały identyczne komunikaty
	błędów zamiast dryfować w dwóch kopiach tej samej logiki."""
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
				"Użytkownik {0} nie ma dostępu do modułu Leady, włącz linię "
				"Leady w Ustawienia → Użytkownicy przed przydzieleniem."
			).format(handlowiec)
		)


def _waliduj_cc(cc: str) -> None:
	"""Waliduje, że `cc` to istniejące, włączone konto z rolą `Volteo Call Center`
	i dostępem do modułu Leady (`custom_linia_leady`), lustro `_waliduj_handlowca`
	powyżej, dla drugiej strony przydziału (ops#93, issue #88)."""
	if not cc:
		frappe.throw(_("CC jest wymagany."))
	if not frappe.db.exists("User", cc):
		frappe.throw(_("Użytkownik {0} nie istnieje.").format(cc))
	if not frappe.db.get_value("User", cc, "enabled"):
		frappe.throw(_("Konto {0} jest wyłączone.").format(cc))
	if not frappe.db.exists("Has Role", {"parent": cc, "parenttype": "User", "role": ROLA_CC}):
		frappe.throw(_("Użytkownik {0} nie ma roli {1}.").format(cc, ROLA_CC))
	if not _ma_linie_leady(cc):
		frappe.throw(
			_(
				"Użytkownik {0} nie ma dostępu do modułu Leady, włącz linię "
				"Leady w Ustawienia → Użytkownicy przed przydzieleniem."
			).format(cc)
		)


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
	`assign_agent`/`share_with_agent`, to jedyny sposób, żeby rep dostał
	widoczność (ToDo + share) bez pisania nowego kodu uprawnień tutaj."""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	handlowiec = (handlowiec or "").strip()
	_waliduj_handlowca(handlowiec)

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
	prawdziwą współrzędną).

	Issue #97 (panel „Szybki podgląd"): dołożone pięć pól potrzebnych do
	dymka pinezki i nagłówka panelu (`custom_cc`, `custom_import_source`,
	`custom_posiadane_produkty`, `custom_status_zrodla`, `mobile_no`).
	`custom_cc` siedzi na permlevel 2 (`ops/crm-leady-call-center.py`), więc
	`get_list` i tak wytnie go dla `Volteo D2D Sales`, nie trzeba tego
	obsługiwać ręcznie tutaj.

	Issue #101 (ustawienia mapy, pole dymku "termin spotkania"): dołożone
	`custom_termin_spotkania`, bez zmiany reszty kontraktu."""
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
			"custom_cc",
			"custom_import_source",
			"custom_posiadane_produkty",
			"custom_status_zrodla",
			"custom_termin_spotkania",
			"mobile_no",
		],
		filters={"custom_lat": ["!=", 0]},
		limit_page_length=0,
	)


@frappe.whitelist()
def przydziel_cc(
	cc: str,
	leady: str | list | None = None,
	filters: str | dict | None = None,
	ilosc: int | None = None,
) -> dict:
	"""Hurtowy przydział leadów do CC (`custom_cc`, issue #88): jawna lista nazw
	ALBO wszystkie leady pasujące do `filters`. Admin-only (`System Manager` /
	`Volteo Core Admin`), bramkowane `frappe.only_for` jako pierwsza instrukcja.

	`ilosc` (issue #104, opcjonalny, TYLKO ze ścieżką `filters`): ogranicza
	liczbę leadów pobranych do przetworzenia do zapytania -- jak `ilosc` w
	`przydziel` powyżej ogranicza paczkę handlowca. Rzutowana (`cint`) i
	przycinana do 1..`LIMIT_PRZYDZIAL_CC`; `None`/pominięte zachowuje stare
	zachowanie (limit = `LIMIT_PRZYDZIAL_CC`). Ignorowana ze ścieżką `leady`
	-- tam liczba jest już jawna, podana przez wołającego.

	Leady, które mają już USTAWIONY `custom_cc` (dowolny, nie tylko inny niż `cc`),
	są pomijane (nie nadpisujemy istniejącego przydziału po cichu, ani cudzego, ani
	tego samego CC) i zliczane w `pominieto`, drugie wywołanie z tymi samymi
	parametrami jest więc no-opem (wszystko trafia do `pominieto`), zgodnie z
	kryterium akceptacji issue #93. Zmiana przydziału na innego CC idzie przez
	`przekaz_handlowcowi`/ręczną edycję pola, nigdy przez ponowne `przydziel_cc`.

	Zapis idzie przez `frappe.db.set_value` (BEZ `doc.save`): w odróżnieniu od
	`lead_owner` (którego zmiana odpala `share_with_agent`/`assign_agent` w
	`CRMLead.validate()`), `custom_cc` nie ma żadnej logiki kontrolera do
	przeprowadzenia, stąd LIMIT_PRZYDZIAL_CC może być dużo wyższy niż ILOSC_MAX
	w `przydziel` powyżej.

	`leady`, po `frappe.parse_json`, musi być pojedynczym stringiem albo listą/
	krotką samych niepustych stringów, inaczej `frappe.throw` z czytelnym
	komunikatem zamiast niejasnego błędu dalej w funkcji. Nazwy spoza bazy (lead
	usunięty, literówka) są pomijane i zliczane osobno w `nieznane`, zamiast
	trafiać do `pominieto` (które oznacza konkretnie "już przydzielony") albo
	wywoływać `DoesNotExistError` przy zapisie śladu. Zwraca
	`{przydzielono, pominieto, nieznane, limit}`."""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	cc = (cc or "").strip()
	_waliduj_cc(cc)

	leady = frappe.parse_json(leady) if leady else None
	filters = frappe.parse_json(filters) if filters else None

	if leady:
		if isinstance(leady, str):
			nazwy = [leady]
		elif isinstance(leady, (list, tuple)):
			nazwy = list(leady)
		else:
			frappe.throw(_("Parametr leady musi być listą nazw albo pojedynczą nazwą."))
		if not all(isinstance(n, str) and n.strip() for n in nazwy):
			frappe.throw(_("Lista leadów musi zawierać wyłącznie niepuste nazwy (stringi)."))
	elif filters:
		_sprawdz_filtry("CRM Lead", filters)
		limit = LIMIT_PRZYDZIAL_CC
		if ilosc is not None:
			limit = cint(ilosc)
			if limit < 1:
				limit = 1
			elif limit > LIMIT_PRZYDZIAL_CC:
				limit = LIMIT_PRZYDZIAL_CC
		nazwy = frappe.get_list(
			"CRM Lead", filters=filters, pluck="name", limit_page_length=limit
		)
	else:
		frappe.throw(_("Podaj listę leadów albo filtry."))

	if not nazwy:
		return {"przydzielono": 0, "pominieto": 0, "nieznane": 0, "limit": LIMIT_PRZYDZIAL_CC}

	istniejace = frappe.get_all(
		"CRM Lead", filters={"name": ["in", nazwy]}, fields=["name", "custom_cc"]
	)
	obecny_cc_wg_nazwy = {row.name: row.custom_cc for row in istniejace}

	cc_full_name = frappe.db.get_value("User", cc, "full_name") or cc

	przydzielono = 0
	pominieto = 0
	nieznane = 0
	for nazwa in nazwy:
		# Nazwa spoza istniejace: lead o tej nazwie nie istnieje (usunięty, literówka,
		# albo filtry/lista podane przez wołającego wskazują na coś nieistniejącego).
		# db.set_value byłby cichym no-opem, a zapisz_slad rzuciłby DoesNotExistError
		# przy wstawianiu Comment z referencją na nieistniejący dokument, więc taką
		# nazwę pomijamy jawnie i liczymy osobno, zamiast dawać jej wpaść do
		# pominieto (co sugerowałoby "już przydzielony", a nie "nie istnieje").
		if nazwa not in obecny_cc_wg_nazwy:
			nieznane += 1
			continue
		obecny_cc = obecny_cc_wg_nazwy[nazwa]
		if obecny_cc:
			pominieto += 1
			continue
		frappe.db.set_value("CRM Lead", nazwa, "custom_cc", cc, update_modified=False)
		zapisz_slad(
			nazwa,
			tekst_sladu("cc_przydzial", cc_full_name=cc_full_name),
			doctype="CRM Lead",
		)
		przydzielono += 1

	return {
		"przydzielono": przydzielono,
		"pominieto": pominieto,
		"nieznane": nieznane,
		"limit": LIMIT_PRZYDZIAL_CC,
	}


@frappe.whitelist()
def przekaz_handlowcowi(lead: str, handlowiec: str) -> dict:
	"""Przekazuje POJEDYNCZY lead od CC do handlowca (`lead_owner`). Dozwolone dla
	Administratora / ról `BYPASS_ROLES`, albo dla CC (rola `Volteo Call Center`)
	ustawionego jako `custom_cc` na TYM leadzie, w przeciwnym razie
	`frappe.PermissionError`. `custom_cc` NIE jest zmieniane: CC zachowuje
	widoczność leada po przekazaniu (decyzja właściciela).

	Zapis idzie przez `doc.save(ignore_permissions=True)`, dokładnie jak w
	`przydziel`, żeby kontroler odpalił `share_with_agent`/`assign_agent` na rzecz
	handlowca (ToDo + DocShare) bez pisania nowej logiki uprawnień tutaj."""
	lead = (lead or "").strip()
	if not lead:
		frappe.throw(_("Lead jest wymagany."))
	if not frappe.db.exists("CRM Lead", lead):
		frappe.throw(_("Lead {0} nie istnieje.").format(lead))

	doc = frappe.get_doc("CRM Lead", lead)

	caller = frappe.session.user
	caller_roles = set(frappe.get_roles(caller))
	czy_bypass = caller == "Administrator" or bool(caller_roles & BYPASS_ROLES)
	czy_wlasny_cc = ROLA_CC in caller_roles and doc.custom_cc == caller

	if not (czy_bypass or czy_wlasny_cc):
		frappe.throw(
			_("Nie masz uprawnień do przekazania tego leada handlowcowi."),
			frappe.PermissionError,
		)

	handlowiec = (handlowiec or "").strip()
	_waliduj_handlowca(handlowiec)

	doc.lead_owner = handlowiec
	doc.save(ignore_permissions=True)

	cc_full_name = frappe.db.get_value("User", doc.custom_cc, "full_name") or doc.custom_cc or "CC"
	handlowiec_full_name = frappe.db.get_value("User", handlowiec, "full_name") or handlowiec
	zapisz_slad(
		lead,
		tekst_sladu(
			"cc_przekazanie",
			cc_full_name=cc_full_name,
			handlowiec_full_name=handlowiec_full_name,
		),
		doctype="CRM Lead",
	)

	return {"lead": lead, "handlowiec": handlowiec}


@frappe.whitelist()
def handlowcy() -> list[dict]:
	"""Lista aktywnych handlowców D2D (`user`, `full_name`) dla ról `Volteo Call
	Center` / `System Manager` / `Volteo Core Admin` / `Volteo Backend`, potrzebne,
	bo `widoczni_uzytkownicy` (`Link.vue` `userScope`, `crm.api.volteo_uzytkownicy`)
	dałby osobie CC spoza jej gałęzi hierarchii pustą listę, mimo że CC MUSI móc
	przekazać leada dowolnemu handlowcowi D2D, nie tylko podwładnym. Inne role
	dostają `frappe.PermissionError`."""
	role_wolajacego = set(frappe.get_roles(frappe.session.user))
	dopuszczone = {ROLA_CC, "System Manager", "Volteo Core Admin", "Volteo Backend"}
	if not (role_wolajacego & dopuszczone):
		frappe.throw(_("Brak uprawnień."), frappe.PermissionError)
	# _aktywni_d2d_reprezentanci() zwraca wiersze frappe.get_all z kluczami
	# "name"/"full_name" (nazwy pol doctype User), nie "user". Przemapowane tutaj
	# na "user", zgodnie z docstringiem powyzej i z tym samym ksztaltem, jaki
	# statystyki() buduje z tych samych wierszy kilka funkcji dalej.
	return [
		{"user": rep["name"], "full_name": rep["full_name"]}
		for rep in _aktywni_d2d_reprezentanci()
	]


def _aktywni_cc_reprezentanci() -> list[dict]:
	"""Userzy `enabled=1` z rolą `Volteo Call Center`, posortowani po nazwisku.
	Lustro `_aktywni_d2d_reprezentanci` powyżej, dla drugiej strony przydziału
	(issue #88/#93/#95): `osoby_cc` niżej daje adminowi listę CC do wyboru w
	modalu masowego przydziału `PrzydzielCCModal.vue`, tak jak
	`_aktywni_d2d_reprezentanci` daje listę handlowców w `przydziel`/
	`handlowcy`."""
	nazwy = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": ROLA_CC},
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
def osoby_cc() -> list[dict]:
	"""Lista aktywnych osób CC (`user`, `full_name`), posortowana po nazwisku,
	dla selecta w modalu masowego przydziału `PrzydzielCCModal.vue` (issue #95).
	Admin-only (`System Manager` / `Volteo Core Admin`), tak jak `przydziel_cc`,
	który tej listy jest źródłem wyboru, w odróżnieniu od `handlowcy()` powyżej
	(dostępnej też dla samego CC, żeby mógł przekazać lead handlowcowi),
	wołający tu musi mieć uprawnienia do PRZYDZIELANIA leadów osobom CC, nie
	tylko do przekazania pojedynczego leada dalej."""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)
	# Ten sam ksztalt co handlowcy(): klucz "user", nie "name" (modal czyta cc.user).
	return [
		{"user": cc["name"], "full_name": cc["full_name"]}
		for cc in _aktywni_cc_reprezentanci()
	]


DOCTYPES_KOMENTARZE = ("CRM Lead", "CRM Deal", "Volteo Audyt", "Volteo Audyt CP")


@frappe.whitelist()
def komentarze(doctype: str, name: str) -> list[dict]:
	"""Komentarze dokumentu dla `KomentarzeLeadaModal.vue` (reuzywanego tez przez
	`LeadSzybkiPodglad.vue` i `LeadsListView.vue`, pseudokolumna "Komentarze") oraz
	dla `AudytTab.vue` i `AudytCPTab.vue` (watek komentarzy w zakladce Audyt na
	szansie, doctype `Volteo Audyt` / `Volteo Audyt CP`, name == nazwa szansy;
	issue #118).

	Od b57 `crm.api.volteo_filtry_guard` bramkuje kazdy core endpoint
	przyjmujacy `filters` przez `crm.api.doc._pola_dozwolone`, a
	`get_permitted_fields("Comment", ...)` zwraca dla ról `Volteo Call
	Center` i `Volteo D2D Sales` wylacznie siedem `default_fields`
	(`name`/`owner`/`creation`/`modified`/`modified_by`/`docstatus`/`idx`),
	bez `reference_doctype`/`reference_name`/`comment_type`. Modal wolal
	wprost `frappe.client.get_list` filtrujac po tych trzech polach, wiec
	strażnik odrzucal zapytanie z komunikatem "Brak uprawnień do
	filtrowania po polu reference_doctype", mimo ze sam komentarz zapisywal
	sie poprawnie (zapis idzie inna sciezka, `crm.api.comment.add_comment`,
	nieobjeta tym strażnikiem, i byl widoczny w Aktywnosci na karcie leada).

	Ta funkcja NIE wola strażnikowanego `frappe.client.get_list` -- czyta
	`Comment` przez `frappe.get_all` (ktore ignoruje uprawnienia), dopiero
	PO jawnym sprawdzeniu `frappe.has_permission` na dokumencie nadrzednym,
	dokladnie tak jak `crm.api.activities.get_lead_activities` juz robi dla
	Aktywnosci. Komentarze nie niosa zadnej tajemnicy kosztow/prowizji --
	widzi je kazdy, kto widzi dokument nadrzedny, wiec brak tu dodatkowego
	filtrowania tresci."""
	if doctype not in DOCTYPES_KOMENTARZE:
		frappe.throw(_("Nieobsługiwany typ dokumentu."))

	# `Volteo Audyt`/`Volteo Audyt CP` maja autoname `field:deal` i nie istnieja,
	# dopoki audyt nie zostanie utworzony -- `frappe.has_permission` na
	# nieistniejacym dokumencie rzuca `frappe.DoesNotExistError`, a nie
	# `PermissionError`, wiec bez tego sprawdzenia zakladka Audyt dostawalaby
	# blad zamiast pustego watku komentarzy dla kazdej szansy bez jeszcze
	# utworzonego audytu. Dawne `frappe.client.get_list` po prostu zwracalo
	# pusta liste w tym przypadku (filtr po nieistniejacym reference_name nie
	# rzuca wyjatku) -- ten fallback zachowuje to samo zachowanie i nie
	# ujawnia nic o istnieniu dokumentu ponad to, co juz wiadomo wywolujacemu.
	if not frappe.db.exists(doctype, name):
		return []

	if not frappe.has_permission(doctype, "read", name):
		frappe.throw(
			_("Brak uprawnień do odczytu tego dokumentu."), frappe.PermissionError
		)

	return frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": doctype,
			"reference_name": name,
			"comment_type": "Comment",
		},
		fields=["name", "owner", "comment_by", "comment_email", "content", "creation"],
		order_by="creation asc",
		limit_page_length=200,
	)
