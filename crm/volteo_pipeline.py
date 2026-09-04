# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Definicje procesów statusów `CRM Deal` dla poszczególnych linii produktowych.

Moduł celowo nie importuje ``frappe`` — to jedyny sposób, żeby dało się go
przetestować lokalnie (na tej maszynie ``frappe`` nie jest instalowalne, więc
reszta backendu ma wyłącznie bramkę składniową). Cała logika zależna od
frameworka (odczyt/zapis statusu na dokumencie, wywołania z Server Scriptów
czy hooków) mieszka w ``crm.api.pipeline``.

KOLEJNOŚĆ etapów procesu żyje WYŁĄCZNIE tutaj, nigdy w `CRM Deal
Status.position` — to pole steruje jedynie kolejnością wyświetlania w
rozwijanej liście i nie ma pojęcia o tym, że proces OZE i proces CP to
dwa niezależne zbiory kroków (historycznie „Finansowanie” było jednym
wierszem statusu współdzielonym przez oba procesy pod różnymi indeksami —
od b49 CP ma już własny krok „Finansowanie Trify” w jego miejsce, ale
zasada zostaje: nawet gdy status JEST fizycznie współdzielony, licząc „do
przodu” po `position`, nie da się odpowiedzieć na pytanie „do przodu
względem czego” — trzeba znać proces danej sprawy). „Weryfikacja
Backoffice” jest statusem WYŁĄCZNIE OZE — CP go nie ma.

Od b49 CP ma własny, 12-krokowy proces (`PIPELINE_CP`) — patrz katalog
podzadań `PODZADANIA_CP` niżej za mini-zadaniami per krok. Ostatni krok,
„Projekt rozliczony”, niesie `type=Won` na wierszu `CRM Deal Status` — CP ma
teraz status wygranej WEWNĄTRZ procesu, nie jako osobny terminal (inaczej
niż OZE, gdzie status wygranej z `TERMINALE["OZE"]` jest terminalem poza
procesem).

Poza procesem żyją statusy TERMINALNE (`TERMINALE`) — wybieralne w
rozwijanej liście sprawy, ale renderowane jako stan pasma odznaki
(wygrana/przegrana), nigdy jako ponumerowany krok. Rozwijana lista w
formularzu sprawy pokazuje dokładnie `grupa_for(rodzaj)`: proces plus
statusy terminalne, w tej kolejności.
"""

import json

OZE_RODZAJE: frozenset[str] = frozenset({"Fotowoltaika", "Fotowoltaika + Magazyn", "Magazyn energii"})
"""Wartości pola `custom_rodzaj_umowy`, które mapują się na proces OZE."""

PIPELINE_OZE: tuple[str, ...] = (
	"Lead",
	"Umowa Wygenerowana",
	"Umowa Podpisana",
	"Weryfikacja Backoffice",
	"Finansowanie",
)
"""Proces statusów dla linii OZE (fotowoltaika + magazyny energii), w kolejności przejścia."""

PIPELINE_CP: tuple[str, ...] = (
	"Lead",
	"Dokumentacja",
	"Audyt Energetyczny",
	"Umowa na realizację",
	"Wniosek o dotację",
	"Dyspozycja wypłaty zaliczki",
	"I transza",
	"Finansowanie Trify",
	"Realizacja",
	"Wniosek o płatność końcową",
	"2 transza",
	"Projekt rozliczony",
)
"""Proces statusów dla linii Czyste Powietrze, w kolejności przejścia. 12 kroków; ostatni,
„Projekt rozliczony”, niesie `type=Won` na wierszu `CRM Deal Status` — patrz docstring modułu."""

TERMINALE: dict[str, tuple[str, ...]] = {
	"OZE": ("Wygrana – montaż", "Przegrana"),
	"CP": ("Przegrana",),
}
"""Statusy terminalne per proces — wybieralne w rozwijanej liście sprawy, renderowane jako
stan pasma odznaki (wygrana/przegrana), nigdy jako ponumerowany krok; CP nie ma osobnego
terminala wygranej, bo „wygraność” niesie ostatni krok procesu („Projekt rozliczony”)."""

NOTATKI: dict[str, dict[str, str]] = {
	"OZE": {"Umowa Podpisana": "Uzupełnij audyt i wyślij do weryfikacji."},
	"CP": {"Dokumentacja": "Umowa na obsługę dotacji, GOPS, pełnomocnictwo"},
}
"""Notatka „co dalej” per proces i status bieżący; brak wpisu oznacza brak notatki."""


STANY_PODZADAN: tuple[str, ...] = ("waiting", "accepted", "error", "nd")
"""Stany podzadania, spójne z `frontend/src/utils/audytWeryfikacja.js`: waiting=niebieski
(oczekuje), accepted=zielony (zaakceptowano), error=czerwony (błąd), nd=nie dotyczy."""

PODZADANIA_CP: dict[str, tuple[dict, ...]] = {
	"Dokumentacja": (
		{
			"klucz": "dok:umowa_obsluga_dotacji",
			"label": "Umowa na obsługę dotacji",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "dok:gops_zaswiadczenie",
			"label": "Zaświadczenie o dochodach (GOPS/MOPS)",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "dok:pelnomocnictwo_notarialne",
			"label": "Pełnomocnictwo notarialne",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "dok:zgoda_wspolwlascicieli",
			"label": "Zgoda współwłaścicieli",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": True,
		},
		{
			"klucz": "dok:zgoda_wspolmalzonka",
			"label": "Zgoda współmałżonka",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": True,
		},
		{
			"klucz": "dok:ankieta_cp",
			"label": "Ankieta danych CP",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "dok:ankieta_trify",
			"label": "Ankieta Trify",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": True,
		},
		{
			"klucz": "dok:zdjecia",
			"label": "Zdjęcia",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "dok:poziom_dotacji",
			"label": "Poziom dotacji potwierdzony",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"Audyt Energetyczny": (
		{
			"klucz": "audyt:zlecony",
			"label": "Audyt zlecony (mail wysłany)",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "audyt:umowiony",
			"label": "Audyt umówiony",
			"typ": "odhaczenie",
			"z_data": True,
			"nd_dozwolone": False,
		},
		{
			"klucz": "audyt:zrealizowany",
			"label": "Audyt zrealizowany (plik audytowy)",
			"typ": "weryfikacja",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"Umowa na realizację": (
		{
			"klucz": "umowa:oferta_przygotowana",
			"label": "Oferta finalna przygotowana",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "umowa:oferta_przedstawiona",
			"label": "Oferta przedstawiona klientowi",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "umowa:oferta_zaakceptowana",
			"label": "Oferta zaakceptowana przez klienta",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "umowa:podpisana",
			"label": "Umowa podpisana",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"Wniosek o dotację": (
		{
			"klucz": "wniosek:termin_operator",
			"label": "Termin u operatora umówiony",
			"typ": "odhaczenie",
			"z_data": True,
			"nd_dozwolone": False,
		},
		{
			"klucz": "wniosek:zlozony",
			"label": "Wniosek złożony",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "wniosek:dotacja_przyznana",
			"label": "Dotacja przyznana",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"Dyspozycja wypłaty zaliczki": (
		{
			"klucz": "dyspozycja:przygotowana",
			"label": "Dyspozycja przygotowana",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "dyspozycja:termin_operator",
			"label": "Termin u operatora umówiony",
			"typ": "odhaczenie",
			"z_data": True,
			"nd_dozwolone": False,
		},
		{
			"klucz": "dyspozycja:zlozona",
			"label": "Dyspozycja złożona",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"I transza": (
		{
			"klucz": "transza1:wyplacona",
			"label": "Transza wypłacona",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "transza1:wklad_wlasny",
			"label": "Wkład własny klienta wpłacony",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"Finansowanie Trify": (
		{
			"klucz": "trify:umowa_podpisana",
			"label": "Umowa Trify podpisana",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": True,
		},
		{
			"klucz": "trify:wyplacone",
			"label": "Trify wypłacone",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": True,
		},
	),
	"Realizacja": (
		{
			"klucz": "realizacja:zrodlo_ciepla",
			"label": "Źródło ciepła + CO/CWU zrealizowane",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "realizacja:termomodernizacja",
			"label": "Termomodernizacja zrealizowana",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"Wniosek o płatność końcową": (
		{
			"klucz": "platnosc:termin_operator",
			"label": "Termin u operatora umówiony",
			"typ": "odhaczenie",
			"z_data": True,
			"nd_dozwolone": False,
		},
		{
			"klucz": "platnosc:wniosek_zlozony",
			"label": "Wniosek złożony",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
	),
	"2 transza": (
		{
			"klucz": "transza2:wyplacona",
			"label": "Transza wypłacona",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": False,
		},
		{
			"klucz": "transza2:trify_zamkniecie",
			"label": "Zamknięcie finansowania Trify",
			"typ": "odhaczenie",
			"z_data": False,
			"nd_dozwolone": True,
		},
	),
}
"""Katalog podzadań (mini zadań) CP, keyed nazwą statusu procesu (`PIPELINE_CP`). Klucze
podzadań mają wzorzec `<prefiks>:<zadanie>` — ten sam wzorzec (`pole:`/`foto:`) co audyt
techniczny w `frontend/src/utils/audytWeryfikacja.js`, stabilny pod przyszły sync z
`Volteo Audyt`. „Lead” i „Projekt rozliczony” celowo bez wpisu — brak podzadań na tych etapach."""


def pipeline_key_for(rodzaj: str | None) -> str | None:
	"""Zwraca klucz procesu ("OZE"/"CP") dla rodzaju umowy, albo None gdy nieznany/pusty/brak."""
	if not rodzaj:
		return None
	if rodzaj in OZE_RODZAJE:
		return "OZE"
	if rodzaj == "Czyste Powietrze":
		return "CP"
	return None


def pipeline_for(rodzaj: str | None) -> tuple[str, ...] | None:
	"""Zwraca krotkę statusów procesu dla rodzaju umowy, albo None gdy rodzaj nie ma procesu."""
	klucz = pipeline_key_for(rodzaj)
	if klucz == "OZE":
		return PIPELINE_OZE
	if klucz == "CP":
		return PIPELINE_CP
	return None


def grupa_for(rodzaj: str | None) -> tuple[str, ...] | None:
	"""Zwraca grupę statusów rozwijanej listy dla rodzaju umowy: proces plus statusy terminalne,
	w tej kolejności (kolejność rozwijanej listy). Zwraca None, gdy rodzaj nie ma procesu.
	"""
	rurociag = pipeline_for(rodzaj)
	if rurociag is None:
		return None
	klucz = pipeline_key_for(rodzaj)
	terminale = TERMINALE.get(klucz, ())
	return rurociag + terminale


def step_index(rodzaj: str | None, status: str | None) -> int:
	"""Zwraca indeks statusu w procesie danego rodzaju umowy.

	Zwraca -1, gdy status jest poza procesem, rodzaj nie ma procesu albo status jest None.
	"""
	if status is None:
		return -1
	rurociag = pipeline_for(rodzaj)
	if rurociag is None:
		return -1
	try:
		return rurociag.index(status)
	except ValueError:
		return -1


def etap_nr(rodzaj: str | None, status: str | None) -> int:
	"""Zwraca numer kroku procesu, do utrwalenia na dokumencie i sortowania listy
	szans po kolejności procesu (`frappe.get_list` sortuje tylko po zwykłych
	polach — sam proces nie da się wyrazić przez `order_by`).

	`0` oznacza brak procesu dla `rodzaj` (rodzaj pusty/nieznany) albo status
	spoza `grupa_for(rodzaj)` dla TEGO rodzaju (np. „Weryfikacja Backoffice”
	pod „Czyste Powietrze” — status istnieje, ale nie w procesie CP). Krok
	procesu to `step_index(...) + 1` (numeracja od 1, nie od 0, żeby 0 zostało
	wolne jako „brak”). Status terminalny (`TERMINALE`) dostaje numer zaraz za
	ostatnim krokiem procesu: `len(pipeline) + 1 + jego_indeks_w_TERMINALE`.

	Czyste Powietrze ma przesunięcie +100 (CP „Lead” = 101 … „Projekt
	rozliczony” = 112, „Przegrana” = 113) — bez tego przesunięcia
	nieprzefiltrowana lista (oba rodzaje razem) przeplatałaby kroki dwóch
	niezależnych, różnej długości procesów zamiast trzymać OZE przed CP.
	"""
	klucz = pipeline_key_for(rodzaj)
	if klucz is None or status is None:
		return 0
	rurociag = pipeline_for(rodzaj)
	offset = 100 if klucz == "CP" else 0
	indeks_procesu = step_index(rodzaj, status)
	if indeks_procesu != -1:
		return offset + indeks_procesu + 1
	terminale = TERMINALE.get(klucz, ())
	try:
		indeks_terminalny = terminale.index(status)
	except ValueError:
		return 0
	return offset + len(rurociag) + 1 + indeks_terminalny


def notatka_for(rodzaj: str | None, status: str | None) -> str | None:
	"""Zwraca notatkę „co dalej” dla bieżącego statusu, albo None gdy brak zdefiniowanej notatki."""
	klucz = pipeline_key_for(rodzaj)
	if klucz is None or status is None:
		return None
	return NOTATKI.get(klucz, {}).get(status)


def is_forward(rodzaj: str | None, current: str | None, target: str) -> bool:
	"""Zwraca True tylko, gdy `current` i `target` są w procesie danego rodzaju i `current` poprzedza `target`.

	Status bieżący spoza procesu (np. "Przegrana", "Wygrana montaż") zawsze daje False —
	automatyzacja nigdy nie ma przesuwać takiej sprawy dalej. Brak procesu dla rodzaju daje False.
	"""
	rurociag = pipeline_for(rodzaj)
	if rurociag is None:
		return False
	indeks_biezacy = step_index(rodzaj, current)
	indeks_docelowy = step_index(rodzaj, target)
	if indeks_biezacy == -1 or indeks_docelowy == -1:
		return False
	return indeks_biezacy < indeks_docelowy


def podzadania_for(rodzaj: str | None) -> dict[str, tuple[dict, ...]]:
	"""Zwraca katalog podzadań (`PODZADANIA_CP`) dla „Czyste Powietrze”, pusty dict dla
	pozostałych rodzajów — OZE (i każdy inny/nieznany/pusty rodzaj) na razie nie ma katalogu
	podzadań."""
	if rodzaj == "Czyste Powietrze":
		return PODZADANIA_CP
	return {}


def podzadanie_def(rodzaj: str | None, klucz: str) -> dict | None:
	"""Płaski lookup definicji podzadania po jego kluczu, niezależnie od etapu, do którego
	należy. Zwraca kopię definicji (bez ryzyka mutacji `PODZADANIA_CP` przez wołającego), albo
	None, gdy rodzaj nie ma takiego podzadania (w tym gdy nie ma katalogu podzadań w ogóle)."""
	for zadania in podzadania_for(rodzaj).values():
		for zadanie in zadania:
			if zadanie["klucz"] == klucz:
				return dict(zadanie)
	return None


def dozwolone_stany(zadanie: dict) -> frozenset[str]:
	"""Zwraca dozwolone stany dla definicji podzadania: `weryfikacja` → {waiting, accepted,
	error}, `odhaczenie` → {accepted}; plus `nd`, gdy definicja ma `nd_dozwolone=True`."""
	if zadanie.get("typ") == "weryfikacja":
		podstawa = frozenset({"waiting", "accepted", "error"})
	else:
		podstawa = frozenset({"accepted"})
	if zadanie.get("nd_dozwolone"):
		return podstawa | frozenset({"nd"})
	return podstawa


def _sparsowana_mapa(raw: object) -> dict:
	"""Defensywnie zamienia `raw` na płaski dict, tolerując None/pusty string/podwójnie
	zakodowany JSON — port `parsedMap` z `frontend/src/utils/audytWeryfikacja.js`."""
	if raw is None or raw == "":
		return {}
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
			if isinstance(raw, str):
				raw = json.loads(raw)
		except (json.JSONDecodeError, TypeError):
			return {}
	return raw if isinstance(raw, dict) else {}


def parsuj_podzadania(raw: object) -> dict[str, dict]:
	"""Parsuje i waliduje surową mapę stanu podzadań (np. odczytaną z pola JSON dokumentu).

	Defensywny parse jak `parseWeryfikacja` w `audytWeryfikacja.js`: toleruje None, pusty
	string i podwójnie zakodowany JSON (`_sparsowana_mapa`), odrzuca wpisy nie-dict i wpisy,
	których `stan` nie jest w `STANY_PODZADAN`. Zwraca NOWY dict — `raw` nigdy nie jest
	mutowane, ani wpisy w wyniku nie są tymi samymi obiektami co w źródle.
	"""
	source = _sparsowana_mapa(raw)
	wynik: dict[str, dict] = {}
	for klucz, wpis in source.items():
		if not isinstance(wpis, dict):
			continue
		if wpis.get("stan") not in STANY_PODZADAN:
			continue
		wynik[klucz] = dict(wpis)
	return wynik
