# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Logika umowy obsługi dotacji Czyste Powietrze (wariant wynagrodzenia, walidacja,
etykiety pól) — odpowiednik `crm/volteo_umowa.py`/`crm/volteo_kredyt.py` dla piątego
dokumentu (issue ops#212).

Moduł celowo nie importuje ``frappe`` — z tego samego powodu co `crm/volteo_umowa.py`:
``frappe`` nie jest instalowalne na tej maszynie, więc to jedyny sposób na lokalną,
silną bramkę testową (`crm/test_volteo_umowa_cp.py`). Cała logika zależna od
frameworka mieszka gdzie indziej — tu tylko czyste funkcje.

TAJEMNICA PROWIZJI (reguła nadrzędna projektu, zob. `CLAUDE.md` → „Preserve the
cost/commission secrecy model"): `Volteo CP Stale` niesie OBOK kwot netto/brutto
także `umowa1_prowizja`/`umowa2_prowizja` (prowizja handlowca) — żadna funkcja w
tym module nie czyta ani nie zwraca tych dwóch pól, pod żadną nazwą klucza.
`kwoty_wariantu_cp()` zwraca WYŁĄCZNIE (netto, brutto); `warianty_wynagrodzenia_cp()`
zwraca WYŁĄCZNIE `{"wariant", "netto", "brutto"}` na wpis. To sprawdza wprost
`crm/test_volteo_umowa_cp.py` (ustawia prowizję na jaskrawo odróżnialną wartość i
sprawdza jej nieobecność w `repr()` wyniku)."""

from decimal import Decimal
from typing import Any

from crm.volteo_umowa import _sparsuj_decimal as _sparsuj_decimal_wspolny
from crm.volteo_umowa import brakujace_dane_klienta as brakujace_dane_klienta

# Reużyty jeden parser z `crm/volteo_umowa.py` (string→Decimal, nigdy nie rzuca)
# — patrz tamtejszy docstring dla szczegółów. Nadany lokalny alias zamiast
# przenoszenia funkcji do wspólnego pliku, tak samo jak w `crm/volteo_umowa_pdf.py`.
_sparsuj_decimal = _sparsuj_decimal_wspolny

# `brakujace_dane_klienta` jest re-eksportowana bez zmian (patrz import wyżej z
# `as brakujace_dane_klienta`) — wołający ma używać `crm.volteo_umowa_cp.
# brakujace_dane_klienta` zamiast importować bezpośrednio z `crm.volteo_umowa`,
# żeby cała logika tego dokumentu (umowa CP) miała jedno miejsce importu.

WARIANTY_WYNAGRODZENIA: tuple[str, ...] = ("1", "2")
"""Dwa dopuszczalne warianty wynagrodzenia (§4 umowy) — kwoty netto/brutto dla
każdego czytane z `Volteo CP Stale` przez `kwoty_wariantu_cp()`. Rep wybiera
JEDEN z tych dwóch literałów, nic innego nie jest poprawną wartością."""

ETYKIETY_POL_CP: dict[str, str] = {
	"wynagrodzenie_wariant": "Wariant wynagrodzenia",
}
"""Kanon etykiet pól formularza umowy obsługi dotacji CP — na wzór `ETYKIETY_POL`
w `crm/volteo_kredyt.py` (ops#148: „ten sam field nigdy dwóch różnych etykiet w
doctype/backend/frontend/PDF"). Jedyne pole tego dokumentu, które nie jest
przepisywane wprost z `Contact`/`CRM Deal` (dane klienta) ani zgodą (Check), więc
jedyne, które potrzebuje własnej etykiety tutaj."""


def brakujace_pola_cp(dane: dict[str, Any]) -> list[str]:
	"""Zwraca etykiety brakujących pól SAMEGO dokumentu umowy CP (nie danych klienta
	— to osobna ścieżka, `brakujace_dane_klienta()`, re-eksportowana wyżej).

	Jedyne wymagane pole tego dokumentu jest `wynagrodzenie_wariant`: umowa jest
	niekompletna, dopóki rep nie wybrał jednego z `WARIANTY_WYNAGRODZENIA` ("1"
	albo "2"). Zgody (`zgoda_przetwarzanie_danych`/`zgoda_kontakt_telefoniczny`/
	`zgoda_dzialania_promocyjne`) są dobrowolne z natury (Załącznik nr 1 samego
	dokumentu to explicite mówi) — ich brak NIGDY nie czyni umowy niekompletną,
	stąd nie są tu sprawdzane."""
	wariant = dane.get("wynagrodzenie_wariant")
	if wariant not in WARIANTY_WYNAGRODZENIA:
		return [ETYKIETY_POL_CP["wynagrodzenie_wariant"]]
	return []


def kwoty_wariantu_cp(stale: dict[str, Any], wariant: str | None) -> tuple[Decimal | None, Decimal | None]:
	"""Zwraca (netto, brutto) wynagrodzenia dla `wariant` ("1" albo "2"), czytane
	z `stale` (kształt `frappe.db.get_singles_dict("Volteo CP Stale")": klucze
	`umowa1_netto`/`umowa1_brutto`/`umowa2_netto`/`umowa2_brutto`, wartości
	STRINGI albo nieobecne, nigdy nie ufamy typowi — patrz `_sparsuj_decimal`).

	`wariant` spoza `WARIANTY_WYNAGRODZENIA` (w tym `None`, pusty string,
	dowolny inny tekst) daje `(None, None)` — nigdy nie zgaduje domyślnego
	wariantu. Stała nieustawiona nigdy (`stale.get(klucz)` zwraca `None`, albo
	pusty string z `get_singles_dict` na kluczu, którego w ogóle nie było)
	daje `None` dla TEJ jednej połówki, druga połówka liczy się niezależnie —
	`_sparsuj_decimal(None)` i `_sparsuj_decimal("")` oba zwracają `None`,
	nigdy `Decimal("0")`, więc nieustawiona stała nigdy nie udaje zera.

	CELOWO nie czyta `umowa{wariant}_prowizja` — zob. docstring modułu,
	akapit „TAJEMNICA PROWIZJI"."""
	if wariant not in WARIANTY_WYNAGRODZENIA:
		return (None, None)
	netto = _sparsuj_decimal(stale.get(f"umowa{wariant}_netto"))
	brutto = _sparsuj_decimal(stale.get(f"umowa{wariant}_brutto"))
	return (netto, brutto)


def warianty_wynagrodzenia_cp(stale: dict[str, Any]) -> list[dict[str, str | None]]:
	"""Zwraca oba warianty wynagrodzenia w stałej kolejności ("1", potem "2"),
	do wyświetlenia w formularzu (rep wybiera jeden z dwóch), jako
	`[{"wariant": "1", "netto": "1600.00", "brutto": "1968.00"}, {"wariant": "2", ...}]`.

	Kwoty są stringami zaokrąglonymi do 2 miejsc (`str(Decimal.quantize(...))`),
	`None` gdy odpowiadająca stała nie jest ustawiona (nigdy `"0.00"` jako
	fałszywy placeholder — zob. `crm/volteo_umowa.py` i CLAUDE.md „Never use a
	Float/Currency 0.0 as an empty marker"). CELOWO nie zawiera żadnego klucza
	ani wartości pochodzącej z `umowa{n}_prowizja` — zob. docstring modułu,
	akapit „TAJEMNICA PROWIZJI"; sprawdzone wprost w teście (prowizja ustawiona
	na jaskrawo odróżnialną wartość, asercja jej nieobecności w `repr()`
	wyniku tej funkcji)."""
	wynik: list[dict[str, str | None]] = []
	for wariant in WARIANTY_WYNAGRODZENIA:
		netto, brutto = kwoty_wariantu_cp(stale, wariant)
		wynik.append(
			{
				"wariant": wariant,
				"netto": str(netto.quantize(Decimal("0.01"))) if netto is not None else None,
				"brutto": str(brutto.quantize(Decimal("0.01"))) if brutto is not None else None,
			}
		)
	return wynik
