# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Odebranie dostepu poprzedniemu wlascicielowi leada/szansy (b82)
================================================================

Zgloszenie backoffice (2026-11-03): po zmianie `CRM Lead.lead_owner` z
handlowca A na handlowca B handlowiec A nadal widzi leada (lista, mapa,
strona leada).

Przyczyna: `crm.permissions.org_hierarchy._permission_query_conditions`
wpuszcza uzytkownika do rekordu takze wtedy, gdy ma na nim `ToDo` o statusie
innym niz `Cancelled` (galaz `q2`, takze `Closed`). `CRMLead.assign_agent`
przy zmianie wlasciciela DODAJE `ToDo` dla B, ale nigdy nie anuluje `ToDo`
dla A, wiec A dalej przechodzi przez `q2`. `DocShare` A jest co prawda
zdejmowany przez `share_with_agent`, ale tylko gdy nowy wlasciciel jest
niepusty (przy wyczyszczeniu `lead_owner` share A tez zostaje).

Ten modul trzyma sama decyzje "ktore wiersze ToDo/DocShare odebrac", bez
`import frappe` (wzorzec repo `crm/volteo_*.py` + `crm/test_volteo_*.py`).
Cienkie adaptery: `CRMLead.on_update` / `CRMDeal.on_update` (biezace zmiany)
oraz skrypt czyszczacy z opisu PR (dane historyczne).

Zasady:
  - odbieramy WYLACZNIE wiersze poprzedniego wlasciciela (A); wiersze B,
    CC (`custom_cc`) i kogokolwiek innego zostaja nietkniete,
  - nic nie robimy, gdy A jest pusty, gdy A == B albo gdy A jest na liscie
    chronionych (nowy wlasciciel, `custom_cc`),
  - `ToDo` A dostaje status `Cancelled` (nie `Closed`: `Closed` nadal
    wpuszcza przez `q2`),
  - niezalezne powody widocznosci A (menedzer nad B w `CRM Sales Hierarchy`,
    rola z `BYPASS_ROLES`, `custom_cc`) nie zaleza od ToDo/DocShare, liczy je
    zapytanie uprawnien, wiec odebranie wierszy ich nie narusza.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

STATUS_ANULOWANE = "Cancelled"
STATUS_ZAMKNIETE = "Closed"


def _wartosc(wiersz: Mapping | object, klucz: str):
	if isinstance(wiersz, Mapping):
		return wiersz.get(klucz)
	return getattr(wiersz, klucz, None)


def _norm(user: str | None) -> str:
	return (user or "").strip()


def plan_odebrania_dostepu(
	stary_wlasciciel: str | None,
	nowy_wlasciciel: str | None,
	todos: Iterable[Mapping | object],
	udostepnienia: Iterable[Mapping | object],
	chronieni: Iterable[str | None] = (),
) -> dict[str, list[str]]:
	"""Zwraca `{"todo": [...], "udostepnienia": [...]}`: nazwy wierszy `ToDo`
	do anulowania i `DocShare` do usuniecia, zeby poprzedni wlasciciel stracil
	dostep po zmianie wlasciciela.

	`todos`: wiersze z `name`, `allocated_to`, `status` (wszystkie ToDo
	rekordu). `udostepnienia`: wiersze z `name`, `user` (wszystkie DocShare
	rekordu). `chronieni`: uzytkownicy, ktorych wierszy nie wolno ruszyc
	(nowy wlasciciel jest chroniony zawsze, wolajacy doklada `custom_cc`).
	"""
	pusty = {"todo": [], "udostepnienia": []}
	stary = _norm(stary_wlasciciel)
	nowy = _norm(nowy_wlasciciel)
	if not stary or stary == nowy:
		return pusty

	chronieni_set = {_norm(u) for u in chronieni if _norm(u)}
	if nowy:
		chronieni_set.add(nowy)
	if stary in chronieni_set:
		return pusty

	todo = [
		_wartosc(t, "name")
		for t in todos
		if _norm(_wartosc(t, "allocated_to")) == stary and _wartosc(t, "status") != STATUS_ANULOWANE
	]
	udostepnienia_out = [_wartosc(s, "name") for s in udostepnienia if _norm(_wartosc(s, "user")) == stary]
	return {"todo": [n for n in todo if n], "udostepnienia": [n for n in udostepnienia_out if n]}


def przypisani_po_zmianie(todos: Iterable[Mapping | object], anulowane: Iterable[str]) -> list[str]:
	"""Wartosc `_assign` po anulowaniu `anulowane`: lista `allocated_to` z
	ToDo, ktore nie sa `Cancelled`/`Closed` (ta sama regula co
	`frappe.desk.doctype.todo.todo.ToDo.update_in_reference`), bez duplikatow,
	w kolejnosci pierwszego wystapienia."""
	anulowane_set = set(anulowane)
	wynik: list[str] = []
	for t in todos:
		if _wartosc(t, "name") in anulowane_set:
			continue
		if _wartosc(t, "status") in (STATUS_ANULOWANE, STATUS_ZAMKNIETE):
			continue
		user = _norm(_wartosc(t, "allocated_to"))
		if user and user not in wynik:
			wynik.append(user)
	return wynik


def nieaktualni_uzytkownicy(
	wlasciciel: str | None,
	uzytkownicy: Iterable[str | None],
	chronieni: Iterable[str | None],
	handlowcy: Iterable[str],
) -> list[str]:
	"""Dla danych historycznych (skrypt czyszczacy): ktorzy uzytkownicy z
	ToDo/DocShare rekordu maja tam nieaktualny wiersz.

	Nieaktualny = handlowiec (`handlowcy`: konta z rola `Volteo D2D Sales`
	bez zadnej roli z `BYPASS_ROLES` i bez roli CC, liczone przez wolajacego),
	ktory NIE jest biezacym wlascicielem i nie jest na liscie `chronieni`
	(`custom_cc`). Konta backoffice/admin/CC nigdy nie sa zwracane.
	Kolejnosc: pierwsze wystapienie, bez duplikatow."""
	wl = _norm(wlasciciel)
	chronieni_set = {_norm(u) for u in chronieni if _norm(u)}
	handlowcy_set = {_norm(u) for u in handlowcy if _norm(u)}
	wynik: list[str] = []
	for u in uzytkownicy:
		user = _norm(u)
		if not user or user == wl or user in chronieni_set or user not in handlowcy_set:
			continue
		if user not in wynik:
			wynik.append(user)
	return wynik
