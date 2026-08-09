from decimal import ROUND_HALF_UP, Decimal
from typing import Any, NoReturn


class CPBlad(Exception):
	"""Wspólna klasa błędów kalkulatora."""


class CPDaneNiekompletne(CPBlad):
	"""Dane potrzebne do wyceny są niepełne albo niepoprawne."""


class CPPozycjaNieaktywna(CPBlad):
	"""Wybrana pozycja katalogowa nie jest dostępna."""


class CPNiedozwolonaKombinacja(CPBlad):
	"""Wybrana kombinacja danych programu lub dodatków jest niedozwolona."""


_POZIOMY = ("podstawowy", "podwyzszony", "najwyzszy")
_STANDARDY = ("do80", "od80do140", "powyzej140")
_PRACE_TERMO = ("elewacja", "strop", "dach", "okna", "drzwi")
_ZERO = Decimal("0")
_JEDEN = Decimal("1")


def _blad(komunikat: str) -> NoReturn:
	raise CPDaneNiekompletne(komunikat)


def _decimal(wartosc: Any, pole: str) -> Decimal:
	try:
		wynik = Decimal(str(wartosc))
	except (ArithmeticError, TypeError, ValueError):
		_blad(f"Nieprawidłowa wartość pola {pole}.")
	if not wynik.is_finite():
		_blad(f"Nieprawidłowa wartość pola {pole}.")
	return wynik


def _kwota(wartosc: Decimal) -> Decimal:
	return wartosc.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _pozycja(kod: str, katalog: dict[str, Any]) -> dict[str, Any]:
	if not isinstance(kod, str) or kod not in katalog or not isinstance(katalog[kod], dict):
		_blad(f"Brak pozycji katalogowej {kod}.")

	pozycja = katalog[kod]
	if "aktywny" not in pozycja:
		_blad(f"Brak danych pozycji {kod}.")
	if pozycja["aktywny"] is False:
		raise CPPozycjaNieaktywna(f"Pozycja {kod} jest nieaktywna.")

	for pole in (
		"kategoria",
		"jednostka",
		"cena_netto",
		"dotacja",
		"limit_dotacji",
		"prowizja",
		"koszt_proenergy",
		"koszt_staly",
	):
		if pole not in pozycja:
			_blad(f"Brak danych pozycji {kod}.")
	return pozycja


def _sprawdz_kategorie(pozycja: dict[str, Any], oczekiwana: str, kod: str) -> None:
	if pozycja["kategoria"] != oczekiwana:
		_blad(f"Nieprawidłowa kategoria pozycji {kod}.")
	if pozycja["jednostka"] not in ("szt", "m2"):
		_blad(f"Nieprawidłowa jednostka pozycji {kod}.")


def _dane_stawki(
	pozycja: dict[str, Any], poziom: str, kod: str
) -> tuple[Decimal, Decimal, Decimal, Decimal | None]:
	dotacje = pozycja["dotacja"]
	limity = pozycja["limit_dotacji"]
	if not isinstance(dotacje, dict) or poziom not in dotacje:
		_blad(f"Brak dotacji pozycji {kod} dla wybranego poziomu.")
	if not isinstance(limit := limity, dict) or poziom not in limit:
		_blad(f"Brak limitu dotacji pozycji {kod} dla wybranego poziomu.")

	netto = _decimal(pozycja["cena_netto"], f"cena_netto:{kod}")
	dotacja = _decimal(dotacje[poziom], f"dotacja:{kod}")
	prowizja = _decimal(pozycja["prowizja"], f"prowizja:{kod}")
	limit_dotacji = None if limit[poziom] is None else _decimal(limit[poziom], f"limit_dotacji:{kod}")
	return netto, dotacja, prowizja, limit_dotacji


def _linia(
	kod: str,
	pozycja: dict[str, Any],
	poziom: str,
	ilosc: Decimal,
	vat: Decimal,
	ilosc_rozliczeniowa: Decimal | None = None,
	ilosc_wyswietlana: Decimal | None = None,
	jednostka_rozliczeniowa: str | None = None,
) -> dict[str, Any]:
	netto_jednostkowe, dotacja_jednostkowa, prowizja_jednostkowa, _ = _dane_stawki(pozycja, poziom, kod)
	koszt_jednostkowy = _decimal(pozycja["koszt_proenergy"], f"koszt_proenergy:{kod}")
	koszt_staly = _decimal(pozycja["koszt_staly"], f"koszt_staly:{kod}")
	ilosc_rozliczeniowa = ilosc if ilosc_rozliczeniowa is None else ilosc_rozliczeniowa
	ilosc_wyswietlana = ilosc if ilosc_wyswietlana is None else ilosc_wyswietlana
	jednostka_rozliczeniowa = pozycja["jednostka"] if jednostka_rozliczeniowa is None else jednostka_rozliczeniowa

	netto = ilosc * netto_jednostkowe
	brutto = netto * vat
	dotacja = ilosc * dotacja_jednostkowa
	prowizja = ilosc_rozliczeniowa * prowizja_jednostkowa
	koszt = ilosc_rozliczeniowa * koszt_jednostkowy + koszt_staly
	return {
		"kod": kod,
		"nazwa_kategorii": pozycja["kategoria"],
		"ilosc": ilosc_wyswietlana,
		"jednostka": pozycja["jednostka"],
		"netto": _kwota(netto),
		"brutto": _kwota(brutto),
		"dotacja": _kwota(max(_ZERO, dotacja)),
		"_netto": netto,
		"_brutto": brutto,
		"_dotacja": max(_ZERO, dotacja),
		"_prowizja": prowizja,
		"_koszt": koszt,
		"_koszt_jednostkowy": koszt_jednostkowy,
		"_koszt_staly": koszt_staly,
		"_stawka_prowizji": prowizja_jednostkowa,
		"_ilosc_rozliczeniowa": ilosc_rozliczeniowa,
		"_jednostka_rozliczeniowa": jednostka_rozliczeniowa,
	}


def _wybrana_praca(prace: Any, kod: str) -> dict[str, Any] | None:
	if not isinstance(prace, dict):
		_blad("Brak danych prac termomodernizacyjnych.")
	wartosc = prace.get(kod)
	if wartosc is None:
		return None
	if not isinstance(wartosc, dict):
		_blad(f"Nieprawidłowe dane pracy {kod}.")
	if wartosc.get("wybrana"):
		return wartosc
	return None


def _powierzchnia_pracy(
	kod: str,
	praca: dict[str, Any],
	powierzchnia: Decimal,
	stale: dict[str, Any],
) -> tuple[Decimal, Decimal | None]:
	if kod == "drzwi":
		ilosc_drzwi = _decimal(praca.get("ilosc"), "ilosc drzwi")
		if ilosc_drzwi < _ZERO:
			_blad("Liczba drzwi nie może być ujemna.")
		m2_na_drzwi = _decimal(stale.get("m2_na_drzwi"), "m2_na_drzwi")
		return ilosc_drzwi * m2_na_drzwi, ilosc_drzwi

	if praca.get("m2") is not None:
		m2 = _decimal(praca["m2"], f"m2:{kod}")
	else:
		mnozniki = stale.get("mnozniki")
		if not isinstance(mnozniki, dict) or kod not in mnozniki:
			_blad(f"Brak mnożnika powierzchni dla pracy {kod}.")
		m2 = powierzchnia * _decimal(mnozniki[kod], f"mnożnik:{kod}")
	if m2 < _ZERO:
		_blad(f"Powierzchnia pracy {kod} nie może być ujemna.")
	return m2, None


# Ostatnia linia obrony przed wyciekiem kosztów/prowizji do wynik["linie"]: usuwa KAŻDY klucz
# zaczynający się od "_", niezależnie od tego, czy jest tu wymieniony po nazwie. Dzięki temu
# nowe prywatne pole dopisane kiedyś do _linia() i zapomniane w tej liście i tak zostanie
# wyczyszczone, zamiast po cichu przeciekło do widoku handlowca terenowego.
def _zaokragl_wynik(linie: list[dict[str, Any]], wynik: dict[str, Any]) -> dict[str, Any]:
	for linia in linie:
		for pole in list(linia.keys()):
			if pole.startswith("_"):
				linia.pop(pole, None)
	return wynik


def oblicz_oferte(
	wejscie: dict[str, Any], katalog: dict[str, Any], limity: dict[Any, Any], stale: dict[str, Any]
) -> dict[str, Any]:
	"""Oblicza ofertę bez dostępu do frameworka, bazy danych ani innych źródeł danych."""
	if (
		not isinstance(wejscie, dict)
		or not isinstance(katalog, dict)
		or not isinstance(limity, dict)
		or not isinstance(stale, dict)
	):
		_blad("Nieprawidłowe dane wejściowe kalkulatora.")

	poziom = wejscie.get("poziom")
	standard = wejscie.get("standard")
	if poziom not in _POZIOMY:
		_blad("Nieznany poziom dofinansowania.")
	if standard not in _STANDARDY:
		_blad("Nieznany standard budynku.")
	if (poziom, standard) not in limity or not isinstance(limity[(poziom, standard)], dict):
		_blad("Brak limitu termomodernizacji dla wybranych danych.")

	limit_termo = limity[(poziom, standard)]
	status_limitu = limit_termo.get("status")
	if status_limitu not in ("kwota", "brak_dotacji", "niedozwolone", "do_ustalenia"):
		_blad("Nieznany status limitu termomodernizacji.")
	if status_limitu == "niedozwolone":
		raise CPNiedozwolonaKombinacja(
			"Wybrana kombinacja poziomu dofinansowania i standardu budynku jest niedozwolona."
		)
	if "kwota" not in limit_termo:
		_blad("Brak kwoty limitu termomodernizacji.")
	kwota_limitu = None if limit_termo["kwota"] is None else _decimal(limit_termo["kwota"], "kwota limitu")
	if status_limitu == "kwota" and kwota_limitu is None:
		_blad("Brak kwoty limitu termomodernizacji.")

	vat = _decimal(stale.get("vat_mnoznik"), "vat_mnoznik")
	linie: list[dict[str, Any]] = []
	zrodlo_linie: list[dict[str, Any]] = []
	co_linie: list[dict[str, Any]] = []
	termo_linie: list[dict[str, Any]] = []

	kod_zrodla = wejscie.get("zrodlo_ciepla")
	if kod_zrodla is not None and kod_zrodla not in ("pompa_ciepla", "pellet", "zgazowujacy"):
		if kod_zrodla == "cwu":
			raise CPNiedozwolonaKombinacja("CWU nie może być wybranym źródłem ciepła.")
		_blad(f"Nieznane źródło ciepła {kod_zrodla}.")

	czy_cwu = wejscie.get("cwu", False)
	if czy_cwu and kod_zrodla not in ("pellet", "zgazowujacy"):
		raise CPNiedozwolonaKombinacja("CWU jest niedozwolone dla wybranego źródła ciepła.")

	typ_grzejnikow = wejscie.get("typ_grzejnikow")
	ilosc_grzejnikow = _ZERO
	if typ_grzejnikow is not None:
		if typ_grzejnikow not in ("grzejnik", "grzejnik_co"):
			_blad("Nieznany typ grzejnika.")
		ilosc_grzejnikow = _decimal(wejscie.get("ilosc_grzejnikow"), "ilosc_grzejnikow")
		if ilosc_grzejnikow < _ZERO:
			_blad("Liczba grzejników nie może być ujemna.")
		if ilosc_grzejnikow > _ZERO and kod_zrodla != "pompa_ciepla":
			raise CPNiedozwolonaKombinacja("Grzejniki są dozwolone wyłącznie dla pompy ciepła.")

	if kod_zrodla is not None:
		pozycja = _pozycja(kod_zrodla, katalog)
		_sprawdz_kategorie(pozycja, "zrodlo", kod_zrodla)
		zrodlo_linie.append(_linia(kod_zrodla, pozycja, poziom, _JEDEN, vat))
	if czy_cwu:
		pozycja = _pozycja("cwu", katalog)
		_sprawdz_kategorie(pozycja, "zrodlo", "cwu")
		zrodlo_linie.append(_linia("cwu", pozycja, poziom, _JEDEN, vat))
	if ilosc_grzejnikow > _ZERO:
		pozycja = _pozycja(typ_grzejnikow, katalog)
		_sprawdz_kategorie(pozycja, "co", typ_grzejnikow)
		co_linie.append(_linia(typ_grzejnikow, pozycja, poziom, ilosc_grzejnikow, vat))

	powierzchnia = _decimal(wejscie.get("powierzchnia_m2"), "powierzchnia_m2")
	if powierzchnia < _ZERO:
		_blad("Powierzchnia budynku nie może być ujemna.")
	prace = wejscie.get("prace")
	if not isinstance(prace, dict):
		_blad("Brak danych prac termomodernizacyjnych.")
	for kod, wartosc in prace.items():
		if wartosc.get("wybrana") if isinstance(wartosc, dict) else False:
			if kod not in _PRACE_TERMO:
				_blad(f"Nieznany typ pracy {kod}.")

	for kod in _PRACE_TERMO:
		praca = _wybrana_praca(prace, kod)
		if praca is None:
			continue
		pozycja = _pozycja(kod, katalog)
		_sprawdz_kategorie(pozycja, "termo", kod)
		m2, liczba_drzwi = _powierzchnia_pracy(kod, praca, powierzchnia, stale)
		ilosc_rozliczeniowa = liczba_drzwi if kod == "drzwi" else m2
		ilosc_wyswietlana = liczba_drzwi if kod == "drzwi" and pozycja["jednostka"] == "szt" else m2
		jednostka_rozliczeniowa = "szt" if kod == "drzwi" else None
		termo_linie.append(
			_linia(
				kod,
				pozycja,
				poziom,
				m2,
				vat,
				ilosc_rozliczeniowa=ilosc_rozliczeniowa,
				ilosc_wyswietlana=ilosc_wyswietlana,
				jednostka_rozliczeniowa=jednostka_rozliczeniowa,
			)
		)

	if termo_linie and status_limitu == "brak_dotacji":
		for linia in termo_linie:
			linia["dotacja"] = _kwota(_ZERO)
			linia["_dotacja"] = _ZERO
	if termo_linie and status_limitu == "do_ustalenia":
		raise CPDaneNiekompletne("Limit termomodernizacji jest jeszcze do ustalenia.")

	linie = zrodlo_linie + co_linie + termo_linie
	brutto_zrodlo = sum((linia["_brutto"] for linia in zrodlo_linie), _ZERO)
	dotacja_zrodlo = sum((linia["_dotacja"] for linia in zrodlo_linie), _ZERO)
	brutto_co = sum((linia["_brutto"] for linia in co_linie), _ZERO)
	dotacja_co_surowa = sum((linia["_dotacja"] for linia in co_linie), _ZERO)
	brutto_termo = sum((linia["_brutto"] for linia in termo_linie), _ZERO)
	dotacja_termo_surowa = sum((linia["_dotacja"] for linia in termo_linie), _ZERO)

	dotacja_co = dotacja_co_surowa
	if co_linie:
		_, _, _, limit_co = _dane_stawki(_pozycja(co_linie[0]["kod"], katalog), poziom, co_linie[0]["kod"])
		if limit_co is not None:
			dotacja_co = min(dotacja_co, limit_co)
		dotacja_co = max(_ZERO, dotacja_co)
		for linia in co_linie:
			linia["dotacja"] = _kwota(dotacja_co)

	dotacja_termo = dotacja_termo_surowa
	dotacja_ograniczona_o = _ZERO
	if termo_linie and status_limitu == "kwota":
		dotacja_termo = max(_ZERO, min(dotacja_termo_surowa, kwota_limitu))
		dotacja_ograniczona_o = max(_ZERO, dotacja_termo_surowa - dotacja_termo)

	suma_netto = sum((linia["_netto"] for linia in linie), _ZERO)
	suma_prowizji = sum((linia["_prowizja"] for linia in linie), _ZERO)
	koszt_calkowity = sum((linia["_koszt"] for linia in linie), _ZERO)
	wklad_zrodlo = max(_ZERO, brutto_zrodlo - dotacja_zrodlo)
	wklad_co = max(_ZERO, brutto_co - dotacja_co)
	wklad_termo = max(_ZERO, brutto_termo - dotacja_termo)

	# Rozbicie kosztów/prowizji per pozycja budowane PRZED czyszczeniem prywatnych pól przez
	# _zaokragl_wynik. Żyje wyłącznie wewnątrz wynik["wewnetrzne"], bo crm/api/czyste_powietrze.py
	# usuwa całe to poddrzewo dla nie-adminów jednym wynik.pop("wewnetrzne", None) — umieszczenie
	# tych danych na wynik["linie"] ujawniłoby koszty i marże handlowcom terenowym.
	linie_wewnetrzne = [
		{
			"kod": linia["kod"],
			"ilosc_rozliczeniowa": linia["_ilosc_rozliczeniowa"],
			"jednostka_rozliczeniowa": linia["_jednostka_rozliczeniowa"],
			"netto": _kwota(linia["_netto"]),
			"koszt": _kwota(linia["_koszt"]),
			"koszt_jednostkowy": _kwota(linia["_koszt_jednostkowy"]),
			"koszt_staly": _kwota(linia["_koszt_staly"]),
			"stawka_prowizji": _kwota(linia["_stawka_prowizji"]),
			"prowizja": _kwota(linia["_prowizja"]),
		}
		for linia in linie
	]

	prowizja_handlowa = _kwota(suma_prowizji)
	marza = _kwota(suma_netto - koszt_calkowity)
	wynik = {
		"wklad_wlasny": _kwota(wklad_zrodlo + wklad_co + wklad_termo),
		"prowizja_handlowa": prowizja_handlowa,
		"linie": linie,
		"dotacja_laczna": _kwota(dotacja_zrodlo + dotacja_co + dotacja_termo),
		"dotacja_ograniczona_o": _kwota(dotacja_ograniczona_o),
		"wewnetrzne": {
			"koszt_calkowity": _kwota(koszt_calkowity),
			"marza": marza,
			"prowizja_handlowa": prowizja_handlowa,
			"zysk": marza - prowizja_handlowa,
			"linie": linie_wewnetrzne,
		},
	}
	return _zaokragl_wynik(linie, wynik)
