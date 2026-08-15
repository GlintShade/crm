"""Whitelisted API formularza „Kredyt” (doctype `Volteo Kredyt`).

`Volteo Kredyt` jest 1:1 z `CRM Deal` (`autoname: "field:deal"` — nazwa
dokumentu to nazwa szansy), analogicznie do `Volteo Umowa`
(`crm/api/umowa.py`, wzorzec skopiowany strukturalnie). Frontend woła te
endpointy WYŁĄCZNIE pełną kropkowaną ścieżką (`crm.api.kredyt.volteo_kredyt_*`)
— gołe nazwy metod działają tylko dla Server Scriptów, nie dla wywołań
`call()` frontendu na whitelisted API forka (patrz pułapka HTTP 417
udokumentowana przy `Volteo Umowa`/`AudytTab.vue`).

Formularz kredytowy jest wypełniany stopniowo przez przedstawiciela — tak
jak formularz umowy, niekompletny zapis jest poprawnym stanem roboczym
(`status="Roboczy"`), nie błędem; brakujące pola wracają w odpowiedzi, nigdy
nie blokują `volteo_kredyt_save`. Generowanie PDF-u jest tu jednak świadomie
SUROWSZE niż w `Volteo Umowa`: `volteo_kredyt_pdf` odmawia złożenia dokumentu,
dopóki formularz i dane kontaktowe kontaktu podstawowego nie są komplet —
decyzja właściciela, bo formularz kredytowy trafia do banku/pośrednika i
częściowy wydruk nie ma tam żadnej wartości roboczej.

Kwoty dochodu/zobowiązań (`_POLA_KWOTOWE_DATA`) są celowo polami Data
(string), nie Currency/Float — ten sam powód co gdzie indziej w tym
repozytorium (`None vs 0` w polach liczbowych): na zwykłym doctypie
nieustawiony Float/Currency czyta się jako `0`, nie do odróżnienia od
zadeklarowanego zera (np. „dochód współmałżonka: 0 zł”, co bank musi widzieć
inaczej niż „pole niewypełnione”). Trzymanie ich jako Data eliminuje tę
niejednoznaczność u źródła, kosztem walidacji po stronie serwera przy każdym
zapisie (`kwota_poprawna`/cyfry-only dla `liczba_osob_na_utrzymaniu`) zamiast
polegania na typie kolumny.

Formularz kredytowy nie ma żadnej integracji z Autenti — w odróżnieniu od
`Volteo Umowa` (wysyłka do e-podpisu od b45), ten dokument nie jest tu ani
wysyłany do podpisu, ani śledzony statusem podpisu; PDF trafia wyłącznie jako
prywatny załącznik `CRM Deal` do ręcznego dalszego obiegu.
"""

from typing import Any, NoReturn

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, getdate

from crm.api.umowa import _dane_kontaktu, _podstawowy_kontakt, _sprawdz_dostep_do_szansy, _sprawdz_role
from crm.volteo_kredyt import GRUPY_DOCHODU, brakujace_pola, kwota_poprawna
from crm.volteo_kredyt_pdf import zbuduj_kontekst_kredytu
from crm.volteo_kredyt_render import sciezka_szablonu_kredytu, zloz_kredyt
from crm.volteo_pipeline import OZE_RODZAJE

DOCTYPE = "Volteo Kredyt"

_DANE_POLA_DOZWOLONE = [
	"miejsce_urodzenia",
	"rodzaj_seria_numer_dokumentu",
	"data_wydania_dokumentu",
	"data_waznosci_dokumentu",
	"adres_zameldowania_taki_sam",
	"adres_zameldowania",
	"adres_korespondencji_taki_sam",
	"adres_korespondencji",
	"wyksztalcenie",
	"stan_cywilny",
	"liczba_osob_na_utrzymaniu",
	"kwota_800_plus",
	"dochod_wspolmalzonka",
	"zrodlo_dochodu_malzonka",
	"oplaty_miesieczne",
	"suma_zobowiazan",
	"numer_rachunku",
	"praca_wlaczone",
	"praca_forma",
	"praca_data_zatrudnienia",
	"praca_okres",
	"praca_okres_od",
	"praca_okres_do",
	"praca_nip",
	"praca_nazwa_zakladu",
	"praca_adres_telefon",
	"praca_kwota_dochodu",
	"emerytura_wlaczone",
	"emerytura_numer_swiadczenia",
	"emerytura_od_kiedy",
	"emerytura_kwota_dochodu",
	"renta_wlaczone",
	"renta_numer_swiadczenia",
	"renta_od_kiedy",
	"renta_kwota_dochodu",
	"dzialalnosc_wlaczone",
	"dzialalnosc_forma_opodatkowania",
	"dzialalnosc_forma_inna",
	"dzialalnosc_nip",
	"dzialalnosc_nazwa",
	"dzialalnosc_adres_telefon",
	"dzialalnosc_od_kiedy",
	"dzialalnosc_kwota_dochodu",
	"gospodarstwo_wlaczone",
	"gospodarstwo_nip",
	"gospodarstwo_od_kiedy",
	"gospodarstwo_kwota_dochodu",
	"inne_wlaczone",
	"inne_1_typ",
	"inne_1_kwota",
	"inne_2_typ",
	"inne_2_kwota",
]
"""Jedyne pola `Volteo Kredyt`, jakie `volteo_kredyt_save` przyjmuje od klienta.

Nigdy nie robimy ślepego `doc.update(dane)` z danych przesłanych przez
przeglądarkę — wszystko spoza tej listy jest po cichu odrzucane. `deal` i
`status` są tu celowo NIEOBECNE: `deal` ustala wyłącznie `volteo_kredyt_create`
(nazwa dokumentu), `status` liczy wyłącznie serwer z `brakujace_pola` po
każdym zapisie — klient nie może żadnego z nich nadpisać.
"""

_POLA_CHECKBOX = frozenset(
	{
		"praca_wlaczone",
		"emerytura_wlaczone",
		"renta_wlaczone",
		"dzialalnosc_wlaczone",
		"gospodarstwo_wlaczone",
		"inne_wlaczone",
	}
)
"""Sześć przełączników źródeł dochodu (pola Check, 0/1 Int) — koercja WYŁĄCZNIE
przez `cint`, nigdy `bool()`. Pułapka: `bool("0")` daje `True` w Pythonie, więc
string `"0"` przepuszczony bez koercji zapisałby się jako źródło włączone,
mimo że przedstawiciel go nie zaznaczył (ten sam błąd, którego unika
`Volteo Umowa` dla swoich pól zgody — patrz `crm/api/umowa.py`).
"""

_POLA_DATY = frozenset(
	{
		"data_wydania_dokumentu",
		"data_waznosci_dokumentu",
		"praca_data_zatrudnienia",
		"praca_okres_od",
		"praca_okres_do",
		"emerytura_od_kiedy",
		"renta_od_kiedy",
		"dzialalnosc_od_kiedy",
		"gospodarstwo_od_kiedy",
	}
)
"""Pola Date formularza — puste wejście (`None`/`""`) zapisuje się jako `None`,
niepuste jest walidowane przez `getdate` (rzuca czytelny komunikat po polsku
przy niepoprawnej dacie zamiast pozwolić Frappe wywalić się gołym wyjątkiem
frameworka przy `.save()`). `praca_okres_od`/`praca_okres_do` SĄ tu: to
kalendarzowe daty początku/końca umowy o pracę na czas określony — `praca_okres`
(Select) tylko wybiera, które z nich mają zastosowanie, nie zmienia ich typu.
"""

_POLA_KWOTOWE_DATA = frozenset(
	{
		"liczba_osob_na_utrzymaniu",
		"kwota_800_plus",
		"dochod_wspolmalzonka",
		"oplaty_miesieczne",
		"suma_zobowiazan",
		"praca_kwota_dochodu",
		"emerytura_kwota_dochodu",
		"renta_kwota_dochodu",
		"dzialalnosc_kwota_dochodu",
		"gospodarstwo_kwota_dochodu",
		"inne_1_kwota",
		"inne_2_kwota",
	}
)
"""Pola Data (string) niosące kwoty/liczby — patrz akapit o `None vs 0` w
docstringu modułu. Niepuste wartości muszą przejść `kwota_poprawna` (Decimal
parsowalny), poza `liczba_osob_na_utrzymaniu`, gdzie liczba osób wymaga
sprawdzenia cyfry-only (`_pole_kwotowe_poprawne` niżej) — dziesiętne „2.5
osoby” nie ma sensu, mimo że jako kwota parsowałoby się poprawnie.
"""

_ETYKIETY_POL: dict[str, str] = {
	"miejsce_urodzenia": "Miejsce urodzenia",
	"rodzaj_seria_numer_dokumentu": "Rodzaj, seria i numer dokumentu tożsamości",
	"data_wydania_dokumentu": "Data wydania dokumentu",
	"data_waznosci_dokumentu": "Data ważności dokumentu",
	"adres_zameldowania_taki_sam": "Adres zameldowania (taki sam jak zamieszkania)",
	"adres_zameldowania": "Adres zameldowania",
	"adres_korespondencji_taki_sam": "Adres korespondencyjny (taki sam jak zamieszkania)",
	"adres_korespondencji": "Adres korespondencyjny",
	"wyksztalcenie": "Wykształcenie",
	"stan_cywilny": "Stan cywilny",
	"liczba_osob_na_utrzymaniu": "Liczba osób na utrzymaniu",
	"kwota_800_plus": "Kwota świadczenia 800+",
	"dochod_wspolmalzonka": "Dochód współmałżonka",
	"zrodlo_dochodu_malzonka": "Źródło dochodu współmałżonka",
	"oplaty_miesieczne": "Miesięczne opłaty stałe",
	"suma_zobowiazan": "Suma zobowiązań kredytowych",
	"numer_rachunku": "Numer rachunku bankowego",
	"praca_wlaczone": "Zatrudnienie na umowę o pracę",
	"praca_forma": "Forma zatrudnienia",
	"praca_data_zatrudnienia": "Data zatrudnienia",
	"praca_okres": "Rodzaj umowy o pracę (okres)",
	"praca_okres_od": "Okres zatrudnienia — od",
	"praca_okres_do": "Okres zatrudnienia — do",
	"praca_nip": "NIP zakładu pracy",
	"praca_nazwa_zakladu": "Nazwa zakładu pracy",
	"praca_adres_telefon": "Adres i telefon zakładu pracy",
	"praca_kwota_dochodu": "Kwota dochodu z pracy",
	"emerytura_wlaczone": "Dochód z emerytury",
	"emerytura_numer_swiadczenia": "Numer świadczenia emerytalnego",
	"emerytura_od_kiedy": "Emerytura — od kiedy",
	"emerytura_kwota_dochodu": "Kwota emerytury",
	"renta_wlaczone": "Dochód z renty",
	"renta_numer_swiadczenia": "Numer świadczenia rentowego",
	"renta_od_kiedy": "Renta — od kiedy",
	"renta_kwota_dochodu": "Kwota renty",
	"dzialalnosc_wlaczone": "Dochód z działalności gospodarczej",
	"dzialalnosc_forma_opodatkowania": "Forma opodatkowania działalności",
	"dzialalnosc_forma_inna": "Inna forma opodatkowania (opis)",
	"dzialalnosc_nip": "NIP działalności",
	"dzialalnosc_nazwa": "Nazwa działalności",
	"dzialalnosc_adres_telefon": "Adres i telefon działalności",
	"dzialalnosc_od_kiedy": "Działalność — od kiedy",
	"dzialalnosc_kwota_dochodu": "Kwota dochodu z działalności",
	"gospodarstwo_wlaczone": "Dochód z gospodarstwa rolnego",
	"gospodarstwo_nip": "NIP gospodarstwa",
	"gospodarstwo_od_kiedy": "Gospodarstwo — od kiedy",
	"gospodarstwo_kwota_dochodu": "Kwota dochodu z gospodarstwa",
	"inne_wlaczone": "Inne źródło dochodu",
	"inne_1_typ": "Inne źródło dochodu 1 — typ",
	"inne_1_kwota": "Inne źródło dochodu 1 — kwota",
	"inne_2_typ": "Inne źródło dochodu 2 — typ",
	"inne_2_kwota": "Inne źródło dochodu 2 — kwota",
}
"""Etykiety PL dla WSZYSTKICH pól `_DANE_POLA_DOZWOLONE` — nadzbiór tego, co
`crm.volteo_kredyt.brakujace_pola` może kiedykolwiek zwrócić, żeby komunikat
blokujący PDF (`volteo_kredyt_pdf`) zawsze miał czytelną nazwę pola, nawet gdy
zbiór pól wymaganych przez rdzeń się zmieni."""

_PREFILL_ETYKIETY: dict[str, str] = {
	"pesel": "PESEL",
	"imiona": "Imię/imiona",
	"nazwisko": "Nazwisko",
	"telefon": "Telefon",
	"email": "E-mail",
	"kod_pocztowy": "Kod pocztowy",
	"miejscowosc": "Miejscowość",
	"ulica": "Ulica",
	"nr_domu": "Nr domu",
	# `nr_lokalu` celowo POMINIĘTY: klient mieszkający w domu jednorodzinnym legalnie
	# nie ma numeru lokalu, więc nie może to blokować generowania PDF-u.
}
"""Etykiety PL dziewięciu WYMAGANYCH pól bloku `prefill` — używane WYŁĄCZNIE do
komunikatu `volteo_kredyt_pdf`, gdy dane kontaktu podstawowego są niekomplet."""


def _sprawdz_rodzaj_oze(deal_doc: "frappe.model.document.Document") -> None:
	"""Formularz kredytowy dotyczy wyłącznie linii OZE — `custom_rodzaj_umowy` szansy
	musi być jedną z wartości `crm.volteo_pipeline.OZE_RODZAJE`. Czyste Powietrze ma
	własny, odrębny rurociąg (`PIPELINE_CP`) bez etapu kredytowego, więc dostęp do
	tego formularza dla takiej szansy jest błędem danych szansy, nie stanem
	roboczym formularza — stąd osobna, jawna bramka zamiast cichego pustego wyniku.
	"""
	if deal_doc.get("custom_rodzaj_umowy") not in OZE_RODZAJE:
		frappe.throw(
			_(
				"Formularz kredytowy dotyczy wyłącznie linii OZE (Fotowoltaika, "
				"Fotowoltaika + Magazyn, Magazyn energii) — ustaw „Rodzaj umowy” na "
				"szansie sprzedaży na jedną z tych wartości."
			)
		)


def _blad_ogolny() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd formularza")
	frappe.throw(_("Wystąpił błąd podczas zapisu formularza kredytowego."))


def _blad_generowania_pdf() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd generowania PDF")
	frappe.throw(_("Wystąpił błąd podczas generowania PDF-u formularza kredytowego. Spróbuj ponownie."))


def _blad_brakujacego_szablonu() -> NoReturn:
	"""Wbudowany szablon PDF-u (`crm/szablony/formularz_kredytowy.pdf`) nie wczytał
	się z dysku. To awaria WDROŻENIA (plik nie trafił do obrazu albo jest
	uszkodzony), nie błąd użytkownika ani danych szansy — patrz analogiczny
	komunikat w `crm.api.umowa._blad_brakujacego_szablonu`.
	"""
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: brak wbudowanego szablonu PDF")
	frappe.throw(
		_("Szablon PDF-u formularza kredytowego nie jest dostępny w tej instalacji. Skontaktuj się z administratorem systemu.")
	)


def _blad_zapisu_pliku() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Kredyt: błąd zapisu pliku PDF")
	frappe.throw(_("PDF wygenerowano, ale nie udało się go zapisać. Spróbuj ponownie."))


def _pobierz_kredyt(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca dokument `Volteo Kredyt` dla szansy, jeśli istnieje — inaczej `None`.

	Nazwa dokumentu jest tożsama z nazwą szansy (`autoname: field:deal`), więc
	sprawdzenie istnienia i pobranie odbywa się po tym samym kluczu.
	"""
	if frappe.db.exists(DOCTYPE, deal):
		return frappe.get_doc(DOCTYPE, deal)
	return None


def _prefill(deal_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Składa blok `prefill`: dane kontaktu podstawowego szansy, wyłącznie do
	odczytu przez zakładkę (formularz kredytowy nigdy nie zapisuje z powrotem
	do `Contact`). Reużywa `crm.api.umowa._podstawowy_kontakt`/`_dane_kontaktu`
	(spacer po kontaktach szansy + odczyt `Contact Email`/`Contact Phone`) zamiast
	duplikować tę logikę — jedyne co robimy tutaj to re-keying na nazwy pól
	formularza kredytowego, inne niż nazwy pól `Volteo Umowa`, które `_dane_kontaktu`
	natywnie zwraca.
	"""
	kontakt = _podstawowy_kontakt(deal_doc)
	dane = _dane_kontaktu(kontakt)
	return {
		"pesel": dane.get("custom_pesel") or "",
		"imiona": dane.get("first_name") or "",
		"nazwisko": dane.get("last_name") or "",
		"telefon": dane.get("mobile_no") or "",
		"email": dane.get("email") or "",
		"kod_pocztowy": dane.get("custom_kod_pocztowy") or "",
		"miejscowosc": dane.get("custom_miasto") or "",
		"ulica": dane.get("custom_ulica") or "",
		"nr_domu": dane.get("custom_nr_domu") or "",
		"nr_lokalu": dane.get("custom_nr_mieszkania") or "",
	}


def _kredyt_do_dict(kredyt_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Spłaszcza dokument `Volteo Kredyt` do bloku `kredyt` odpowiedzi."""
	wynik = {pole: kredyt_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE}
	wynik["name"] = kredyt_doc.name
	wynik["deal"] = kredyt_doc.deal
	wynik["status"] = kredyt_doc.status
	return wynik


def _data_lub_none(pole: str, wartosc: Any) -> Any:
	"""Konwertuje wejście Date na coś, co `Document.set` przyjmie — puste wejście
	(`None`/`""`) daje `None` (pole czyszczone), niepuste jest walidowane przez
	`getdate`, rzucając czytelny komunikat po polsku zamiast surowego wyjątku
	frameworka przy `.save()`.
	"""
	if wartosc is None or wartosc == "":
		return None
	try:
		return getdate(wartosc)
	except Exception:
		frappe.throw(_("Nieprawidłowa data w polu „{0}”.").format(_ETYKIETY_POL.get(pole, pole)))


def _pole_kwotowe_poprawne(pole: str, tekst: str) -> bool:
	"""`liczba_osob_na_utrzymaniu` to LICZBA osób (cyfry-only), nie kwota — reszta
	pól `_POLA_KWOTOWE_DATA` idzie przez `kwota_poprawna` (Decimal parsowalny).
	"""
	if pole == "liczba_osob_na_utrzymaniu":
		return tekst.isdigit()
	return kwota_poprawna(tekst)


def _wyczysc_nieaktywne_grupy_dochodu(kredyt_doc: "frappe.model.document.Document") -> None:
	"""Obrona w głąb: dla każdego przełącznika `GRUPY_DOCHODU`, który jest
	WYŁĄCZONY po zastosowaniu allowlisty, czyści (`None`) wszystkie pola jego
	grupy na dokumencie. Bez tego nieaktualny payload przeglądarki (np. stara
	karta z otwartym formularzem, w której rep odznaczył „Emerytura” już PO
	stronie klienta, ale request zawierał tylko zmienione pole przełącznika)
	mógłby zostawić martwe dane dochodowe źródła, które użytkownik jawnie wyłączył.
	"""
	for przelacznik, pola_grupy in GRUPY_DOCHODU.items():
		if not cint(kredyt_doc.get(przelacznik)):
			for pole_grupy in pola_grupy:
				kredyt_doc.set(pole_grupy, None)


def _usun_stare_pliki_kredytu(deal: str, nazwa_pliku: str) -> None:
	"""Analogiczne do `crm.api.umowa._usun_stare_pdfy_umowy` — usuwa wszystkie
	wcześniejsze rekordy `File` z PDF-em formularza kredytowego TEJ szansy.

	Frappe nie nadpisuje pliku o istniejącej nazwie przy kolejnym `insert()` —
	dokleja losowy sufiks tuż przed rozszerzeniem, więc dopasowanie po
	dokładnej nazwie niczego by nie znalazło po drugim wywołaniu; zamiast tego
	dopasowujemy PREFIKS `nazwa_pliku` bez rozszerzenia + dowolny sufiks + `.pdf`.

	Bezpieczeństwo zakresu — filtr łączy TRZY warunki jednocześnie:
	`attached_to_doctype == "CRM Deal"`, `attached_to_name == deal` (żaden
	załącznik INNEJ szansy nie może zostać złapany) i `file_name LIKE
	"<prefiks tej szansy>%.pdf"` (inne załączniki TEJ SAMEJ szansy, np. PDF
	umowy, mają inny prefiks nazwy i nie pasują). Znaki `%`/`_` w nazwie
	szansy są eskejpowane, żeby nie działały jako wildcardy LIKE. Nieudane
	sprzątnięcie NIE MOŻE zablokować wygenerowania nowego PDF-u — błąd trafia
	do `frappe.log_error` i przetwarzanie idzie dalej.
	"""
	prefiks = nazwa_pliku[: -len(".pdf")]  # "Formularz-kredytowy-<szansa z myślnikami zamiast ukośników>"
	wzorzec = prefiks.replace("%", r"\%").replace("_", r"\_") + "%.pdf"
	stare_pliki = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"file_name": ["like", wzorzec],
		},
		pluck="name",
	)
	for nazwa in stare_pliki:
		try:
			frappe.delete_doc("File", nazwa, ignore_permissions=True, delete_permanently=True)
		except Exception:
			frappe.log_error(title="volteo_kredyt_pdf: nie udało się usunąć starego pliku PDF formularza kredytowego")


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_kredyt_get(deal: str) -> dict[str, Any]:
	"""Zwraca istniejący rekord `Volteo Kredyt` (jeśli jest), `prefill` kontaktu
	i listę brakujących pól. Celowo BEZ bramki OZE (`_sprawdz_rodzaj_oze`) —
	inaczej niż `create`/`save`/`pdf`: jeśli rep przełączy „Rodzaj umowy” szansy
	na Czyste Powietrze podczas gdy zakładka Kredyt jest już otwarta, `get`
	nadal ma zwrócić dane, żeby UI mogło się spokojnie ukryć (stan zakładki),
	zamiast wywalić się błędem na zwykłym odświeżeniu widoku.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	kredyt_doc = _pobierz_kredyt(deal)
	dane_do_walidacji = {pole: kredyt_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE} if kredyt_doc else {}

	return {
		"kredyt": _kredyt_do_dict(kredyt_doc) if kredyt_doc else None,
		"prefill": _prefill(deal_doc),
		"brakujace_pola": brakujace_pola(dane_do_walidacji),
	}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_kredyt_create(deal: str) -> dict[str, Any]:
	"""Tworzy `Volteo Kredyt` dla szansy. Idempotentne: jeśli rekord już istnieje
	(np. podwójne kliknięcie), zwraca istniejący zamiast rzucać
	`DuplicateEntryError` — nazwa dokumentu jest nazwą szansy, więc naiwny
	`insert()` wybuchłby przy powtórnym wywołaniu.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	kredyt_doc = _pobierz_kredyt(deal)
	if kredyt_doc is None:
		try:
			kredyt_doc = frappe.get_doc({"doctype": DOCTYPE, "deal": deal, "status": "Roboczy"})
			kredyt_doc.insert()
		except frappe.DuplicateEntryError:
			# Wyścig: inna sesja/kliknięcie zdążyło wstawić rekord między sprawdzeniem a insertem.
			kredyt_doc = frappe.get_doc(DOCTYPE, deal)
		except Exception:
			_blad_ogolny()

	dane_do_walidacji = {pole: kredyt_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE}
	return {
		"kredyt": _kredyt_do_dict(kredyt_doc),
		"prefill": _prefill(deal_doc),
		"brakujace_pola": brakujace_pola(dane_do_walidacji),
	}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_kredyt_save(deal: str, dane: dict[str, Any]) -> dict[str, Any]:
	"""Zapisuje formularz kredytowy z allowlistą pól i koercją typów.

	Niekompletny zapis jest poprawnym stanem roboczym (przedstawiciel wypełnia
	formularz stopniowo) — brakujące pola NIE blokują zapisu, tylko ustawiają
	`status="Roboczy"` i trafiają do odpowiedzi, żeby UI mógł je podświetlić.
	Dopiero komplet danych daje `status="Kompletny"`. Blokada dotyczy wyłącznie
	generowania PDF-u (`volteo_kredyt_pdf`), nie zapisu.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	if not isinstance(dane, dict):
		frappe.throw(_("Nieprawidłowy format danych formularza."))

	kredyt_doc = _pobierz_kredyt(deal)
	if kredyt_doc is None:
		frappe.throw(_("Najpierw utwórz formularz kredytowy dla tej szansy sprzedaży."))

	for pole in _DANE_POLA_DOZWOLONE:
		if pole not in dane:
			continue
		wartosc = dane[pole]
		if pole in _POLA_CHECKBOX:
			# Jawna koercja przez cint — NIGDY bool(), bo bool("0") == True w Pythonie.
			wartosc = cint(wartosc)
		elif pole in _POLA_DATY:
			wartosc = _data_lub_none(pole, wartosc)
		elif pole in _POLA_KWOTOWE_DATA:
			tekst = "" if wartosc is None else str(wartosc).strip()
			if tekst and not _pole_kwotowe_poprawne(pole, tekst):
				frappe.throw(_("Nieprawidłowa wartość w polu „{0}”.").format(_ETYKIETY_POL.get(pole, pole)))
			wartosc = tekst
		kredyt_doc.set(pole, wartosc)

	_wyczysc_nieaktywne_grupy_dochodu(kredyt_doc)

	braki = brakujace_pola({pole: kredyt_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE})
	kredyt_doc.status = "Roboczy" if braki else "Kompletny"

	try:
		kredyt_doc.save()
	except Exception:
		_blad_ogolny()

	return {
		"kredyt": _kredyt_do_dict(kredyt_doc),
		"prefill": _prefill(deal_doc),
		"brakujace_pola": braki,
	}


@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def volteo_kredyt_pdf(deal: str) -> dict[str, Any]:
	"""Generuje PDF formularza kredytowego dla szansy sprzedaży i zapisuje go jako
	prywatny plik podpięty do `CRM Deal`. Zwraca `{"file_url": ..., "file_name": ...}`.

	W odróżnieniu od `volteo_umowa_pdf` (który generuje niekompletny PDF bez
	blokady — dokument jest roboczy, wracany do edycji), generowanie tutaj jest
	CELOWO zablokowane, dopóki: (1) formularz `Volteo Kredyt` nie ma żadnych
	brakujących pól wg `crm.volteo_kredyt.brakujace_pola`, i (2) wszystkie
	dziesięć pól `prefill` kontaktu podstawowego szansy nie są wypełnione —
	decyzja właściciela: ten PDF trafia do banku/pośrednika kredytowego, więc
	częściowy wydruk nie ma tam żadnej wartości roboczej.

	Rurociąg OZE (`crm.volteo_pipeline.PIPELINE_OZE`) nie ma etapu „Kredyt” —
	w odróżnieniu od `volteo_umowa_pdf` ten endpoint celowo NIE wywołuje
	`crm.api.pipeline.advance_deal_status`: wygenerowanie formularza kredytowego
	nie przesuwa szansy w rurociągu.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	_sprawdz_rodzaj_oze(deal_doc)

	kredyt_doc = _pobierz_kredyt(deal)
	if kredyt_doc is None:
		frappe.throw(_("Najpierw wypełnij formularz kredytowy dla tej szansy sprzedaży."))

	braki = brakujace_pola({pole: kredyt_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE})
	if braki:
		etykiety = ", ".join(_ETYKIETY_POL.get(pole, pole) for pole in braki)
		frappe.throw(_("Formularz kredytowy jest niekompletny — uzupełnij pola: {0}.").format(etykiety))

	prefill = _prefill(deal_doc)
	brakujace_prefill = [klucz for klucz in _PREFILL_ETYKIETY if not prefill.get(klucz)]
	if brakujace_prefill:
		etykiety = ", ".join(_PREFILL_ETYKIETY[klucz] for klucz in brakujace_prefill)
		frappe.throw(
			_(
				"Dane kontaktu podstawowego są niekomplet — uzupełnij na karcie kontaktu: "
				"{0}."
			).format(etykiety)
		)

	try:
		szablon_pdf = sciezka_szablonu_kredytu().read_bytes()
	except OSError:
		_blad_brakujacego_szablonu()

	try:
		kontekst = zbuduj_kontekst_kredytu(
			kredyt=_kredyt_do_dict(kredyt_doc),
			kontakt=prefill,
			dzis=getdate(),
		)
		pdf_bytes = zloz_kredyt(kontekst, szablon_pdf)
	except Exception:
		_blad_generowania_pdf()

	nazwa_pliku = f"Formularz-kredytowy-{deal.replace('/', '-')}.pdf"
	_usun_stare_pliki_kredytu(deal, nazwa_pliku)
	try:
		plik = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": nazwa_pliku,
				"attached_to_doctype": "CRM Deal",
				"attached_to_name": deal,
				"is_private": 1,
				"content": pdf_bytes,
			}
		)
		plik.insert(ignore_permissions=True)
	except Exception:
		_blad_zapisu_pliku()

	return {"file_url": plik.file_url, "file_name": plik.file_name}
