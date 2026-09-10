# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Blokada filtrów/sortowania/grupowania po polach bez uprawnień odczytu (permlevel).

Frappe blokuje sortowanie i grupowanie po polach permlevel > 0
(`validate_fieldlevel_permissions_for_sort`, `frappe/model/db_query.py:1545`) i
bezpośredni odczyt takich pól przez `get_permitted_fields`, ale NIE filtrowanie —
`frappe.desk.reportview.validate_filters` sprawdza tylko, czy pole istnieje w
doctype, nie czy wolno je odczytać. Bez tej bramki handlowiec (`Volteo D2D
Sales`) mógłby np. filtrem `custom_koszty_zysk_plan > 0` odczytać zysk i
prowizje każdej szansy mimo że pole ma permlevel 2 i nie jest mu udostępnione
do odczytu wprost.

Moduł celowo nie importuje ``frappe`` — to jedyny sposób, żeby dało się go
przetestować lokalnie (na tej maszynie ``frappe`` nie jest instalowalny, więc
reszta backendu ma wyłącznie bramkę składniową). Sam zbiór "dozwolonych pól"
(wynik `frappe.model.get_permitted_fields`) liczy wywołujący (`crm/api/doc.py`)
i przekazuje tutaj — ten moduł tylko porównuje klucze filtra z tym zbiorem.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence

# Pola zawsze dozwolone do filtrowania/sortowania/grupowania, niezaleznie od
# tego, co zwroci `get_permitted_fields` dla danego doctype'u — bezpiecznik
# uzywany przez `crm.api.doc._pola_dozwolone` (ops#79). Trzy ostatnie pozycje
# (`parent`, `parenttype`, `parentfield`) to `frappe.model.child_table_fields`
# — dopisane w ops#80 follow-up, bo dla TABELI PODRZEDNEJ wywolanej BEZ
# `parenttype` (np. `frappe.client.get_list` na `Volteo Zestaw Item` bez
# przekazania parenttype do `get_permitted_fields`) rdzen zwraca WYLACZNIE
# `default_fields` (7 pol) — bez `parent`/`parenttype`/`parentfield` i bez
# ktoregokolwiek DocFielda wiersza — wiec filtr `{parenttype: ..., parent:
# ...}` uzywany przez kazdy odczyt tabeli podrzednej (np. `ZestawTab.vue`)
# byl odrzucany jako "niedozwolony". Ten modul jest celowo frappe-free (patrz
# docstring modulu), wiec te trzy nazwy sa tu zapisane literalnie jako
# backstop; `crm.api.doc` dodatkowo dokleja `frappe.model.child_table_fields`
# wprost z frameworka, gdyby go kiedys przemianowano.
POLA_ZAWSZE_DOZWOLONE: frozenset[str] = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"_assign",
		"_liked_by",
		"_comments",
		"_user_tags",
		"parent",
		"parenttype",
		"parentfield",
	}
)

# Allowlisty sortowania i filtrow listy szans (ops#81). Kazda krotka to
# `(fieldname, etykieta)`; `etykieta is None` oznacza "wez etykiete ze
# standardowej listy pol albo z meta doctype'u przez `_()`" (Property Settery
# nadaja wtedy polskie nazwy: "Klient", "Doradca", "Telefon", "Mail",
# "Miejscowosc", "Kod pocztowy", "Wojewodztwo", "Kwota brutto", "Data
# zamkniecia"). Kolejnosc krotek to kolejnosc prezentacji w UI — konsumowana
# przez `CRMDeal.volteo_sort_fields()` / `volteo_filter_fields()`
# (`crm/fcrm/doctype/crm_deal/crm_deal.py`), `crm.api.doc.sort_options` /
# `get_filterable_fields`, oraz przez skrypt ops `crm-lista-szans-filtry.py`
# (normalizuje pary do samych fieldnames).
SORT_FIELDS_DEAL: tuple[tuple[str, str | None], ...] = (
	("modified", "Ostatnia zmiana"),
	("creation", "Data utworzenia"),
	("custom_etap_nr", "Etap"),
	("lead_name", None),
	("deal_owner", None),
	("deal_value", None),
	("custom_rodzaj_umowy", None),
	("custom_install_postal_code", None),
)

FILTER_FIELDS_DEAL: tuple[tuple[str, str | None], ...] = (
	("custom_rodzaj_umowy", None),
	("status", "Etap"),
	("deal_owner", None),
	("lead_name", None),
	("mobile_no", None),
	("email", None),
	("custom_install_city", None),
	("custom_install_postal_code", None),
	("custom_voivodeship", None),
	("deal_value", None),
	("modified", "Ostatnia zmiana"),
	("creation", "Data utworzenia"),
	("closed_date", None),
	("_assign", "Przypisano do"),
)

# Allowlisty sortowania i filtrow listy leadow (ops#94), ten sam ksztalt i te
# same konsumenty jak SORT_FIELDS_DEAL / FILTER_FIELDS_DEAL wyzej:
# `CRMLead.volteo_sort_fields()` / `volteo_filter_fields()`
# (`crm/fcrm/doctype/crm_lead/crm_lead.py`), `crm.api.doc.sort_options` /
# `get_filterable_fields`, oraz skrypt ops `crm-lista-leadow.py`. Kolejnosc
# krotek to kolejnosc prezentacji w UI, etykiety nadpisane tam, gdzie kolumna
# listy leadow (ops#94) uzywa innej nazwy niz standardowa etykieta pola.
# `email` jest CELOWO poza obiema listami: ops#94 przenosi liste leadow z
# modelu "email-first" (B2B) na "telefon-first" (B2C/D2D, patrz "Bez
# e-maila" w kolumnach), wiec filtr/sort po mailu nie jest oferowany tu tak
# samo jak nie jest kolumna.
SORT_FIELDS_LEAD: tuple[tuple[str, str | None], ...] = (
	("modified", "Ostatnia zmiana"),
	("creation", "Data utworzenia"),
	("status", "Status CC"),
	("lead_name", "Klient"),
	("lead_owner", "Przypisany handlowiec"),
	("custom_cc", "Przypisany CC"),
	("custom_kolejny_kontakt", "Kolejny kontakt"),
	("custom_termin_spotkania", "Termin spotkania"),
)

FILTER_FIELDS_LEAD: tuple[tuple[str, str | None], ...] = (
	("status", "Status CC"),
	("custom_status_handlowy", None),
	("custom_cc", "Przypisany CC"),
	("lead_owner", "Przypisany handlowiec"),
	("lead_name", "Klient"),
	("mobile_no", "Telefon"),
	("custom_zasady_dotacji", "Zasady"),
	("custom_posiadane_produkty", "Obecne produkty"),
	("custom_install_address", "Ulica"),
	("custom_nr_domu", "Nr domu"),
	("custom_install_postal_code", "Kod pocztowy"),
	("custom_install_city", "Miejscowość"),
	("custom_voivodeship", None),
	("custom_powiat", None),
	("custom_status_zrodla", "Status źródła"),
	("custom_import_source", "Źródło"),
	("custom_kolejny_kontakt", "Kolejny kontakt"),
	("custom_termin_spotkania", "Termin spotkania"),
	("modified", "Ostatnia zmiana"),
	("creation", "Data utworzenia"),
	("_assign", "Przypisano do"),
)


def niedozwolone_klucze_filtrow(
	filters: Mapping[str, object] | Sequence[object] | None,
	permitted: Iterable[str],
	doctype: str | None = None,
) -> list[object]:
	"""Zwraca listę kluczy pól z `filters`, których nie ma w zbiorze `permitted`.

	`filters` może być:
	  - `dict`: `{fieldname: wartość}` albo `{fieldname: [operator, wartość]}`.
	    Kluczem jest bezpośrednio nazwa pola;
	  - listą/krotką trójek `[fieldname, operator, wartość]` (rdzeń Frappe
	    dokłada tu domyślnie filtrowany `doctype`) albo list o 4 LUB WIĘCEJ
	    elementach, `[doctype, fieldname, operator, wartość, ...]`. Nazwa
	    pola to odpowiednio pierwszy albo DRUGI element. To dokładnie sposób,
	    w jaki rdzeń rozpoznaje kształt filtra (`frappe.utils.data.get_filter`,
	    zweryfikowane w kontenerze): `len(f) == 3` dokleja doctype z przodu,
	    `len(f) > 4` OBCINA do pierwszych 4 elementów, `len(f) == 4` bierze
	    wprost. W obu ostatnich przypadkach nazwa pola to zawsze `f[1]`.
	    Desk (`/app`) wysyła filtry list-view jako piątki
	    `[doctype, fieldname, operator, wartość, hidden]`. To właśnie ten
	    piąty element ("hidden", bool) sprawiał, że starsza wersja tej
	    funkcji (sprawdzająca tylko długości 3 i 4) traktowała całą piątkę
	    jako nieznany kształt i odrzucała KAŻDY filtr Desk, w tym zwykłe
	    `["CRM Lead", "converted", "=", 0, False]` na polu bez permlevel;
	  - listą zagnieżdżonych `dict`-ów (rzadziej spotykane, ale obsługiwane
	    tak samo jak `dict` główny).

	Klucz nie będący `str`, klucz zawierający kropkę (dostęp przez join do
	powiązanego doctype'u, np. `"user.email"`) albo wpis o nieoczekiwanym
	kształcie (nie 3 ani 4-lub-więcej elementów, np. 0/1/2, rdzeń sam by to
	odrzucił jako niepoprawny filtr) jest zawsze traktowany jako niedozwolony,
	niezależnie od `permitted`. Nie da się bezpiecznie wywnioskować, że nie
	omija to ograniczenia permlevel.

	`doctype` (opcjonalnie, domyślnie `None`): nazwa filtrowanego doctype'u,
	używana WYŁĄCZNIE do rozpoznania wpisów 4-lub-więcej-elementowych, które
	wskazują INNY doctype niż `doctype` w elemencie [0], czyli filtr po polu
	dołączonym przez JOIN (np. tabela podrzędna) w widoku Report. Rdzeniowe
	`DatabaseQuery.append_table` sprawdza wtedy tylko podstawowe uprawnienie
	"read" do TEGO doctype'u jako całości, NIE permlevel konkretnego pola w
	nim, a ten moduł jest celowo frappe-free (patrz docstring modułu) i nie
	zna allowlisty pól tego drugiego doctype'u, więc nie da się bezpiecznie
	sprawdzić takiego wpisu wprost. Dlatego KAŻDY wpis, którego element [0]
	różni się od `doctype`, jest zawsze traktowany jako niedozwolony,
	niezależnie od tego, czy nazwa pola akurat pasuje do `permitted`. To
	świadomie bardziej restrykcyjne niż "sprawdź względem allowlisty
	wskazanego doctype'u" (druga opcja z brief ops#124): żadna znana ścieżka
	wywołania (SPA forka używa wyłącznie dict-ów i trójek, patrz docstring
	modułu i `crm/api/volteo_filtry_guard.py`) nigdy nie wysyła takich
	wpisów, więc to zawężenie niczego nie blokuje w praktyce. Blokuje
	wyłącznie hipotetyczny filtr Report View z JOIN-em po innym doctype,
	którego ten strażnik i tak nie potrafi bezpiecznie zweryfikować. Fail
	open na takim wpisie byłby luką: nazwa pola mogłaby przypadkiem pasować
	do `permitted` głównego doctype'u, a w rzeczywistości odnosić się do
	wrażliwego pola innego doctype'u o tej samej nazwie. Gdy `doctype` nie
	jest podany (domyślnie `None`, zachowanie sprzed ops#124), porównanie
	jest pomijane, sprawdzane jest wyłącznie pole, tak jak dotychczas.

	Nie mutuje żadnego z argumentów. Zwraca listę (nie zbiór) zachowującą
	kolejność pierwszego wystąpienia, bez duplikatów.
	"""
	if not filters:
		return []

	permitted_set = set(permitted)
	# Para (klucz, wymus_niedozwolony). `wymus_niedozwolony=True` omija
	# sprawdzenie wzgledem `permitted_set` i zawsze laduje w wyniku (patrz
	# akapit o `doctype` w docstringu wyzej).
	surowe_wpisy: list[tuple[object, bool]] = []

	if isinstance(filters, Mapping):
		surowe_wpisy.extend((klucz, False) for klucz in filters.keys())
	else:
		for wpis in filters:
			if isinstance(wpis, Mapping):
				surowe_wpisy.extend((klucz, False) for klucz in wpis.keys())
			elif isinstance(wpis, (list, tuple)) and len(wpis) == 3:
				surowe_wpisy.append((wpis[0], False))
			elif isinstance(wpis, (list, tuple)) and len(wpis) >= 4:
				# [doctype, fieldname, operator, wartosc, ...]. Nazwa pola to
				# zawsze f[1], niezaleznie od tego, ile elementow jest ZA
				# wartoscia (Desk dokleja piaty element "hidden"; rdzen i tak
				# obcina wszystko od piatego wzwyz, patrz get_filter powyzej).
				doctype_wpisu = wpis[0]
				wymus_niedozwolony = doctype is not None and doctype_wpisu != doctype
				surowe_wpisy.append((wpis[1], wymus_niedozwolony))
			else:
				# Ksztalt nieznany (0/1/2 elementy). Nie da sie bezpiecznie
				# wydobyc nazwy pola, traktujemy caly wpis jako niedozwolony
				# (domyslnie bezpiecznie).
				surowe_wpisy.append((wpis, False))

	niedozwolone: list[object] = []
	for klucz, wymus_niedozwolony in surowe_wpisy:
		if klucz in niedozwolone:
			continue
		if (
			wymus_niedozwolony
			or not isinstance(klucz, str)
			or "." in klucz
			or klucz not in permitted_set
		):
			niedozwolone.append(klucz)

	return niedozwolone


def podstaw_dzis(
	filters: Mapping[str, object],
	dzis: str,
	jutro: str,
	czy_datetime: Callable[[str], bool],
) -> dict:
	"""Podstawia literal ``"@dzis"`` w wartościach ``filters`` za dzisiejszą
	datę (``dzis``, format ``YYYY-MM-DD`` jak ``frappe.utils.nowdate()``, w
	strefie site). Analogiczne do ``crm.api.doc._podstaw_me`` dla ``"@me"``
	(issue #128, decyzja właściciela 2026-09-10, opcja B). Ten moduł jest
	frappe-free (patrz docstring modułu), więc ``crm.api.doc._podstaw_dzis``
	wylicza ``dzis``/``jutro`` (``frappe.utils.nowdate()`` /
	``add_days(nowdate(), 1)``) i funkcję sprawdzającą typ pola
	(``frappe.get_meta(doctype)``) i przekazuje je tutaj jako argumenty --
	ten moduł sam nie wie nic o meta doctype'u ani o dacie.

	Obsługiwane kształty wartości filtra (te same, które rozumie
	``frappe.utils.make_filter_tuple``):
	  - skalar ``"@dzis"`` -> ``dzis``;
	  - ``[operator, "@dzis"]`` -> ``[operator, dzis]``, chyba że ``operator``
	    to ``"<="`` na polu Datetime (patrz niżej);
	  - ``["between", [od, do]]`` -> każdy element wewnętrznej listy równy
	    ``"@dzis"`` zamieniany osobno (jeden, drugi albo oba);
	  - ``["in"/"not in", [...]]`` -> każdy element listy równy ``"@dzis"``
	    zamieniany.
	Wartości bez literału ``"@dzis"`` w żadnej z powyższych pozycji wracają
	bez zmian. Zwracany jest zawsze NOWY dict (immutability, patrz
	coding-style.md) i nowe listy tam, gdzie cokolwiek faktycznie się
	zmieniło -- reszta wartości (i sam obiekt filters) nie jest mutowana.

	Datetime + operator ``"<="``: ``"<=" @dzis`` na polu Datetime objąłby
	TYLKO północ (00:00:00) dnia dzisiejszego -- rekord z godziną 10:00
	zostałby odcięty. Zamiast tego operator zamieniany jest na ``"<"`` z
	wartością ``jutro`` (podaną przez wołającego, format ``YYYY-MM-DD``,
	``add_days(nowdate(), 1)``), co obejmuje cały dzień dzisiejszy do
	23:59:59.999... Pozostałe operatory (``">="``, ``">"``, ``"<"``,
	składniki ``"between"``, ``"in"``) na polu Datetime zostają z
	``dzis``/``jutro`` bez zmiany operatora -- ``">="`` poprawnie obejmuje
	cały dzień od północy. Operator ``"="`` na polu Datetime dopasuje
	praktycznie WYŁĄCZNIE rekord z czasem dokładnie ``00:00:00`` -- to znana,
	zaakceptowana niedoskonałość (patrz brief issue #128), celowo nie
	naprawiana tutaj.

	``czy_datetime(fieldname)`` decyduje, czy dane pole jest typu Datetime;
	wołający odpowiada za poprawność tej funkcji (w ``crm.api.doc`` to
	``frappe.get_meta(doctype).get_field(fieldname)``, z osobnym bezpiecznikiem
	dla pól standardowych bez własnego DocField, np. ``modified``/``creation``,
	które SĄ Datetime w rdzeniu mimo braku wpisu w ``meta.fields``)."""
	wynik: dict = {}
	for pole, wartosc in filters.items():
		wynik[pole] = _podstaw_wartosc_dzis(pole, wartosc, dzis, jutro, czy_datetime)
	return wynik


def _podstaw_wartosc_dzis(
	pole: str,
	wartosc: object,
	dzis: str,
	jutro: str,
	czy_datetime: Callable[[str], bool],
) -> object:
	"""Podstawianie dla JEDNEJ wartości filtra -- wydzielone z `podstaw_dzis`
	żeby ta funkcja została czytelną pętlą po `filters.items()`. Patrz
	docstring `podstaw_dzis` dla pełnego opisu obsługiwanych kształtów."""
	if wartosc == "@dzis":
		return dzis
	if not isinstance(wartosc, list) or len(wartosc) != 2:
		return wartosc

	operator, argument = wartosc
	operator_l = operator.lower() if isinstance(operator, str) else operator

	if operator_l in ("between", "in", "not in") and isinstance(argument, list):
		if "@dzis" not in argument:
			return wartosc
		nowy_argument = [dzis if element == "@dzis" else element for element in argument]
		return [operator, nowy_argument]

	if argument != "@dzis":
		return wartosc

	if operator_l == "<=" and czy_datetime(pole):
		return ["<", jutro]

	return [operator, dzis]
