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
# Warianty materiałowe dla prac, które je mają -- pierwszy element każdej krotki jest
# DOMYŚLNY (piana PUR, tańsza dla firmy przy tej samej cenie dla klienta) i jednocześnie
# pierwszy w kolejności rozwijanej listy pokazywanej w UI: kolejność krotki to zarówno
# priorytet domyślny, jak i kolejność wyświetlania.
_WARIANTY_TERMO = {
	"strop": ("strop_piana", "strop_welna", "strop_styropian"),
	"dach": ("dach_piana", "dach_welna"),
}
_DOMYSLNY_WARIANT = {"strop": "strop_piana", "dach": "dach_piana"}
_BAZA_WARIANTU = {w: baza for baza, warianty in _WARIANTY_TERMO.items() for w in warianty}
_ZERO = Decimal("0")
_JEDEN = Decimal("1")


def baza_pracy(kod: str) -> str:
	"""Zwraca kod bazowy pracy dla kodu wariantu; dla kodów bez wariantów zwraca wejście."""
	return _BAZA_WARIANTU.get(kod, kod)


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
		"nadprowizja_manager",
		"nadprowizja_partner",
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
	ilosc_dotowana: Decimal | None = None,
) -> dict[str, Any]:
	netto_jednostkowe, dotacja_jednostkowa, prowizja_jednostkowa, _ = _dane_stawki(pozycja, poziom, kod)
	# Stawki nadprowizji Managera/Partnera -- nie poziomowane (w odróżnieniu od dotacji),
	# więc czytane wprost z pozycji, nie przez _dane_stawki() (który zostaje niezmieniony).
	stawka_nadprowizji_manager = _decimal(pozycja["nadprowizja_manager"], f"nadprowizja_manager:{kod}")
	stawka_nadprowizji_partner = _decimal(pozycja["nadprowizja_partner"], f"nadprowizja_partner:{kod}")
	koszt_jednostkowy = _decimal(pozycja["koszt_proenergy"], f"koszt_proenergy:{kod}")
	koszt_staly = _decimal(pozycja["koszt_staly"], f"koszt_staly:{kod}")
	ilosc_rozliczeniowa = ilosc if ilosc_rozliczeniowa is None else ilosc_rozliczeniowa
	ilosc_wyswietlana = ilosc if ilosc_wyswietlana is None else ilosc_wyswietlana
	jednostka_rozliczeniowa = pozycja["jednostka"] if jednostka_rozliczeniowa is None else jednostka_rozliczeniowa
	# Dotacja zwykle liczy się od tej samej ilości co netto/brutto -- ale elewacja jest
	# świadomym wyjątkiem (patrz wywołanie w pętli termo w oblicz_oferte): fundusz dotuje
	# tylko 90% powierzchni ściany (okna zajmują resztę fasady), mimo że klient płaci
	# (netto/brutto) i ProEnergy rozlicza prowizję/koszt (przez ilosc_rozliczeniowa) od
	# CAŁEJ powierzchni. Domyślnie ilosc_dotowana == ilosc, więc każde inne dotychczasowe
	# wywołanie _linia() ma dokładnie niezmienione zachowanie.
	ilosc_dotowana = ilosc if ilosc_dotowana is None else ilosc_dotowana

	netto = ilosc * netto_jednostkowe
	brutto = netto * vat
	dotacja = ilosc_dotowana * dotacja_jednostkowa
	prowizja = ilosc_rozliczeniowa * prowizja_jednostkowa
	# Nadprowizje liczone DOKŁADNIE jak prowizja (ta sama ilosc_rozliczeniowa) -- dziedziczą
	# więc jej semantykę jednostek za darmo (drzwi per SZTUKA, elewacja na PEŁNEJ
	# powierzchni, strop/dach per wariant materiałowy).
	nadprowizja_manager = ilosc_rozliczeniowa * stawka_nadprowizji_manager
	nadprowizja_partner = ilosc_rozliczeniowa * stawka_nadprowizji_partner
	koszt = ilosc_rozliczeniowa * koszt_jednostkowy + koszt_staly
	return {
		"kod": kod,
		"nazwa_kategorii": pozycja["kategoria"],
		# Grupa prezentacyjna: dla WSZYSTKICH pozycji równa kategorii katalogowej, poza
		# jednym świadomym wyjątkiem -- "cwu" ma kategoria="zrodlo" w katalogu (bo TAK
		# liczy się jej limit dotacji), ale w prezentacji dzieli wiersz i limit z centralnym
		# ogrzewaniem (patrz długi komentarz przy regrupowaniu wynik["grupy"] niżej). To pole
		# jest tu po to, żeby front mógł pogrupować pozycje z wynik["linie"] 1:1 z grupami w
		# wynik["grupy"] bez zgadywania -- grupowanie po samym "nazwa_kategorii" wsadziłoby
		# cwu do złego pudełka (do "zrodlo" zamiast do "co").
		"grupa": "co" if kod == "cwu" else pozycja["kategoria"],
		"ilosc": ilosc_wyswietlana,
		"jednostka": pozycja["jednostka"],
		"netto": _kwota(netto),
		"brutto": _kwota(brutto),
		# Celowo BRAK publicznego pola "dotacja" -- subsydium per pozycja jest wymyślone,
		# gdy wiąże limit grupy (patrz komentarz przy budowie wynik["grupy"] niżej).
		# "_dotacja" zostaje jako pole prywatne, potrzebne do policzenia sum per grupa.
		"_netto": netto,
		"_brutto": brutto,
		"_dotacja": max(_ZERO, dotacja),
		"_prowizja": prowizja,
		"_nadprowizja_manager": nadprowizja_manager,
		"_nadprowizja_partner": nadprowizja_partner,
		"_stawka_nadprowizji_manager": stawka_nadprowizji_manager,
		"_stawka_nadprowizji_partner": stawka_nadprowizji_partner,
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
	powierzchnia_elewacji: Decimal,
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
	elif kod == "okna":
		# Powierzchnia okien NIE pochodzi już od powierzchni użytkowej (mnoznik_okna,
		# wciąż obecny w danych, ale od tej zmiany celowo tu nie czytany), tylko od
		# powierzchni fasady -- okna są częścią elewacji, nie podłogi. Baza to ZAWSZE
		# powierzchnia_elewacji przekazana z oblicz_oferte (patrz komentarz przy jej
		# wyliczeniu), niezależnie od tego, czy praca "elewacja" jest wybrana i
		# niezależnie od jej ewentualnego ręcznego m2.
		mnoznik_okna_od_elewacji = _decimal(
			stale.get("mnoznik_okna_od_elewacji"), "mnoznik_okna_od_elewacji"
		)
		m2 = powierzchnia_elewacji * mnoznik_okna_od_elewacji
	else:
		mnozniki = stale.get("mnozniki")
		if not isinstance(mnozniki, dict) or kod not in mnozniki:
			_blad(f"Brak mnożnika powierzchni dla pracy {kod}.")
		m2 = powierzchnia * _decimal(mnozniki[kod], f"mnożnik:{kod}")
	if m2 < _ZERO:
		_blad(f"Powierzchnia pracy {kod} nie może być ujemna.")
	return m2, None


def _kod_katalogowy(kod: str, praca: dict[str, Any]) -> str:
	"""Rozstrzyga kod pozycji katalogowej dla pracy termo, uwzględniając wariant materiału.

	Dla prac bez wariantów (elewacja, okna, drzwi) zwraca kod bez zmian. Dla prac z
	wariantami (patrz _WARIANTY_TERMO) brak materiału albo pusty string oznacza domyślny
	wariant (piana PUR); nieznany materiał jest błędem -- literówka w payloadzie NIE może
	po cichu przeliczyć oferty na domyślny wariant, bo to zmieniłoby koszt/prowizję bez
	wiedzy handlowca.
	"""
	if kod not in _WARIANTY_TERMO:
		return kod
	material = praca.get("material")
	if material is None or (isinstance(material, str) and material.strip() == ""):
		return _DOMYSLNY_WARIANT[kod]
	if material not in _WARIANTY_TERMO[kod]:
		_blad(f"Nieznany wariant materiału {material} dla pracy {kod}.")
	return material


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


_OKRES_LAT_DOMYSLNY = 5
_OKRES_LAT_MIN, _OKRES_LAT_MAX = 1, 10


def _podstawa_trify_raw(dotacja_laczna: Decimal, stale_finansowanie: Any) -> Decimal | None:
	"""Surowa (niezaokrąglona) podstawa raty Trify = dotacja_laczna x trify_udzial.

	Zwraca None, gdy stale_finansowanie nie jest dict-em (w szczególności None) -- ten sam
	kontrakt "brak bloku Single nie jest błędem" co w oblicz_finansowanie(): dopóki nikt nie
	zasiał stałych finansowania, ani wyłączony przełącznik, ani odczyt figury głównej
	(wynik["podstawa_trify"] w oblicz_oferte) nie mają czego liczyć -- to nie jest to samo co
	dotacja_laczna == 0, więc None, nigdy 0, jest tu poprawnym markerem "brak danych". Gdy
	stale_finansowanie JEST dict-em, ale ma zły/brakujący klucz trify_udzial, to nadal głośny
	błąd przez _decimal()/_blad() -- nigdy cichy fallback.
	"""
	if not isinstance(stale_finansowanie, dict):
		return None
	trify_udzial = _decimal(stale_finansowanie.get("trify_udzial"), "trify_udzial")
	return dotacja_laczna * trify_udzial


def _podstawa_trify(dotacja_laczna: Decimal, stale_finansowanie: Any) -> Decimal | None:
	"""Zaokrąglona (publiczna) podstawa raty Trify -- patrz _podstawa_trify_raw().

	Używana zarówno dla wynik["podstawa_trify"] (poziom główny oblicz_oferte, ZAWSZE
	obecna, niezależnie od przełącznika finansowania) jak i dla
	wynik["finansowanie"]["podstawa_trify"] (przez oblicz_finansowanie, który woła
	_podstawa_trify_raw bezpośrednio, żeby rata_trify liczyła się z SUROWEJ, niezaokrąglonej
	podstawy) -- obie figury dostają dokładnie tę samą surową wartość na wejściu do _kwota(),
	więc są identyczne co do grosza.
	"""
	raw = _podstawa_trify_raw(dotacja_laczna, stale_finansowanie)
	return None if raw is None else _kwota(raw)


def oblicz_finansowanie(
	wklad_wlasny: Decimal,
	dotacja_laczna: Decimal,
	wejscie_finansowanie: Any,
	stale_finansowanie: Any,
) -> dict[str, Any] | None:
	"""Liczy blok "Finansowanie" (rata kredytu na wkład własny + rata Trify).

	``wejscie_finansowanie`` równe None/nieobecne oznacza wyłączony przełącznik -- w tym
	KAŻDY payload sprzed tej zmiany (dawne wejścia nie znają tego klucza) -- i zwraca
	None bez dotykania stale_finansowanie (świadomie: włączenie sprawdzania stałych dla
	wyłączonego przełącznika zepsułoby każdy dotychczasowy wywołujący, który jeszcze nie
	zna nowego bloku Single). Brakujące podklucze wejścia (okres_lat, wplata_gotowka)
	dostają wartości domyślne. Wejście OBECNE, ale niepoprawne (zły typ, spoza zakresu,
	ujemne) jest błędem głośnym, nigdy cichym fallbackiem -- patrz _blad().

	rata_trify jest CELOWO niezależna od okres_lat: to osobna rata miesięczna finansowania
	Trify, liczona wyłącznie od podstawy = dotacja_laczna x udział (stała admina), nie rata
	kredytu bankowego -- okres kredytowania na nią nie wpływa. Ta podstawa (podstawa_trify)
	jest liczona przez _podstawa_trify_raw/_podstawa_trify, tą samą funkcją, którą
	oblicz_oferte() woła niezależnie od przełącznika dla wynik["podstawa_trify"] -- obie
	figury są więc zawsze identyczne co do grosza, nawet gdy ten blok w ogóle się nie liczy.

	Oba wejściowe kwoty (wklad_wlasny, dotacja_laczna) to już zaokrąglone publiczne figury
	z oblicz_oferte -- dzięki temu liczby widziane przez klienta w innych częściach oferty
	(wklad_wlasny, dotacja_laczna) i te użyte tutaj są DOKŁADNIE te same, więc suma się
	zgadza handlowcowi na ekranie.
	"""
	if wejscie_finansowanie is None:
		return None
	if not isinstance(wejscie_finansowanie, dict):
		_blad("Nieprawidłowe dane finansowania.")

	okres_lat = wejscie_finansowanie.get("okres_lat", _OKRES_LAT_DOMYSLNY)
	# bool jest podklasą int w Pythonie -- bez tego jawnego odrzucenia True/False
	# przeszłyby test "isinstance(okres_lat, int)" i dały okres_lat=1 albo 0.
	if isinstance(okres_lat, bool) or not isinstance(okres_lat, int):
		_blad("Okres kredytowania musi być liczbą całkowitą lat.")
	if not (_OKRES_LAT_MIN <= okres_lat <= _OKRES_LAT_MAX):
		_blad("Okres kredytowania musi być z zakresu 1-10 lat.")

	wplata_gotowka = _decimal(wejscie_finansowanie.get("wplata_gotowka", 0), "wplata_gotowka")
	if wplata_gotowka < _ZERO:
		_blad("Wpłata gotówką nie może być ujemna.")

	if not isinstance(stale_finansowanie, dict):
		_blad("Brak danych stałych finansowania.")
	oprocentowanie_mies = _decimal(stale_finansowanie.get("oprocentowanie_mies"), "oprocentowanie_mies")
	trify_stawka_za_1000 = _decimal(
		stale_finansowanie.get("trify_stawka_za_1000"), "trify_stawka_za_1000"
	)
	if oprocentowanie_mies < _ZERO:
		_blad("Oprocentowanie raty nie może być ujemne.")

	kwota_kredytu = max(_ZERO, wklad_wlasny - wplata_gotowka)
	n = okres_lat * 12
	i = oprocentowanie_mies / 100
	if kwota_kredytu <= _ZERO:
		rata_wkladu = _ZERO
	elif i == _ZERO:
		rata_wkladu = kwota_kredytu / n
	else:
		mnoznik = (_JEDEN + i) ** n
		rata_wkladu = kwota_kredytu * i * mnoznik / (mnoznik - _JEDEN)

	# stale_finansowanie jest tu już zweryfikowane jako dict (patrz wyżej), więc helper nigdy
	# nie zwróci None -- ta sama funkcja liczy wynik["podstawa_trify"] w oblicz_oferte(),
	# żeby obie figury (tu i tam) były identyczne co do grosza.
	podstawa_trify_raw = _podstawa_trify_raw(dotacja_laczna, stale_finansowanie)
	rata_trify_raw = podstawa_trify_raw / 1000 * trify_stawka_za_1000

	return {
		"okres_lat": okres_lat,
		"wplata_gotowka": _kwota(wplata_gotowka),
		"kwota_kredytu": _kwota(kwota_kredytu),
		"rata_wkladu": _kwota(rata_wkladu),
		"podstawa_trify": _kwota(podstawa_trify_raw),
		"rata_trify": _kwota(rata_trify_raw),
	}


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

	# Powierzchnia fasady jest bazą dla automatycznej powierzchni okien (patrz
	# _powierzchnia_pracy) i jest liczona TU, RAZ, dla całej pętli termo poniżej -- nie
	# per-praca i nie z globali. Liczona ZAWSZE, niezależnie od tego, czy praca "elewacja"
	# jest w ogóle wybrana i niezależnie od jej ewentualnego ręcznego m2: to świadoma
	# decyzja produktowa -- okna to procent CAŁEJ fasady budynku, a nie procent tego
	# kawałka elewacji, który akurat ktoś aktualnie ociepla. Gdyby bazować na policzonym
	# m2 pracy "elewacja", ręczna korekta elewacji po cichu zmieniałaby powierzchnię okien.
	mnozniki_stale = stale.get("mnozniki")
	if not isinstance(mnozniki_stale, dict) or "elewacja" not in mnozniki_stale:
		_blad("Brak mnożnika powierzchni dla pracy elewacja.")
	powierzchnia_elewacji = powierzchnia * _decimal(mnozniki_stale["elewacja"], "mnożnik:elewacja")

	for kod in _PRACE_TERMO:
		praca = _wybrana_praca(prace, kod)
		if praca is None:
			continue
		kod_katalogowy = _kod_katalogowy(kod, praca)
		pozycja = _pozycja(kod_katalogowy, katalog)
		_sprawdz_kategorie(pozycja, "termo", kod_katalogowy)
		# Mnożnik powierzchni pozostaje kluczowany kodem BAZOWYM (mnozniki w stale) -- podanie
		# tu wariantu (np. "strop_piana") rzuciłoby "Brak mnożnika powierzchni".
		m2, liczba_drzwi = _powierzchnia_pracy(kod, praca, powierzchnia, powierzchnia_elewacji, stale)
		# Wybrana praca o zerowej powierzchni nie generuje pozycji na wycenie -- taka linia
		# wnosi zero do netto/brutto/dotacji/prowizji, więc jej pominięcie usuwa wyłącznie
		# szum z dokumentu klienta (np. "Drzwi" z ilością 0 w BOM-ie szansy), nie zmienia
		# żadnej sumy. Rdzeń już tak traktuje grupę CO (patrz test_t_piec_i_zero_grzejnikow:
		# 0 grzejników nie daje linii) -- prace termo miały tu niespójność, którą to
		# ujednolica. Sprawdzenie DZIAŁA WALIDACJĘ po sobie (_powierzchnia_pracy już rzuciła
		# błąd dla ujemnej ilości/powierzchni powyżej), więc pomijamy tylko legalne zera --
		# nie unikamy walidacji. Dla "drzwi" m2 == ilosc_drzwi * m2_na_drzwi, więc zero
		# drzwi daje zerowe m2 -- ten sam warunek pokrywa więc drzwi i prace liczone w m2
		# (w tym przypadek pustej powierzchni budynku, patrz areaOrZero w cpForm.js).
		# Dla "elewacja" pominięcie usuwa też jej koszt_staly (jednorazowy koszt wewnętrzny)
		# -- to celowe: bez wykonanej pracy nie ma kosztu do rozliczenia.
		if m2 == _ZERO:
			continue
		# drzwi/elewacja: kod BAZOWY celowo (nie kod_katalogowy) -- żadna z tych dwóch prac
		# nie ma wariantów materiału, więc rozróżnienie tu jest bez znaczenia; zostaje jawne
		# dla czytelności zamiast milcząco polegać na tym, że oba kody są sobie równe.
		ilosc_rozliczeniowa = liczba_drzwi if kod == "drzwi" else m2
		ilosc_wyswietlana = liczba_drzwi if kod == "drzwi" and pozycja["jednostka"] == "szt" else m2
		jednostka_rozliczeniowa = "szt" if kod == "drzwi" else None
		ilosc_dotowana = None
		if kod == "elewacja":
			# Dotacja na elewację obejmuje tylko 90% jej powierzchni -- okna zajmują resztę
			# fasady, więc fundusz w praktyce dotuje tylko część ściany. netto/brutto/
			# prowizja/koszt zostają na PEŁNEJ powierzchni (klient kupuje i płaci za całą
			# ścianę, ProEnergy rozlicza całość) -- tylko dotacja jest liczona od
			# zmniejszonej ilości. Stąd osobny parametr ilosc_dotowana zamiast zmiany
			# `ilosc` przekazywanego do _linia() (co zredukowałoby też netto/brutto).
			udzial_dotacji_elewacja = _decimal(
				stale.get("udzial_dotacji_elewacja"), "udzial_dotacji_elewacja"
			)
			ilosc_dotowana = m2 * udzial_dotacji_elewacja
		termo_linie.append(
			_linia(
				kod_katalogowy,
				pozycja,
				poziom,
				m2,
				vat,
				ilosc_rozliczeniowa=ilosc_rozliczeniowa,
				ilosc_wyswietlana=ilosc_wyswietlana,
				jednostka_rozliczeniowa=jednostka_rozliczeniowa,
				ilosc_dotowana=ilosc_dotowana,
			)
		)

	if termo_linie and status_limitu == "brak_dotacji":
		for linia in termo_linie:
			linia["_dotacja"] = _ZERO
	if termo_linie and status_limitu == "do_ustalenia":
		raise CPDaneNiekompletne("Limit termomodernizacji jest jeszcze do ustalenia.")

	linie = zrodlo_linie + co_linie + termo_linie
	netto_zrodlo = sum((linia["_netto"] for linia in zrodlo_linie), _ZERO)
	brutto_zrodlo = sum((linia["_brutto"] for linia in zrodlo_linie), _ZERO)
	dotacja_zrodlo = sum((linia["_dotacja"] for linia in zrodlo_linie), _ZERO)
	netto_co = sum((linia["_netto"] for linia in co_linie), _ZERO)
	brutto_co = sum((linia["_brutto"] for linia in co_linie), _ZERO)
	dotacja_co_surowa = sum((linia["_dotacja"] for linia in co_linie), _ZERO)
	netto_termo = sum((linia["_netto"] for linia in termo_linie), _ZERO)
	brutto_termo = sum((linia["_brutto"] for linia in termo_linie), _ZERO)
	dotacja_termo_surowa = sum((linia["_dotacja"] for linia in termo_linie), _ZERO)

	dotacja_co = dotacja_co_surowa
	if co_linie:
		_, _, _, limit_co = _dane_stawki(_pozycja(co_linie[0]["kod"], katalog), poziom, co_linie[0]["kod"])
		if limit_co is not None:
			dotacja_co = min(dotacja_co, limit_co)
		dotacja_co = max(_ZERO, dotacja_co)

	dotacja_termo = dotacja_termo_surowa
	dotacja_ograniczona_o = _ZERO
	if termo_linie and status_limitu == "kwota":
		dotacja_termo = max(_ZERO, min(dotacja_termo_surowa, kwota_limitu))
		dotacja_ograniczona_o = max(_ZERO, dotacja_termo_surowa - dotacja_termo)

	suma_netto = sum((linia["_netto"] for linia in linie), _ZERO)
	suma_prowizji = sum((linia["_prowizja"] for linia in linie), _ZERO)
	suma_nadprowizji_manager = sum((linia["_nadprowizja_manager"] for linia in linie), _ZERO)
	suma_nadprowizji_partner = sum((linia["_nadprowizja_partner"] for linia in linie), _ZERO)
	koszt_calkowity = sum((linia["_koszt"] for linia in linie), _ZERO)
	wklad_zrodlo = max(_ZERO, brutto_zrodlo - dotacja_zrodlo)
	wklad_co = max(_ZERO, brutto_co - dotacja_co)
	wklad_termo = max(_ZERO, brutto_termo - dotacja_termo)

	# --- Regrupowanie prezentacyjne: dotacja per GRUPA zakresu prac, nie per pozycja ---
	# Program dotuje per pozycję, ale limituje per grupę; jego dokumenty nigdzie nie
	# definiują, jak rozbić limit grupy z powrotem na pozycje, więc jakakolwiek kwota per
	# pozycja byłaby wymyślona. Stąd wynik["grupy"] zamiast wynik["linie"][i]["dotacja"].
	#
	# Pozycja "cwu" ma w katalogu kategoria="zrodlo" (bo TAK liczy się jej limit -- źródło
	# nie ma ograniczenia grupowego), ale w prezentacji programu CWU dzieli jeden wiersz i
	# jeden limit z centralnym ogrzewaniem. Dlatego tutaj -- WYŁĄCZNIE na poziomie
	# prezentacji, PO policzeniu limitów powyżej -- przenosimy jej kwoty (netto/brutto/
	# dotacja) z grupy "zrodlo" do grupy "co". Nie zmieniamy `kategoria` w katalogu ani
	# logiki limitów wyżej: zrobienie tego na poziomie kategorii przesunęłoby, który limit
	# obowiązuje pozycji cwu, i mogłoby zmienić wycenę.
	cwu_linia = next((linia for linia in zrodlo_linie if linia["kod"] == "cwu"), None)
	cwu_dotacja = cwu_linia["_dotacja"] if cwu_linia is not None else _ZERO
	cwu_netto = cwu_linia["_netto"] if cwu_linia is not None else _ZERO
	cwu_brutto = cwu_linia["_brutto"] if cwu_linia is not None else _ZERO
	zrodlo_ma_linie_bez_cwu = any(linia["kod"] != "cwu" for linia in zrodlo_linie)

	# Kolejność (kod, kwota_dotacji_surowa, netto_surowe, brutto_surowe, czy_grupa_obecna).
	# Grupa "zrodlo" nie ma limitu, więc odjęcie cwu jest tu zawsze bezpieczne (nigdy nie
	# robi kwoty ujemnej -- cwu_dotacja jest podzbiorem dotacja_zrodlo).
	_grupy_dane = (
		("zrodlo", "Źródło ciepła", dotacja_zrodlo - cwu_dotacja, netto_zrodlo - cwu_netto, brutto_zrodlo - cwu_brutto, zrodlo_ma_linie_bez_cwu),
		("co", "Centralne Ogrzewanie i Ciepła Woda Użytkowa", dotacja_co + cwu_dotacja, netto_co + cwu_netto, brutto_co + cwu_brutto, bool(co_linie) or cwu_linia is not None),
		("termo", "Termomodernizacja", dotacja_termo, netto_termo, brutto_termo, bool(termo_linie)),
	)

	# Sumowanie kumulatywne (zamiast zaokrąglania każdej grupy z osobna) jest tu konieczne:
	# dotacja_laczna niżej to _kwota(suma trzech SUROWYCH kwot), a niezależne zaokrąglenie
	# każdej grupy osobno mogłoby dać sumę różniącą się o grosz od dotacja_laczna (klasyczny
	# problem apportionment rounding -- możliwy tu, bo powierzchnia budynku i mnożniki prac
	# mogą mieć więcej niż 2 miejsca po przecinku). Ta metoda gwarantuje dokładną zgodność
	# sumy grup z dotacja_laczna w każdym przypadku, bo różnica jest telescopująca.
	grupy: list[dict[str, Any]] = []
	_suma_surowa = _ZERO
	_suma_zaokraglona = _ZERO
	for kod_grupy, nazwa_grupy, dotacja_raw, netto_raw, brutto_raw, obecna in _grupy_dane:
		_suma_surowa += dotacja_raw
		_nowa_suma_zaokraglona = _kwota(_suma_surowa)
		dotacja_grupy = _nowa_suma_zaokraglona - _suma_zaokraglona
		_suma_zaokraglona = _nowa_suma_zaokraglona
		if not obecna:
			continue
		grupy.append(
			{
				"kod": kod_grupy,
				"nazwa": nazwa_grupy,
				"dotacja": dotacja_grupy,
				"netto": _kwota(netto_raw),
				"brutto": _kwota(brutto_raw),
			}
		)

	# Rozbicie kosztów/prowizji per pozycja budowane PRZED czyszczeniem prywatnych pól przez
	# _zaokragl_wynik. Żyje wyłącznie wewnątrz wynik["wewnetrzne"], bo crm/api/czyste_powietrze.py
	# usuwa całe to poddrzewo dla nie-adminów jednym wynik.pop("wewnetrzne", None) — umieszczenie
	# tych danych na wynik["linie"] ujawniłoby koszty i marże handlowcom terenowym. Od
	# volteo_cp_create_deal (crm/api/czyste_powietrze.py) to poddrzewo jest DODATKOWO
	# zrzucane do trwałego snapshotu w permlevel-2 custom_koszty_json (schema v1,
	# crm/koszty/rdzen.py::zbuduj_snapshot_cp) — nadal nigdy do wynik["linie"].
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
			"stawka_nadprowizji_manager": _kwota(linia["_stawka_nadprowizji_manager"]),
			"nadprowizja_manager": _kwota(linia["_nadprowizja_manager"]),
			"stawka_nadprowizji_partner": _kwota(linia["_stawka_nadprowizji_partner"]),
			"nadprowizja_partner": _kwota(linia["_nadprowizja_partner"]),
			"prowizja_pelna": _kwota(linia["_prowizja"] + linia["_nadprowizja_manager"] + linia["_nadprowizja_partner"]),
		}
		for linia in linie
	]

	prowizja_handlowa = _kwota(suma_prowizji)
	prowizja_pelna_calkowita = _kwota(suma_prowizji + suma_nadprowizji_manager + suma_nadprowizji_partner)
	marza = _kwota(suma_netto - koszt_calkowity)
	# suma_brutto liczona z JUŻ zaokrąglonych linia["brutto"] (nie z surowego brutto_zrodlo/
	# brutto_co/brutto_termo ani z wklad_wlasny + dotacja_laczna) -- to jedyna wersja
	# gwarantująca, że klient patrzący na linie zawsze doliczy się do tej sumy. wklad_wlasny
	# jest przycinany do zera per grupa (patrz max(_ZERO, ...) wyżej), więc jego suma z
	# dotacja_laczna NIE jest w ogólności tożsama z sumą brutto.
	suma_brutto = _kwota(sum((linia["brutto"] for linia in linie), _ZERO))
	# Figury publiczne, policzone RAZ tutaj -- oblicz_finansowanie() dostaje dokładnie te
	# same, już zaokrąglone wartości, które trafiają do wynik["wklad_wlasny"] i
	# wynik["dotacja_laczna"] niżej, żeby liczby w bloku "Finansowanie" zgadzały się
	# handlowcowi z resztą ekranu co do grosza.
	wklad_wlasny = _kwota(wklad_zrodlo + wklad_co + wklad_termo)
	dotacja_laczna = _kwota(dotacja_zrodlo + dotacja_co + dotacja_termo)
	finansowanie = oblicz_finansowanie(
		wklad_wlasny, dotacja_laczna, wejscie.get("finansowanie"), stale.get("finansowanie")
	)
	# Podstawa Trify liczona ZAWSZE, niezależnie od przełącznika finansowania (wejscie.get
	# ("finansowanie") może być None) -- decyzja właściciela: szansa ma pokazywać kwotę
	# Trify nawet gdy handlowiec nie włączył bloku finansowania. None znaczy WYŁĄCZNIE
	# "stałe finansowania jeszcze nie zasiane na Volteo CP Stale" (Single bez tego bloku),
	# nigdy "dotacja_laczna wynosi zero" -- 0 jest tu poprawną, policzoną wartością.
	podstawa_trify = _podstawa_trify(dotacja_laczna, stale.get("finansowanie"))
	wynik = {
		"suma_brutto": suma_brutto,
		"wklad_wlasny": wklad_wlasny,
		# "prowizja_handlowa" ZOSTAJE niezmienione (kompatybilność wsteczna z bramką Vue
		# `result.prowizja_handlowa != null` i z `custom_cp_prowizja_handlowa`) -- nowe
		# nadprowizje Managera/Partnera żyją wyłącznie w "prowizje" (publiczne) i
		# "wewnetrzne" (koszty), nigdy nie modyfikują to pole.
		"prowizja_handlowa": prowizja_handlowa,
		"prowizje": {
			"handlowiec": prowizja_handlowa,
			"nadprowizja_manager": _kwota(suma_nadprowizji_manager),
			"nadprowizja_partner": _kwota(suma_nadprowizji_partner),
			"suma": prowizja_pelna_calkowita,
		},
		"linie": linie,
		"grupy": grupy,
		"dotacja_laczna": dotacja_laczna,
		"dotacja_ograniczona_o": _kwota(dotacja_ograniczona_o),
		# Podstawa raty Trify -- publiczna, ZAWSZE obecna (niezależnie od przełącznika
		# finansowania, patrz komentarz przy jej wyliczeniu wyżej). None wyłącznie gdy stałe
		# finansowania jeszcze nie istnieją na Volteo CP Stale -- nigdy 0 jako marker braku.
		"podstawa_trify": podstawa_trify,
		# Blok "Finansowanie" (rata kredytu na wkład własny + rata Trify) -- publiczny,
		# widoczny dla handlowca terenowego, celowo POZA "wewnetrzne" (nie niesie kosztów
		# ani marż). None gdy przełącznik jest wyłączony -- patrz oblicz_finansowanie().
		"finansowanie": finansowanie,
		"wewnetrzne": {
			"koszt_calkowity": _kwota(koszt_calkowity),
			"marza": marza,
			"prowizja_handlowa": prowizja_handlowa,
			"nadprowizja_manager": _kwota(suma_nadprowizji_manager),
			"nadprowizja_partner": _kwota(suma_nadprowizji_partner),
			"prowizja_pelna": prowizja_pelna_calkowita,
			# Zmiana semantyczna (decyzja właściciela 2026-08-31): "zysk" liczy się teraz jako
			# marza - prowizja_pelna (handlowiec + obie nadprowizje), nie tylko marza -
			# prowizja_handlowa. Gdy realne stawki nadprowizji zostaną zasiane, zysk i
			# zysk_plan (crm/koszty/rdzen.py) SPADNĄ o te kwoty -- to zamierzone: reprezentują
			# realny koszt struktury prowizyjnej. Przy stawkach zerowych (stan seed) liczby są
			# identyczne z zachowaniem sprzed tej zmiany.
			"zysk": marza - prowizja_pelna_calkowita,
			"linie": linie_wewnetrzne,
		},
	}
	return _zaokragl_wynik(linie, wynik)
