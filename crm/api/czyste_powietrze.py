"""Whitelisted API kalkulatora z rozdzieleniem dostępu do kosztów wewnętrznych.

Przeglądarka otrzymuje z katalogu wyłącznie dane potrzebne do wyrenderowania formularza.
Obliczenia i dane kosztowe są pobierane na serwerze, a blok ``wewnetrzne`` trafia tylko
do administratorów. Mapowanie traktuje limit równy zero jako ``None`` — przekazanie zera
do rdzenia oznaczałoby limit dotacji równy zero, a nie brak limitu.
"""

import json
from decimal import Decimal
from typing import Any, NoReturn

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import flt

from crm.api import volteo_ma_linie, volteo_poziom_prowizji, volteo_widzi_prowizje
from crm.czyste_powietrze.mapowanie import (
	katalog_z_wierszy,
	limity_z_wierszy,
	stale_z_dokumentu,
)
from crm.czyste_powietrze.obliczenia import (
	CPDaneNiekompletne,
	CPNiedozwolonaKombinacja,
	CPPozycjaNieaktywna,
	baza_pracy,
	oblicz_oferte,
)
from crm.koszty.rdzen import zbuduj_snapshot_cp
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad

KALKULATOR_ROLE = {"Volteo D2D Sales", "Volteo Backend", "Volteo Core Admin", "System Manager"}
ADMIN_ROLE = {"Volteo Core Admin", "System Manager"}

_POZYCJE_POLA = ["kod", "nazwa", "kategoria", "jednostka", "aktywny"]
_POZYCJE_POLA_KALKULATORA = [
	"kod",
	"nazwa",
	"kategoria",
	"jednostka",
	"cena_netto",
	"dotacja_podstawowy",
	"dotacja_podwyzszony",
	"dotacja_najwyzszy",
	"limit_podstawowy",
	"limit_podwyzszony",
	"limit_najwyzszy",
	"prowizja",
	# Nadprowizje Managera/Partnera (ops#46 schema, ops#47 rdzeń) -- katalog_z_wierszy
	# / _wymagane wymagają obu pól na każdym wierszu; brak ich tutaj rzuca
	# CPBladMapowania "Brak wymaganego pola: nadprowizja_manager" dla KAŻDEGO wywołania
	# kalkulatora, nie tylko przy nadprowizji > 0.
	"nadprowizja_manager",
	"nadprowizja_partner",
	"koszt_proenergy",
	"koszt_staly",
	"aktywny",
]
_LIMITY_POLA = ["poziom", "standard", "status_limitu", "limit_laczny"]

# Etykiety grup zakresu prac -- MUSZĄ być identyczne z nazwami budowanymi w rdzeniu
# (obliczenia.py, słownik _grupy_dane w oblicz_oferte) i z ops/crm-zestaw-cp.py, bo
# stamtąd pochodzi wynik["grupy"][i]["nazwa"] użyte niżej wprost. Trzymane tu osobno tylko
# jako fallback dla wierszy niebędących cwu, których "typ" pochodzi z nazwy_kategorii linii
# -- patrz _typ_grupy_dla_linii().
_KATEGORIA_TYP = {
	"zrodlo": "Źródło ciepła",
	"co": "Centralne Ogrzewanie i Ciepła Woda Użytkowa",
	"termo": "Termomodernizacja",
}


def _typ_grupy_dla_linii(kod_pozycji: str, kod_kategorii: str) -> str:
	"""Zamienia kategorię pozycji na etykietę GRUPY do BOM-u (custom_zestaw.typ), tak by
	widok Zestaw grupował się spójnie z wynik["grupy"]. "cwu" ma w katalogu
	kategoria="zrodlo" (patrz obliczenia.py), ale w prezentacji programu dzieli jeden
	limit z centralnym ogrzewaniem, więc dostaje etykietę grupy "co", nie "zrodlo" --
	to samo przegrupowanie co w rdzeniu, powtórzone tu tylko dla wiersza BOM. Nieznany
	kod przechodzi bez zmian zamiast wywalać zapis szansy."""
	if kod_pozycji == "cwu":
		return _KATEGORIA_TYP["co"]
	return _KATEGORIA_TYP.get(kod_kategorii, kod_kategorii)


def _powierzchnia_do_zapisu(wartosc: Any) -> Decimal | None:
	"""Bezpiecznie zamienia powierzchnię (z przeglądarki może przyjść jako string) na liczbę
	do zapisu w custom_cp_powierzchnia_m2 (Float). Rdzeń już ją zwalidował własnym _decimal()
	wewnątrz oblicz_oferte, więc w praktyce ta funkcja nie powinna nigdy zwrócić None na tym
	etapie — to wyłącznie druga linia obrony: błędna wartość ma zostawić pole puste, a nie
	wywalić całe tworzenie szansy."""
	try:
		wynik = Decimal(str(wartosc))
	except (ArithmeticError, TypeError, ValueError):
		return None
	if not wynik.is_finite():
		return None
	return wynik


# Prace powierzchniowe, które MOGĄ mieć ręcznie wpisaną powierzchnię zamiast automatycznego
# przeliczenia (powierzchnia budynku x mnożnik) -- patrz obliczenia.py::_powierzchnia_pracy.
# "drzwi" świadomie POMINIĘTE: liczy się zawsze wpisaną ilością sztuk, nie ma trybu
# automatycznego, więc nie jest "ręcznym nadpisaniem" w tym sensie.
_PRACE_M2_RECZNE = ("elewacja", "strop", "dach", "okna")


def _czy_reczna_ilosc(kod: str, wejscie: dict[str, Any]) -> bool:
	"""Rozpoznaje, czy dana pozycja BOM pochodzi z ręcznie wpisanej powierzchni, a nie z
	automatycznego przeliczenia. Frontend wysyła m2=None w trybie automatycznym i surowy
	wpisany string w trybie ręcznym (patrz obliczenia.py::_powierzchnia_pracy) -- stąd
	sprawdzenie, że m2 jest niepustym stringiem, a nie samo "m2 is not None". Źródło
	ciepła, CWU i grzejniki nigdy nie są "ręczną powierzchnią" w tym sensie, więc kody
	spoza _PRACE_M2_RECZNE (w tym "drzwi") zawsze dają False.
	"""
	# Pułapka wariantów materiału (obliczenia.py::_kod_katalogowy): linie termo z wariantem
	# (np. "strop_piana") docierają tu z linia["kod"] JUŻ podmienionym na kod wariantu, który
	# nie jest kluczem w _PRACE_M2_RECZNE (ta krotka trzyma tylko kody BAZOWE). Bez tej
	# normalizacji funkcja po cichu zwróciłaby False dla każdej ręcznie wpisanej powierzchni
	# stropu/dachu -- reczna_ilosc zapisałoby się jako 0 mimo ręcznego wpisu handlowca.
	kod = baza_pracy(kod)
	if kod not in _PRACE_M2_RECZNE:
		return False
	prace = wejscie.get("prace")
	if not isinstance(prace, dict):
		return False
	dane_pracy = prace.get(kod)
	if not isinstance(dane_pracy, dict):
		return False
	wartosc_m2 = dane_pracy.get("m2")
	return isinstance(wartosc_m2, str) and wartosc_m2.strip() != ""


def _cp_zrodlo_pola_do_zapisu(wejscie: dict[str, Any]) -> dict[str, Any]:
	"""Wyciąga surowe kody źródła ciepła / CWU / grzejników z wejścia kalkulatora do
	zapisu w polach nagłówkowych szansy. Rdzeń (_wynik_kalkulatora -> oblicz_oferte) już
	zwalidował te wartości -- gdyby były niepoprawne, wywołanie rzuciłoby błąd, zanim
	kod dotarłby do tego miejsca. Zapisujemy surowe kody katalogowe (np. "pompa_ciepla",
	"grzejnik_co"), spójnie z custom_cp_poziom/custom_cp_standard, które też trzymają
	surowe kody, nie etykiety czytelne dla człowieka.
	"""
	zrodlo_ciepla = wejscie.get("zrodlo_ciepla")
	typ_grzejnikow = wejscie.get("typ_grzejnikow")
	ilosc_grzejnikow = 0
	if typ_grzejnikow is not None:
		try:
			ilosc_grzejnikow = int(Decimal(str(wejscie.get("ilosc_grzejnikow"))))
		except (ArithmeticError, TypeError, ValueError):
			ilosc_grzejnikow = 0
	return {
		"custom_cp_zrodlo_ciepla": zrodlo_ciepla,
		"custom_cp_cwu": 1 if wejscie.get("cwu") else 0,
		"custom_cp_typ_grzejnikow": typ_grzejnikow,
		# custom_cp_ilosc_grzejnikow jest Int na zwykłym doctype -- nieustawiona kolumna
		# i tak czyta się jako 0 (NOT NULL DEFAULT 0), więc "0 grzejników" i "brak
		# grzejników" są nierozróżnialne. Rozważone świadomie i zaakceptowane: oba
		# znaczą dokładnie to samo (brak grzejników na szansie), więc -- w odróżnieniu
		# od pól typu moc/powierzchnia/gwarancja -- nie potrzeba tu osobnego markera
		# pustki jak przy Singles (patrz CLAUDE.md "None vs 0 w polach liczbowych").
		"custom_cp_ilosc_grzejnikow": ilosc_grzejnikow,
	}


def _czy_admin(roles: set[str]) -> bool:
	"""Sprawdza osobno prawo do oglądania kosztów i marży."""
	return bool(ADMIN_ROLE & roles)


def _prowizje_wedlug_poziomu(prowizje: dict[str, Any], poziom: str) -> dict[str, Any]:
	"""Przycina publiczny blok wynik["prowizje"] do tego, co wolno zobaczyć na
	danym poziomie prowizyjnym (issue #48, schema ops#46, rdzeń ops#47).
	Buduje NOWY dict, nie mutuje wejścia (konwencja niemutowalności repo).

	- "Handlowiec": tylko własna prowizja bazowa, celowo BEZ klucza "suma" --
	  zachowuje dzisiejszy jednowierszowy UX (przed tą zmianą "prowizje" miało
	  po stronie przeglądarki tylko ten jeden klucz).
	- "Manager": bazowa + nadprowizja managera + suma tych DWÓCH -- policzona
	  TU OD NOWA jako handlowiec + manager, nigdy nie brana z trzypoziomowego
	  wynik["prowizje"]["suma"] (który zawiera też nadprowizję partnera --
	  stawka/kwota partnera nie może wyciec managerowi tą drogą).
	- "Partner": pełny, niezmieniony 4-kluczowy dict.
	"""
	if poziom == "Partner":
		return dict(prowizje)
	if poziom == "Manager":
		handlowiec = prowizje["handlowiec"]
		nadprowizja_manager = prowizje["nadprowizja_manager"]
		return {
			"handlowiec": handlowiec,
			"nadprowizja_manager": nadprowizja_manager,
			"suma": handlowiec + nadprowizja_manager,
		}
	# "Handlowiec" -- fail-safe domyślne z volteo_poziom_prowizji, celowo bez
	# klucza "suma".
	return {"handlowiec": prowizje["handlowiec"]}


def _blad_ogolny() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo CP: błąd kalkulatora")
	frappe.throw(_("Wystąpił błąd podczas obliczania oferty."))


@frappe.whitelist()
def volteo_cp_pozycje() -> dict[str, Any]:
	"""Zwraca bezpieczne dane katalogu do wyświetlenia w formularzu."""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)
	if not volteo_ma_linie("Czyste Powietrze"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)
	wiersze = frappe.get_all(
		"Volteo CP Pozycja",
		fields=_POZYCJE_POLA,
		ignore_permissions=True,
	)
	pozycje = [
		{
			"kod": wiersz["kod"],
			"nazwa": wiersz["nazwa"],
			"kategoria": wiersz["kategoria"],
			"jednostka": wiersz["jednostka"],
			"aktywny": bool(wiersz["aktywny"]),
		}
		for wiersz in wiersze
	]
	stale = frappe.db.get_singles_dict("Volteo CP Stale")
	# Udostępniamy wyłącznie heurystyki formularza, aby nie ujawnić prowizji ani innych stałych.
	# None oznacza brak automatycznego obliczania i umożliwia ręczne wprowadzenie.
	return {
		"pozycje": pozycje,
		"mnozniki": {
			"elewacja": stale.get("mnoznik_elewacja"),
			"strop": stale.get("mnoznik_strop"),
			"dach": stale.get("mnoznik_dach"),
			"okna": stale.get("mnoznik_okna"),
			"okna_od_elewacji": stale.get("mnoznik_okna_od_elewacji"),
		},
		"m2_na_drzwi": stale.get("m2_na_drzwi"),
	}


def _wynik_kalkulatora(
	wejscie: dict[str, Any],
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]], dict[str, str]]:
	"""Pobiera katalog/limity/stałe i liczy ofertę przez wspólny rdzeń.

	Wspólna ścieżka dla ``volteo_cp_calc`` i ``volteo_cp_create_deal``, żeby oba
	wywołania liczyły identycznie. Zwraca surowy wynik (z blokiem ``wewnetrzne``),
	zmapowane limity termomodernizacji (aby wywołujący mógł sprawdzić status limitu
	bez ponownego odpytywania bazy) oraz mapę kod -> nazwa czytelna pozycji katalogowej.

	Mapa nazw jest budowana z surowych wierszy katalogu, zanim trafią do
	``katalog_z_wierszy`` — ta funkcja waliduje obecność "nazwa" (patrz
	``mapowanie._wymagane``), ale nie przenosi jej do struktury zwracanej rdzeniowi, bo
	``oblicz_oferte`` jej nie potrzebuje. ``_POZYCJE_POLA_KALKULATORA`` już zawiera
	"nazwa", więc nie jest potrzebne dodatkowe zapytanie do bazy.
	"""
	pozycje = frappe.get_all(
		"Volteo CP Pozycja",
		fields=_POZYCJE_POLA_KALKULATORA,
		ignore_permissions=True,
	)
	limity_wiersze = frappe.get_all(
		"Volteo CP Limity",
		fields=_LIMITY_POLA,
		ignore_permissions=True,
	)
	stale = frappe.db.get_singles_dict("Volteo CP Stale")
	limity = limity_z_wierszy(limity_wiersze)
	nazwy = {
		wiersz["kod"]: wiersz["nazwa"]
		for wiersz in pozycje
		if wiersz.get("kod") and wiersz.get("nazwa")
	}
	wynik = oblicz_oferte(
		wejscie,
		katalog_z_wierszy(pozycje),
		limity,
		stale_z_dokumentu(stale),
	)
	return wynik, limity, nazwy


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_cp_calc(wejscie: dict[str, Any]) -> dict[str, Any]:
	"""Oblicza ofertę i usuwa dane kosztowe dla użytkowników niebędących adminami."""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)
	if not volteo_ma_linie("Czyste Powietrze"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	try:
		wynik, _limity, _nazwy = _wynik_kalkulatora(wejscie)
		czy_moze_widziec_koszty = _czy_admin(role_uzytkownika)
		if not czy_moze_widziec_koszty:
			# Ten jeden pop celowo usuwa też rozbicie kosztów/prowizji per pozycja
			# (wynik["wewnetrzne"]["linie"]) wprowadzone w obliczenia.py — wszystkie dane
			# kosztowe żyją wyłącznie wewnątrz poddrzewa "wewnetrzne".
			wynik.pop("wewnetrzne", None)
			# V6 (issue #48, ops#46/#47): warstwa prowizji nad V5. custom_widzi_prowizje
			# WYGRYWA na KAŻDYM poziomie -- wyłączona, usuwa prowizję CAŁKOWICIE (obie
			# ścieżki: legacy "prowizja_handlowa" i publiczne "prowizje"), niezależnie
			# od custom_poziom_prowizji. Włączona (V5 default), handlowiec nadal widzi
			# zagregowaną prowizję w zwiniętym okienku „Informacje dodatkowe" -- ale
			# "prowizje" jest teraz przycinane do poziomu prowizyjnego wywołującego
			# (Handlowiec/Manager/Partner), żeby nadprowizja Managera/Partnera nie
			# przeciekła niżej niż powinna. Koszty i marża nadal wyłącznie w
			# "wewnetrzne", usuniętym wyżej dla każdego nie-admina bez wyjątku.
			if not volteo_widzi_prowizje():
				wynik.pop("prowizja_handlowa", None)
				wynik.pop("prowizje", None)
			else:
				wynik["prowizje"] = _prowizje_wedlug_poziomu(wynik["prowizje"], volteo_poziom_prowizji())
		return wynik
	except (CPNiedozwolonaKombinacja, CPPozycjaNieaktywna, CPDaneNiekompletne) as blad:
		frappe.throw(_(str(blad)))
	except Exception:
		_blad_ogolny()


def _imie_nazwisko_kontaktu(kontakt: str) -> str:
	"""Pobiera imię i nazwisko z kontaktu; rzuca czytelny błąd, gdy kontakt nie istnieje."""
	if not frappe.has_permission("Contact", ptype="read", doc=kontakt):
		frappe.throw(_("Brak dostępu do wybranego kontaktu."), frappe.PermissionError)
	dane = frappe.db.get_value("Contact", kontakt, ["first_name", "last_name"], as_dict=True)
	if not dane:
		frappe.throw(_("Wybrany kontakt nie istnieje."))
	imie_nazwisko = " ".join(filter(None, [dane.first_name, dane.last_name])).strip()
	if not imie_nazwisko:
		frappe.throw(_("Wybrany kontakt nie ma podanego imienia i nazwiska."))
	return imie_nazwisko


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_cp_create_deal(wejscie: dict[str, Any], contact: str) -> dict[str, Any]:
	"""Przelicza ofertę Czyste Powietrze na serwerze i zapisuje wyłącznie ``CRM Deal``.

	Kwoty klienta nigdy nie są przyjmowane — wycena jest liczona od nowa przez ten
	sam rdzeń, którego używa ``volteo_cp_calc``. Nie tworzy ``Volteo CP Oferta``,
	PDF-a ani żadnego innego rekordu — to świadomie odroczone.
	"""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)
	if not volteo_ma_linie("Czyste Powietrze"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	kontakt = (contact or "").strip()
	if not kontakt:
		frappe.throw(_("Wybierz kontakt, aby utworzyć szansę."))

	try:
		wynik, limity, nazwy = _wynik_kalkulatora(wejscie)
	except (CPNiedozwolonaKombinacja, CPPozycjaNieaktywna, CPDaneNiekompletne) as blad:
		frappe.throw(_(str(blad)))
	except Exception:
		_blad_ogolny()

	if not wynik.get("linie"):
		frappe.throw(
			_("Formularz kalkulatora jest pusty — wybierz źródło ciepła, dodatki lub prace termomodernizacyjne.")
		)

	poziom = wejscie.get("poziom")
	standard = wejscie.get("standard")
	limit_termo = limity.get((poziom, standard)) or {}
	if limit_termo.get("status") == "brak_dotacji" and wynik["dotacja_laczna"] == Decimal("0.00"):
		frappe.throw(
			_(
				"Wybrana konfiguracja nie kwalifikuje się do żadnej dotacji w programie "
				"Czyste Powietrze. Nie można utworzyć szansy bez dotacji."
			)
		)

	imie_nazwisko = _imie_nazwisko_kontaktu(kontakt)
	koszt_calkowity = sum((Decimal(str(linia["brutto"])) for linia in wynik["linie"]), Decimal("0.00"))

	deal_status_wiersze = frappe.get_all(
		"CRM Deal Status", fields=["name"], order_by="position asc", limit_page_length=1
	)
	deal_status = deal_status_wiersze[0]["name"] if deal_status_wiersze else None
	if not deal_status:
		frappe.log_error(title="Volteo CP: brak statusu szansy")
		frappe.throw(_("Nie można utworzyć szansy: brak skonfigurowanego statusu szansy."))

	powierzchnia_do_zapisu = _powierzchnia_do_zapisu(wejscie.get("powierzchnia_m2"))

	# Dotacja per pozycja jest wymyślona, gdy wiąże limit grupy -- program dotuje per
	# pozycję, ale limituje per grupę zakresu prac, a jego dokumenty nigdzie nie definiują
	# jak rozbić limit grupy z powrotem na pozycje (patrz komentarz przy oblicz_oferte()
	# w obliczenia.py). Dlatego ten pułapkowy trop jest teraz ROZWIĄZANY, nie tylko
	# udokumentowany: dotacja jest raportowana per GRUPA (wynik["grupy"]), zapisywana do
	# trzech pól nagłówkowych szansy poniżej, a nie per pozycja na custom_zestaw. Grupa
	# nieobecna w wynik["grupy"] (bo nie ma żadnej linii) NIE dostaje zapisanego pola --
	# zostaje nieustawione, a nie zapisane jako zero. Suma tych trzech pól równa się
	# DOKŁADNIE custom_estimated_subsidy_pln (właściwość gwarantowana przez rdzeń, patrz
	# testy grupy_sumuja_sie w test_obliczenia.py) -- to jedyne miejsce, gdzie sumowanie
	# per-grupa jest bezpieczne; sumowanie per-pozycja nigdy nie było i nadal nie jest.
	pola_dotacji_grup = {
		"zrodlo": "custom_cp_dotacja_zrodlo",
		"co": "custom_cp_dotacja_co",
		"termo": "custom_cp_dotacja_termo",
	}
	dotacja_grup_do_zapisu = {
		pola_dotacji_grup[grupa["kod"]]: grupa["dotacja"]
		for grupa in wynik["grupy"]
		if grupa["kod"] in pola_dotacji_grup
	}

	# Blok "Finansowanie" (rata kredytu na wkład własny) -- jak dotacja_grup_do_zapisu
	# wyżej, budowany PRZED insertem, nie przez db_set(): wszystkie cztery pola
	# (custom_cp_okres_lat, custom_cp_wplata_gotowka, custom_cp_kwota_kredytu,
	# custom_cp_rata_wkladu) żyją na permlevel 0, więc zwykły insert() przez
	# "Volteo D2D Sales" jest wystarczający (w odróżnieniu od custom_cp_prowizja_handlowa,
	# permlevel 2, patrz komentarz przy db_set() niżej). Przełącznik WYŁĄCZONY
	# (wynik["finansowanie"] is None) zostawia wszystkie cztery pola NIEUSTAWIONE, nie
	# zerami -- zero byłoby fałszywym sygnałem "rata wynosi 0 zł", podczas gdy naprawdę
	# oznacza "handlowiec nie liczył kredytu na wkład własny". custom_cp_rata_trify NIE
	# jest tu już zapisywane (ops#76) -- rata Trify nie zależy od tego przełącznika, więc
	# przeniosła się do trify_do_zapisu niżej, obok podstawy.
	finansowanie_do_zapisu = (
		{}
		if wynik["finansowanie"] is None
		else {
			"custom_cp_okres_lat": wynik["finansowanie"]["okres_lat"],
			"custom_cp_wplata_gotowka": wynik["finansowanie"]["wplata_gotowka"],
			"custom_cp_kwota_kredytu": wynik["finansowanie"]["kwota_kredytu"],
			"custom_cp_rata_wkladu": wynik["finansowanie"]["rata_wkladu"],
		}
	)

	# Podstawa i rata Trify (custom_cp_podstawa_trify, custom_cp_rata_trify) -- oba pola
	# zapisywane ZAWSZE RAZEM, także przy wyłączonym przełączniku finansowania (ops#76,
	# decyzja właściciela): szansa ma pokazywać kwotę i ratę Trify niezależnie od tego,
	# czy handlowiec w ogóle otworzył blok finansowania kredytu na wkład własny -- rata
	# Trify zależy wyłącznie od dotacji i stałych, nigdy od kredytu. Permlevel 0, jak
	# pozostałe cztery pola wyżej -- zwykły insert() wystarcza. wynik["podstawa_trify"]
	# jest None wyłącznie, gdy stałe finansowania jeszcze nie istnieją na Volteo CP Stale
	# (patrz _trify()/_trify_raw() w obliczenia.py, które liczą oba pola razem) -- wtedy
	# oba pola zostają NIEUSTAWIONE, nigdy zapisane jako zero.
	trify_do_zapisu = (
		{}
		if wynik.get("podstawa_trify") is None
		else {
			"custom_cp_podstawa_trify": wynik["podstawa_trify"],
			"custom_cp_rata_trify": wynik["rata_trify"],
		}
	)

	try:
		deal = frappe.get_doc(
			{
				"doctype": "CRM Deal",
				"status": deal_status,
				"lead_name": imie_nazwisko,
				"deal_value": koszt_calkowity,
				"custom_rodzaj_umowy": "Czyste Powietrze",
				"custom_estimated_subsidy_pln": wynik["dotacja_laczna"],
				"custom_cp_poziom": poziom,
				"custom_cp_standard": standard,
				"custom_cp_powierzchnia_m2": powierzchnia_do_zapisu,
				"custom_cp_wklad_wlasny": wynik["wklad_wlasny"],
				"custom_cp_dotacja_ograniczona_o": wynik["dotacja_ograniczona_o"],
				**dotacja_grup_do_zapisu,
				**finansowanie_do_zapisu,
				**trify_do_zapisu,
				**_cp_zrodlo_pola_do_zapisu(wejscie),
				# Zapis dosłowny tego, co wpisał handlowiec -- jedyna gwarancja wiernego
				# odtworzenia wejścia kalkulatora dla zaplecza przygotowującego "ofertę
				# właściwą" po audycie technicznym. NIE jest źródłem prawdy dla wyceny:
				# wycena jest zawsze liczona od nowa po stronie serwera przez ten sam
				# rdzeń (_wynik_kalkulatora), z aktualnego katalogu/limitów/stałych w
				# chwili przeliczenia, nigdy z tego zapisu.
				"custom_cp_wejscie_json": json.dumps(wejscie, ensure_ascii=False),
				# Decyzja odwrócona: prowizja handlowa (wynik["prowizja_handlowa"]) JEST
				# teraz zapisywana -- ale NIE tutaj, w tym dict przekazywanym do
				# frappe.get_doc(). Jest dopisywana niżej przez deal.db_set(...), tuż obok
				# analogicznego db_set dla "deal_owner". Powód jest identyczny w obu
				# przypadkach: pole żyje na permlevel 2 (custom_cp_prowizja_handlowa,
				# ops/crm-zestaw-cp.py), a handlowiec tworzący szansę zwykle ma tylko rolę
				# "Volteo D2D Sales", która na permlevel 2 nie ma prawa zapisu -- Frappe
				# po cichu odrzuciłby tę wartość przy insert(), gdyby trafiła do tego
				# dict-a. db_set() pomija sprawdzanie uprawnień i zapisuje bezpośrednio.
				# Odczyt permlevel 2 mają wyłącznie role "Volteo Core Admin" i
				# "System Manager" (patrz ops/crm-zestaw-cp.py) -- każda inna rola,
				# łącznie z "Volteo D2D Sales" i "Volteo Backend", nie zobaczy tej
				# wartości żadną ścieżką odczytu (frappe.get_doc, frappe.client.get_value,
				# widoki list). wynik["wewnetrzne"] (koszt/marża per pozycja) JEST teraz
				# UTRWALANE -- ale nie w tym dict-cie: patrz snapshot kosztów budowany i
				# zapisywany przez db_set() niżej, tuż obok custom_cp_prowizja_handlowa
				# (custom_koszty_json, crm/koszty/rdzen.py, ops/crm-koszty-montaz.py).
			}
		)
		# Wiersze BOM per pozycja, dopisywane PRZED insert() (wzorzec z kalkulatora PV,
		# ops/crm-kalkulator-bom.py ok. linii 1305-1310). "typ" grupuje teraz wg GRUPY
		# zakresu prac (nie wg surowej kategorii pozycji), więc zgadza się z
		# wynik["grupy"] i z zakładką Zestaw grupującą wizualnie po tym polu; "cwu" dostaje
		# etykietę grupy "co" mimo kategoria="zrodlo" w katalogu (patrz
		# _typ_grupy_dla_linii()). Pole "dotacja" per wiersz NIE jest zapisywane -- program
		# nie definiuje, jak rozbić limit grupy na pozycje, więc każda taka liczba byłaby
		# wymyślona; jedynym źródłem prawdy o dotacji są trzy pola nagłówkowe wyżej.
		for linia in wynik["linie"]:
			deal.append(
				"custom_zestaw",
				{
					"typ": _typ_grupy_dla_linii(linia["kod"], linia["nazwa_kategorii"]),
					# .get(kod, kod) by tu nie wystarczyło: gdy wiersz istnieje, ale jego
					# "nazwa" jest puste/NULL, klucz JEST obecny, więc .get() zwróciłby tę
					# pustą wartość zamiast wartości domyślnej — stąd jawny fallback "or"
					# na surowy kod katalogowy.
					"nazwa": nazwy.get(linia["kod"]) or linia["kod"],
					"ilosc": linia["ilosc"],
					"jednostka": linia["jednostka"],
					"netto": linia["netto"],
					"brutto": linia["brutto"],
					"reczna_ilosc": 1 if _czy_reczna_ilosc(linia["kod"], wejscie) else 0,
				},
			)
		deal.insert()
		deal.append("contacts", {"contact": kontakt, "is_primary": 1})
		deal.save()
		deal.db_set("deal_owner", frappe.session.user)
		# permlevel 2 -- db_set() bypasses the write-permission check that would
		# otherwise silently strip this from a Volteo D2D Sales rep's insert (see
		# the comment above, next to custom_cp_wejscie_json).
		deal.db_set("custom_cp_prowizja_handlowa", wynik["prowizja_handlowa"])
		# Nadprowizje Managera/Partnera (issue #48, schema ops#46) -- sam wzorzec
		# db_set() na permlevel 2 co custom_cp_prowizja_handlowa wyżej. Zapisywane
		# z SUROWEGO wynik["prowizje"] (sprzed przycięcia poziomem w
		# volteo_cp_calc), więc pełne kwoty trafiają na szansę niezależnie od
		# poziomu prowizyjnego/flagi custom_widzi_prowizje twórcy -- to odczyt
		# (permlevel 2 + volteo_prowizja_szansy) chroni te wartości, nie ten zapis.
		deal.db_set("custom_cp_nadprowizja_manager", wynik["prowizje"]["nadprowizja_manager"])
		deal.db_set("custom_cp_nadprowizja_partner", wynik["prowizje"]["nadprowizja_partner"])
		# Snapshot kosztów/marży (schema v1, crm/koszty/rdzen.py) -- pola permlevel-2
		# (custom_koszty_json, custom_koszty_zysk_plan; ops/crm-koszty-montaz.py), więc
		# db_set() pomija brak prawa zapisu twórcy tak samo jak custom_cp_prowizja_handlowa
		# wyżej. Snapshot pochodzi z tego samego autorytatywnego przeliczenia serwerowego
		# (wynik["wewnetrzne"]) niezależnie od roli twórcy szansy -- administrator edytuje
		# "koszty rzeczywiste" na tym snapshocie później z zakładki Zestaw (crm/api/koszty.py).
		snapshot = zbuduj_snapshot_cp(wynik["wewnetrzne"], nazwy, frappe.utils.now())
		deal.db_set("custom_koszty_json", json.dumps(snapshot, ensure_ascii=False))
		deal.db_set("custom_koszty_zysk_plan", flt(snapshot["podsumowanie"]["zysk_plan"], 2))
		# Ślad aktywności (ops#69) -- czytelny wpis w feedzie zamiast gołego "utworzył
		# szansę" + wersji z ~24 polami. Owinięty we WŁASNY try/except: usterka zapisu
		# śladu nie może nigdy zepsuć utworzenia szansy, które w tym miejscu już się
		# powiodło (insert + wszystkie db_set powyżej zaszły).
		try:
			zapisz_slad(deal.name, tekst_sladu("kalkulator_cp", pozycje=len(wynik["linie"])))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Volteo CP: błąd zapisu śladu aktywności")
	except Exception:
		_blad_ogolny()

	return {"deal": deal.name}
