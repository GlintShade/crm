# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Budowniczy kontekstu do renderowania PDF-u wniosku kredytowego (nakładka).

Moduł celowo nie importuje ``frappe`` — z tego samego powodu co
`crm/volteo_umowa_pdf.py`: ``frappe`` nie jest instalowalne na tej maszynie,
więc to jedyny sposób na lokalną, silną bramkę testową
(`crm/test_volteo_kredyt_pdf.py`). Cała logika zależna od frameworka
(pobranie dokumentów, wywołanie nakładki PDF) mieszka gdzie indziej — tu
tylko czysta funkcja `zbuduj_kontekst_kredytu`, która zamienia surowe dane
domenowe na gotowe do wydruku stringi i booleany.

REGUŁA NADRZĘDNA (dokument finansowy dołączany do umowy): brak danych zawsze
renderuje się jako pusty string (albo `False` dla kratek), nigdy jako
zmyślona wartość.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from crm.volteo_kredyt import GRUPY_DOCHODU
from crm.volteo_kredyt import _wlaczone as _wlaczone_wspolne

# Reużyty jeden parser "czy grupa włączona" z `crm/volteo_kredyt.py` — patrz
# tamtejszy docstring. Lokalny alias zamiast przenoszenia funkcji do wspólnego
# pliku, dokładnie tak jak `crm/volteo_umowa_pdf.py` reużywa `_sparsuj_decimal`
# z `crm/volteo_umowa.py`.
_wlaczone = _wlaczone_wspolne

# `GRUPY_DOCHODU` samo nie jest tu iterowane dla budowy kontekstu (każda grupa
# ma własny, nietrywialny routing pól — patrz bloki poniżej), ale import
# trzyma oba moduły w zgodzie: gdyby ktoś dodał nową grupę dochodu do
# `crm/volteo_kredyt.py` i zapomniał dopisać jej obsługi tutaj, `TestKontraktKluczy`
# (dokładny zestaw kluczy) w pliku testów to złapie.
_GRUPY_DOCHODU_NAZWY = frozenset(GRUPY_DOCHODU)

# AUTORYTETEM dla dokładnej treści opcji Select poniżej jest transkrypcja
# formularza PDF w `crm/volteo_kredyt_mapa.py` oraz schemat w
# `ops/crm-kredyt.py` (potwierdzone przez orkiestratora 2026-08-15,
# character-for-character). `praca_okres` jest WYJĄTKIEM — to nasz własny
# Select, niezależny od formularza PDF, więc nie podlega tej transkrypcji.
# Porównania są dokładne (case-sensitive) wobec tych stałych.
FORMA_UMOWA_O_PRACE = "Umowa o pracę"
FORMA_UMOWA_ZLECENIE = "Umowa zlecenie"
FORMA_UMOWA_DZIELO = "Umowa o dzieło"

OKRES_CZAS_OKRESLONY = "Czas określony"
OKRES_CZAS_NIEOKRESLONY = "Czas nieokreślony"

# Pisownia małą literą jest tu celowa (transkrypcja PDF-u) — w odróżnieniu od
# `OKRES_CZAS_OKRESLONY` powyżej.
FORMA_RYCZALT = "ryczałt"
FORMA_KPIR = "księga przychodów i rozchodów (KPiR)"
FORMA_INNE = "inne"

WYKSZTALCENIE_WYZSZE = "wyższe"
WYKSZTALCENIE_SREDNIE = "średnie"
WYKSZTALCENIE_ZAWODOWE = "zawodowe"
WYKSZTALCENIE_PODSTAWOWE = "podstawowe/gimnazjalne"

STAN_KAWALER_PANNA = "kawaler/panna"
STAN_ROZWIEDZIONY = "Rozwiedziony/a"
STAN_MALZENSTWO_ROZDZIELNOSC = "W związku małżeńskim rozdzielność majątkowa"
STAN_MALZENSTWO_WSPOLNOTA = "W związku małżeńskim wspólnota majątkowa"
STAN_WDOWIEC_WDOWA = "Wdowiec/wdowa"
STAN_SEPARACJA = "Separacja"

ADRES_TAK = "Tak"
ADRES_NIE = "Nie"

_KWOTA_KWANT = Decimal("0.01")
"""Precyzja kwotowa (grosze) przy formatowaniu do wydruku."""

_NBSP = "\xa0"
"""Spacja nierozdzielająca — polski separator tysięcy w kwotach na wydruku."""

KLUCZE_KONTEKSTU: frozenset[str] = frozenset(
	{
		# Blok kontaktowy
		"pesel",
		"imiona",
		"nazwisko",
		"telefon",
		"email",
		"kod_pocztowy",
		"miejscowosc",
		"ulica",
		"nr_domu",
		"nr_lokalu",
		# Dane dokumentu i osobowe
		"miejsce_urodzenia",
		"rodzaj_seria_numer_dokumentu",
		"data_wydania_dokumentu",
		"data_waznosci_dokumentu",
		"adres_zameldowania",
		"adres_korespondencji",
		"liczba_osob_na_utrzymaniu",
		"kwota_800_plus",
		"dochod_wspolmalzonka",
		"zrodlo_dochodu_malzonka",
		"oplaty_miesieczne",
		"suma_zobowiazan",
		"numer_rachunku",
		# Kratki adresowe (nie bramkowane grupami dochodu)
		"adres_zameldowania_tak",
		"adres_zameldowania_nie",
		"adres_korespondencji_tak",
		"adres_korespondencji_nie",
		# Kratki wykształcenia
		"wyksztalcenie_wyzsze",
		"wyksztalcenie_srednie",
		"wyksztalcenie_zawodowe",
		"wyksztalcenie_podstawowe",
		# Kratki stanu cywilnego
		"stan_kawaler_panna",
		"stan_rozwiedziony",
		"stan_malzenstwo_rozdzielnosc",
		"stan_malzenstwo_wspolnota",
		"stan_wdowiec_wdowa",
		"stan_separacja",
		# Praca
		"praca_data_zatrudnienia",
		"praca_okreslony_od",
		"praca_okreslony_do",
		"praca_nieokreslony_od",
		"praca_nip",
		"praca_nazwa_zakladu",
		"praca_adres_telefon",
		"praca_kwota_dochodu",
		"praca_umowa_o_prace",
		"praca_zlecenie",
		"praca_dzielo",
		# Emerytura
		"emerytura_numer_swiadczenia",
		"emerytura_od_kiedy",
		"emerytura_kwota_dochodu",
		# Renta
		"renta_numer_swiadczenia",
		"renta_od_kiedy",
		"renta_kwota_dochodu",
		# Gospodarstwo
		"gospodarstwo_nip",
		"gospodarstwo_od_kiedy",
		"gospodarstwo_kwota_dochodu",
		# Działalność
		"dzialalnosc_ryczalt",
		"dzialalnosc_kpir",
		"dzialalnosc_inne",
		"dzialalnosc_forma_inna",
		"dzialalnosc_nip",
		"dzialalnosc_nazwa",
		"dzialalnosc_adres_telefon",
		"dzialalnosc_od_kiedy",
		"dzialalnosc_kwota_dochodu",
		# Inne
		"inne_1_typ",
		"inne_2_typ",
		"inne_1_kwota",
		"inne_2_kwota",
		# Podpisy
		"podpis_data",
		"podpis_imie_nazwisko",
	}
)
"""Zamrożony zestaw kluczy zwracanych przez `zbuduj_kontekst_kredytu()`. Nazwy
są wiążące dla mapy współrzędnych PDF-u budowanej przez inny agent — nie
zmieniać bez uzgodnienia."""


def zbuduj_kontekst_kredytu(
	kredyt: dict[str, Any], kontakt: dict[str, Any], dzis: date
) -> dict[str, str | bool]:
	"""Buduje kontekst do wstawienia w nakładkę PDF-u wniosku kredytowego.

	Nie mutuje `kredyt` ani `kontakt`. Zwraca dokładnie zestaw kluczy z
	`KLUCZE_KONTEKSTU` — żadna wartość nigdy nie jest `None`.
	"""
	imiona = _tekst(kontakt.get("first_name"))
	nazwisko = _tekst(kontakt.get("last_name"))

	kontekst: dict[str, str | bool] = {
		"pesel": _tekst(kontakt.get("custom_pesel")),
		"imiona": imiona,
		"nazwisko": nazwisko,
		"telefon": _tekst(kontakt.get("mobile_no")),
		"email": _tekst(kontakt.get("email")),
		"kod_pocztowy": _tekst(kontakt.get("custom_kod_pocztowy")),
		"miejscowosc": _tekst(kontakt.get("custom_miasto")),
		"ulica": _tekst(kontakt.get("custom_ulica")),
		"nr_domu": _tekst(kontakt.get("custom_nr_domu")),
		"nr_lokalu": _tekst(kontakt.get("custom_nr_mieszkania")),
	}

	kontekst.update(_blok_dokument_i_zobowiazania(kredyt))
	kontekst.update(_blok_adresy_kratki(kredyt))
	kontekst.update(_blok_wyksztalcenie(kredyt.get("wyksztalcenie")))
	kontekst.update(_blok_stan_cywilny(kredyt.get("stan_cywilny")))
	kontekst.update(_blok_praca(kredyt))
	kontekst.update(_blok_swiadczenie("emerytura", kredyt))
	kontekst.update(_blok_swiadczenie("renta", kredyt))
	kontekst.update(_blok_gospodarstwo(kredyt))
	kontekst.update(_blok_dzialalnosc(kredyt))
	kontekst.update(_blok_inne(kredyt))
	kontekst.update(
		{
			"podpis_data": _data_pl(dzis),
			"podpis_imie_nazwisko": _polacz(imiona, nazwisko),
		}
	)

	return kontekst


def _blok_dokument_i_zobowiazania(kredyt: dict[str, Any]) -> dict[str, str]:
	"""Pola osobowe/dokumentu i zobowiązań finansowych — nigdy bramkowane grupą dochodu."""
	zameldowanie_inne = _rowna(kredyt.get("adres_zameldowania_taki_sam"), ADRES_NIE)
	korespondencja_inna = _rowna(kredyt.get("adres_korespondencji_taki_sam"), ADRES_NIE)
	return {
		"miejsce_urodzenia": _tekst(kredyt.get("miejsce_urodzenia")),
		"rodzaj_seria_numer_dokumentu": _tekst(kredyt.get("rodzaj_seria_numer_dokumentu")),
		"data_wydania_dokumentu": _data_pl(kredyt.get("data_wydania_dokumentu")),
		"data_waznosci_dokumentu": _data_pl(kredyt.get("data_waznosci_dokumentu")),
		"adres_zameldowania": _tekst(kredyt.get("adres_zameldowania")) if zameldowanie_inne else "",
		"adres_korespondencji": _tekst(kredyt.get("adres_korespondencji")) if korespondencja_inna else "",
		"liczba_osob_na_utrzymaniu": _tekst(kredyt.get("liczba_osob_na_utrzymaniu")),
		"kwota_800_plus": _kwota(kredyt.get("kwota_800_plus")),
		"dochod_wspolmalzonka": _kwota(kredyt.get("dochod_wspolmalzonka")),
		"zrodlo_dochodu_malzonka": _tekst(kredyt.get("zrodlo_dochodu_malzonka")),
		"oplaty_miesieczne": _kwota(kredyt.get("oplaty_miesieczne")),
		"suma_zobowiazan": _kwota(kredyt.get("suma_zobowiazan")),
		"numer_rachunku": _tekst(kredyt.get("numer_rachunku")),
	}


def _blok_adresy_kratki(kredyt: dict[str, Any]) -> dict[str, bool]:
	"""Kratki Tak/Nie dla adresu zameldowania i korespondencji — NIE bramkowane grupami dochodu."""
	return {
		"adres_zameldowania_tak": _rowna(kredyt.get("adres_zameldowania_taki_sam"), ADRES_TAK),
		"adres_zameldowania_nie": _rowna(kredyt.get("adres_zameldowania_taki_sam"), ADRES_NIE),
		"adres_korespondencji_tak": _rowna(kredyt.get("adres_korespondencji_taki_sam"), ADRES_TAK),
		"adres_korespondencji_nie": _rowna(kredyt.get("adres_korespondencji_taki_sam"), ADRES_NIE),
	}


def _blok_wyksztalcenie(wartosc: Any) -> dict[str, bool]:
	return {
		"wyksztalcenie_wyzsze": _rowna(wartosc, WYKSZTALCENIE_WYZSZE),
		"wyksztalcenie_srednie": _rowna(wartosc, WYKSZTALCENIE_SREDNIE),
		"wyksztalcenie_zawodowe": _rowna(wartosc, WYKSZTALCENIE_ZAWODOWE),
		"wyksztalcenie_podstawowe": _rowna(wartosc, WYKSZTALCENIE_PODSTAWOWE),
	}


def _blok_stan_cywilny(wartosc: Any) -> dict[str, bool]:
	return {
		"stan_kawaler_panna": _rowna(wartosc, STAN_KAWALER_PANNA),
		"stan_rozwiedziony": _rowna(wartosc, STAN_ROZWIEDZIONY),
		"stan_malzenstwo_rozdzielnosc": _rowna(wartosc, STAN_MALZENSTWO_ROZDZIELNOSC),
		"stan_malzenstwo_wspolnota": _rowna(wartosc, STAN_MALZENSTWO_WSPOLNOTA),
		"stan_wdowiec_wdowa": _rowna(wartosc, STAN_WDOWIEC_WDOWA),
		"stan_separacja": _rowna(wartosc, STAN_SEPARACJA),
	}


_PUSTE_PRACA: dict[str, str | bool] = {
	"praca_data_zatrudnienia": "",
	"praca_okreslony_od": "",
	"praca_okreslony_do": "",
	"praca_nieokreslony_od": "",
	"praca_nip": "",
	"praca_nazwa_zakladu": "",
	"praca_adres_telefon": "",
	"praca_kwota_dochodu": "",
	"praca_umowa_o_prace": False,
	"praca_zlecenie": False,
	"praca_dzielo": False,
}
"""Wartości zwracane dla bloku "praca", gdy `praca_wlaczone` jest wyłączone —
zerują WSZYSTKIE klucze bloku, nawet gdy `kredyt` niesie resztki wcześniej
wypełnionych pól (wyłączony przełącznik unieważnia dane)."""


def _blok_praca(kredyt: dict[str, Any]) -> dict[str, str | bool]:
	"""Blok "praca" — bramkowany `praca_wlaczone`; routing okresu zatrudnienia opisany w `zbuduj_kontekst_kredytu`."""
	if not _wlaczone(kredyt.get("praca_wlaczone")):
		return dict(_PUSTE_PRACA)

	okres = kredyt.get("praca_okres")
	okreslony_od = okreslony_do = nieokreslony_od = ""
	if _rowna(okres, OKRES_CZAS_OKRESLONY):
		okreslony_od = _data_pl(kredyt.get("praca_okres_od"))
		okreslony_do = _data_pl(kredyt.get("praca_okres_do"))
	elif _rowna(okres, OKRES_CZAS_NIEOKRESLONY):
		nieokreslony_od = _data_pl(kredyt.get("praca_okres_od"))

	forma = kredyt.get("praca_forma")
	return {
		"praca_data_zatrudnienia": _data_pl(kredyt.get("praca_data_zatrudnienia")),
		"praca_okreslony_od": okreslony_od,
		"praca_okreslony_do": okreslony_do,
		"praca_nieokreslony_od": nieokreslony_od,
		"praca_nip": _tekst(kredyt.get("praca_nip")),
		"praca_nazwa_zakladu": _tekst(kredyt.get("praca_nazwa_zakladu")),
		"praca_adres_telefon": _tekst(kredyt.get("praca_adres_telefon")),
		"praca_kwota_dochodu": _kwota(kredyt.get("praca_kwota_dochodu")),
		"praca_umowa_o_prace": _rowna(forma, FORMA_UMOWA_O_PRACE),
		"praca_zlecenie": _rowna(forma, FORMA_UMOWA_ZLECENIE),
		"praca_dzielo": _rowna(forma, FORMA_UMOWA_DZIELO),
	}


def _blok_swiadczenie(prefiks: str, kredyt: dict[str, Any]) -> dict[str, str]:
	"""Blok wspólny dla emerytury/renty — oba mają identyczny kształt (numer świadczenia/od kiedy/kwota)."""
	przelacznik = f"{prefiks}_wlaczone"
	klucz_numer = f"{prefiks}_numer_swiadczenia"
	klucz_od_kiedy = f"{prefiks}_od_kiedy"
	klucz_kwota = f"{prefiks}_kwota_dochodu"

	if not _wlaczone(kredyt.get(przelacznik)):
		return {klucz_numer: "", klucz_od_kiedy: "", klucz_kwota: ""}

	return {
		klucz_numer: _tekst(kredyt.get(klucz_numer)),
		klucz_od_kiedy: _data_pl(kredyt.get(klucz_od_kiedy)),
		klucz_kwota: _kwota(kredyt.get(klucz_kwota)),
	}


def _blok_gospodarstwo(kredyt: dict[str, Any]) -> dict[str, str]:
	"""Blok "gospodarstwo rolne" — kształt jak `_blok_swiadczenie`, ale pole tożsamości to `nip`, nie numer świadczenia."""
	if not _wlaczone(kredyt.get("gospodarstwo_wlaczone")):
		return {"gospodarstwo_nip": "", "gospodarstwo_od_kiedy": "", "gospodarstwo_kwota_dochodu": ""}

	return {
		"gospodarstwo_nip": _tekst(kredyt.get("gospodarstwo_nip")),
		"gospodarstwo_od_kiedy": _data_pl(kredyt.get("gospodarstwo_od_kiedy")),
		"gospodarstwo_kwota_dochodu": _kwota(kredyt.get("gospodarstwo_kwota_dochodu")),
	}


_PUSTE_DZIALALNOSC: dict[str, str | bool] = {
	"dzialalnosc_ryczalt": False,
	"dzialalnosc_kpir": False,
	"dzialalnosc_inne": False,
	"dzialalnosc_forma_inna": "",
	"dzialalnosc_nip": "",
	"dzialalnosc_nazwa": "",
	"dzialalnosc_adres_telefon": "",
	"dzialalnosc_od_kiedy": "",
	"dzialalnosc_kwota_dochodu": "",
}
"""Wartości zwracane dla bloku "działalność", gdy `dzialalnosc_wlaczone` jest wyłączone."""


def _blok_dzialalnosc(kredyt: dict[str, Any]) -> dict[str, str | bool]:
	"""Blok "działalność gospodarcza" — bramkowany `dzialalnosc_wlaczone`."""
	if not _wlaczone(kredyt.get("dzialalnosc_wlaczone")):
		return dict(_PUSTE_DZIALALNOSC)

	forma = kredyt.get("dzialalnosc_forma_opodatkowania")
	return {
		"dzialalnosc_ryczalt": _rowna(forma, FORMA_RYCZALT),
		"dzialalnosc_kpir": _rowna(forma, FORMA_KPIR),
		"dzialalnosc_inne": _rowna(forma, FORMA_INNE),
		"dzialalnosc_forma_inna": _tekst(kredyt.get("dzialalnosc_forma_inna")) if _rowna(forma, FORMA_INNE) else "",
		"dzialalnosc_nip": _tekst(kredyt.get("dzialalnosc_nip")),
		"dzialalnosc_nazwa": _tekst(kredyt.get("dzialalnosc_nazwa")),
		"dzialalnosc_adres_telefon": _tekst(kredyt.get("dzialalnosc_adres_telefon")),
		"dzialalnosc_od_kiedy": _data_pl(kredyt.get("dzialalnosc_od_kiedy")),
		"dzialalnosc_kwota_dochodu": _kwota(kredyt.get("dzialalnosc_kwota_dochodu")),
	}


def _blok_inne(kredyt: dict[str, Any]) -> dict[str, str]:
	"""Blok "inne źródła dochodu" — bramkowany `inne_wlaczone`; druga para (2) jest opcjonalna, nie osobno bramkowana."""
	if not _wlaczone(kredyt.get("inne_wlaczone")):
		return {"inne_1_typ": "", "inne_2_typ": "", "inne_1_kwota": "", "inne_2_kwota": ""}

	return {
		"inne_1_typ": _tekst(kredyt.get("inne_1_typ")),
		"inne_2_typ": _tekst(kredyt.get("inne_2_typ")),
		"inne_1_kwota": _kwota(kredyt.get("inne_1_kwota")),
		"inne_2_kwota": _kwota(kredyt.get("inne_2_kwota")),
	}


def _tekst(wartosc: Any) -> str:
	"""Normalizuje dowolną wartość tekstową do gotowego do wydruku stringu: `None` → `""`, białe znaki na brzegach ucięte."""
	if wartosc is None:
		return ""
	return str(wartosc).strip()


def _polacz(*czesci: Any, sep: str = " ") -> str:
	"""Łączy niepuste, przefiltrowane przez `_tekst` fragmenty jednym separatorem (bez podwójnych spacji przy pustym fragmencie)."""
	niepuste = [c for c in (_tekst(c) for c in czesci) if c]
	return sep.join(niepuste)


def _rowna(wartosc: Any, wzorzec: str) -> bool:
	"""Porównanie tekstowe odporne na białe znaki na brzegach i nie-stringi; `None`/nietekstowe → `False`, nigdy nie rzuca."""
	return isinstance(wartosc, str) and wartosc.strip() == wzorzec


def _data_pl(wartosc: Any) -> str:
	"""Formatuje datę jako `DD.MM.RRRR`.

	Akceptuje `datetime.date` (i `datetime.datetime`, jego podklasę), string
	ISO `"YYYY-MM-DD"`, albo `""`/`None` — wszystko inne (nieparsowalny
	string, zły typ) daje `""`, nigdy nie rzuca.
	"""
	if isinstance(wartosc, date):
		return f"{wartosc.day:02d}.{wartosc.month:02d}.{wartosc.year:04d}"
	if isinstance(wartosc, str):
		tekst = wartosc.strip()
		if tekst == "":
			return ""
		try:
			rok_s, miesiac_s, dzien_s = tekst.split("-")
			sparsowana = date(int(rok_s), int(miesiac_s), int(dzien_s))
		except (ValueError, TypeError):
			return ""
		return f"{sparsowana.day:02d}.{sparsowana.month:02d}.{sparsowana.year:04d}"
	return ""


def _sparsuj_kwote(wartosc: Any) -> Decimal | None:
	"""Parsuje kwotę w polskiej formie ("1234,56", "1 234,56" ze zwykłą spacją albo NBSP) albo kropkowej ("1234.56").

	Zwraca `None` dla `None`, pustego/samego-białego-znaku stringu, albo
	niesparsowalnej wartości — nigdy nie rzuca.
	"""
	if wartosc is None:
		return None
	if not isinstance(wartosc, str):
		try:
			return Decimal(str(wartosc))
		except InvalidOperation:
			return None
	oczyszczona = wartosc.strip()
	if oczyszczona == "":
		return None
	oczyszczona = oczyszczona.replace("\xa0", "").replace(" ", "").replace(",", ".")
	try:
		return Decimal(oczyszczona)
	except InvalidOperation:
		return None


def _grupuj_tysiace(cyfry: str) -> str:
	"""Grupuje ciąg cyfr (część całkowita kwoty) po 3 od prawej, spacją nierozdzielającą."""
	n = len(cyfry)
	grupy = []
	while n > 3:
		grupy.append(cyfry[n - 3 : n])
		n -= 3
	grupy.append(cyfry[:n])
	return _NBSP.join(reversed(grupy))


def _kwota(wartosc: Any) -> str:
	"""Formatuje kwotę pieniężną: `"41236.5"`/`"41 236,50"` → `"41 236,50"`; puste/niesparsowalne → `""`.

	W ODRÓŻNIENIU od `crm/volteo_umowa_pdf.py::_kwota` (gdzie zero jest pustką
	dla WSZYSTKICH kwot umowy — dokument o wynagrodzeniu 0 zł nie ma sensu),
	tutaj zero jest wartością wypełnioną i drukuje się jako `"0,00"`: "0 zł
	dochodu współmałżonka" albo "0 zł 800+" są tu poprawnymi, realnymi
	odpowiedziami wniosku kredytowego, nie brakiem danych. Jedyne warunki na
	pustkę to brak wartości albo format nie do sparsowania — zgodnie z
	kontraktem zadania ("unparseable or empty → pusty string").
	"""
	dec = _sparsuj_kwote(wartosc)
	if dec is None:
		return ""
	zaokraglona = dec.quantize(_KWOTA_KWANT, rounding=ROUND_HALF_UP)
	znak = "-" if zaokraglona < 0 else ""
	zaokraglona = abs(zaokraglona)
	czesc_calkowita, _, czesc_dziesietna = format(zaokraglona, "f").partition(".")
	czesc_dziesietna = (czesc_dziesietna + "00")[:2]
	return f"{znak}{_grupuj_tysiace(czesc_calkowita)},{czesc_dziesietna}"
