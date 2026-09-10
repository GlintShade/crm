import json

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.desk.form.assign_to import set_status
from frappe.model import get_permitted_fields, no_value_fields
from frappe.model.delete_doc import get_dynamic_linked_docs, get_linked_docs
from frappe.model.document import get_controller
from frappe.utils import add_days, make_filter_tuple, nowdate
from pypika import Criterion

from crm.api.views import get_views
from crm.fcrm.doctype.crm_form_script.crm_form_script import get_form_script
from crm.utils import is_frappe_version
from crm.volteo_grupy_filtrow import klucze_z_grup, waliduj_grupy, wydziel_grupy
from crm.volteo_lista_szans import POLA_ZAWSZE_DOZWOLONE, niedozwolone_klucze_filtrow, podstaw_dzis

# Bezpiecznik rozmiaru unii w `rozwin_grupy` (issue #129): patrz jej
# docstring. Chroni zapytanie `name in [...]` przed nieograniczonym
# kosztem, gdyby grupy filtrów dopasowały praktycznie całą tabelę.
LIMIT_UNIA_GRUP = 20000

# Pola standardowe, ktore SA typu Datetime w rdzeniu Frappe mimo ze nie maja
# wlasnego wpisu w `meta.fields` (`frappe.get_meta(doctype).get_field(...)`
# zwraca `None` dla nich): bezpiecznik dla `_podstaw_dzis` (issue #128),
# zeby filtr `{"modified": ["<=", "@dzis"]}` (obecny w FILTER_FIELDS_DEAL
# i FILTER_FIELDS_LEAD, `crm/volteo_lista_szans.py`) dostal ten sam
# caly-dzien-Datetime traktowanie co pole custom Datetime, zamiast cicho
# przejsc jako "nie-Datetime" i objac tylko polnoc dnia dzisiejszego.
_STANDARDOWE_POLA_DATETIME = frozenset({"creation", "modified"})

try:
	# Nazwy pol tabeli podrzednej ("parent", "parentfield", "parenttype"),
	# ktore `get_permitted_fields` dokleja SAM tylko wtedy, gdy dostanie
	# `parenttype` (patrz `_pola_dozwolone` nizej i ops#80 follow-up).
	# `crm.volteo_lista_szans.POLA_ZAWSZE_DOZWOLONE` juz zawiera te same
	# trzy nazwy jako literalny backstop (modul jest frappe-free) — ten
	# import dokleja je jeszcze raz wprost z frameworka, zeby przemianowanie
	# stalej w Frappe nie rozjechalo sie cicho z literalami.
	from frappe.model import child_table_fields as _CHILD_TABLE_FIELDS
except ImportError:  # pragma: no cover - tylko gdyby framework usunal stala
	_CHILD_TABLE_FIELDS = ()

COUNT_NAME = (
	{"COUNT": "name", "as": "total_count"}
	if is_frappe_version("16", above=True)
	else "count(name) as total_count"
)

# Standardowe/opcjonalne pola, ktore musza zostac dozwolone do filtrowania
# niezaleznie od tego, co zwroci get_permitted_fields dla danego doctype'u —
# bezpiecznik na wypadek, gdyby framework kiedys ich stamtad nie zwrocil
# (patrz ops#79). get_permitted_fields juz je zwraca w normalnym przypadku
# (default_fields + optional_fields z frappe/model/__init__.py), ale ta
# lista jest tania do policzenia i nie zalezy od wersji frameworka. Zrodlo
# prawdy to `crm.volteo_lista_szans.POLA_ZAWSZE_DOZWOLONE` (frappe-free, wiec
# testowalne bez frameworka) — tutaj dokladamy jeszcze
# `frappe.model.child_table_fields` wprost, na wypadek gdyby framework kiedys
# przemianowal `parent`/`parentfield`/`parenttype` (ops#80 follow-up).
_POLA_ZAWSZE_DOZWOLONE = POLA_ZAWSZE_DOZWOLONE | frozenset(_CHILD_TABLE_FIELDS)

# Pseudo-pola listy (issue #117): NIE sa prawdziwymi DocFieldami (wiec
# get_permitted_fields ich nie zwroci), ale musza przezyc filtrowanie
# columns/rows w get_data ponizej. "_comment_count" dzieli klucz kolumny
# "Komentarze" z default_list_data() na CRM Lead (ops#94). Reszta
# pseudo-pol (name, _assign, _liked_by, _comments...) jest juz w
# _POLA_ZAWSZE_DOZWOLONE powyzej.
_POLA_LISTY_ZAWSZE_DOZWOLONE = _POLA_ZAWSZE_DOZWOLONE | frozenset({"_comment_count"})


def _pola_dozwolone(doctype: str, parenttype: str | None = None) -> set[str]:
	"""Zbior nazw pol doctype'u dostepnych BIEZACEMU uzytkownikowi do odczytu.

	Pole permlevel > 0 bez uprawnienia read na tym poziomie jest wylaczone —
	to jest zbior, po ktorym wolno filtrowac/sortowac/grupowac (patrz modul
	`crm.volteo_lista_szans` i ops#79). Liczony raz na wywolanie whitelisted
	metody, nie w petli.

	`parenttype` (ops#80 follow-up): dla TABELI PODRZEDNEJ (child table)
	`get_permitted_fields` doklada `parent`/`parentfield`/`parenttype` oraz
	DocFieldy wiersza WYLACZNIE gdy dostanie `parenttype` (nazwe doctype'u
	rodzica) — bez niego zwraca tylko `default_fields` (7 pol: name, owner,
	creation, modified, modified_by, docstatus, idx), co bez tej poprawki
	odrzucalo kazdy filtr typu `{parenttype: "CRM Deal", parent: <deal>}`
	uzywany przez froncikowe odczyty tabel podrzednych (np.
	`ZestawTab.vue`'s `Volteo Zestaw Item`). Wywolujacy, ktorzy znaja
	rodzica (np. `crm.api.volteo_filtry_guard.get_list`, ktory dostaje
	argument `parent`), przekazuja go tutaj; wywolania bez znanego rodzica
	(np. `get_data` w tym module) dostaja fallback nizej.
	"""
	permitted = get_permitted_fields(
		doctype, parenttype=parenttype, user=frappe.session.user, permission_type="read"
	)
	dozwolone = set(permitted) | _POLA_ZAWSZE_DOZWOLONE

	# Fallback dla tabeli podrzednej BEZ podanego parenttype: `permitted`
	# powyzej jest wtedy prawie puste (patrz docstring), wiec bez tego
	# dokladamy WLASNE pola tego doctype'u na permlevel 0 — zeby nie
	# blokowac uzasadnionych filtrow po zwyklych polach wiersza (np.
	# `kategoria`). Pola permlevel > 0 zostaja zablokowane tak jak
	# dotychczas — nie sa tu dodawane.
	meta = frappe.get_meta(doctype)
	if meta.istable and not parenttype:
		dozwolone |= {field.fieldname for field in meta.fields if not field.get("permlevel")}

	return dozwolone


def _podstaw_me(filters: dict) -> dict:
	"""Podstawia frappe.session.user za literal "@me" (takze wewnatrz "%@me%"
	w filtrach LIKE, uzywanych przez operator LIKE) w wartosciach `filters`.
	Wyciagnieta z `get_data` (issue #100), zeby `crm.api.volteo_leady.mapa`
	mogla podstawiac "@me" identycznie jak SPA forka zamiast duplikowac te
	sama logike osobno dla mapy leadow.

	Zwraca NOWY dict i nie mutuje ani `filters`, ani zagniezdzonych list w
	jego wartosciach (coding-style.md: immutability)  -  oryginalny kod w
	`get_data` mutowal listy w miejscu, co bylo nieszkodliwe dopoki jedynym
	wolajacym byl ten sam request; wspoldzielenie z drugim wolajacym usuwa
	to bezpieczne zalozenie."""
	wynik: dict = {}
	for key, value in filters.items():
		if isinstance(value, list):
			nowa_wartosc = list(value)
			if "@me" in nowa_wartosc:
				nowa_wartosc[nowa_wartosc.index("@me")] = frappe.session.user
			elif "%@me%" in nowa_wartosc:
				for i, v in enumerate(nowa_wartosc):
					if v == "%@me%":
						nowa_wartosc[i] = "%" + frappe.session.user + "%"
			wynik[key] = nowa_wartosc
		elif value == "@me":
			wynik[key] = frappe.session.user
		else:
			wynik[key] = value
	return wynik


def _podstaw_dzis(filters: dict, doctype: str) -> dict:
	"""Podstawia literal "@dzis" za dzisiejsza date (issue #128, analogicznie
	do `_podstaw_me` powyzej dla "@me"). Cienki wrapper: liczy `dzis`
	(`frappe.utils.nowdate()`, data w strefie site), `jutro` (dzien pozniej,
	uzywany WYLACZNIE dla operatora "<=" na polu Datetime -- patrz docstring
	`crm.volteo_lista_szans.podstaw_dzis`) i funkcje `czy_datetime`
	sprawdzajaca typ pola przez `frappe.get_meta(doctype)`, po czym oddaje
	cala robote frappe-free rdzeniowi `podstaw_dzis`. Wywolywany w tym samym
	miejscu co `_podstaw_me`, w `get_data` ponizej i w
	`crm.api.volteo_leady.mapa`.

	`_STANDARDOWE_POLA_DATETIME` (modul, wyzej) to bezpiecznik dla pol
	standardowych bez wlasnego DocField (np. "modified"/"creation", ktore
	`FILTER_FIELDS_DEAL`/`FILTER_FIELDS_LEAD` udostepniaja jako filtrowalne,
	patrz `crm/volteo_lista_szans.py`) -- `meta.get_field` zwraca dla nich
	`None`, mimo ze SA Datetime w rdzeniu."""
	dzis = nowdate()
	jutro = add_days(dzis, 1)
	meta = frappe.get_meta(doctype)

	def czy_datetime(fieldname: str) -> bool:
		if fieldname in _STANDARDOWE_POLA_DATETIME:
			return True
		field = meta.get_field(fieldname)
		return bool(field) and field.fieldtype == "Datetime"

	return podstaw_dzis(filters, dzis, jutro, czy_datetime)


def _sprawdz_filtry(doctype: str, filters, parenttype: str | None = None) -> None:
	"""Rzuca PermissionError, jesli `filters` odwoluje sie do pola spoza
	`_pola_dozwolone(doctype, parenttype)`. `filters` moze byc dict-em
	(typowy przypadek w `get_data`) albo pojedynczym polem opakowanym w
	`{pole: None}` — patrz wywolania dla `column_field`/`group_by_field` w
	`get_data`. `parenttype` patrz `_pola_dozwolone` — domyslnie `None`,
	istniejace wywolania w tym module (`get_data` i pochodne) go nie
	przekazuja i zostaja bez zmian. `doctype` jedzie dalej do
	`niedozwolone_klucze_filtrow` (ops#124) wylacznie po to, zeby wpisy
	listowe wskazujace INNY doctype w elemencie [0] (JOIN po tabeli
	podrzednej w widoku Report) byly zawsze odrzucane, patrz docstring tej
	funkcji w `crm.volteo_lista_szans`."""
	permitted = _pola_dozwolone(doctype, parenttype=parenttype)
	niedozwolone = niedozwolone_klucze_filtrow(filters, permitted, doctype=doctype)
	if niedozwolone:
		frappe.throw(
			_("Brak uprawnień do filtrowania po polu {0}").format(niedozwolone[0]),
			frappe.PermissionError,
		)


def rozwin_grupy(doctype: str, filters: dict) -> dict:
	"""Rozwija zarezerwowany klucz `volteo_grupy` (issue #129, grupy filtrów
	ORAZ/ALBO w oknie „Filtr" listy leadów) na zwykły filtr `name in
	[...]`, żeby `get_data`/`crm.api.volteo_leady.mapa`/`przydziel_cc`
	mogły dalej operować na płaskim słowniku filtrów bez świadomości grup.

	Wołać PO `_podstaw_me`/`_podstaw_dzis` i PO scaleniu `default_filters`
	do `filters` (tak jak w `get_data` niżej), PRZED `_sprawdz_filtry`:
	ten strażnik nie zna klucza `volteo_grupy` i odrzuciłby go jak każde
	inne nieznane pole (fail closed - patrz `crm.volteo_grupy_filtrow`,
	docstring `KLUCZ_GRUP`, celowo NIE zmieniony przez ten issue, żeby ta
	sama bramka nadal odrzucała klucz na endpointach rdzenia,
	`crm.api.volteo_filtry_guard`, gdzie grupy pozostają NIEDOZWOLONE).

	`crm.volteo_grupy_filtrow.wydziel_grupy` wydziela `(filtry_bez_grup,
	grupy)` z `filters` (frappe-free, testowalne osobno). Pusta lista grup
	(albo brak klucza) zwraca `filtry_bez_grup` bez zmian - "Pusta lista
	grup = brak wpływu" (kontrakt issue #129), stare widoki bez klucza
	przechodzą przez tę funkcję identycznie jak dotąd.

	Dla NIEPUSTEJ listy grup: `waliduj_grupy` (kształt - lista słowników,
	limity `MAX_GRUP`/`MAX_WARUNKOW_W_GRUPIE`, zakaz zagnieżdżenia) rzuca
	`ValueError` przy złym kształcie, złapane tu i przekazane do
	`frappe.throw` (domyślnie `frappe.ValidationError`). `klucze_z_grup`
	daje jeden łączny pre-check permlevel na kluczach ZE WSZYSTKICH grup
	naraz, PRZED wykonaniem jakiegokolwiek zapytania dla pojedynczej grupy
	- fail fast, bez efektów ubocznych zapytań do wcześniejszych grup,
	gdyby dopiero któraś PÓŹNIEJSZA grupa odwoływała się do niedozwolonego
	pola. Potem, dla KAŻDEJ grupy z osobna: `_sprawdz_filtry` (ten sam
	strażnik, tym razem na samej tej grupie) i `frappe.get_list(doctype,
	filters=grupa ORAZ filtry_bez_grup, pluck="name", limit_page_length=0)`
	- `filtry_bez_grup` (już zawiera scalone `default_filters`, patrz wyżej)
	jest doklejany do KAŻDEJ grupy, nie tylko do finalnego wyniku: to
	czysto wydajnościowe (np. `custom_cc="ja"` zawęża zapytanie KAŻDEJ
	grupy zamiast dociągać wszystkie pasujące wiersze WSZYSTKICH
	użytkowników i dopiero na końcu je odcinać) - algebraicznie unia
	wyników z tym zawężeniem w każdej grupie i bez niego (a potem
	odcięcie na końcu) daje IDENTYCZNY finalny zbiór `name`, bo
	`custom_cc=ja ORAZ (A LUB B)` == `(custom_cc=ja ORAZ A) LUB
	(custom_cc=ja ORAZ B)` (rozdzielność ORAZ względem LUB). Wartość
	pola współdzielonego między grupą a `filtry_bez_grup` (rzadki
	przypadek - czemu użytkownik miałby filtrować to samo pole i wspólnie,
	i w grupie - kontrakt tego nie precyzuje): grupa wygrywa jako
	bardziej szczegółowa (`{**filtry_bez_grup, **grupa}`).

	`frappe.get_list` (NIE `get_all`): permission query conditions
	(`crm/permissions/org_hierarchy.py` i pokrewne) działają automatycznie
	dla każdej grupy z osobna, tak samo jak dla głównego zapytania.

	Unia nazw ze wszystkich grup (zbiór, bez duplikatów) > `LIMIT_UNIA_GRUP`
	(20000) -> `frappe.throw` po polsku - bezpiecznik rozmiaru zapytania
	`name in [...]` w wyniku. Pusta unia (żadna grupa nic nie dopasowała)
	daje świadomie `name in [""]` (0 wyników), NIE brak filtra w ogóle -
	inaczej brak dopasowań w grupach cicho zamieniłby się w "pokaż
	wszystko", odwrotność zamierzonej semantyki ALBO.

	Zwraca NOWY dict (immutability): `filtry_bez_grup` z dodanym kluczem
	`"name"`. Jeśli `filtry_bez_grup` miało już własny filtr po `name`
	(rzadkie w praktyce - UI nie oferuje filtrowania po `name` w oknie
	„Filtr" grup), zostaje on NADPISANY przez unię grup - kontrakt issue
	#129 opisuje to wprost jako "dokładany", bez rozstrzygania takiego
	konfliktu, więc zachowanie jest zgodne z brzmieniem issue.

	Fix (issue #129, po scaleniu): `_podstaw_me`/`_podstaw_dzis` wołane w
	`get_data`/`mapa` PRZED tą funkcją podstawiają placeholdery WYŁĄCZNIE
	na najwyższym poziomie `filters` - nie schodzą w głąb listy pod
	`volteo_grupy`, więc "@me"/"@dzis" WEWNĄTRZ warunku grupy (np. widok
	"Do obdzwonienia", `{"custom_kolejny_kontakt": ["<=", "@dzis"]}` w
	grupie) docierały do `frappe.get_list` jako litera string: dla pola
	Date/Datetime rdzeń Frappe rzucał `ValidationError` z `getdate()`, dla
	"@me" po cichu nie dopasowywał żadnego wiersza. Dlatego każda grupa
	jest tutaj przepuszczana przez TE SAME dwie funkcje, PO walidacji
	kształtu (`waliduj_grupy` już zagwarantowała, że każda grupa jest
	słownikiem): `_podstaw_dzis(_podstaw_me(grupa), doctype)`. Grupa jest
	płaskim słownikiem identycznym w kształcie do `filters` najwyższego
	poziomu (zakaz zagnieżdżenia w `waliduj_grupy`), więc te same funkcje
	są tu bezpiecznie stosowane ponownie bez żadnej zmiany w nich samych."""
	filtry_bez_grup, grupy = wydziel_grupy(filters)
	if not grupy:
		return filtry_bez_grup

	try:
		waliduj_grupy(grupy)
	except ValueError as e:
		frappe.throw(str(e))

	grupy = [_podstaw_dzis(_podstaw_me(grupa), doctype) for grupa in grupy]

	_sprawdz_filtry(doctype, dict.fromkeys(klucze_z_grup(grupy)))

	nazwy: set = set()
	for grupa in grupy:
		_sprawdz_filtry(doctype, grupa)
		grupa_polaczona = {**filtry_bez_grup, **grupa}
		nazwy.update(
			frappe.get_list(doctype, filters=grupa_polaczona, pluck="name", limit_page_length=0)
		)

	if len(nazwy) > LIMIT_UNIA_GRUP:
		frappe.throw(
			_("Zbyt wiele wyników pasujących do grup filtrów (limit {0}).").format(LIMIT_UNIA_GRUP)
		)

	wynik = dict(filtry_bez_grup)
	wynik["name"] = ["in", sorted(nazwy) if nazwy else [""]]
	return wynik


def _odfiltruj_niedozwolone_klucze(doctype: str, klucze: list) -> list:
	"""Zwraca `klucze` (nazwy pol z `rows`/`kanban_fields` w `get_data`) bez
	tych, do ktorych biezacy uzytkownik nie ma odczytu na poziomie permlevel
	(issue #117), pseudo-pola listy (`_POLA_LISTY_ZAWSZE_DOZWOLONE`) zawsze
	przezywaja. Kolejnosc zachowana."""
	dozwolone = _pola_dozwolone(doctype) | _POLA_LISTY_ZAWSZE_DOZWOLONE
	return [klucz for klucz in klucze if klucz in dozwolone]


def _odfiltruj_niedozwolone_kolumny(doctype: str, columns: list) -> list:
	"""Jak `_odfiltruj_niedozwolone_klucze`, ale dla `columns` w `get_data`
	(lista dictow z kluczem "key"), zeby handlowiec dostal calkowity brak
	naglowka kolumny pola permlevel > 0 (np. "Przypisany CC" na CRM Lead),
	nie tylko pusta wartosc w komorkach (issue #117)."""
	dozwolone = _pola_dozwolone(doctype) | _POLA_LISTY_ZAWSZE_DOZWOLONE
	return [column for column in columns if column.get("key") in dozwolone]


@frappe.whitelist()
def sort_options(doctype: str):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	fields = frappe.get_meta(doctype).fields
	fields = [field for field in fields if field.fieldtype not in no_value_fields]
	fields = [
		{
			"label": _(field.label),
			"value": field.fieldname,
			"fieldname": field.fieldname,
		}
		for field in fields
		if field.label and field.fieldname
	]

	standard_fields = [
		{"label": "Name", "fieldname": "name"},
		{"label": "Created On", "fieldname": "creation"},
		{"label": "Last Modified", "fieldname": "modified"},
		{"label": "Modified By", "fieldname": "modified_by"},
		{"label": "Owner", "fieldname": "owner"},
	]

	for field in standard_fields:
		field["label"] = _(field["label"])
		field["value"] = field["fieldname"]
		fields.append(field)

	# Nie oferuj sortowania po polu, po ktorym i tak nie wolno filtrowac
	# (permlevel > 0 bez uprawnienia read) — patrz ops#79.
	permitted = _pola_dozwolone(doctype)

	# Allowlista sortowania (np. CRM Deal, ops#81) — jesli kontroler ja
	# udostepnia, zwracamy WYLACZNIE te pola, w podanej kolejnosci, z
	# etykietami nadpisanymi tam, gdzie krotka je podaje. Pola nieobecne w
	# meta/liscie standardowej (np. `custom_etap_nr` przed skryptem ops z
	# issue 3) albo niedozwolone permlevelem sa po cichu pomijane.
	controller = get_controller(doctype)
	if hasattr(controller, "volteo_sort_fields"):
		by_fieldname = {field["fieldname"]: field for field in fields}
		allowlisted = []
		for fieldname, etykieta in controller.volteo_sort_fields():
			if fieldname not in by_fieldname or fieldname not in permitted:
				continue
			label = _(etykieta) if etykieta is not None else by_fieldname[fieldname]["label"]
			allowlisted.append({"label": label, "value": fieldname, "fieldname": fieldname})
		return allowlisted

	fields = [field for field in fields if field["fieldname"] in permitted]

	return fields


@frappe.whitelist()
def get_filterable_fields(doctype: str, scope: str = "list"):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	allowed_fieldtypes = [
		"Check",
		"Data",
		"Float",
		"Int",
		"Currency",
		"Dynamic Link",
		"Link",
		"Long Text",
		"Select",
		"Small Text",
		"Text Editor",
		"Text",
		"Duration",
		"Rating",
		"Date",
		"Datetime",
	]

	c = get_controller(doctype)
	restricted_fields = []
	if hasattr(c, "get_non_filterable_fields"):
		restricted_fields = c.get_non_filterable_fields()

	fields = []

	meta = frappe.get_meta(doctype).as_dict()

	# append standard fields (getting error when using frappe.model.std_fields)
	standard_fields = [
		{"fieldname": "name", "fieldtype": "Link", "label": "Name", "options": doctype},
		{"fieldname": "owner", "fieldtype": "Link", "label": "Created By", "options": "User"},
		{
			"fieldname": "modified_by",
			"fieldtype": "Link",
			"label": "Last Updated By",
			"options": "User",
		},
		{"fieldname": "_user_tags", "fieldtype": "Data", "label": "Tags"},
		{"fieldname": "_liked_by", "fieldtype": "Data", "label": "Like"},
		{"fieldname": "_comments", "fieldtype": "Text", "label": "Comments"},
		{"fieldname": "_assign", "fieldtype": "Text", "label": "Assigned To"},
		{"fieldname": "creation", "fieldtype": "Datetime", "label": "Created On"},
		{"fieldname": "modified", "fieldtype": "Datetime", "label": "Last Updated On"},
	]

	for field in standard_fields + meta.get("fields", []):
		if field.get("fieldname") not in restricted_fields and field.get("fieldtype") in allowed_fieldtypes:
			fields.append(
				{
					**field,
					"name": field.get("fieldname"),
					"label": _(field.get("label")),
					"value": field.get("fieldname"),
				}
			)

	# Nie oferuj filtrowania po polu, po ktorym i tak nie wolno filtrowac
	# (permlevel > 0 bez uprawnienia read) — patrz ops#79.
	permitted = _pola_dozwolone(doctype)

	# Allowlista filtrow listy szans (np. CRM Deal, ops#81) — tylko dla
	# scope="list" (widok listy). `scope="conditions"` (reguly przypisan,
	# SLA — `ConditionsFilter`) i kazdy inny doctype dostaja pelna liste jak
	# dotychczas, zeby nie stracic pol w tych ustawieniach.
	if scope == "list" and hasattr(c, "volteo_filter_fields"):
		by_fieldname = {field["fieldname"]: field for field in fields}
		allowlisted = []
		for fieldname, etykieta in c.volteo_filter_fields():
			if fieldname not in by_fieldname or fieldname not in permitted:
				continue
			entry = by_fieldname[fieldname]
			if etykieta is not None:
				entry = {**entry, "label": _(etykieta)}
			allowlisted.append(entry)
		return allowlisted

	fields = [field for field in fields if field.get("fieldname") in permitted]

	return fields


@frappe.whitelist()
def get_group_by_fields(doctype: str):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	allowed_fieldtypes = [
		"Check",
		"Data",
		"Float",
		"Int",
		"Currency",
		"Dynamic Link",
		"Link",
		"Select",
		"Duration",
		"Date",
		"Datetime",
	]

	fields = frappe.get_meta(doctype).fields
	fields = [
		field
		for field in fields
		if field.fieldtype not in no_value_fields
		and field.fieldtype in allowed_fieldtypes
		# Pole hidden=1 (np. custom_etap_nr, ops#82 — wewnetrzne pole
		# sortowania, nigdy nie pokazywane wprost uzytkownikowi) nie ma co
		# robic w "Grupuj wedlug"; to samo uzasadnienie co pominiecie takich
		# pol w allowlistach sortowania/filtrow (crm.volteo_lista_szans).
		and not field.hidden
	]
	fields = [
		{
			"label": _(field.label),
			"fieldname": field.fieldname,
		}
		for field in fields
		if field.label and field.fieldname
	]

	standard_fields = [
		{"label": "Name", "fieldname": "name"},
		{"label": "Created On", "fieldname": "creation"},
		{"label": "Last Modified", "fieldname": "modified"},
		{"label": "Modified By", "fieldname": "modified_by"},
		{"label": "Owner", "fieldname": "owner"},
		{"label": "Like", "fieldname": "_liked_by"},
		{"label": "Assigned To", "fieldname": "_assign"},
		{"label": "Comments", "fieldname": "_comments"},
		{"label": "Created On", "fieldname": "creation"},
		{"label": "Modified On", "fieldname": "modified"},
	]

	for field in standard_fields:
		field["label"] = _(field["label"])
		fields.append(field)

	# Nie oferuj grupowania po polu, po ktorym i tak nie wolno filtrowac
	# (permlevel > 0 bez uprawnienia read) — patrz ops#79.
	permitted = _pola_dozwolone(doctype)
	fields = [field for field in fields if field.get("fieldname") in permitted]

	return fields


@frappe.whitelist()
def get_quick_filters(doctype: str, cached: bool = True):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	meta = frappe.get_meta(doctype, cached)
	quick_filters = []

	if global_settings := frappe.db.exists("CRM Global Settings", {"dt": doctype, "type": "Quick Filters"}):
		_quick_filters = frappe.db.get_value("CRM Global Settings", global_settings, "json")
		_quick_filters = json.loads(_quick_filters) or []

		fields = []

		for filter in _quick_filters:
			if filter == "name":
				fields.append({"label": "Name", "fieldname": "name", "fieldtype": "Data"})
			else:
				field = next((f for f in meta.fields if f.fieldname == filter), None)
				if field:
					fields.append(field)

	else:
		fields = [field for field in meta.fields if field.in_standard_filter]

	# VOLTEO (ops#94): przed ta zmiana get_quick_filters nie sprawdzal
	# permlevel wcale, wiec pole permlevel > 0 (np. "Przypisany CC" na CRM
	# Lead, bez odczytu dla `Volteo D2D Sales`) wyswietlaloby sie w pasku
	# kazdemu, tak jak ops#79 juz naprawil dla sort_options/
	# get_filterable_fields/get_group_by_fields (patrz `_pola_dozwolone`).
	# Global Settings dalej moze wymienic pole niedozwolone, filtrujemy
	# dopiero tutaj po stronie odczytu, konfiguracja w bazie zostaje
	# nietknieta.
	permitted = _pola_dozwolone(doctype)
	fields = [field for field in fields if field.get("fieldname") in permitted]

	for field in fields:
		options = field.get("options")
		if field.get("fieldtype") == "Select" and options and isinstance(options, str):
			options = options.split("\n")
			options = [{"label": option, "value": option} for option in options]
			if not any([not option.get("value") for option in options]):
				options.insert(0, {"label": "", "value": ""})
		quick_filters.append(
			{
				"label": _(field.get("label")),
				"fieldname": field.get("fieldname"),
				"fieldtype": field.get("fieldtype"),
				"options": options,
			}
		)

	if doctype == "CRM Lead":
		quick_filters = [filter for filter in quick_filters if filter.get("fieldname") != "converted"]

	return quick_filters


@frappe.whitelist()
def update_quick_filters(quick_filters: str, old_filters: str, doctype: str):
	quick_filters = json.loads(quick_filters)
	old_filters = json.loads(old_filters)

	new_filters = [filter for filter in quick_filters if filter not in old_filters]
	removed_filters = [filter for filter in old_filters if filter not in quick_filters]

	# update or create global quick filter settings
	create_update_global_settings(doctype, quick_filters)

	# remove old filters
	for filter in removed_filters:
		update_in_standard_filter(filter, doctype, 0)

	# add new filters
	for filter in new_filters:
		update_in_standard_filter(filter, doctype, 1)


def create_update_global_settings(doctype, quick_filters):
	if global_settings := frappe.db.exists("CRM Global Settings", {"dt": doctype, "type": "Quick Filters"}):
		frappe.db.set_value("CRM Global Settings", global_settings, "json", json.dumps(quick_filters))
	else:
		# create CRM Global Settings doc
		doc = frappe.new_doc("CRM Global Settings")
		doc.dt = doctype
		doc.type = "Quick Filters"
		doc.json = json.dumps(quick_filters)
		doc.insert()


def update_in_standard_filter(fieldname, doctype, value):
	if property_name := frappe.db.exists(
		"Property Setter",
		{"doc_type": doctype, "field_name": fieldname, "property": "in_standard_filter"},
	):
		frappe.db.set_value("Property Setter", property_name, "value", value)
	else:
		make_property_setter(
			doctype,
			fieldname,
			"in_standard_filter",
			value,
			"Check",
			validate_fields_for_doctype=False,
		)


@frappe.whitelist()
def get_data(
	doctype: str,
	filters: dict,
	order_by: str,
	page_length: int = 20,
	page_length_count: int = 20,
	column_field: str | None = None,
	title_field: str | None = None,
	columns: str | list | None = None,
	rows: str | list | None = None,
	kanban_columns: str | list | None = None,
	kanban_fields: str | list | None = None,
	view: str | dict | None = None,
	default_filters: dict | None = None,
):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	custom_view = False
	filters = frappe._dict(filters)
	rows = frappe.parse_json(rows or "[]")
	columns = frappe.parse_json(columns or "[]")
	kanban_fields = frappe.parse_json(kanban_fields or "[]")
	kanban_columns = frappe.parse_json(kanban_columns or "[]")

	custom_view_name = view.get("custom_view_name") if view else None
	view_type = view.get("view_type") if view else None
	group_by_field = view.get("group_by_field") if view else None

	# Blokada grupowania po polu bez uprawnien odczytu (permlevel > 0) — patrz
	# ops#79. Walidujemy natychmiast po ekstrakcji, przed jakimkolwiek uzyciem
	# group_by_field (dopisanie do rows nizej, potem do fields=rows w
	# frappe.get_list).
	if group_by_field:
		_sprawdz_filtry(doctype, {group_by_field: None})

	filters = frappe._dict(_podstaw_me(filters))
	filters = frappe._dict(_podstaw_dzis(filters, doctype))

	if default_filters:
		default_filters = frappe.parse_json(default_filters)
		filters.update(default_filters)

	# VOLTEO (issue #129): rozwija ewentualny klucz "volteo_grupy" (grupy
	# filtrów ORAZ/ALBO) na zwykly filtr "name in [...]" -- PO scaleniu
	# default_filters (rozwin_grupy dokleja "filtry_bez_grup", ktore juz je
	# zawiera, do KAZDEJ grupy, patrz jej docstring), PRZED _sprawdz_filtry
	# nizej (ktora nie zna tego klucza i odrzucilaby go jak kazde inne
	# nieznane pole). Bez klucza w filters ta funkcja jest no-opem.
	filters = frappe._dict(rozwin_grupy(doctype, filters))

	# Blokada filtrowania po polu bez uprawnien odczytu (permlevel > 0) — patrz
	# ops#79. Walidujemy PO scaleniu default_filters i podstawieniu @me/@dzis,
	# zeby objac kazdy filtr, ktory trafi do frappe.get_list nizej (l.374/437/448/554
	# w wersji sprzed tej zmiany) — filters jest jedynym zrodlem tych wywolan.
	_sprawdz_filtry(doctype, filters)

	is_default = True
	data = []
	_list = get_controller(doctype)
	default_rows = []
	if hasattr(_list, "default_list_data"):
		default_rows = _list.default_list_data().get("rows")

	meta = frappe.get_meta(doctype)

	if view_type != "kanban":
		if columns or rows:
			custom_view = True
			is_default = False
			columns = frappe.parse_json(columns)
			rows = frappe.parse_json(rows)

		if not columns:
			columns = [
				{"label": "Name", "type": "Data", "key": "name", "width": "16rem"},
				{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
			]

		if not rows:
			rows = ["name"]

		default_view_filters = {
			"dt": doctype,
			"type": view_type or "list",
			"is_standard": 1,
			"user": frappe.session.user,
		}

		if not custom_view and frappe.db.exists("CRM View Settings", default_view_filters):
			list_view_settings = frappe.get_doc("CRM View Settings", default_view_filters)
			columns = frappe.parse_json(list_view_settings.columns)
			rows = frappe.parse_json(list_view_settings.rows)
			is_default = False
		elif not custom_view or (is_default and hasattr(_list, "default_list_data")):
			rows = default_rows
			columns = _list.default_list_data().get("columns")

		# VOLTEO (issue #117): filtrowanie po permlevel TUTAJ, na finalnych
		# columns/rows, niezaleznie od zrodla (custom_view przeslany przez
		# klienta, zapisany CRM View Settings, albo default_list_data()) --
		# bez tego pole permlevel > 0 bez odczytu (np. custom_cc na CRM Lead
		# dla Volteo D2D Sales) renderowalo sie jako naglowek kolumny z pusta
		# wartoscia zamiast znikac calkowicie. Zapisane widoki NIE sa
		# modyfikowane, filtr dziala wylacznie przy odczycie.
		columns = _odfiltruj_niedozwolone_kolumny(doctype, columns)
		rows = _odfiltruj_niedozwolone_klucze(doctype, rows)

		# check if rows has all keys from columns if not add them
		for column in columns:
			if column.get("key") not in rows:
				rows.append(column.get("key"))
			column["label"] = _(column.get("label"))

			if column.get("key") == "_liked_by" and column.get("width") == "10rem":
				column["width"] = "50px"

			# remove column if column.hidden is True
			column_meta = meta.get_field(column.get("key"))
			if column_meta and column_meta.get("hidden"):
				columns.remove(column)

		# check if rows has group_by_field if not add it
		if group_by_field and group_by_field not in rows:
			rows.append(group_by_field)

		# VOLTEO (ops#94): "_comment_count" nie jest prawdziwym DocFieldem, wiec
		# psulby zapytanie SQL wprost w `fields`. Wycinamy je z listy pol PRZED
		# `frappe.get_list`, a po pobraniu danych doliczamy JEDNYM zapytaniem
		# grupowanym po "reference_name" (nie N+1 per wiersz). `rows` samo w
		# sobie zostaje nietkniete, bo jest zwracane wprost do frontendu.
		chce_licznik_komentarzy = "_comment_count" in rows
		sql_rows = [row for row in rows if row != "_comment_count"]

		data = (
			frappe.get_list(
				doctype,
				fields=sql_rows,
				filters=filters,
				order_by=order_by,
				page_length=page_length,
			)
			or []
		)
		data = parse_list_data(data, doctype)

		if chce_licznik_komentarzy:
			nazwy = [d.get("name") for d in data if d.get("name")]
			mapa_licznikow = {}
			if nazwy:
				for wiersz in frappe.get_all(
					"Comment",
					filters={
						"reference_doctype": doctype,
						"reference_name": ["in", nazwy],
						"comment_type": "Comment",
					},
					fields=["reference_name", "count(name) as n"],
					group_by="reference_name",
				):
					mapa_licznikow[wiersz.reference_name] = wiersz.n
			for d in data:
				d["_comment_count"] = mapa_licznikow.get(d.get("name"), 0)

	if view_type == "kanban":
		if not rows:
			rows = default_rows

		# Blokada grupowania kanbanu po polu bez uprawnien odczytu (permlevel > 0)
		# — patrz ops#79. Walidujemy przed jakimkolwiek uzyciem column_field jako
		# klucza filtra nizej (column_filters, new_filters, get_records_based_on_order).
		if column_field:
			_sprawdz_filtry(doctype, {column_field: None})

		if not kanban_columns and column_field:
			field_meta = frappe.get_meta(doctype).get_field(column_field)
			if field_meta.fieldtype == "Link":
				# get_list (not get_all) so this respects read permission and
				# permission_query_conditions on the linked doctype instead of
				# leaking its full directory (e.g. every User) to any caller.
				kanban_columns = frappe.get_list(
					field_meta.options,
					fields=["name"],
					order_by="modified asc",
				)
			elif field_meta.fieldtype == "Select":
				kanban_columns = [{"name": option} for option in field_meta.options.split("\n")]

		if not title_field:
			title_field = "name"
			if hasattr(_list, "default_kanban_settings"):
				title_field = _list.default_kanban_settings().get("title_field")

		if title_field not in rows:
			rows.append(title_field)

		if not kanban_fields:
			kanban_fields = ["name"]
			if hasattr(_list, "default_kanban_settings"):
				kanban_fields = json.loads(_list.default_kanban_settings().get("kanban_fields"))

		for field in kanban_fields:
			if field not in rows:
				rows.append(field)

		# VOLTEO (issue #117): jak w gałęzi niekanban powyzej -- rows/
		# kanban_fields sa juz w tym miejscu w pelni ustalone (defaultowe
		# albo przeslane przez klienta), wiec filtrujemy je RAZ, przed
		# zapytaniem do bazy nizej.
		rows = _odfiltruj_niedozwolone_klucze(doctype, rows)
		kanban_fields = _odfiltruj_niedozwolone_klucze(doctype, kanban_fields)

		for kc in kanban_columns:
			column_filters = {column_field: kc.get("name")}
			order = kc.get("order")
			if (column_field in filters and filters.get(column_field) != kc.get("name")) or kc.get("delete"):
				column_data = []
			else:
				column_filters.update(filters.copy())
				page_length = 20

				if kc.get("page_length"):
					page_length = kc.get("page_length")

				if order:
					column_data = get_records_based_on_order(
						doctype, rows, column_filters, page_length, order
					)
				else:
					column_data = frappe.get_list(
						doctype,
						fields=rows,
						filters=convert_filter_to_tuple(doctype, column_filters),
						order_by=order_by,
						page_length=page_length,
					)

				new_filters = filters.copy()
				new_filters.update({column_field: kc.get("name")})

				all_count = frappe.get_list(
					doctype,
					filters=convert_filter_to_tuple(doctype, new_filters),
					fields=[COUNT_NAME],
				)[0].total_count

				kc["all_count"] = all_count
				kc["count"] = len(column_data)

				for d in column_data:
					getCounts(d, doctype)

			if order:
				column_data = sorted(
					column_data,
					key=lambda x: order.index(x.get("name")) if x.get("name") in order else len(order),
				)

			data.append({"column": kc, "fields": kanban_fields, "data": column_data})

	fields = frappe.get_meta(doctype).fields
	fields = [field for field in fields if field.fieldtype not in no_value_fields]
	fields = [
		{
			"label": _(field.label),
			"fieldtype": field.fieldtype,
			"fieldname": field.fieldname,
			"options": field.options,
		}
		for field in fields
		if field.label and field.fieldname
	]

	std_fields = [
		{"label": "Name", "fieldtype": "Data", "fieldname": "name"},
		{"label": "Created On", "fieldtype": "Datetime", "fieldname": "creation"},
		{"label": "Last Modified", "fieldtype": "Datetime", "fieldname": "modified"},
		{
			"label": "Modified By",
			"fieldtype": "Link",
			"fieldname": "modified_by",
			"options": "User",
		},
		{"label": "Assigned To", "fieldtype": "Text", "fieldname": "_assign"},
		{"label": "Owner", "fieldtype": "Link", "fieldname": "owner", "options": "User"},
		{"label": "Like", "fieldtype": "Data", "fieldname": "_liked_by"},
	]

	for field in std_fields:
		if field.get("fieldname") not in rows:
			rows.append(field.get("fieldname"))
		if field not in fields:
			field["label"] = _(field["label"])
			fields.append(field)

	if not is_default and custom_view_name:
		is_default = frappe.db.get_value("CRM View Settings", custom_view_name, "load_default_columns")

	if group_by_field and view_type == "group_by":

		def get_options(type, options):
			if type == "Select":
				return [option for option in options.split("\n")]
			else:
				has_empty_values = any([not d.get(group_by_field) for d in data])
				options = list(set([d.get(group_by_field) for d in data]))
				options = [u for u in options if u]
				if has_empty_values:
					options.append("")

				if order_by and group_by_field in order_by:
					order_by_fields = order_by.split(",")
					order_by_fields = [
						(field.split(" ")[0], field.split(" ")[1]) for field in order_by_fields
					]
					if (group_by_field, "asc") in order_by_fields:
						options.sort()
					elif (group_by_field, "desc") in order_by_fields:
						options.sort(reverse=True)
				else:
					options.sort()
				return options

		for field in fields:
			if field.get("fieldname") == group_by_field:
				group_by_field = {
					"label": field.get("label"),
					"fieldname": field.get("fieldname"),
					"fieldtype": field.get("fieldtype"),
					"options": get_options(field.get("fieldtype"), field.get("options")),
				}

	return {
		"data": data,
		"columns": columns,
		"rows": rows,
		"fields": fields,
		"column_field": column_field,
		"title_field": title_field,
		"kanban_columns": kanban_columns,
		"kanban_fields": kanban_fields,
		"group_by_field": group_by_field,
		"page_length": page_length,
		"page_length_count": page_length_count,
		"is_default": is_default,
		"views": get_views(doctype),
		"total_count": frappe.get_list(doctype, filters=filters, fields=[COUNT_NAME])[0].total_count,
		"row_count": len(data),
		"form_script": get_form_script(doctype),
		"list_script": get_form_script(doctype, "List"),
		"view_type": view_type,
	}


def parse_list_data(data, doctype):
	_list = get_controller(doctype)
	if hasattr(_list, "parse_list_data"):
		data = _list.parse_list_data(data)
	return data


def convert_filter_to_tuple(doctype, filters):
	if isinstance(filters, dict):
		filters_items = filters.items()
		filters = []
		for key, value in filters_items:
			filters.append(make_filter_tuple(doctype, key, value))
	return filters


def get_records_based_on_order(doctype, rows, filters, page_length, order):
	records = []
	filters = convert_filter_to_tuple(doctype, filters)
	in_filters = filters.copy()
	in_filters.append([doctype, "name", "in", order[:page_length]])
	records = frappe.get_list(
		doctype,
		fields=rows,
		filters=in_filters,
		order_by="creation desc",
		page_length=page_length,
	)

	if len(records) < page_length:
		not_in_filters = filters.copy()
		not_in_filters.append([doctype, "name", "not in", order])
		remaining_records = frappe.get_list(
			doctype,
			fields=rows,
			filters=not_in_filters,
			order_by="creation desc",
			page_length=page_length - len(records),
		)
		for record in remaining_records:
			records.append(record)

	return records


@frappe.whitelist()
def remove_assignments(doctype: str, name: str, assignees: str | list):
	# ignore_permissions was previously a caller-settable whitelisted HTTP parameter
	# that let any authenticated user bypass assignment authorization. Removed;
	# the legitimate frontend never passed it, so set_status now always runs
	# with its own default (ignore_permissions=False).
	assignees = frappe.parse_json(assignees)

	if not assignees:
		return

	for assign_to in assignees:
		set_status(
			doctype,
			name,
			todo=None,
			assign_to=assign_to,
			status="Cancelled",
		)


@frappe.whitelist()
def can_delete(doctype: str) -> bool:
	from crm.permissions.delete_lockdown import LOCKED_DELETE_DOCTYPES, is_delete_admin

	if doctype in LOCKED_DELETE_DOCTYPES and not is_delete_admin(frappe.session.user):
		return False
	return bool(frappe.has_permission(doctype, ptype="delete"))


@frappe.whitelist()
def get_assigned_users(doctype: str, name: str | int, default_assigned_to: str | None = None):
	assigned_users = frappe.get_all(
		"ToDo",
		fields=["allocated_to"],
		filters={
			"reference_type": doctype,
			"reference_name": name,
			"status": ("!=", "Cancelled"),
		},
		pluck="allocated_to",
	)

	users = list(set(assigned_users))

	# if users is empty, add default_assigned_to
	if not users and default_assigned_to:
		users = [default_assigned_to]
	return users


@frappe.whitelist()
def get_fields(doctype: str, allow_all_fieldtypes: bool = False):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	not_allowed_fieldtypes = [*list(frappe.model.no_value_fields), "Read Only"]
	if allow_all_fieldtypes:
		not_allowed_fieldtypes = []
	fields = frappe.get_meta(doctype).fields

	_fields = []

	for field in fields:
		if field.fieldtype not in not_allowed_fieldtypes and field.fieldname:
			_fields.append(field)

	return _fields


def getCounts(d, doctype):
	d["_email_count"] = (
		frappe.db.count(
			"Communication",
			filters={
				"reference_doctype": doctype,
				"reference_name": d.get("name"),
				"communication_type": "Communication",
			},
		)
		or 0
	)
	d["_email_count"] = d["_email_count"] + frappe.db.count(
		"Communication",
		filters={
			"reference_doctype": doctype,
			"reference_name": d.get("name"),
			"communication_type": "Automated Message",
		},
	)
	d["_comment_count"] = frappe.db.count(
		"Comment",
		filters={"reference_doctype": doctype, "reference_name": d.get("name"), "comment_type": "Comment"},
	)
	d["_task_count"] = frappe.db.count(
		"CRM Task", filters={"reference_doctype": doctype, "reference_docname": d.get("name")}
	)
	d["_note_count"] = frappe.db.count(
		"FCRM Note", filters={"reference_doctype": doctype, "reference_docname": d.get("name")}
	)
	return d


@frappe.whitelist()
def get_linked_docs_of_document(doctype: str, docname: str):
	if not frappe.has_permission(doctype, "read", docname):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	try:
		doc = frappe.get_doc(doctype, docname)
	except frappe.DoesNotExistError:
		return []

	linked_docs = get_linked_docs(doc)
	dynamic_linked_docs = get_dynamic_linked_docs(doc)

	linked_docs.extend(dynamic_linked_docs)
	linked_docs = list({doc["reference_docname"]: doc for doc in linked_docs}.values())

	docs_data = []
	for doc in linked_docs:
		if not doc.get("reference_doctype") or not doc.get("reference_docname"):
			continue

		try:
			data = frappe.get_doc(doc["reference_doctype"], doc["reference_docname"])
		except (frappe.DoesNotExistError, frappe.ValidationError):
			continue

		title = data.get("title")
		if data.doctype == "CRM Call Log":
			title = f"Call from {data.get('from')} to {data.get('to')}"

		if data.doctype == "CRM Deal":
			title = data.get("organization")

		if data.doctype == "CRM Notification":
			title = data.get("message")

		docs_data.append(
			{
				"doc": data.doctype,
				"title": title or data.get("name"),
				"reference_docname": doc["reference_docname"],
				"reference_doctype": doc["reference_doctype"],
			}
		)

	if doctype == "CRM Deal":
		# Doctypy Volteo linkuja CRM Deal przez wlasne pole Link "deal", wiec
		# generyczny mechanizm reference_doctype/reference_docname powyzej ich
		# nie widzi — dopisujemy je jawnie, zeby DeleteLinkedDocModal je pokazal.
		existing_keys = {(d["reference_doctype"], d["reference_docname"]) for d in docs_data}
		for cascade_doctype, cascade_field in DEAL_CASCADE_DOCTYPES:
			if not frappe.db.exists("DocType", cascade_doctype):
				continue

			for row_name in frappe.get_all(
				cascade_doctype, filters={cascade_field: docname}, pluck="name"
			):
				key = (cascade_doctype, row_name)
				if key in existing_keys:
					continue

				try:
					row_doc = frappe.get_doc(cascade_doctype, row_name)
				except (frappe.DoesNotExistError, frappe.ValidationError):
					continue

				docs_data.append(
					{
						"doc": cascade_doctype,
						"title": row_doc.get("title") or row_name,
						"reference_docname": row_name,
						"reference_doctype": cascade_doctype,
					}
				)
				existing_keys.add(key)

	return docs_data


# Doctype'y Volteo linkujace CRM Deal przez wlasne pole Link "deal" —
# generyczny mechanizm reference_doctype/reference_docname ich nie zna,
# wiec kaskada musi byc jawna.
DEAL_CASCADE_DOCTYPES = [
	("Volteo Umowa", "deal"),
	("Volteo Kredyt", "deal"),
	("Volteo Audyt", "deal"),
	("Volteo Audyt CP", "deal"),
	("Volteo Faktura", "deal"),
	("Volteo Montaz Update", "deal"),
	("Volteo Trify Update", "deal"),
	("Volteo Oferta", "deal"),
	("Volteo CP Oferta", "deal"),
]
AUTENTI_STATUSY_BLOKADY = {"Wysyłanie", "Wysłana", "Podpisana"}
OFERTA_STATUSY_BLOKADY = {"Wysłana do podpisu", "Podpisana"}
CONTACT_UNLINK_LINK_FIELDS = [("Volteo Oferta", "contact")]


def remove_doc_link(doctype, docname):
	if not doctype or not docname:
		return

	try:
		linked_doc_data = frappe.get_doc(doctype, docname)
		if doctype == "CRM Notification":
			delete_notification_type = {
				"notification_type_doctype": "",
				"notification_type_doc": "",
			}
			delete_references = {
				"reference_doctype": "",
				"reference_name": "",
			}
			if linked_doc_data.get("notification_type_doctype") == linked_doc_data.get("reference_doctype"):
				delete_references.update(delete_notification_type)

			linked_doc_data.update(delete_references)
		else:
			linked_doc_data.update(
				{
					"reference_doctype": "",
					"reference_docname": "",
				}
			)
		linked_doc_data.save(ignore_permissions=True)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		pass


def remove_contact_link(doctype, docname):
	if not doctype or not docname:
		return

	try:
		linked_doc_data = frappe.get_doc(doctype, docname)
		linked_doc_data.update(
			{
				"contact": None,
				"contacts": [],
			}
		)
		linked_doc_data.save(ignore_permissions=True)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		pass


@frappe.whitelist()
def remove_linked_doc_reference(items: str | list, remove_contact: bool = False, delete: bool = False):
	if isinstance(items, str):
		items = frappe.parse_json(items)

	for item in items:
		if not item.get("doctype") or not item.get("docname"):
			continue

		if not frappe.has_permission(item["doctype"], "write", item["docname"]):
			continue

		try:
			if remove_contact:
				remove_contact_link(item["doctype"], item["docname"])
			else:
				remove_doc_link(item["doctype"], item["docname"])
			if delete:
				frappe.delete_doc(item["doctype"], item["docname"])
		except (frappe.DoesNotExistError, frappe.ValidationError):
			# Skip if document doesn't exist or has validation errors
			continue

	return "success"


def _bezpiecznik_autenti(deal_name: str) -> str | None:
	"""Blokuje usuniecie CRM Deal, jesli powiazany dokument Volteo ma juz
	status podpisu (Autenti lub Oferta) — usuniecie kaskadowe skasowaloby
	prawnie wiazacy dokument."""
	for cascade_doctype, cascade_field in DEAL_CASCADE_DOCTYPES:
		if not frappe.db.exists("DocType", cascade_doctype):
			continue

		meta = frappe.get_meta(cascade_doctype)
		status_field = None
		blocked_statuses = None
		if cascade_doctype in ("Volteo Umowa", "Volteo Kredyt") and meta.has_field("autenti_status"):
			status_field = "autenti_status"
			blocked_statuses = AUTENTI_STATUSY_BLOKADY
		elif cascade_doctype == "Volteo Oferta" and meta.has_field("status"):
			status_field = "status"
			blocked_statuses = OFERTA_STATUSY_BLOKADY

		if not status_field:
			continue

		rows = frappe.get_all(cascade_doctype, filters={cascade_field: deal_name}, fields=["name", status_field])
		for row in rows:
			status = row.get(status_field)
			if status in blocked_statuses:
				return (
					f"Powiązany dokument {cascade_doctype} {row.name} ma status podpisu "
					f"„{status}” — podpisanych lub wysłanych do podpisu dokumentów nie wolno usuwać."
				)

	return None


def _usun_jeden(doctype: str, name: str, delete_linked: bool) -> None:
	"""Usuwa jeden dokument wraz z powiazaniami. Rzuca wyjatek na kazdym
	niepowodzeniu — wywolujacy (delete_bulk_docs) lapie go per-rekord."""
	if not frappe.has_permission(doctype, "delete", name):
		frappe.throw(_("Brak uprawnień do usunięcia tego rekordu."), frappe.PermissionError)

	if doctype == "CRM Deal":
		powod = _bezpiecznik_autenti(name)
		if powod:
			frappe.throw(powod, frappe.ValidationError)

		for cascade_doctype, cascade_field in DEAL_CASCADE_DOCTYPES:
			if not frappe.db.exists("DocType", cascade_doctype):
				continue
			for row_name in frappe.get_all(cascade_doctype, filters={cascade_field: name}, pluck="name"):
				frappe.delete_doc(cascade_doctype, row_name)

		linked_docs = get_linked_docs_of_document("CRM Deal", name)
		for linked_doc in linked_docs:
			if not linked_doc.get("reference_doctype") or not linked_doc.get("reference_docname"):
				continue

			remove_linked_doc_reference(
				[
					{
						"doctype": linked_doc["reference_doctype"],
						"docname": linked_doc["reference_docname"],
					}
				],
				remove_contact=False,
				delete=delete_linked,
			)

		frappe.delete_doc("CRM Deal", name)

	elif doctype == "Contact":
		# Wpierw celowane odlinkowanie: tylko wiersze/dealy DOTYCZACE tego
		# kontaktu, nie remove_contact_link (ktory czysci CALA tabele
		# "contacts" dokumentu, wliczajac innych kontaktow).
		child_deal_names = frappe.get_all(
			"CRM Contacts",
			filters={"contact": name, "parenttype": "CRM Deal"},
			pluck="parent",
			distinct=True,
		)
		direct_deal_names = frappe.get_all("CRM Deal", filters={"contact": name}, pluck="name")
		affected_deals = set(child_deal_names) | set(direct_deal_names)

		for deal_name in affected_deals:
			deal_doc = frappe.get_doc("CRM Deal", deal_name)
			deal_doc.contacts = [row for row in deal_doc.contacts if row.contact != name]
			if deal_doc.get("contact") == name:
				deal_doc.contact = None
			deal_doc.save(ignore_permissions=True)

		for cascade_doctype, cascade_field in CONTACT_UNLINK_LINK_FIELDS:
			if not frappe.db.exists("DocType", cascade_doctype):
				continue
			for row_name in frappe.get_all(cascade_doctype, filters={cascade_field: name}, pluck="name"):
				frappe.db.set_value(cascade_doctype, row_name, cascade_field, None)

		# Adresy linkuja kontakt przez child table Dynamic Link — usun tylko
		# wiersze tego kontaktu; osierocony adres (bez zadnych pozostalych
		# linkow) usun w calosci.
		adresy = frappe.get_all(
			"Dynamic Link",
			filters={"link_doctype": "Contact", "link_name": name, "parenttype": "Address"},
			pluck="parent",
			distinct=True,
		)
		osierocone_adresy = []
		for adres_name in adresy:
			adres_doc = frappe.get_doc("Address", adres_name)
			pozostale = [
				row for row in adres_doc.links
				if not (row.link_doctype == "Contact" and row.link_name == name)
			]
			adres_doc.links = pozostale
			adres_doc.save(ignore_permissions=True)
			if not pozostale:
				osierocone_adresy.append(adres_name)

		# Generyczna sciezka dla reszty (Task/Note/itp.) — wykluczamy CRM
		# Deal, bo obsluzylismy go wyzej celowo (remove_contact_link
		# wyczyscilby CALA tabele "contacts", nie tylko ten wiersz).
		linked_docs = get_linked_docs_of_document("Contact", name)
		linked_docs = [d for d in linked_docs if d.get("reference_doctype") != "CRM Deal"]
		for linked_doc in linked_docs:
			if not linked_doc.get("reference_doctype") or not linked_doc.get("reference_docname"):
				continue

			remove_linked_doc_reference(
				[
					{
						"doctype": linked_doc["reference_doctype"],
						"docname": linked_doc["reference_docname"],
					}
				],
				remove_contact=True,
				delete=delete_linked,
			)

		frappe.delete_doc("Contact", name)

		# Dopiero po skasowaniu kontaktu nic juz nie linkuje osieroconych
		# adresow — usuwamy je teraz, zeby uniknac LinkExistsError z
		# jeszcze zywego Contact.address.
		for adres_name in osierocone_adresy:
			frappe.delete_doc("Address", adres_name)

	else:
		linked_docs = get_linked_docs_of_document(doctype, name)
		for linked_doc in linked_docs:
			if not linked_doc.get("reference_doctype") or not linked_doc.get("reference_docname"):
				continue

			remove_linked_doc_reference(
				[
					{
						"doctype": linked_doc["reference_doctype"],
						"docname": linked_doc["reference_docname"],
					}
				],
				remove_contact=False,
				delete=delete_linked,
			)

		frappe.delete_doc(doctype, name)


@frappe.whitelist()
def delete_bulk_docs(doctype: str, items: str | list, delete_linked: bool = False):
	if not doctype:
		frappe.throw(_("Doctype is required"))

	if not items:
		frappe.throw(_("Items are required"))

	items = frappe.parse_json(items)
	if not isinstance(items, list):
		frappe.throw(_("Items must be a list"))

	if len(items) > 200:
		frappe.throw(_("Za dużo rekordów naraz (limit 200)."))

	deleted = []
	failed = []

	for idx, name in enumerate(items):
		savepoint = f"bulk_del_{idx}"
		frappe.db.savepoint(savepoint)
		try:
			if not frappe.db.exists(doctype, name):
				# Cel juz osiagniety — rekordu i tak nie ma.
				deleted.append(name)
				continue

			_usun_jeden(doctype, name, delete_linked)
			deleted.append(name)
		except frappe.DoesNotExistError:
			deleted.append(name)
		except frappe.PermissionError:
			frappe.db.rollback(save_point=savepoint)
			frappe.clear_messages()
			failed.append({"name": name, "reason": "Brak uprawnień do usunięcia tego rekordu."})
		except frappe.LinkExistsError:
			frappe.db.rollback(save_point=savepoint)
			frappe.clear_messages()
			failed.append(
				{
					"name": name,
					"reason": (
						"Rekord jest powiązany z innymi dokumentami, których nie można "
						"automatycznie usunąć."
					),
				}
			)
		except frappe.ValidationError as e:
			frappe.db.rollback(save_point=savepoint)
			frappe.clear_messages()
			reason = e.args[0] if e.args else str(e)
			failed.append({"name": name, "reason": str(reason)})
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.clear_messages()
			frappe.log_error(frappe.get_traceback(), "Bulk Delete Error")
			failed.append({"name": name, "reason": "Nieoczekiwany błąd — szczegóły w logu serwera."})

	# Bezpiecznik: gwarantuje czysta koperte HTTP niezaleznie od tego, ktore
	# galezie wyzej sie wykonaly (np. msgprint z frappe.get_doc przy
	# DoesNotExistError albo z udanej kaskady nie powinien wyciec jako
	# _server_messages przy odpowiedzi 200).
	frappe.clear_messages()

	return {"total": len(items), "deleted": deleted, "failed": failed}


@frappe.whitelist()
def pola_dozwolone(doctype: str) -> list[str]:
	"""Posortowana lista nazw pol doctype'u dostepnych BIEZACEMU uzytkownikowi
	do odczytu (permlevel), do filtrowania listy pol oferowanych w oknie
	"Kolumny" po stronie frontu (`ColumnSettings.vue`).

	Zanim ten endpoint powstal, `ColumnSettings.vue` budowal liste "Dodaj
	kolumne" z `getMeta(doctype).getFields()`, ktore wywoluje rdzeniowe
	`frappe.desk.form.load.getdoctype` i zwraca WSZYSTKIE pola doctype'u,
	takze permlevel > 0 (np. "Przypisany CC" na `CRM Lead`, pola
	kosztow/prowizji na `CRM Deal`). Handlowiec (`Volteo D2D Sales`) mogl
	wiec dodac taka kolumne, po czym `get_data` w tym module i tak wycinal
	jej dane przez `_odfiltruj_niedozwolone_kolumny` (issue #117): kolumna
	zostawala pusta zamiast wcale sie nie pojawic. Ten endpoint zwraca
	dokladnie ten sam zbior nazw, ktory `_odfiltruj_niedozwolone_kolumny`
	uzywa do wycinania kolumn w `get_data`
	(`_pola_dozwolone(doctype) | _POLA_LISTY_ZAWSZE_DOZWOLONE`), zeby lista
	"Dodaj kolumne" byla spojna z tym, co faktycznie trafi do danych.
	"""
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	dozwolone = _pola_dozwolone(doctype) | _POLA_LISTY_ZAWSZE_DOZWOLONE
	return sorted(dozwolone)
