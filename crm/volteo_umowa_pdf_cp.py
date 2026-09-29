# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Budowniczy kontekstu do renderowania PDF-u umowy obsługi dotacji Czyste Powietrze.

Odpowiednik `crm/volteo_umowa_pdf.py`/`crm/volteo_kredyt_pdf.py` dla piątego
dokumentu (issue ops#212). Moduł celowo nie importuje ``frappe`` — z tego samego
powodu co `crm/volteo_umowa_pdf.py`: ``frappe`` nie jest instalowalne na tej
maszynie, więc to jedyny sposób na lokalną, silną bramkę testową
(`crm/test_volteo_umowa_pdf_cp.py` — a w tym zadaniu, `crm/test_volteo_umowa_cp.py`,
patrz sekcja kontekstu tamtego pliku). Cała logika zależna od frameworka mieszka
gdzie indziej — tu tylko czysta funkcja `zbuduj_kontekst_cp`, która zamienia
surowe dane domenowe na gotowe do wydruku stringi i booleany. Szablon PDF nie
liczy ani nie formatuje niczego.

REGUŁA NADRZĘDNA (dokument prawny podpisywany przez klienta, jak w
`volteo_umowa_pdf.py`): brak danych zawsze renderuje się jako pusty string,
nigdy jako zmyślona wartość — ani `"0"`, ani `"0,00"`, ani `"None"`.

Reużywa (nie duplikuje) formatujące funkcje pomocnicze z `crm/volteo_umowa_pdf.py`
(`_stan_bool`, `_tekst`, `_polacz`, `_data_pl`, `_adres`, `_kwota`) — dokładnie
ten sam wzorzec importu jak `crm.volteo_umowa._sparsuj_decimal` reużyty w tamtym
module i w `crm/volteo_umowa_cp.py`."""

from datetime import date
from typing import Any

from crm.volteo_umowa_cp import kwoty_wariantu_cp
from crm.volteo_umowa_pdf import _adres, _data_pl, _kwota, _polacz, _stan_bool, _tekst


def klient_do_wyswietlenia(kontakt: dict[str, Any]) -> dict[str, str]:
	"""Zwraca dane klienta gotowe do wydruku/podglądu (`imie_nazwisko`, `adres`,
	`pesel`, `telefon`, `email`), zbudowane DOKŁADNIE tymi samymi funkcjami
	formatującymi, których `zbuduj_kontekst_cp()` używa do samego PDF-u — więc
	to, co rep widzi w podglądzie formularza, nigdy nie może rozjechać się z
	tym, co faktycznie wydrukuje się w dokumencie. `zbuduj_kontekst_cp()`
	wywołuje tę funkcję wewnętrznie zamiast duplikować te same wywołania.

	`kontakt` ma kształt zwracany przez `crm.api.umowa._dane_kontaktu()`:
	`first_name`, `last_name`, `custom_pesel`, `custom_ulica`, `custom_nr_domu`,
	`custom_nr_mieszkania`, `custom_kod_pocztowy`, `custom_miasto`, `email`,
	`mobile_no`."""
	return {
		"imie_nazwisko": _polacz(kontakt.get("first_name"), kontakt.get("last_name")),
		"adres": _adres(
			kontakt.get("custom_ulica"),
			kontakt.get("custom_nr_domu"),
			kontakt.get("custom_nr_mieszkania"),
			kontakt.get("custom_kod_pocztowy"),
			kontakt.get("custom_miasto"),
		),
		"pesel": _tekst(kontakt.get("custom_pesel")),
		"telefon": _tekst(kontakt.get("mobile_no")),
		"email": _tekst(kontakt.get("email")),
	}


def zbuduj_kontekst_cp(
	umowa: dict[str, Any],
	deal: dict[str, Any],
	kontakt: dict[str, Any],
	stale: dict[str, Any],
	dzis: date,
) -> dict[str, Any]:
	"""Buduje kontekst do nakładania na `crm/szablony/umowa_cp_obsluga_dotacji.pdf`
	(mapa współrzędnych: `crm.volteo_umowa_mapa_cp.MAPA_CP`).

	`umowa` — pola dokumentu umowy CP (m.in. `wynagrodzenie_wariant`,
	`zgoda_przetwarzanie_danych`, `zgoda_kontakt_telefoniczny`,
	`zgoda_dzialania_promocyjne`). `deal` — pola `CRM Deal` (tylko `name`,
	do numeru umowy). `kontakt` — dane klienta, kształt `_dane_kontaktu()` z
	`crm/api/umowa.py` (patrz `klient_do_wyswietlenia()` wyżej). `stale` —
	`frappe.db.get_singles_dict("Volteo CP Stale")` (kwoty wynagrodzenia,
	CELOWO bez prowizji — zob. `crm.volteo_umowa_cp`, akapit „TAJEMNICA
	PROWIZJI"). `dzis` — data wygenerowania dokumentu.

	Jedyna wartość podpisu Wykonawcy (`podpis_wykonawca`) jest stałym
	literałem `"PROENERGY"`, tak samo jak w `crm.volteo_umowa_pdf.zbuduj_kontekst`.
	Nie mutuje żadnego argumentu."""
	klient = klient_do_wyswietlenia(kontakt)
	klient_imie_nazwisko = klient["imie_nazwisko"]

	netto, brutto = kwoty_wariantu_cp(stale, umowa.get("wynagrodzenie_wariant"))

	return {
		"umowa_nr": _tekst(deal.get("name")),
		"data_zawarcia": _data_pl(dzis),
		"klient_imie_nazwisko": klient_imie_nazwisko,
		"klient_adres": klient["adres"],
		"klient_pesel": klient["pesel"],
		"klient_telefon": klient["telefon"],
		"klient_email": klient["email"],
		"wynagrodzenie_netto": _kwota(netto),
		"wynagrodzenie_brutto": _kwota(brutto),
		"zgoda_przetwarzanie_danych": _stan_bool(umowa.get("zgoda_przetwarzanie_danych")) is True,
		"zgoda_telefon": _stan_bool(umowa.get("zgoda_kontakt_telefoniczny")) is True,
		"zgoda_promocja": _stan_bool(umowa.get("zgoda_dzialania_promocyjne")) is True,
		"podpis_zamawiajacy": klient_imie_nazwisko.upper(),
		"podpis_wykonawca": "PROENERGY",
		"data_i_podpis_zamawiajacy": ", ".join(
			c for c in (_data_pl(dzis), klient_imie_nazwisko.upper()) if c
		),
	}
