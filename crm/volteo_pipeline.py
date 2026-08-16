# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Definicje rurociągów statusów `CRM Deal` dla poszczególnych linii produktowych.

Moduł celowo nie importuje ``frappe`` — to jedyny sposób, żeby dało się go
przetestować lokalnie (na tej maszynie ``frappe`` nie jest instalowalne, więc
reszta backendu ma wyłącznie bramkę składniową). Cała logika zależna od
frameworka (odczyt/zapis statusu na dokumencie, wywołania z Server Scriptów
czy hooków) mieszka w ``crm.api.pipeline``.

KOLEJNOŚĆ etapów rurociągu żyje WYŁĄCZNIE tutaj, nigdy w `CRM Deal
Status.position` — to pole steruje jedynie kolejnością wyświetlania w
rozwijanej liście i nie ma pojęcia o tym, że „Finansowanie” to JEDEN wiersz
statusu, który w dwóch różnych rurociągach zajmuje dwa różne miejsca (indeks
4 w OZE, indeks 5 w CP). Licząc „do przodu” po `position` dla takiego
statusu, nie da się w ogóle odpowiedzieć na pytanie „do przodu względem
czego” — trzeba znać rurociąg danej sprawy. „Weryfikacja Backoffice” jest od
teraz statusem WYŁĄCZNIE OZE — CP go nie ma (usunięty razem z „Ofertą
Docelową”, zastąpioną przez „Ofertę Wstępną” i „Ofertę Właściwą”).

Oba rurociągi będą rosnąć: kroki od szóstego (OZE) i od siódmego (CP) są
celowo niezdefiniowane. Dodanie kolejnego kroku w przyszłości to zmiana w
odpowiedniej krotce (`PIPELINE_OZE`/`PIPELINE_CP`) plus założenie wiersza
statusu skryptem ops — nic więcej.

Poza rurociągiem żyją statusy TERMINALNE (`TERMINALE`) — wybieralne w
rozwijanej liście sprawy, ale renderowane jako stan pasma odznaki
(wygrana/przegrana), nigdy jako ponumerowany krok. CP celowo nie ma jeszcze
statusu wygranej. Rozwijana lista w formularzu sprawy pokazuje dokładnie
`grupa_for(rodzaj)`: rurociąg plus statusy terminalne, w tej kolejności.
"""

OZE_RODZAJE: frozenset[str] = frozenset({"Fotowoltaika", "Fotowoltaika + Magazyn", "Magazyn energii"})
"""Wartości pola `custom_rodzaj_umowy`, które mapują się na rurociąg OZE."""

PIPELINE_OZE: tuple[str, ...] = (
	"Lead",
	"Umowa Wygenerowana",
	"Umowa Podpisana",
	"Weryfikacja Backoffice",
	"Finansowanie",
)
"""Rurociąg statusów dla linii OZE (fotowoltaika + magazyny energii), w kolejności przejścia."""

PIPELINE_CP: tuple[str, ...] = (
	"Lead",
	"Oferta Wstępna",
	"Dokumentacja",
	"Audyt Energetyczny",
	"Oferta Właściwa",
	"Finansowanie",
)
"""Rurociąg statusów dla linii Czyste Powietrze, w kolejności przejścia."""

TERMINALE: dict[str, tuple[str, ...]] = {
	"OZE": ("Wygrana – montaż", "Przegrana"),
	"CP": ("Przegrana",),
}
"""Statusy terminalne per rurociąg — wybieralne w rozwijanej liście sprawy, renderowane jako
stan pasma odznaki (wygrana/przegrana), nigdy jako ponumerowany krok; CP celowo nie ma jeszcze
statusu wygranej."""

NOTATKI: dict[str, dict[str, str]] = {
	"OZE": {"Umowa Podpisana": "Uzupełnij audyt i wyślij do weryfikacji."},
	"CP": {"Dokumentacja": "Umowa na obsługę dotacji, GOPS, pełnomocnictwo"},
}
"""Notatka „co dalej” per rurociąg i status bieżący; brak wpisu oznacza brak notatki."""


def pipeline_key_for(rodzaj: str | None) -> str | None:
	"""Zwraca klucz rurociągu ("OZE"/"CP") dla rodzaju umowy, albo None gdy nieznany/pusty/brak."""
	if not rodzaj:
		return None
	if rodzaj in OZE_RODZAJE:
		return "OZE"
	if rodzaj == "Czyste Powietrze":
		return "CP"
	return None


def pipeline_for(rodzaj: str | None) -> tuple[str, ...] | None:
	"""Zwraca krotkę statusów rurociągu dla rodzaju umowy, albo None gdy rodzaj nie ma rurociągu."""
	klucz = pipeline_key_for(rodzaj)
	if klucz == "OZE":
		return PIPELINE_OZE
	if klucz == "CP":
		return PIPELINE_CP
	return None


def grupa_for(rodzaj: str | None) -> tuple[str, ...] | None:
	"""Zwraca grupę statusów rozwijanej listy dla rodzaju umowy: rurociąg plus statusy terminalne,
	w tej kolejności (kolejność rozwijanej listy). Zwraca None, gdy rodzaj nie ma rurociągu.
	"""
	rurociag = pipeline_for(rodzaj)
	if rurociag is None:
		return None
	klucz = pipeline_key_for(rodzaj)
	terminale = TERMINALE.get(klucz, ())
	return rurociag + terminale


def step_index(rodzaj: str | None, status: str | None) -> int:
	"""Zwraca indeks statusu w rurociągu danego rodzaju umowy.

	Zwraca -1, gdy status jest poza rurociągiem, rodzaj nie ma rurociągu albo status jest None.
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


def notatka_for(rodzaj: str | None, status: str | None) -> str | None:
	"""Zwraca notatkę „co dalej” dla bieżącego statusu, albo None gdy brak zdefiniowanej notatki."""
	klucz = pipeline_key_for(rodzaj)
	if klucz is None or status is None:
		return None
	return NOTATKI.get(klucz, {}).get(status)


def is_forward(rodzaj: str | None, current: str | None, target: str) -> bool:
	"""Zwraca True tylko, gdy `current` i `target` są w rurociągu danego rodzaju i `current` poprzedza `target`.

	Status bieżący spoza rurociągu (np. "Przegrana", "Wygrana montaż") zawsze daje False —
	automatyzacja nigdy nie ma przesuwać takiej sprawy dalej. Brak rurociągu dla rodzaju daje False.
	"""
	rurociag = pipeline_for(rodzaj)
	if rurociag is None:
		return False
	indeks_biezacy = step_index(rodzaj, current)
	indeks_docelowy = step_index(rodzaj, target)
	if indeks_biezacy == -1 or indeks_docelowy == -1:
		return False
	return indeks_biezacy < indeks_docelowy
