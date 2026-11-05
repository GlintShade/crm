# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kalendarz spotkan handlowcow (ops#318).

Spotkanie to `CRM Lead` z `custom_termin_spotkania` i `lead_owner`; nic nowego
w schemacie. Tablica "wszyscy" (System Manager, Volteo Core Admin, Volteo
Backend, Volteo Call Center) pokazuje spotkania wszystkich aktywnych handlowcow
D2D, handlowiec widzi tylko wlasne. Logika zakresu i dat zyje w frappe-free
`crm/volteo_kalendarz.py`; ten plik to cienki adapter.

Grafik dostepnosci (b82): `spotkania` zwraca tez `dostepnosc` (wzor tygodniowy
plus zmiany na dni, rozwiniete na kazdy dzien zakresu), `ustaw_dostepnosc`
zapisuje tydzien z edytora na karcie handlowca. Doctype `Volteo Dostepnosc`
tworzy skrypt ops (wzor w docs/ops/crm-dostepnosc.py); dopoki go nie ma,
`dostepnosc` jest None, a front nie pokazuje cieniowania.

Frontend wola te metody PELNA sciezka kropkowana `crm.api.kalendarz.<metoda>`.
"""

import frappe
from frappe import _

from crm.api.volteo_leady import _aktywni_d2d_reprezentanci
from crm.volteo_kalendarz import (
	DNI_TYGODNIA,
	DOCTYPE_DOSTEPNOSCI,
	ZAKRES_WLASNY,
	ZAKRES_WSZYSCY,
	dni_zakresu,
	dostepnosc_handlowcow,
	granice_czasu,
	moze_edytowac_grafik,
	normalizuj_handlowcow,
	normalizuj_termin,
	normalizuj_tydzien,
	plan_zapisu,
	pogrupuj_spotkania,
	przetnij_handlowcow,
	rozdziel_wiersze,
	waliduj_wiersz_dostepnosci,
	waliduj_zakres_dat,
	wiersze_dnia,
	zakres_kalendarza,
	zakres_tygodnia,
)

# Minimalna projekcja: nigdy `custom_cc` ani pola permlevel 2/3.
POLA_SPOTKANIA = [
	"name",
	"lead_name",
	"custom_termin_spotkania",
	"lead_owner",
	"custom_install_city",
	"status",
	"mobile_no",
]


def _zakres_wolajacego() -> str:
	zakres = zakres_kalendarza(frappe.session.user, frappe.get_roles())
	if zakres is None:
		frappe.throw(_("Brak uprawnień."), frappe.PermissionError)
	return zakres


POLA_DOSTEPNOSCI = ["name", "handlowiec", "dzien_tygodnia", "data", "wolne", "od", "do"]


def _grafik_wlaczony() -> bool:
	return bool(frappe.db.exists("DocType", DOCTYPE_DOSTEPNOSCI))


def _wiersze_dostepnosci(maile: list[str], od: str | None = None, do: str | None = None) -> list:
	"""Wiersze wzoru oraz zmian z datami `od`..`do` (bez zakresu: wszystkie zmiany).

	get_all celowo (jak przy spotkaniach): CC i handlowiec nie maja DocPerm na
	doctype, a cieniowanie widza wszyscy z kalendarza (decyzja 4). Zakres
	handlowcow wyznacza `spotkania`.
	"""
	if not maile:
		return []
	or_filters = [["data", "is", "not set"]]
	if od and do:
		or_filters.append(["data", "between", [od, do]])
	else:
		or_filters.append(["data", "is", "set"])
	return frappe.get_all(
		DOCTYPE_DOSTEPNOSCI,
		filters={"handlowiec": ["in", maile]},
		or_filters=or_filters,
		fields=POLA_DOSTEPNOSCI,
		limit_page_length=0,
	)


def validate_dostepnosc(doc, method: str | None = None) -> None:
	"""Hook `validate` na `Volteo Dostepnosc` (dziala tez przy zapisie z Desk)."""
	komunikat = waliduj_wiersz_dostepnosci(
		doc.get("dzien_tygodnia"), doc.get("data"), doc.get("wolne"), doc.get("od"), doc.get("do")
	)
	if komunikat:
		frappe.throw(_(komunikat))
	if doc.get("data"):
		doc.dzien_tygodnia = ""
	if doc.get("wolne"):
		doc.od = None
		doc.do = None


def _spotkanie(wiersz) -> dict:
	return {
		"name": wiersz.name,
		"lead_name": wiersz.lead_name,
		"termin": str(wiersz.custom_termin_spotkania) if wiersz.custom_termin_spotkania else None,
		"lead_owner": wiersz.lead_owner,
		"miasto": wiersz.custom_install_city,
		"status": wiersz.status,
		"telefon": wiersz.mobile_no,
	}


@frappe.whitelist()
def spotkania(od: str, do: str, handlowcy: str | list | None = None) -> dict:
	"""Spotkania handlowcow w zakresie dat `od`..`do` (RRRR-MM-DD, max 62 dni).

	Zwraca `{"zakres", "handlowcy": [{user, full_name}], "spotkania": {user: [...]},
	"dostepnosc": {user: {data: [[od, do], ...]} | None} | None,
	"zmiany_grafiku": {user: [data, ...]}, "moze_edytowac_grafik": bool}`.
	W `dostepnosc` pusta lista to dzien wolny, None dnia to brak wzoru na ten
	dzien, None handlowca to brak grafiku; `dostepnosc` None = brak doctype.
	Dla zakresu "wlasny" parametr `handlowcy` jest ignorowany.
	"""
	zakres = _zakres_wolajacego()
	try:
		waliduj_zakres_dat(od, do)
		poczatek, koniec = granice_czasu(od, do)
	except ValueError as exc:
		frappe.throw(_(str(exc)))

	if zakres == ZAKRES_WLASNY:
		user = frappe.session.user
		handlowcy_wiersze = [
			{"user": user, "full_name": frappe.db.get_value("User", user, "full_name") or user}
		]
	else:
		wszyscy = [{"user": r["name"], "full_name": r["full_name"]} for r in _aktywni_d2d_reprezentanci()]
		wybrani = przetnij_handlowcow(normalizuj_handlowcow(handlowcy), [h["user"] for h in wszyscy])
		handlowcy_wiersze = [h for h in wszyscy if h["user"] in wybrani]

	maile = [h["user"] for h in handlowcy_wiersze]
	wiersze = []
	if maile:
		# get_all celowo: CC widzi normalnie tylko leady `custom_cc == user`, a
		# tablica ma pokazac spotkania wszystkich handlowcow. Projekcja minimalna.
		wiersze = frappe.get_all(
			"CRM Lead",
			filters={
				"lead_owner": ["in", maile],
				"custom_termin_spotkania": ["between", [poczatek, koniec]],
				"converted": 0,
			},
			fields=POLA_SPOTKANIA,
			order_by="custom_termin_spotkania asc",
		)
	pogrupowane = pogrupuj_spotkania(
		[
			{"lead_owner": w.lead_owner, "custom_termin_spotkania": w.custom_termin_spotkania, "wiersz": w}
			for w in wiersze
		],
		maile,
	)
	dostepnosc, zmiany_grafiku = None, {}
	if _grafik_wlaczony():
		dostepnosc, zmiany_grafiku = dostepnosc_handlowcow(
			_wiersze_dostepnosci(maile, od, do), maile, dni_zakresu(od, do)
		)
	return {
		"zakres": zakres,
		"handlowcy": handlowcy_wiersze,
		"spotkania": {user: [_spotkanie(w["wiersz"]) for w in lista] for user, lista in pogrupowane.items()},
		"dostepnosc": dostepnosc,
		"zmiany_grafiku": zmiany_grafiku,
		"moze_edytowac_grafik": moze_edytowac_grafik(frappe.session.user, frappe.get_roles())
		and _grafik_wlaczony(),
	}


@frappe.whitelist(methods=["POST"])
def ustaw_dostepnosc(handlowiec: str, dni: str | list, zakres: str, tydzien_od: str) -> dict:
	"""Zapisuje grafik tygodnia `tydzien_od` (poniedzialek) jednego handlowca.

	`dni`: 7 list okien `[od, do]` w pelnych godzinach (pon..niedz), pusta lista
	= wolne. `zakres` "staly" (tydzien staje sie stalym wzorem) albo "tydzien"
	(zmiana tylko dla dni rozniacych sie od wzoru); szczegoly w
	`crm.volteo_kalendarz.plan_zapisu`. Tylko role `ROLE_GRAFIKU`; wiersze
	przez `insert()`/`delete_doc` bez `ignore_permissions` (DocPerm doctype).
	"""
	if not moze_edytowac_grafik(frappe.session.user, frappe.get_roles()):
		frappe.throw(_("Grafik wpisuje tylko administracja i backoffice."), frappe.PermissionError)
	if not _grafik_wlaczony():
		frappe.throw(_("Grafik dostępności nie jest jeszcze włączony na tym serwerze."))
	dozwoleni = {r["name"] for r in _aktywni_d2d_reprezentanci()}
	if handlowiec not in dozwoleni:
		frappe.throw(_("Wskazany handlowiec nie jest aktywnym handlowcem z dostępem do modułu Leady."))
	try:
		poniedzialek, niedziela = zakres_tygodnia(tydzien_od)
		if poniedzialek != str(tydzien_od)[:10]:
			raise ValueError("Tydzień musi zaczynać się od poniedziałku.")
		tydzien = normalizuj_tydzien(dni)
		wzor_obecny, _zmiany = rozdziel_wiersze(_wiersze_dostepnosci([handlowiec]))
		plan = plan_zapisu(tydzien, zakres, poniedzialek, wzor_obecny)
	except ValueError as exc:
		frappe.throw(_(str(exc)))

	def _usun(filtry):
		for name in frappe.get_all(DOCTYPE_DOSTEPNOSCI, filters=filtry, pluck="name", limit_page_length=0):
			frappe.delete_doc(DOCTYPE_DOSTEPNOSCI, name)

	def _wstaw(okna, dzien_tygodnia="", data=None):
		for w in wiersze_dnia(okna):
			frappe.get_doc(
				{
					"doctype": DOCTYPE_DOSTEPNOSCI,
					"handlowiec": handlowiec,
					"dzien_tygodnia": dzien_tygodnia,
					"data": data,
					**w,
				}
			).insert()

	if plan["wzor"] is not None:
		_usun({"handlowiec": handlowiec, "data": ["is", "not set"]})
		for i, okna in enumerate(plan["wzor"]):
			_wstaw(okna, dzien_tygodnia=DNI_TYGODNIA[i])
	_usun({"handlowiec": handlowiec, "data": ["in", plan["usun_zmiany"]]})
	for data, okna in plan["zmiany"].items():
		_wstaw(okna, data=data)

	dostepnosc, zmiany = dostepnosc_handlowcow(
		_wiersze_dostepnosci([handlowiec], poniedzialek, niedziela),
		[handlowiec],
		dni_zakresu(poniedzialek, niedziela),
	)
	return {"dostepnosc": dostepnosc[handlowiec], "zmiany_grafiku": zmiany[handlowiec]}


@frappe.whitelist()
def ustaw_termin(
	lead: str, termin: str | None = None, handlowiec: str | None = None, notatka: str | None = None
) -> dict:
	"""Ustawia (albo czyści, gdy `termin` pusty) termin spotkania na leadzie.

	`notatka` (b84, ops#332): niepusta dodaje komentarz do leada (zakładka
	"Komentarze", `crm.api.comment.add_comment`, te same uprawnienia) w tej
	samej transakcji co zapis terminu; pusta albo same spacje = bez komentarza.

	`handlowiec` (tylko zakres "wszyscy") zmienia `lead_owner` na wskazanego
	aktywnego handlowca D2D. Zapis przez `doc.save()` BEZ `ignore_permissions`:
	brak prawa zapisu = PermissionError od Frappe, a `CRMLead.on_update` wysyla
	mail o terminie (ops#182).
	"""
	zakres = _zakres_wolajacego()
	try:
		termin_norm = normalizuj_termin(termin)
	except ValueError as exc:
		frappe.throw(_(str(exc)))

	try:
		doc = frappe.get_doc("CRM Lead", lead)
	except frappe.DoesNotExistError:
		frappe.throw(_("Nie znaleziono leada."), frappe.DoesNotExistError)

	if zakres == ZAKRES_WLASNY and doc.lead_owner != frappe.session.user:
		frappe.throw(_("Możesz ustawić termin tylko na własnym leadzie."), frappe.PermissionError)

	if zakres == ZAKRES_WSZYSCY and handlowiec and handlowiec != doc.lead_owner:
		dozwoleni = {r["name"] for r in _aktywni_d2d_reprezentanci()}
		if handlowiec not in dozwoleni:
			frappe.throw(_("Wskazany handlowiec nie jest aktywnym handlowcem z dostępem do modułu Leady."))
		doc.lead_owner = handlowiec

	doc.custom_termin_spotkania = termin_norm
	# Termin ustawiony => status CC "Umówiony", o ile wolno wołającemu zmieniać
	# status (ta sama zasada co strażnik w `CRMLead.validate`, ops#265/#308).
	from crm.permissions.org_hierarchy import ma_flage_zmiany_statusu_cc
	from crm.volteo_kalendarz import czy_ustawic_status_umowiony
	from crm.volteo_leady_status import czy_moze_zmienic_status_cc

	if czy_ustawic_status_umowiony(
		termin_norm,
		doc.status,
		czy_moze_zmienic_status_cc(
			frappe.session.user, frappe.get_roles(), ma_flage_zmiany_statusu_cc(frappe.session.user)
		),
	):
		doc.status = "Umówiony"
	doc.save()
	_dodaj_notatke_spotkania(doc.name, notatka)
	return {
		"lead": doc.name,
		"termin": str(doc.custom_termin_spotkania) if doc.custom_termin_spotkania else None,
		"lead_owner": doc.lead_owner,
		"status": doc.status,
	}


# ---------------------------------------------------------------------------
# Okno "Nowe spotkanie" (b84, ops#332): lista leadow i notatka. Logika
# warunkow w frappe-free `crm.volteo_kalendarz`.
# ---------------------------------------------------------------------------


def _dodaj_notatke_spotkania(lead: str, notatka: str | None) -> None:
	"""Komentarz do leada z notatki okna (bez komentarza, gdy notatka pusta).

	Przez `crm.api.comment.add_comment`, jak zakładka "Komentarze": autor to
	zalogowany użytkownik, `check_permission` na leadzie jak dziś. Błąd
	przerywa żądanie, więc Frappe wycofuje też zapis terminu.
	"""
	from crm.api.comment import add_comment
	from crm.volteo_kalendarz import notatka_do_html

	tresc = notatka_do_html(notatka)
	if tresc:
		add_comment("CRM Lead", lead, tresc)


@frappe.whitelist()
def leady_do_spotkania(
	tekst: str | None = None, handlowiec: str | None = None, tylko_fb: str | int | bool | None = None
) -> list[dict]:
	"""Leady do wyboru w oknie "Nowe spotkanie" (b84, ops#332).

	Ukrywa leady przypisane do innego handlowca niż `handlowiec` (pusty
	`lead_owner` przechodzi); zakres "wlasny" pokazuje tylko leady
	zalogowanego (`ustaw_termin` odrzuca tam cudze i nieprzypisane).
	`tylko_fb` (domyślnie tak) zawęża do leadów z webhooka Make. Odczyt przez
	`frappe.get_list` (uprawnienia wołającego, jak dziś), projekcja bez
	`custom_cc`. Zwraca `[{name, lead_name, mobile_no, lead_owner}]`.
	"""
	from crm.volteo_kalendarz import (
		LIMIT_LEADOW_SPOTKANIA,
		POLA_LEADA_SPOTKANIA,
		czy_tak,
		scal_leady_spotkania,
		zapytania_leadow_spotkania,
	)

	zakres = _zakres_wolajacego()
	if zakres == ZAKRES_WLASNY:
		handlowiec = frappe.session.user
	wyniki = [
		frappe.get_list(
			"CRM Lead",
			filters=z["filters"],
			or_filters=z["or_filters"],
			fields=list(POLA_LEADA_SPOTKANIA),
			order_by="modified desc",
			limit_page_length=LIMIT_LEADOW_SPOTKANIA,
		)
		for z in zapytania_leadow_spotkania(
			tekst, handlowiec, czy_tak(tylko_fb, domyslnie=True), tylko_wlasne=zakres == ZAKRES_WLASNY
		)
	]
	return [
		{
			"name": w.get("name"),
			"lead_name": w.get("lead_name"),
			"mobile_no": w.get("mobile_no"),
			"lead_owner": w.get("lead_owner"),
		}
		for w in scal_leady_spotkania(wyniki)
	]
