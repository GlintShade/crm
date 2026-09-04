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

from collections.abc import Iterable, Mapping, Sequence


def niedozwolone_klucze_filtrow(
	filters: Mapping[str, object] | Sequence[object] | None,
	permitted: Iterable[str],
) -> list[object]:
	"""Zwraca listę kluczy pól z `filters`, których nie ma w zbiorze `permitted`.

	`filters` może być:
	  - `dict`: `{fieldname: wartość}` albo `{fieldname: [operator, wartość]}` —
	    kluczem jest bezpośrednio nazwa pola;
	  - listą/krotką trójek `[fieldname, operator, wartość]` albo czwórek
	    `[doctype, fieldname, operator, wartość]` (standardowy format filtrów
	    Frappe) — nazwa pola to odpowiednio pierwszy albo drugi element;
	  - listą zagnieżdżonych `dict`-ów (rzadziej spotykane, ale obsługiwane
	    tak samo jak `dict` główny).

	Klucz nie będący `str`, klucz zawierający kropkę (dostęp przez join do
	powiązanego doctype'u, np. `"user.email"`) albo wpis o nieoczekiwanym
	kształcie (nie 3 ani 4 elementy) jest zawsze traktowany jako niedozwolony,
	niezależnie od `permitted` — nie da się bezpiecznie wywnioskować, że nie
	omija to ograniczenia permlevel.

	Nie mutuje żadnego z argumentów. Zwraca listę (nie zbiór) zachowującą
	kolejność pierwszego wystąpienia, bez duplikatów.
	"""
	if not filters:
		return []

	permitted_set = set(permitted)
	surowe_klucze: list[object] = []

	if isinstance(filters, Mapping):
		surowe_klucze.extend(filters.keys())
	else:
		for wpis in filters:
			if isinstance(wpis, Mapping):
				surowe_klucze.extend(wpis.keys())
			elif isinstance(wpis, (list, tuple)) and len(wpis) == 4:
				surowe_klucze.append(wpis[1])
			elif isinstance(wpis, (list, tuple)) and len(wpis) == 3:
				surowe_klucze.append(wpis[0])
			else:
				# Kształt nieznany — nie da się bezpiecznie wydobyć nazwy pola,
				# traktujemy cały wpis jako niedozwolony (domyślnie bezpiecznie).
				surowe_klucze.append(wpis)

	niedozwolone: list[object] = []
	for klucz in surowe_klucze:
		if klucz in niedozwolone:
			continue
		if not isinstance(klucz, str) or "." in klucz or klucz not in permitted_set:
			niedozwolone.append(klucz)

	return niedozwolone
