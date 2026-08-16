# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Karty paneli PV — katalog kart producenckich w `Volteo Komponent`
======================================================================

Panele fotowoltaiczne stają się wierszami katalogu `Volteo Komponent` w
nowej kategorii `Panel PV` (schemat dowozi w tym samym buildzie osobny
skrypt ops — pola istnieją, zanim to API trafia na produkcję). Ten moduł
jest jedyną ścieżką zapisu dla tych wierszy z poziomu UI: listowanie,
tworzenie/edycja karty i przełączanie dostępności.

Model uprawnień
----------------
Dostęp wyłącznie dla `Volteo Core Admin` / `System Manager` — dokładnie ten
sam zestaw ról co `crm.api.volteo_uzytkownicy`. `volteo_panele_lista` zwraca
`cena_jednostkowa_netto` (permlevel 1, cena wewnętrzna) wprost w polach —
to bezpieczne, bo wołający jest już przefiltrowany do tych samych ról, które
mają dostęp do kosztów wewnętrznych gdzie indziej w systemie (por. model
tajemnicy kosztów opisany w `crm/api/umowa.py` i `crm/czyste_powietrze/`).

Karty użyte w jakiejkolwiek szansie nigdy nie są usuwane
-------------------------------------------------------------
Zgodnie z konwencją katalogu `Volteo Komponent` (patrz `crm/api/umowa.py`,
`_komponenty_katalogu`) karta, którą wskazuje choć jeden deal, nie może zniknąć
— `crm/volteo_umowa_pdf.py::_znajdz_komponent` rozwiązuje panel historycznego
deala dopasowując `f"{nazwa} {model}"` do `CRM Deal.custom_panel`, więc
usunięcie użytej karty po cichu degradowałoby regenerowane umowy. Dla kart w
użyciu jedyną operacją pozostaje rotacja dostępności przez `aktywny`
(patrz `volteo_panel_aktywnosc`).

Karta, której żaden deal nigdy nie użył — „wyszła z użycia na dobre" zanim
w ogóle trafiła do jakiejkolwiek szansy — MOŻE zostać trwale skasowana przez
`volteo_panel_usun`. Metoda sama sprawdza referencje (ten sam sklejony klucz
`f"{nazwa} {model}"` co `_znajdz_komponent`) i odmawia, jeśli znajdzie choćby
jedno użycie; w takim wypadku instruuje wywołującego, żeby zamiast tego użył
`volteo_panel_aktywnosc`.

Pole `producent` pozostaje puste na wierszach paneli
--------------------------------------------------------
`Volteo Komponent.producent` to osobny Select od tekstowego `nazwa` (który
tu pełni rolę nazwy producenta, np. "AIKO" — konwencja odwrotna do intuicji,
udokumentowana też w `crm/api/umowa.py::_komponenty_katalogu`). Ten moduł
nigdy nie odczytuje ani nie zapisuje `producent` — pole zostaje takie, jakie
było (puste na nowych wierszach, bo `frappe.new_doc` go nie wypełnia).

Wzorzec zaczerpnięty z `crm.api.volteo_uzytkownicy`
--------------------------------------------------------
Bramka wejścia (`frappe.only_for`) jako pierwsza instrukcja każdej metody,
komunikaty błędów po polsku przez `frappe.throw`, adnotacje typów na każdym
parametrze (wymóg `require_type_annotated_api_methods`). Wartości liczbowe
mogą przychodzić jako stringi (form-encoded, np. curl) LUB jako liczby JSON
(fetch/`createResource` z ciałem `application/json` — dokładnie tak wysyła
je `KartyPaneli.vue`) — adnotacje na polach liczbowych dopuszczają obie
postaci (`str | int`, `str | float | int`), bo `require_type_annotated_api_methods`
odrzuca żądanie na samej walidacji typu Pydantic, zanim ciało funkcji w
ogóle się wykona. Parsujemy przez `cint`/`flt` PRZED walidacją biznesową,
nigdy nie polegamy na samej adnotacji typu.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

# Jedyna kategoria `Volteo Komponent`, którą ten moduł wolno czytać/pisać.
KATEGORIA_PANEL = "Panel PV"

# Kto może wołać którąkolwiek funkcję tego modułu — identyczny zestaw co
# crm.api.volteo_uzytkownicy.
DOPUSZCZONE_ROLE_WOLAJACEGO = ["Volteo Core Admin", "System Manager"]

# Pola zwracane przez volteo_panele_lista(). Cena wewnętrzna WŁĄCZONA
# celowo — patrz docstring modułu, sekcja "Model uprawnień".
_POLA_LISTY = (
	"name",
	"nazwa",
	"model",
	"moc_wp",
	"cena_jednostkowa_netto",
	"gwarancja_tekst",
	"aktywny",
	"sort",
)


def _wiersz_do_dict(doc) -> dict:
	"""Kształt jednej karty zwracany po zapisie/przełączeniu — te same klucze
	co pola `_POLA_LISTY`, żeby odpowiedź `volteo_panel_zapisz`/
	`volteo_panel_aktywnosc` dało się bez przeróbek wstawić w tę samą listę
	po stronie frontu."""
	return {
		"name": doc.name,
		"nazwa": doc.nazwa,
		"model": doc.model,
		"moc_wp": doc.moc_wp,
		"cena_jednostkowa_netto": doc.cena_jednostkowa_netto,
		"gwarancja_tekst": doc.gwarancja_tekst,
		"aktywny": doc.aktywny,
		"sort": doc.sort,
	}


def _pobierz_karte_panelu(docname: str):
	"""Pobiera wiersz `Volteo Komponent` i sprawdza, że to karta panelu PV.

	Współdzielone przez `volteo_panel_zapisz` (ścieżka edycji) i
	`volteo_panel_aktywnosc` — obie odmawiają, jeśli wskazany wiersz istnieje,
	ale należy do innej kategorii katalogu (np. falownika czy baterii)."""
	if not frappe.db.exists("Volteo Komponent", docname):
		frappe.throw(_("Karta {0} nie istnieje.").format(docname))

	doc = frappe.get_doc("Volteo Komponent", docname)
	if doc.kategoria != KATEGORIA_PANEL:
		frappe.throw(
			_("Wiersz {0} nie jest kartą panelu PV (kategoria: {1}).").format(
				docname, doc.kategoria or _("(brak)")
			)
		)
	return doc


@frappe.whitelist()
def volteo_panele_lista() -> dict:
	"""Zwraca wszystkie karty paneli PV (aktywne I nieaktywne), posortowane po
	`sort`, potem `nazwa`. Cena wewnętrzna jest w odpowiedzi — patrz docstring
	modułu."""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	wiersze = frappe.get_all(
		"Volteo Komponent",
		filters={"kategoria": KATEGORIA_PANEL},
		fields=list(_POLA_LISTY),
		order_by="sort asc, nazwa asc",
	)
	return {"karty": wiersze}


@frappe.whitelist()
def volteo_panel_zapisz(
	nazwa: str,
	model: str,
	moc_wp: str | int,
	cena_jednostkowa_netto: str | float | int,
	docname: str | None = None,
	gwarancja_tekst: str | None = None,
	sort: str | int | None = None,
) -> dict:
	"""Tworzy nową kartę panelu PV lub aktualizuje istniejącą.

	Pusty/brakujący `docname` tworzy nowy wiersz; niepusty aktualizuje wiersz
	o tej nazwie, o ile jest kategorii `Panel PV` (patrz `_pobierz_karte_panelu`).
	`kategoria` jest przypięta do `Panel PV` zarówno przy tworzeniu, jak i przy
	aktualizacji — wywołujący nie może jej zmienić. `producent` nigdy nie jest
	tu ustawiane (patrz docstring modułu).
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	docname = (docname or "").strip()
	nazwa = (nazwa or "").strip()
	model = (model or "").strip()
	gwarancja_tekst = (gwarancja_tekst or "").strip()

	if not nazwa:
		frappe.throw(_("Nazwa producenta jest wymagana."))

	moc_wp_int = cint(moc_wp)
	if moc_wp_int <= 0:
		frappe.throw(_("Moc (Wp) musi być liczbą całkowitą większą od zera."))

	cena = flt(cena_jednostkowa_netto, 2)
	if cena < 0:
		frappe.throw(_("Cena jednostkowa netto nie może być ujemna."))

	sort_int = cint(sort) if sort not in (None, "") else 0

	if docname:
		doc = _pobierz_karte_panelu(docname)
	else:
		doc = frappe.new_doc("Volteo Komponent")

	# Przypięte bezwarunkowo, na tworzeniu i na aktualizacji — patrz docstring.
	doc.kategoria = KATEGORIA_PANEL
	doc.nazwa = nazwa
	doc.model = model
	doc.moc_wp = moc_wp_int
	doc.cena_jednostkowa_netto = cena
	doc.gwarancja_tekst = gwarancja_tekst
	doc.sort = sort_int

	if docname:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)

	return {"karta": _wiersz_do_dict(doc)}


@frappe.whitelist()
def volteo_panel_aktywnosc(name: str, aktywny: int | str) -> dict:
	"""Przełącza dostępność karty panelu PV (`aktywny`), bez zmiany innych pól.

	Karty nigdy nie są usuwane — to jedyna operacja rotacji dostępności.
	Odmawia, jeśli wskazany wiersz nie istnieje lub nie jest kategorii
	`Panel PV` (patrz `_pobierz_karte_panelu`).
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	name = (name or "").strip()
	if not name:
		frappe.throw(_("Nazwa karty jest wymagana."))

	doc = _pobierz_karte_panelu(name)
	doc.aktywny = 1 if cint(aktywny) else 0
	doc.save(ignore_permissions=True)

	return {"karta": _wiersz_do_dict(doc)}


@frappe.whitelist()
def volteo_panel_usun(name: str) -> dict:
	"""Trwale kasuje kartę panelu PV, o ile żaden deal nigdy jej nie użył.

	Referencję sprawdzamy po tym samym sklejonym kluczu `f"{nazwa} {model}"`,
	którego używa `crm/volteo_umowa_pdf.py::_znajdz_komponent` do rozwiązania
	panelu historycznego deala — dokładnie ten string ląduje w
	`CRM Deal.custom_panel` przy generowaniu oferty. Sprawdzamy dwa miejsca:
	`CRM Deal.custom_panel` wprost oraz pozycje BOM (`Volteo Zestaw Item` typu
	`Panele PV`) jako dodatkowe zabezpieczenie. Jeśli karta jest użyta,
	odmawiamy i każemy wywołującemu użyć `volteo_panel_aktywnosc` zamiast
	usuwania. Odmawia też, jeśli wskazany wiersz nie istnieje lub nie jest
	kategorii `Panel PV` (patrz `_pobierz_karte_panelu`).
	"""
	frappe.only_for(DOPUSZCZONE_ROLE_WOLAJACEGO, True)

	name = (name or "").strip()
	if not name:
		frappe.throw(_("Nazwa karty jest wymagana."))

	doc = _pobierz_karte_panelu(name)

	sklejka = f"{doc.nazwa or ''} {doc.model or ''}".strip()
	uzyta = frappe.db.exists("CRM Deal", {"custom_panel": sklejka}) or frappe.db.exists(
		"Volteo Zestaw Item",
		{"parenttype": "CRM Deal", "typ": "Panele PV", "nazwa": sklejka},
	)
	if uzyta:
		frappe.throw(
			_(
				"Karta {0} była użyta w co najmniej jednej szansie i nie może zostać"
				" usunięta. Użyj akcji Dezaktywuj, żeby wycofać ją z dostępności."
			).format(sklejka or name)
		)

	frappe.delete_doc("Volteo Komponent", doc.name, ignore_permissions=True)

	return {"usunieto": doc.name}
