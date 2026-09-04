# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Dobór użytkowników podpowiadanych po `@` (wzmianki w Trify i komentarzach szansy).

Moduł celowo nie importuje ``frappe`` — to jedyny sposób, żeby dało się go
przetestować lokalnie (na tej maszynie ``frappe`` nie jest instalowalne, więc
reszta backendu ma wyłącznie bramkę składniową, patrz `crm/volteo_naming.py`
po ten sam wzorzec). Cała logika zależna od frameworka (kim jest wołający,
jakie ma role, kto jest w jego poddrzewie Sales Hierarchy) mieszka w
`crm.api.volteo_uzytkownicy.uzytkownicy_do_wzmianek`.

Reguła właściciela (decyzja 2026-09-04)
------------------------------------------
Lista podpowiadana po `@` ma pokazywać WYŁĄCZNIE:

- zarząd (rola `Volteo Core Admin`),
- backoffice (rola `Volteo Backend`),
- podwładnych wołającego w drzewie `CRM Sales Hierarchy` — jego własne
  poddrzewo, NIE przełożonych, NIE inne poddrzewa.

Wołający z `BYPASS_ROLES` (System Manager / Volteo Core Admin / Volteo
Backend) oraz `Administrator` widzą WSZYSTKICH użytkowników CRM — to jest
`bypass=True` poniżej, rozstrzygane przez wołający kod (moduł ten nie zna
ról ani sesji, więc nie może sam tego ustalić).

Niezależnie od trybu, wynik zawsze: tylko `enabled=1` (filtrowane przez
wołający kod przed/po wywołaniu tej funkcji), nigdy sam wołający, nigdy
`Administrator`, nigdy `Guest`.
"""

from collections.abc import Iterable

WYKLUCZENI_ZAWSZE: tuple[str, str] = ("Administrator", "Guest")
"""Konta, które nigdy nie trafiają do listy wzmiankowalnych, niezależnie od trybu."""


def wybierz_wzmiankowalnych(
	wolajacy: str,
	role_wolajacego: set[str],
	bypass: bool,
	zarzad: Iterable[str],
	backoffice: Iterable[str],
	poddrzewo: Iterable[str] | None,
	wszyscy_crm: Iterable[str],
) -> list[str]:
	"""Zwraca posortowaną, odfiltrowaną listę nazw (adresów e-mail) użytkowników do podpowiedzi `@`.

	Reguła właściciela (patrz docstring modułu): gdy `bypass` jest prawdziwe,
	wynikiem jest cały zbiór `wszyscy_crm` (wołający widzi wszystkich
	użytkowników CRM — zarząd, backoffice i podwładnych i tak są tego
	podzbiorem, więc nie trzeba ich osobno sumować). W przeciwnym razie wynik
	to suma zbiorów `zarzad + backoffice + (poddrzewo or ())` — dla wołającego spoza
	drzewa hierarchii (np. handlowiec bez podwładnych) `poddrzewo` jest
	`None`, więc lista zawęża się do samego zarządu i backoffice'u.

	`role_wolajacego` jest przyjmowane, ale w bieżącej regule nie różnicuje
	wyniku poza samym `bypass` — parametr zostaje w sygnaturze, żeby wołający
	kod mógł w przyszłości rozszerzyć regułę (np. inny zestaw dla ról
	pośrednich) bez zmiany kształtu funkcji.

	Zawsze, w obu trybach: usuwa `wolajacy` z wyniku, usuwa `Administrator` i
	`Guest` (`WYKLUCZENI_ZAWSZE`), deduplikuje i sortuje alfabetycznie.
	"""
	if bypass:
		kandydaci = set(wszyscy_crm)
	else:
		kandydaci = set(zarzad) | set(backoffice) | set(poddrzewo or ())

	kandydaci.discard(wolajacy)
	for wykluczony in WYKLUCZENI_ZAWSZE:
		kandydaci.discard(wykluczony)

	return sorted(kandydaci)
