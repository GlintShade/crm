# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Whitelisted API edycji zestawu i ceny szansy przez administracje (ops#270, b72).

Adapter Frappe nad frappe-free rdzeniem `crm/volteo_zestaw.py` (walidacja, lancuch
ceny, roznice, propozycja konfiguracji, tekst sladu) i `crm/koszty/rdzen.py`
(`aktualizuj_po_edycji_zestawu`). Trzy metody: `volteo_zestaw_get`,
`volteo_zestaw_podglad` (bez zapisu), `volteo_zestaw_zapisz`.

Bramka: `ADMIN_ROLE` z `crm.api.koszty` (fail-closed, PRZED sprawdzeniem istnienia
szansy), potem `write` na szansie. Zakres: rodzaje z `crm.volteo_pipeline.OZE_RODZAJE`
oraz Czyste Powietrze (ops#274) za przelacznikiem danych
`Volteo CP Stale.edycja_zestawu_wlaczona` (0 = `dozwolone=False`, `podglad` i `zapisz`
odrzucaja komunikatem `MSG_CP_WYLACZONE`). CP ma osobny blok odpowiedzi `cena_cp`
(w OZE `cena` jest slownikiem OZE, w CP pustym).

Kwoty w odpowiedziach to STRINGI z dwoma miejscami ("12345.67"), procenty
(`vat_pct`, `ulga_pct`) to znormalizowane stringi ("8", "12"), `okres_lat` to int.
Zapis idzie przez `doc.save()` (powstaje `Version`, `modified` sie przesuwa), pola
permlevel 2 (snapshot, pola z ops#271) przez `frappe.db.set_value(...,
update_modified=False)`. Brak `frappe.db.commit()`: request commituje sam.
"""

import json
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, now, now_datetime

from crm.api.koszty import ADMIN_ROLE
from crm.api.umowa import RODZAJ_CP, _sprawdz_dostep_do_szansy
from crm.integrations.autenti.logika import mozna_wyslac
from crm.koszty.rdzen import aktualizuj_po_edycji_zestawu
from crm.volteo_aktywnosc import zapisz_slad
from crm.volteo_kalkulator_oze import RODZAJE_NOWE
from crm.volteo_pipeline import OZE_RODZAJE
from crm.volteo_zestaw import (
	KLUCZE_DOTACJI_CP,
	TYPY_WIERSZY_CP,
	TYPY_WIERSZY_OZE,
	ZNACZNIK_ZESTAW,
	kwota,
	odtworz_dodatki_bez_ulgi,
	przelicz_cene,
	przelicz_cene_cp,
	roznice_zestawu,
	tekst_sladu_zestawu,
	waliduj_cene,
	waliduj_cene_cp,
	waliduj_wiersze,
	zaproponuj_konfiguracje,
)
from crm.volteo_zestaw import formatuj_kwote as _formatuj_kwote

DOCTYPE = "CRM Deal"
POLE_EDYTOWANO = "custom_zestaw_edytowano"
POLE_POWOD = "custom_zestaw_edycja_powod"
MAX_POWOD = 500
MAX_DATA = 140  # dlugosc pola Data (typ, nazwa, jednostka)

POLA_KONFIGURACJI: tuple[str, ...] = (
	"custom_falownik",
	"custom_bateria",
	"custom_pojemnosc_kwh",
	"custom_panel",
	"custom_panele",
	"custom_konstrukcja",
	"custom_kabel_m",
	"custom_licznik_dodatkowy",
	"custom_dod_klima",
	"custom_dod_panele",
	"custom_dod_panele_mikro",
	"custom_ems_breeze",
	"custom_pstryk",
	"custom_ev_ladowarka",
)
"""14 pol konfiguracji PV edytowalnych w tym API (lustro kluczy `zaproponuj_konfiguracje`)."""

_POLA_KONFIGURACJI_LICZBOWE = frozenset(
	{
		"custom_pojemnosc_kwh",
		"custom_panele",
		"custom_kabel_m",
		"custom_dod_panele",
		"custom_dod_panele_mikro",
	}
)

_KLUCZE_CENY_Z_WEJSCIA = (
	"netto",
	"vat_pct",
	"dotacja",
	"ulga_pct",
	"okres_lat",
	"wplata_wlasna",
	"dodatki_bez_ulgi_brutto",
)
"""Klucze `cena` z klienta, ktore wchodza do lancucha; reszta (pola pochodne) ignorowana."""

MSG_CP_WYLACZONE = "Edycja zestawu Czystego Powietrza jest wyłączona."
MSG_CP_KONFIGURACJA = "Konfiguracji Czystego Powietrza nie edytuje się w tym oknie. Użyj panelu bocznego."
MSG_RODZAJ_NIEDOSTEPNY = "Edycja zestawu nie jest dostępna dla tego rodzaju umowy."
MSG_PDF_REGENERUJ = "Wygeneruj ponownie PDF umowy w zakładce Umowa."
MSG_PDF_ANEKS = "Umowa w Autenti pozostaje bez zmian. Zmianę opisz w aneksie."
MSG_INFO_KONFIGURACJI_CP = (
	"Pola kalkulatora CP (poziom, standard, powierzchnia, źródło ciepła) edytuj w panelu bocznym."
)
MSG_INFO_KONFIGURACJI = "Pola urządzenia edytuj w panelu bocznym."

# ---------------------------------------------------------------------------
# Pomocnicze: formatowanie
# ---------------------------------------------------------------------------


def _s2(x: Any) -> str:
	"""Kwota jako string z dwoma miejscami (ROUND_HALF_UP)."""
	d = kwota(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
	return format(d, "f")


def _pct(x: Any) -> str:
	"""Procent jako znormalizowany string ("8", "12", "12.5")."""
	d = kwota(x)
	if d == d.to_integral_value():
		return str(int(d))
	return format(d.normalize(), "f")


def _tekst(x: Any) -> str:
	return "" if x is None else str(x).strip()


def _rozne(a: Any, b: Any) -> bool:
	try:
		return kwota(a) != kwota(b)
	except ValueError:
		return _tekst(a) != _tekst(b)


# ---------------------------------------------------------------------------
# Bramka i blokada
# ---------------------------------------------------------------------------


def _sprawdz_admina() -> None:
	if not (ADMIN_ROLE & set(frappe.get_roles(frappe.session.user))):
		frappe.throw(_("Brak uprawnień do edycji zestawu."), frappe.PermissionError)


def _cp_wlaczone() -> bool:
	"""Przelacznik `Volteo CP Stale.edycja_zestawu_wlaczona`. Single zwraca stringi
	("0" jest prawda), wiec odczyt WYLACZNIE przez `get_singles_dict` + `cint`."""
	return bool(cint((frappe.db.get_singles_dict("Volteo CP Stale") or {}).get("edycja_zestawu_wlaczona")))


def _blokada(rodzaj: str | None) -> tuple[bool, str, str]:
	"""`(dozwolone, powod_blokady, linia)` dla rodzaju umowy szansy."""
	if rodzaj in OZE_RODZAJE:
		return True, "", "oze"
	if rodzaj == RODZAJ_CP:
		if _cp_wlaczone():
			return True, "", "cp"
		return False, _(MSG_CP_WYLACZONE), "cp"
	return False, _(MSG_RODZAJ_NIEDOSTEPNY), "oze"


def _wczytaj_dla_edycji(deal: str) -> "frappe.model.document.Document":
	_sprawdz_admina()
	_sprawdz_dostep_do_szansy(deal, "write")
	return frappe.get_doc(DOCTYPE, deal)


# ---------------------------------------------------------------------------
# Odczyt stanu
# ---------------------------------------------------------------------------


def _ilosc(x: Any) -> float:
	try:
		return float(kwota(x))
	except ValueError:
		return 0.0


def _wiersz_json(w: Any, bez_name: bool = False) -> dict[str, Any]:
	"""Wiersz zestawu jako slownik serializowalny (kwoty jako stringi)."""
	get = w.get if hasattr(w, "get") else (lambda k, d=None: getattr(w, k, d))
	wynik: dict[str, Any] = {
		"typ": get("typ") or "",
		"nazwa": get("nazwa") or "",
		"ilosc": _ilosc(get("ilosc")),
		"jednostka": get("jednostka") or "",
		"netto": _s2(get("netto")),
		"brutto": _s2(get("brutto")),
	}
	if not bez_name:
		wynik = {"name": get("name"), "idx": get("idx"), **wynik}
	return wynik


def _wiersze_z_dokumentu(doc: "frappe.model.document.Document") -> list[dict[str, Any]]:
	wiersze = [_wiersz_json(w) for w in doc.get("custom_zestaw") or []]
	return sorted(wiersze, key=lambda w: w["idx"] or 0)


def _stale() -> dict[str, Any]:
	ustawienia = frappe.db.get_singles_dict("Volteo Kalkulator Stale") or {}
	return {"pmt_oprocentowanie_mies": flt(ustawienia.get("pmt_oprocentowanie_mies"))}


def _cena_ze_szansy(doc: "frappe.model.document.Document") -> dict[str, Any]:
	return {
		"netto": _s2(doc.get("custom_netto")),
		"vat_pct": _pct(doc.get("custom_vat_pct")),
		"brutto": _s2(doc.get("deal_value")),
		"dotacja": _s2(doc.get("custom_dotacja")),
		"zasady_dotacji": doc.get("custom_zasady_dotacji") or "",
		"ulga_pct": _pct(doc.get("custom_ulga_pct")),
		"ulga_kwota": _s2(doc.get("custom_ulga_kwota")),
		"cena_po_dotacji": _s2(doc.get("custom_cena_po_dotacji")),
		"cena_po_uldze": _s2(doc.get("custom_cena_po_uldze")),
		"okres_lat": int(flt(doc.get("custom_okres_lat"))),
		"wplata_wlasna": _s2(doc.get("custom_wplata_wlasna")),
		"rata_brutto": _s2(doc.get("custom_rata_brutto")),
		"rata_po_dotacji": _s2(doc.get("custom_rata_po_dotacji")),
		"rata_po_uldze": _s2(doc.get("custom_rata_po_uldze")),
		"typ_klienta": doc.get("custom_typ_klienta") or "",
		"dodatki_netto": _s2(doc.get("custom_dodatki_netto")),
		"dodatki_bez_ulgi_brutto": _s2(
			odtworz_dodatki_bez_ulgi(
				doc.get("custom_cena_po_dotacji"), doc.get("custom_ulga_kwota"), doc.get("custom_ulga_pct")
			)
		),
	}


def _cena_z_wyniku(
	doc: "frappe.model.document.Document", wejscie: dict[str, Any], wynik: dict[str, Any]
) -> dict[str, Any]:
	"""Ta sama ksztalt co `_cena_ze_szansy`, z wartosciami przeliczonymi przez rdzen."""
	return {
		"netto": _s2(wynik["netto"]),
		"vat_pct": _pct(wynik["vat_pct"]),
		"brutto": _s2(wynik["brutto"]),
		"dotacja": _s2(wynik["dotacja"]),
		"zasady_dotacji": doc.get("custom_zasady_dotacji") or "",
		"ulga_pct": _pct(wynik["ulga_pct"]),
		"ulga_kwota": _s2(wynik["ulga_kwota"]),
		"cena_po_dotacji": _s2(wynik["cena_po_dotacji"]),
		"cena_po_uldze": _s2(wynik["cena_po_uldze"]),
		"okres_lat": int(kwota(wejscie.get("okres_lat"))),
		"wplata_wlasna": _s2(wejscie.get("wplata_wlasna")),
		"rata_brutto": _s2(wynik["rata_brutto"]),
		"rata_po_dotacji": _s2(wynik["rata_po_dotacji"]),
		"rata_po_uldze": _s2(wynik["rata_po_uldze"]),
		"typ_klienta": doc.get("custom_typ_klienta") or "",
		"dodatki_netto": _s2(doc.get("custom_dodatki_netto")),
		"dodatki_bez_ulgi_brutto": _s2(wejscie.get("dodatki_bez_ulgi_brutto")),
	}


def _stale_cp() -> dict[str, Any]:
	"""Stale finansowania CP w ksztalcie dla `przelicz_cene_cp`; nie zasiana wartosc to `None`."""
	ust = frappe.db.get_singles_dict("Volteo CP Stale") or {}

	def wartosc(klucz: str) -> Any:
		surowa = ust.get(klucz)
		return None if surowa is None or _tekst(surowa) == "" else surowa

	return {
		"oprocentowanie_mies": wartosc("oprocentowanie_raty_mies"),
		"trify_udzial": wartosc("trify_udzial_dotacji"),
		"trify_stawka_za_1000": wartosc("trify_stawka_za_1000"),
	}


def _s2_lub_none(x: Any) -> str | None:
	return None if x is None else _s2(x)


def _cena_cp_ze_szansy(
	doc: "frappe.model.document.Document", wiersze: list[dict[str, Any]]
) -> dict[str, Any]:
	okres = int(flt(doc.get("custom_cp_okres_lat")))
	return {
		"deal_value": _s2(doc.get("deal_value")),
		"dotacja_zrodlo": _s2(doc.get("custom_cp_dotacja_zrodlo")),
		"dotacja_co": _s2(doc.get("custom_cp_dotacja_co")),
		"dotacja_termo": _s2(doc.get("custom_cp_dotacja_termo")),
		"dotacja_laczna": _s2(doc.get("custom_estimated_subsidy_pln")),
		"wklad_wlasny": _s2(doc.get("custom_cp_wklad_wlasny")),
		"okres_lat": okres,
		"wplata_gotowka": _s2(doc.get("custom_cp_wplata_gotowka")),
		"kwota_kredytu": _s2(doc.get("custom_cp_kwota_kredytu")) if okres > 0 else None,
		"rata_wkladu": _s2(doc.get("custom_cp_rata_wkladu")) if okres > 0 else None,
		"podstawa_trify": _s2_lub_none(doc.get("custom_cp_podstawa_trify")),
		"rata_trify": _s2_lub_none(doc.get("custom_cp_rata_trify")),
		"netto_suma": _s2(sum((kwota(w["netto"]) for w in wiersze), Decimal(0))),
	}


def _cena_cp_z_wyniku(wynik: dict[str, Any]) -> dict[str, Any]:
	return {
		"deal_value": _s2(wynik["deal_value"]),
		"dotacja_zrodlo": _s2(wynik["dotacje"]["zrodlo"]),
		"dotacja_co": _s2(wynik["dotacje"]["co"]),
		"dotacja_termo": _s2(wynik["dotacje"]["termo"]),
		"dotacja_laczna": _s2(wynik["dotacja_laczna"]),
		"wklad_wlasny": _s2(wynik["wklad_wlasny"]),
		"okres_lat": wynik["okres_lat"],
		"wplata_gotowka": _s2(wynik["wplata_gotowka"]),
		"kwota_kredytu": _s2_lub_none(wynik["kwota_kredytu"]),
		"rata_wkladu": _s2_lub_none(wynik["rata_wkladu"]),
		"podstawa_trify": _s2_lub_none(wynik["podstawa_trify"]),
		"rata_trify": _s2_lub_none(wynik["rata_trify"]),
		"netto_suma": _s2(wynik["netto_suma"]),
	}


def _wejscie_cp(doc: "frappe.model.document.Document", cena: Any) -> tuple[dict[str, Any], dict[str, Any]]:
	"""`(dotacje, finansowanie)` dla `przelicz_cene_cp`: wartosci ze szansy nadpisane
	kluczami z klienta (`dotacja_zrodlo|co|termo`, `okres_lat`, `wplata_gotowka`)."""
	if not isinstance(cena, dict):
		frappe.throw(_("Dane ceny mają nieprawidłowy format."))
	dotacje = {}
	for grupa in KLUCZE_DOTACJI_CP:
		klucz = f"dotacja_{grupa}"
		if klucz in cena and cena[klucz] is not None:
			dotacje[grupa] = cena[klucz]
		else:
			dotacje[grupa] = doc.get(f"custom_cp_dotacja_{grupa}")
	fin = {
		"okres_lat": cena["okres_lat"]
		if cena.get("okres_lat") is not None
		else doc.get("custom_cp_okres_lat"),
		"wplata_gotowka": cena["wplata_gotowka"]
		if cena.get("wplata_gotowka") is not None
		else doc.get("custom_cp_wplata_gotowka"),
	}
	return dotacje, fin


def _przelicz_cp(
	doc: "frappe.model.document.Document", nowe: list[dict[str, Any]], cena: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
	"""Waliduje i liczy cene CP. Zwraca `(wynik, dotacje)`; bledy to `frappe.throw`."""
	dotacje, fin = _wejscie_cp(doc, cena)
	bledy = waliduj_cene_cp(nowe, dotacje, fin)
	if bledy:
		frappe.throw("\n".join(bledy))
	try:
		return przelicz_cene_cp(nowe, dotacje, fin, _stale_cp()), dotacje
	except ValueError as exc:
		frappe.throw(str(exc))


def _konfiguracja_ze_szansy(doc: "frappe.model.document.Document") -> dict[str, Any]:
	return {p: doc.get(p) for p in POLA_KONFIGURACJI}


def _informacja_o_umowie(deal: str) -> dict[str, Any]:
	istnieje = bool(frappe.db.exists("Volteo Umowa", deal))
	status = frappe.db.get_value("Volteo Umowa", deal, "autenti_status") if istnieje else None
	pdf = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": DOCTYPE,
			"attached_to_name": deal,
			"file_name": ["like", "Umowa%"],
		},
		fields=["modified", "file_name"],
		order_by="modified desc",
		limit_page_length=10,
	)
	# Podpisany plik z Autenti ("...-podpisana.pdf") to nie wygenerowany PDF umowy.
	pdf = [p for p in pdf if "podpisana" not in (p.file_name or "")]
	return {
		"istnieje": istnieje,
		"autenti_status": status or "",
		"pdf_data": str(pdf[0].modified) if pdf else None,
		"mozna_regenerowac": bool(istnieje and mozna_wyslac(status)),
	}


def _ostatnia_edycja(deal: str, meta: "frappe.model.meta.Meta") -> dict[str, Any] | None:
	komentarz = frappe.get_all(
		"Comment",
		filters={
			"comment_type": "Info",
			"reference_doctype": DOCTYPE,
			"reference_name": deal,
			"content": ["like", ZNACZNIK_ZESTAW + "%"],
		},
		fields=["creation", "comment_email"],
		order_by="creation desc",
		limit_page_length=1,
	)
	kiedy = frappe.db.get_value(DOCTYPE, deal, POLE_EDYTOWANO) if meta.has_field(POLE_EDYTOWANO) else None
	powod = frappe.db.get_value(DOCTYPE, deal, POLE_POWOD) if meta.has_field(POLE_POWOD) else None
	if not kiedy and komentarz:
		kiedy = komentarz[0].creation
	if not kiedy:
		return None
	return {
		"kiedy": str(kiedy),
		"kto": komentarz[0].comment_email if komentarz else "",
		"powod": powod or "",
	}


def _ostrzezenie_falownika(konfiguracja_falownik: Any, wiersze: Any) -> list[str]:
	falowniki = [w for w in wiersze if _tekst(w.get("typ")) == "Falownik"]
	if not falowniki:
		return []
	nazwa = _tekst(falowniki[0].get("nazwa"))
	if _tekst(konfiguracja_falownik) and _tekst(konfiguracja_falownik) != nazwa:
		return [
			_(
				'Falownik w konfiguracji ("{0}") różni się od nazwy pozycji Falownik ("{1}"). '
				"PDF umowy poda liczbę falowników tylko przy zgodnych nazwach."
			).format(_tekst(konfiguracja_falownik), nazwa)
		]
	return []


def _stan(doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Pelny stan edytora zestawu (odpowiedz `volteo_zestaw_get`)."""
	deal = doc.name
	meta = frappe.get_meta(DOCTYPE)
	rodzaj = doc.get("custom_rodzaj_umowy") or ""
	dozwolone, powod_blokady, linia = _blokada(rodzaj)
	wiersze = _wiersze_z_dokumentu(doc)
	nowy_rodzaj = rodzaj in RODZAJE_NOWE
	if linia == "cp":
		return {
			"dozwolone": dozwolone,
			"powod_blokady": powod_blokady,
			"rodzaj": rodzaj,
			"linia": linia,
			"modified": str(doc.modified),
			"wiersze": wiersze,
			"typy": list(TYPY_WIERSZY_CP),
			"cena": {},
			"cena_cp": _cena_cp_ze_szansy(doc, wiersze),
			"konfiguracja": {},
			"konfiguracja_info": _(MSG_INFO_KONFIGURACJI_CP),
			"umowa": _informacja_o_umowie(deal),
			"ostatnia_edycja": _ostatnia_edycja(deal, meta),
			"ostrzezenia": [],
		}
	return {
		"dozwolone": dozwolone,
		"powod_blokady": powod_blokady,
		"rodzaj": rodzaj,
		"linia": linia,
		"modified": str(doc.modified),
		"wiersze": wiersze,
		"typy": list(TYPY_WIERSZY_OZE),
		"cena": _cena_ze_szansy(doc),
		"konfiguracja": {} if nowy_rodzaj else _konfiguracja_ze_szansy(doc),
		"konfiguracja_info": _(MSG_INFO_KONFIGURACJI) if nowy_rodzaj else "",
		"umowa": _informacja_o_umowie(deal),
		"ostatnia_edycja": _ostatnia_edycja(deal, meta),
		"ostrzezenia": [] if nowy_rodzaj else _ostrzezenie_falownika(doc.get("custom_falownik"), wiersze),
	}


# ---------------------------------------------------------------------------
# Walidacja wejscia
# ---------------------------------------------------------------------------


def _wiersze_wejscia(wiersze: Any) -> list[dict[str, Any]]:
	"""Surowe wiersze z klienta (lista slownikow) z sanityzacja kluczy."""
	if not isinstance(wiersze, list) or not all(isinstance(w, dict) for w in wiersze):
		frappe.throw(_("Pozycje zestawu mają nieprawidłowy format."))
	return [dict(w) for w in wiersze]


def _sprawdz_wiersze(wiersze: list[dict[str, Any]], linia: str = "oze") -> None:
	bledy = waliduj_wiersze(wiersze, linia)
	for nr, w in enumerate(wiersze, start=1):
		for klucz in ("typ", "nazwa", "jednostka"):
			if len(_tekst(w.get(klucz))) > MAX_DATA:
				bledy.append(f"Pozycja {nr}: pole {klucz} jest za długie (maksymalnie {MAX_DATA} znaków).")
	if bledy:
		frappe.throw("\n".join(bledy))


def _wiersze_do_porownania(wiersze: list[dict[str, Any]], linia: str = "oze") -> list[dict[str, Any]]:
	"""Wiersze z klienta, z opcjonalnym `name`. OZE nie ma cen pozycji (zerowane), CP je zachowuje."""
	wynik = []
	for w in wiersze:
		zrodlo = w if linia == "cp" else {**w, "netto": 0, "brutto": 0}
		wiersz = _wiersz_json(zrodlo, bez_name=True)
		wiersz["name"] = _tekst(w.get("name")) or None
		wynik.append(wiersz)
	return wynik


def _wejscie_ceny(doc: "frappe.model.document.Document", cena: Any) -> dict[str, Any]:
	"""Wejscie lancucha ceny: wartosci ze szansy nadpisane kluczami z klienta."""
	if not isinstance(cena, dict):
		frappe.throw(_("Dane ceny mają nieprawidłowy format."))
	bazowa = _cena_ze_szansy(doc)
	wejscie: dict[str, Any] = {k: bazowa[k] for k in _KLUCZE_CENY_Z_WEJSCIA}
	for klucz in _KLUCZE_CENY_Z_WEJSCIA:
		if klucz in cena and cena[klucz] is not None:
			wejscie[klucz] = cena[klucz]
	wejscie["typ_klienta"] = doc.get("custom_typ_klienta")
	return wejscie


def _przelicz(wejscie: dict[str, Any]) -> dict[str, Any]:
	bledy = waliduj_cene(wejscie)
	if bledy:
		frappe.throw("\n".join(bledy))
	return przelicz_cene(wejscie, _stale())


def _komponenty() -> list[dict[str, Any]]:
	return frappe.get_all(
		"Volteo Komponent",
		filters={"aktywny": 1},
		fields=["nazwa", "model", "kategoria", "pojemnosc_kwh"],
	)


def _propozycja(
	doc: "frappe.model.document.Document", wiersze: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
	surowa = zaproponuj_konfiguracje(
		wiersze,
		_komponenty(),
		obecna={"custom_pojemnosc_kwh": doc.get("custom_pojemnosc_kwh")},
		rodzaj=doc.get("custom_rodzaj_umowy"),
	)
	ostrzezenia = list(surowa.pop("_ostrzezenia", []) or [])
	propozycja = {k: (flt(v) if isinstance(v, Decimal) else v) for k, v in surowa.items()}
	return propozycja, ostrzezenia


def _sprawdz_konfiguracje(konfiguracja: Any) -> dict[str, Any]:
	if not isinstance(konfiguracja, dict):
		frappe.throw(_("Konfiguracja ma nieprawidłowy format."))
	nieznane = sorted(set(konfiguracja) - set(POLA_KONFIGURACJI))
	if nieznane:
		frappe.throw(_("Nieznane pola konfiguracji: {0}.").format(", ".join(nieznane)))
	wynik: dict[str, Any] = {}
	for pole, wartosc in konfiguracja.items():
		if pole in _POLA_KONFIGURACJI_LICZBOWE:
			try:
				liczba = kwota(wartosc)
			except ValueError:
				frappe.throw(_("Pole konfiguracji {0} musi być liczbą.").format(pole))
			if liczba < 0:
				frappe.throw(_("Pole konfiguracji {0} nie może być ujemne.").format(pole))
			wynik[pole] = flt(liczba)
		else:
			tekst = _tekst(wartosc)
			if len(tekst) > MAX_DATA:
				frappe.throw(_("Pole konfiguracji {0} jest za długie.").format(pole))
			wynik[pole] = tekst
	return wynik


def _serializuj_roznice(roznice: Any) -> dict[str, Any]:
	def wiersz(w: dict[str, Any]) -> dict[str, Any]:
		return _wiersz_json(w, bez_name=True) | {"name": w.get("name")}

	return {
		"dodane": [wiersz(w) for w in roznice.dodane],
		"usuniete": [wiersz(w) for w in roznice.usuniete],
		"zmienione": [
			{"stary": wiersz(stary), "nowy": wiersz(nowy), "pola": list(pola)}
			for stary, nowy, pola in roznice.zmienione
		],
	}


# ---------------------------------------------------------------------------
# Metody whitelisted
# ---------------------------------------------------------------------------


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_zestaw_get(deal: str) -> dict[str, Any]:
	"""Stan edytora zestawu: wiersze, cena, konfiguracja, umowa, ostatnia edycja.

	Wymaga roli z `ADMIN_ROLE` i uprawnienia `write` na szansie. Dla rodzaju spoza
	`OZE_RODZAJE` zwraca `dozwolone=False` z `powod_blokady` (stan nadal jest zwracany).
	"""
	doc = _wczytaj_dla_edycji(deal)
	return _stan(doc)


@frappe.whitelist()
@rate_limit(limit=120, seconds=60)
def volteo_zestaw_podglad(deal: str, wiersze: list[dict[str, Any]], cena: dict[str, Any]) -> dict[str, Any]:
	"""Podglad edycji bez zapisu: przeliczona cena, propozycja konfiguracji, roznice, ostrzezenia.

	Ta sama bramka i walidacja co `volteo_zestaw_zapisz`; bledy walidacji to
	`frappe.throw` z komunikatami polaczonymi znakiem nowej linii.
	"""
	doc = _wczytaj_dla_edycji(deal)
	dozwolone, powod, linia = _blokada(doc.get("custom_rodzaj_umowy"))
	if not dozwolone:
		frappe.throw(powod)

	if linia == "cp":
		surowe = _wiersze_wejscia(wiersze)
		_sprawdz_wiersze(surowe, "cp")
		nowe = _wiersze_do_porownania(surowe, "cp")
		wynik, _dotacje = _przelicz_cp(doc, nowe, cena)
		return {
			"cena": {},
			"cena_cp": _cena_cp_z_wyniku(wynik),
			"konfiguracja_propozycja": {},
			"roznice": _serializuj_roznice(roznice_zestawu(_wiersze_z_dokumentu(doc), nowe)),
			"ostrzezenia": [],
		}

	surowe = _wiersze_wejscia(wiersze)
	_sprawdz_wiersze(surowe)
	nowe = _wiersze_do_porownania(surowe)
	wejscie = _wejscie_ceny(doc, cena)
	wynik = _przelicz(wejscie)

	roznice = roznice_zestawu(_wiersze_z_dokumentu(doc), nowe)
	propozycja, ostrzezenia = _propozycja(doc, nowe)
	if propozycja:
		ostrzezenia += _ostrzezenie_falownika(doc.get("custom_falownik"), nowe)

	return {
		"cena": _cena_z_wyniku(doc, wejscie, wynik),
		"konfiguracja_propozycja": propozycja,
		"roznice": _serializuj_roznice(roznice),
		"ostrzezenia": ostrzezenia,
	}


def _pola_ceny_do_zapisu(wynik: dict[str, Any], wejscie: dict[str, Any]) -> dict[str, Any]:
	return {
		"custom_netto": float(wynik["netto"]),
		"custom_vat_pct": float(wynik["vat_pct"]),
		"deal_value": float(wynik["brutto"]),
		"custom_dotacja": float(wynik["dotacja"]),
		"custom_estimated_subsidy_pln": float(wynik["dotacja"]),
		"custom_cena_po_dotacji": float(wynik["cena_po_dotacji"]),
		"custom_ulga_pct": _pct(wynik["ulga_pct"]),
		"custom_ulga_kwota": float(wynik["ulga_kwota"]),
		"custom_cena_po_uldze": float(wynik["cena_po_uldze"]),
		"custom_okres_lat": int(kwota(wejscie.get("okres_lat"))),
		"custom_wplata_wlasna": float(kwota(wejscie.get("wplata_wlasna"))),
		"custom_rata_brutto": float(wynik["rata_brutto"]),
		"custom_rata_po_dotacji": float(wynik["rata_po_dotacji"]),
		"custom_rata_po_uldze": float(wynik["rata_po_uldze"]),
	}


def _zapisz_snapshot(deal: str, netto: Decimal, powod: str, meta: "frappe.model.meta.Meta") -> str:
	"""Aktualizuje snapshot kosztow po edycji. Zwraca krotki opis do sladu."""
	surowy = frappe.db.get_value(DOCTYPE, deal, "custom_koszty_json")
	if not surowy:
		return "brak snapshotu, pominięto"
	try:
		snapshot = json.loads(surowy)
	except (TypeError, ValueError):
		frappe.log_error(frappe.get_traceback(), "Volteo Zestaw: uszkodzony snapshot kosztów")
		return "uszkodzony snapshot, pominięto"
	nowy = aktualizuj_po_edycji_zestawu(snapshot, netto, frappe.session.user, now(), powod)
	if nowy is None:
		return "brak snapshotu, pominięto"
	pola: dict[str, Any] = {"custom_koszty_json": json.dumps(nowy, ensure_ascii=False)}
	if meta.has_field("custom_koszty_zysk_plan"):
		pola["custom_koszty_zysk_plan"] = flt(nowy["podsumowanie"]["zysk_plan"], 2)
	rzeczywiste = nowy.get("podsumowanie_rzeczywiste")
	if rzeczywiste is not None and meta.has_field("custom_koszty_zysk_rzeczywisty"):
		pola["custom_koszty_zysk_rzeczywisty"] = flt(rzeczywiste["zysk_rzeczywisty"], 2)
	# permlevel 2: zapis bez dotykania `modified` (patrz docstring modulu).
	frappe.db.set_value(DOCTYPE, deal, pola, update_modified=False)
	return "zaktualizowano netto {0} zł".format(_formatuj_kwote(netto))


def _zapisz_cp(
	doc: "frappe.model.document.Document",
	wiersze: Any,
	cena: Any,
	konfiguracja: Any,
	powod: str,
) -> dict[str, Any]:
	"""Zapis edycji zestawu Czystego Powietrza (ops#274). Wywolywane po bramce, blokadzie
	optymistycznej i sprawdzeniu przelacznika. Prowizje CP (permlevel 2) i
	`custom_cp_wejscie_json` NIE sa dotykane."""
	deal = doc.name
	if konfiguracja:
		frappe.throw(_(MSG_CP_KONFIGURACJA))
	surowe = _wiersze_wejscia(wiersze)
	_sprawdz_wiersze(surowe, "cp")
	nowe = _wiersze_do_porownania(surowe, "cp")
	wynik, _dotacje = _przelicz_cp(doc, nowe, cena)
	meta = frappe.get_meta(DOCTYPE)

	stare = _wiersze_z_dokumentu(doc)
	roznice = roznice_zestawu(stare, nowe)

	# Grupa dotacji jest zapisywana, gdy byla juz na szansie (nie None) albo jest teraz niezerowa.
	pola_dotacji = {
		f"custom_cp_dotacja_{g}": float(wynik["dotacje"][g])
		for g in KLUCZE_DOTACJI_CP
		if doc.get(f"custom_cp_dotacja_{g}") is not None or wynik["dotacje"][g] != 0
	}
	pola_ceny: dict[str, Any] = {
		"deal_value": float(wynik["deal_value"]),
		"custom_estimated_subsidy_pln": float(wynik["dotacja_laczna"]),
		"custom_cp_wklad_wlasny": float(wynik["wklad_wlasny"]),
		"custom_cp_okres_lat": wynik["okres_lat"],
		"custom_cp_wplata_gotowka": float(wynik["wplata_gotowka"]),
		"custom_cp_kwota_kredytu": None if wynik["kwota_kredytu"] is None else float(wynik["kwota_kredytu"]),
		"custom_cp_rata_wkladu": None if wynik["rata_wkladu"] is None else float(wynik["rata_wkladu"]),
		**pola_dotacji,
	}
	if wynik["podstawa_trify"] is not None:
		pola_ceny["custom_cp_podstawa_trify"] = float(wynik["podstawa_trify"])
		pola_ceny["custom_cp_rata_trify"] = float(wynik["rata_trify"])
	zmienione_pola_cen = [p for p, v in pola_ceny.items() if _rozne(doc.get(p), v)]
	if roznice.puste and not zmienione_pola_cen:
		frappe.throw(_("Brak zmian do zapisania."))

	przed = {
		"deal_value": doc.get("deal_value"),
		"dotacja_laczna": doc.get("custom_estimated_subsidy_pln"),
		"wklad_wlasny": doc.get("custom_cp_wklad_wlasny"),
	}
	po = {
		"deal_value": wynik["deal_value"],
		"dotacja_laczna": wynik["dotacja_laczna"],
		"wklad_wlasny": wynik["wklad_wlasny"],
	}

	status_umowy = ""
	umowa = _informacja_o_umowie(deal)
	if umowa["istnieje"]:
		status_umowy = umowa["autenti_status"] or "niewysłana do Autenti"

	stare_wiersze = {w.get("name"): w for w in doc.get("custom_zestaw") or [] if w.get("name")}
	zmienione_nazwy = {n.get("name") for _s, n, _p in roznice.zmienione if n.get("name")}
	doc.set("custom_zestaw", [])
	for w in nowe:
		wiersz = {
			"typ": w["typ"],
			"nazwa": w["nazwa"],
			"ilosc": w["ilosc"],
			"jednostka": w["jednostka"],
			"netto": float(kwota(w["netto"])),
			"brutto": float(kwota(w["brutto"])),
		}
		poprzedni = stare_wiersze.get(w["name"]) if w["name"] else None
		if poprzedni is None or w["name"] in zmienione_nazwy:
			wiersz["reczna_ilosc"] = 1
		else:
			wiersz["reczna_ilosc"] = poprzedni.get("reczna_ilosc") or 0
		doc.append("custom_zestaw", wiersz)
	for pole, wartosc in pola_ceny.items():
		doc.set(pole, wartosc)
	doc.save()

	if meta.has_field(POLE_EDYTOWANO) or meta.has_field(POLE_POWOD):
		pola_edycji: dict[str, Any] = {}
		if meta.has_field(POLE_EDYTOWANO):
			pola_edycji[POLE_EDYTOWANO] = now_datetime()
		if meta.has_field(POLE_POWOD):
			pola_edycji[POLE_POWOD] = _tekst(powod)[:MAX_POWOD]
		frappe.db.set_value(DOCTYPE, deal, pola_edycji, update_modified=False)

	opis_snapshotu = _zapisz_snapshot(deal, wynik["netto_suma"], _tekst(powod)[:MAX_POWOD], meta)
	try:
		zapisz_slad(
			deal,
			tekst_sladu_zestawu(
				roznice,
				None,
				None,
				[],
				_tekst(powod)[:MAX_POWOD],
				status_umowy,
				snapshot=opis_snapshotu,
				cp={"przed": przed, "po": po},
			),
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Volteo Zestaw: błąd zapisu śladu aktywności")

	stan = _stan(frappe.get_doc(DOCTYPE, deal))
	if stan["umowa"]["istnieje"]:
		wskazowka = _(MSG_PDF_REGENERUJ) if stan["umowa"]["mozna_regenerowac"] else _(MSG_PDF_ANEKS)
	else:
		wskazowka = ""
	return {**stan, "wskazowka_pdf": wskazowka}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_zestaw_zapisz(
	deal: str,
	wiersze: list[dict[str, Any]],
	cena: dict[str, Any],
	konfiguracja: dict[str, Any],
	powod: str,
	modified: str,
) -> dict[str, Any]:
	"""Zapisuje edycje zestawu i ceny szansy (OZE), aktualizuje snapshot kosztow i dopisuje
	slad `[volteo:zestaw]` (widoczny tylko dla administracji).

	Zwraca stan jak `volteo_zestaw_get` plus `wskazowka_pdf`. Blokada optymistyczna po
	`modified`. Brak zmian (identyczne wiersze, cena i konfiguracja) jest odrzucany.
	"""
	doc = _wczytaj_dla_edycji(deal)
	powod = _tekst(powod)[:MAX_POWOD]

	if _tekst(modified) != str(doc.modified):
		frappe.throw(_("Szansa została w międzyczasie zmieniona. Odśwież i wprowadź zmiany ponownie."))

	dozwolone, powod_blokady, linia = _blokada(doc.get("custom_rodzaj_umowy"))
	if not dozwolone:
		frappe.throw(powod_blokady)

	if linia == "cp":
		return _zapisz_cp(doc, wiersze, cena, konfiguracja, powod)

	surowe = _wiersze_wejscia(wiersze)
	_sprawdz_wiersze(surowe)
	nowe = _wiersze_do_porownania(surowe)
	wejscie = _wejscie_ceny(doc, cena)
	wynik = _przelicz(wejscie)
	zmiany_konfiguracji = _sprawdz_konfiguracje(konfiguracja)
	meta = frappe.get_meta(DOCTYPE)
	zmiany_konfiguracji = {p: v for p, v in zmiany_konfiguracji.items() if meta.has_field(p)}

	stare = _wiersze_z_dokumentu(doc)
	roznice = roznice_zestawu(stare, nowe)
	pola_ceny = _pola_ceny_do_zapisu(wynik, wejscie)
	cena_przed = {
		"netto": doc.get("custom_netto"),
		"brutto": doc.get("deal_value"),
		"dotacja": doc.get("custom_dotacja"),
		"cena_po_uldze": doc.get("custom_cena_po_uldze"),
	}
	cena_po = {
		"netto": wynik["netto"],
		"brutto": wynik["brutto"],
		"dotacja": wynik["dotacja"],
		"cena_po_uldze": wynik["cena_po_uldze"],
	}
	zmienione_pola_cen = [p for p, v in pola_ceny.items() if _rozne(doc.get(p), v)]
	zmienione_konfiguracje = [p for p, v in zmiany_konfiguracji.items() if _rozne(doc.get(p), v)]
	if roznice.puste and not zmienione_pola_cen and not zmienione_konfiguracje:
		frappe.throw(_("Brak zmian do zapisania."))

	status_umowy = ""
	umowa = _informacja_o_umowie(deal)
	if umowa["istnieje"]:
		status_umowy = umowa["autenti_status"] or "niewysłana do Autenti"

	stara_reczna = {w.get("name"): w for w in doc.get("custom_zestaw") or [] if w.get("name")}
	doc.set("custom_zestaw", [])
	for w in nowe:
		wiersz = {
			"typ": w["typ"],
			"nazwa": w["nazwa"],
			"ilosc": w["ilosc"],
			"jednostka": w["jednostka"],
		}
		poprzedni = stara_reczna.get(w["name"]) if w["name"] else None
		if poprzedni is not None:
			wiersz["reczna_ilosc"] = poprzedni.get("reczna_ilosc") or 0
		doc.append("custom_zestaw", wiersz)
	for pole, wartosc in pola_ceny.items():
		doc.set(pole, wartosc)
	for pole, wartosc in zmiany_konfiguracji.items():
		doc.set(pole, wartosc)
	doc.save()

	if meta.has_field(POLE_EDYTOWANO) or meta.has_field(POLE_POWOD):
		pola_edycji: dict[str, Any] = {}
		if meta.has_field(POLE_EDYTOWANO):
			pola_edycji[POLE_EDYTOWANO] = now_datetime()
		if meta.has_field(POLE_POWOD):
			pola_edycji[POLE_POWOD] = powod
		frappe.db.set_value(DOCTYPE, deal, pola_edycji, update_modified=False)

	opis_snapshotu = _zapisz_snapshot(deal, wynik["netto"], powod, meta)

	etykiety = {p: (meta.get_label(p) or p) for p in zmienione_konfiguracje}
	try:
		zapisz_slad(
			deal,
			tekst_sladu_zestawu(
				roznice,
				cena_przed,
				cena_po,
				zmienione_konfiguracje,
				powod,
				status_umowy,
				etykiety=etykiety,
				snapshot=opis_snapshotu,
			),
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Volteo Zestaw: błąd zapisu śladu aktywności")

	stan = _stan(frappe.get_doc(DOCTYPE, deal))
	if stan["umowa"]["istnieje"]:
		wskazowka = _(MSG_PDF_REGENERUJ) if stan["umowa"]["mozna_regenerowac"] else _(MSG_PDF_ANEKS)
	else:
		wskazowka = ""
	return {**stan, "wskazowka_pdf": wskazowka}
