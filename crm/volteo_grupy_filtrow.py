# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Grupy filtrów ORAZ / ALBO w oknie „Filtr" listy leadów (issue #129).

Kontrakt danych (trudno odwracalny, patrz issue): `filters` w
`crm.api.doc.get_data`, `crm.api.volteo_leady.mapa` i w
`CRM View Settings.filters` pozostaje zwykłym słownikiem. Grupy ALBO
siedzą pod zarezerwowanym kluczem `KLUCZ_GRUP` ("volteo_grupy"): lista
słowników, każdy słownik to JEDNA grupa warunków ORAZ, w dokładnie tym
samym formacie co zwykłe filtry (`{pole: wartość}` / `{pole: [operator,
wartość]}`). Semantyka: `(grupa1 ALBO grupa2 ALBO ...) ORAZ (pozostałe
klucze słownika)`. Pusta lista grup (albo brak klucza w ogóle) = brak
wpływu - stare widoki bez tego klucza działają bez zmian.

Przykład reguły Remigiusza (widok „Do obdzwonienia"):
    {
        "custom_cc": "@me",
        "volteo_grupy": [
            {"status": "Odłożony", "custom_kolejny_kontakt": ["<=", "@dzis"]},
            {"status": ["in", ["Nowy", "Próba kontaktu"]]},
        ],
    }

Ten moduł WYŁĄCZNIE waliduje kształt i wydziela grupy z reszty filtrów -
frappe-free (żadnego importu `frappe`, ten sam powód co
`crm.volteo_lista_szans`/`crm.volteo_leady_import`: to jedyny sposób, żeby
dało się go przetestować lokalnie bez frameworka, patrz
`crm/test_volteo_grupy_filtrow.py`). Samo ROZWIJANIE grup na zapytania do
bazy (permission query conditions, unia nazw, bezpiecznik rozmiaru unii)
robi wywołujący, `crm.api.doc.rozwin_grupy`, bo to wymaga `frappe.get_list`.
"""

from collections.abc import Mapping, Sequence

# Zarezerwowany klucz kontenera grup. Nigdy nie trafia do `frappe.get_list`
# ani do endpointów rdzenia (`crm.api.volteo_filtry_guard`) - `rozwin_grupy`
# w `crm.api.doc` zawsze go wycina PRZED wywołaniem `_sprawdz_filtry`/
# `frappe.get_list`; gdyby jednak dotarł tam inną ścieżką (wołający
# zapomniał wywołać `rozwin_grupy`), istniejący strażnik
# (`niedozwolone_klucze_filtrow`, `crm.volteo_lista_szans`) odrzuca go jak
# każde inne nieznane pole - fail closed bez żadnej zmiany w tamtym module.
KLUCZ_GRUP = "volteo_grupy"

# Limity walidowane przez `waliduj_grupy` - patrz issue #129 ("limity 5
# grup x 10 warunków"). Czysto UX/bezpieczeństwo (chroni przed zapytaniem
# `name in [...]` o nieograniczonym koszcie w `rozwin_grupy`); to samo
# ograniczenie jest luźno powtórzone we froncie (`grupyFiltrow.js`) jako
# podpowiedź UI, ale TEN moduł jest jedynym autorytatywnym źródłem -
# backend waliduje niezależnie od tego, co wysłał frontend.
MAX_GRUP = 5
MAX_WARUNKOW_W_GRUPIE = 10


def wydziel_grupy(filters: Mapping[str, object] | None) -> tuple[dict, list]:
	"""Zwraca `(filtry_bez_grup, grupy)`.

	`filtry_bez_grup` to NOWY dict (immutability, coding-style.md - ani
	`filters`, ani zagnieżdżone wartości nie są mutowane) identyczny z
	`filters`, ale bez klucza `KLUCZ_GRUP`. `grupy` to wartość spod tego
	klucza (oczekiwana: lista słowników) ALBO pusta lista `[]`, jeśli
	klucz nie występuje w ogóle, `filters` jest puste/`None`, albo nie
	jest mapowaniem - w każdym z tych przypadków funkcja NIE rzuca
	wyjątku, po prostu traktuje wejście jako "brak grup". Kształt `grupy`
	NIE jest tu jeszcze walidowany - patrz `waliduj_grupy` osobno,
	wołane przez wywołującego PRZED użyciem wyniku tej funkcji do budowy
	zapytań (`crm.api.doc.rozwin_grupy` woła obie w tej kolejności)."""
	if not filters or not isinstance(filters, Mapping):
		return {}, []

	filtry_bez_grup = {klucz: wartosc for klucz, wartosc in filters.items() if klucz != KLUCZ_GRUP}
	grupy = filters.get(KLUCZ_GRUP, [])
	if grupy is None:
		grupy = []
	return filtry_bez_grup, grupy


def waliduj_grupy(grupy: object) -> None:
	"""Rzuca `ValueError` (komunikat po polsku, gotowy do przekazania
	wprost do `frappe.throw`) jeśli `grupy` ma niepoprawny kształt. Nic nie
	zwraca przy sukcesie (styl wyjątków, nie wyniku bool) - wywołujący
	łapie `ValueError` i mapuje je na `frappe.throw(str(e))`, co domyślnie
	daje `frappe.ValidationError` (konwencja modułu, patrz `_sprawdz_filtry`
	w `crm.api.doc` dla analogicznego `frappe.PermissionError` obok).

	Sprawdzane kształty, w kolejności:
	  - `grupy` musi być listą (albo `None`/pustą - wtedy walidacja jest
	    no-opem, "brak grup" jest zawsze poprawne);
	  - co najwyżej `MAX_GRUP` elementów;
	  - każdy element musi być słownikiem (pojedyncza grupa warunków ORAZ);
	  - żadna grupa nie może sama zawierać `KLUCZ_GRUP` (zakaz
	    zagnieżdżenia - grupy grup nie są częścią kontraktu issue #129);
	  - co najwyżej `MAX_WARUNKOW_W_GRUPIE` warunków w KAŻDEJ grupie z osobna."""
	if not grupy:
		return
	if not isinstance(grupy, list):
		raise ValueError("Grupy filtrów ({0}) muszą być listą.".format(KLUCZ_GRUP))
	if len(grupy) > MAX_GRUP:
		raise ValueError("Za dużo grup filtrów (maksymalnie {0}).".format(MAX_GRUP))
	for grupa in grupy:
		if not isinstance(grupa, Mapping):
			raise ValueError("Każda grupa filtrów musi być słownikiem warunków.")
		if KLUCZ_GRUP in grupa:
			raise ValueError("Grupy filtrów nie mogą być zagnieżdżone.")
		if len(grupa) > MAX_WARUNKOW_W_GRUPIE:
			raise ValueError(
				"Za dużo warunków w jednej grupie filtrów (maksymalnie {0}).".format(
					MAX_WARUNKOW_W_GRUPIE
				)
			)


def klucze_z_grup(grupy: Sequence[object] | None) -> list:
	"""Zwraca listę nazw pól użytych we WSZYSTKICH grupach łącznie, bez
	duplikatów, z zachowaniem kolejności pierwszego wystąpienia - do
	użytku przez strażnika permlevel (`_sprawdz_filtry` w `crm.api.doc`)
	jako szybki, łączny pre-check WSZYSTKICH grup naraz, przed
	wykonaniem jakiegokolwiek zapytania do bazy dla pojedynczej grupy
	(fail fast: jedno niedozwolone pole w PÓŹNIEJSZEJ grupie nie zostawia
	po sobie efektów ubocznych zapytań do WCZEŚNIEJSZYCH grup).

	Elementy niebędące mapowaniem są po cichu pomijane (obronnie - zakłada
	się, że `grupy` przeszło już `waliduj_grupy`, które i tak by je
	odrzuciło, więc to tylko dodatkowe zabezpieczenie tej funkcji samej w
	sobie na wypadek wywołania bez wcześniejszej walidacji)."""
	wynik: list = []
	for grupa in grupy or []:
		if not isinstance(grupa, Mapping):
			continue
		for klucz in grupa.keys():
			if klucz not in wynik:
				wynik.append(klucz)
	return wynik
