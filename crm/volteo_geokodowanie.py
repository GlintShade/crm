# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Geokodowanie adresu leada, frappe-free (issue #102, decyzja właściciela
2026-09-10: łańcuch GUGiK UUG -> OSM Nominatim -> dotychczasowy centroid
kodu pocztowego).

Zero `import frappe`, zero I/O sieciowego wewnątrz modułu: cały HTTP
wchodzi przez wstrzykiwaną funkcję `http_get(url, params, headers) -> dict | None`,
tak jak `crm/integrations/autenti/logika.py` trzyma logikę decyzyjną z dala
od `requests` i od `crm/integrations/autenti/client.py`. Wołający (hook
`on_update`, przycisk admina, wsad `ops/crm-leady-geokodowanie.py`) dostarcza
prawdziwe `http_get` przez `requests.get(url, params=..., headers=...,
timeout=(10, 30)).json()`; testy tego modułu dostarczają nagrane odpowiedzi.

Współrzędne liczone są RAZ na adres: `hash_adresu()` daje skrót czterech pól
adresu, a wołający porównuje go z zapisanym `custom_geo_adres_hash`, żeby
zdecydować, czy adres się zmienił od ostatniego udanego geokodowania -
ten moduł sam niczego nie zapisuje i nie wie nic o Frappe/CRM Lead.

Łańcuch (`geokoduj`), rozszerzony QA #102 rundą 2 (2026-09-18) z dwóch do
czterech kroków:
  1. GUGiK UUG (`https://services.gugik.gov.pl/uug/`), pełny adres - darmowy,
     bez limitu zapytań, oficjalne dane adresowe państwa; próbowany pierwszy.
  2. GUGiK, hipoteza przysiółka (`"<Ulica> <Nr>"` bez miejscowości) - adresy
     wiejskie, gdzie `Ulica` to nazwa przysiółka/wsi a `Miejscowość` to
     nazwa poczty (np. "Zalesie 14, 77-400 Święta"); wymaga kodu pocztowego
     leada, akceptowane wyłącznie po dokładnej zgodności kodu.
  3. OSM Nominatim (`https://nominatim.openstreetmap.org/search`) - wymaga
     nagłówka `User-Agent` z adresem kontaktowym i maks. 1 zapytania/s
     (polityka użytkowania Nominatim); próbowany tylko gdy kroki 1-2 nie
     dały wystarczającego trafienia, i tylko gdy `uzyj_nominatim=True`.
  4. GUGiK, sama miejscowość (`type == "city"`, dokładność `"miejscowosc"`)
     - ostatnia deska ratunku przed `None`: środek miejscowości jest lepszy
     niż całkowity brak (175 leadów lokalnie nie ma nawet centroidu kodu).
  5. Centroid kodu pocztowego (`Postal Code.lat`/`lng`, już zasilony przez
     `ops/crm-kody-geo.py` z GeoNames od b52) - poza tym modułem: gdy
     WSZYSTKIE cztery kroki wyżej zwrócą `None`, wołający zostawia
     dotychczasowe `custom_lat`/`custom_lng` (centroid) i zapisuje tylko
     `custom_geo_dokladnosc = "kod"`.

`geokoduj()` nigdy nie rzuca: każdy wyjątek z `http_get` (sieciowy, JSON,
cokolwiek) jest łapany i traktowany jak brak trafienia, więc jeden zepsuty
adres w wsadzie nie przerywa całej partii.
"""

import hashlib
import math
from typing import NamedTuple

GUGIK_URL = "https://services.gugik.gov.pl/uug/"
"""GUGiK UUG (Usługa Udostępniania Uniwersalnego), format zapytania GetAddress."""

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

NOMINATIM_USER_AGENT = "VolteoCRM/1.0 (kontakt: crm@proenergy.pro)"
"""Wymagany przez politykę użytkowania Nominatim: identyfikowalny User-Agent
z adresem kontaktowym, nie domyślny `python-requests/...`."""

DOKLADNOSCI = ("adres", "ulica", "miejscowosc", "kod", "brak")
"""Wartości `custom_geo_dokladnosc` na `CRM Lead`, od najdokładniejszej do
najmniej: `adres` (numer budynku), `ulica`, `miejscowosc`, `kod` (centroid
kodu pocztowego, sprzed geokodowania po adresie), `brak` (żadna z powyższych,
lead zostaje bez współrzędnych)."""

ZRODLA = ("gugik", "osm", "kod", "reczne")
"""Wartości `custom_geo_zrodlo`: skąd wzięto współrzędne. `reczne` nigdy nie
jest nadpisywane przez ten moduł ani przez wołających go - to jedyna wartość
zarezerwowana dla ręcznej korekty admina."""

_POLSKA_LAT = (49.0, 55.0)
_POLSKA_LNG = (14.0, 24.2)
"""Zgrubny prostokąt otaczający Polskę. Próg jakości: wynik spoza tego
zakresu (błąd parsowania po stronie dostawcy, pomyłka w geokoderze) jest
odrzucany, tak jakby dostawca nie zwrócił żadnego trafienia."""

_PROMIEN_NIEJEDNOZNACZNOSCI_M = 300.0
"""Gdy GUGiK zwraca wiele adresów o tym samym kodzie pocztowym (rzadkie, ale
możliwe przy błędnym/nieaktualnym kodzie w danych leada), przyjmujemy
pierwszy tylko jeśli wszystkie kandydatury leżą praktycznie w tym samym
miejscu - inaczej zgadywanie który to adres byłoby gorsze niż brak wyniku."""


class Adres(NamedTuple):
	"""Cztery pola adresu leada, dokładnie te, które niesie `CRM Lead`
	(`custom_install_address`, `custom_nr_domu`, `custom_install_postal_code`,
	`custom_install_city`). Puste pola to `""`, nigdy `None` - wołający
	odpowiada za normalizację przed zbudowaniem `Adres`."""

	ulica: str
	nr_domu: str
	kod: str
	miejscowosc: str


class Wynik(NamedTuple):
	"""Wynik udanego geokodowania. `lat`/`lng` w WGS84 (stopnie dziesiętne),
	`dokladnosc` jedna z `DOKLADNOSCI` (nigdy `"kod"`/`"brak"` stąd - te dwie
	wartości nadaje wyłącznie wołający, gdy ten moduł zwróci `None`),
	`zrodlo` jedna z `("gugik", "osm")`."""

	lat: float
	lng: float
	dokladnosc: str
	zrodlo: str


def _w_polsce(lat: float, lng: float) -> bool:
	return _POLSKA_LAT[0] <= lat <= _POLSKA_LAT[1] and _POLSKA_LNG[0] <= lng <= _POLSKA_LNG[1]


def _odleglosc_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
	"""Odległość haversine w metrach - wystarczająco dokładna na 300 m."""
	promien_ziemi_m = 6371000.0
	f1, f2 = math.radians(lat1), math.radians(lat2)
	delta_f = math.radians(lat2 - lat1)
	delta_l = math.radians(lng2 - lng1)
	a = math.sin(delta_f / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(delta_l / 2) ** 2
	return 2 * promien_ziemi_m * math.asin(math.sqrt(min(1.0, a)))


def _wszystkie_w_promieniu(kandydaci: list[dict], promien_m: float) -> bool:
	try:
		punkty = [(float(c["y"]), float(c["x"])) for c in kandydaci]
	except (KeyError, TypeError, ValueError):
		return False
	bazowy_lat, bazowy_lng = punkty[0]
	return all(_odleglosc_m(bazowy_lat, bazowy_lng, lat, lng) <= promien_m for lat, lng in punkty)


def _wynik_z_kandydata_gugik(kandydat: dict, dokladnosc: str, zrodlo: str = "gugik") -> "Wynik | None":
	try:
		lat = float(kandydat["y"])
		lng = float(kandydat["x"])
	except (KeyError, TypeError, ValueError):
		return None
	return Wynik(lat=lat, lng=lng, dokladnosc=dokladnosc, zrodlo=zrodlo)


def _dokladnosc_gugik_adres(kandydat: dict) -> str:
	if kandydat.get("number"):
		return "adres"
	if kandydat.get("street"):
		return "ulica"
	return "miejscowosc"


def _wies_bez_ulicy(adres: Adres) -> bool:
	"""Wieś bez ulicy: pole Ulica puste, albo równe Miejscowości bez
	rozróżniania wielkości liter (import zdarza się kopiować nazwę wsi do
	obu pól - patrz `crm/volteo_leady_import.py`, reguła "Ulica = Miejscowość"
	z issue #116)."""
	ulica = (adres.ulica or "").strip()
	miejscowosc = (adres.miejscowosc or "").strip()
	return not ulica or ulica.lower() == miejscowosc.lower()


def zapytanie_gugik(adres: Adres) -> str | None:
	"""Buduje wartość parametru `address` zapytania GUGiK UUG GetAddress.

	Cztery kształty, od najbardziej do najmniej precyzyjnego:
	  - wieś bez ulicy, z numerem: `"<Miejscowość> <Nr>"` (GUGiK NIE akceptuje
	    tu przecinka - "Sypniewo, 10" nie trafia, "Sypniewo 10" trafia);
	  - prawdziwa ulica z numerem: `"<Miejscowość>, <Ulica> <Nr>"` (przecinek
	    WYMAGANY - "Sypniewo Miodowa 10" bez przecinka nie trafia, sprawdzone
	    2026-09-18);
	  - sama prawdziwa ulica, bez numeru: `"<Miejscowość>, <Ulica>"`;
	  - tylko miejscowość (i wieś-bez-ulicy bez numeru): `"<Miejscowość>"`.
	Brak miejscowości -> `None`, bo bez niej nawet centroid gminy jest
	niewiarygodny (Polska ma wiele identycznie nazwanych miejscowości).
	"""
	miejscowosc = (adres.miejscowosc or "").strip()
	if not miejscowosc:
		return None

	ulica = (adres.ulica or "").strip()
	nr_domu = (adres.nr_domu or "").strip()
	wies = _wies_bez_ulicy(adres)

	if wies and nr_domu:
		return f"{miejscowosc} {nr_domu}"
	if not wies and ulica and nr_domu:
		return f"{miejscowosc}, {ulica} {nr_domu}"
	if not wies and ulica:
		return f"{miejscowosc}, {ulica}"
	return miejscowosc


def _wojewodztwo_pasuje(kandydat: dict, wojewodztwo: str) -> bool:
	return (kandydat.get("voivodeship") or "").strip().lower() == wojewodztwo.strip().lower()


def _bez_prefiksu_ulicy(tekst: str) -> str:
	"""Zdejmuje prefiks „ul.”/„ulica” (bez wielkości liter) z nazwy ulicy,
	tak jak zwraca go czasem GUGiK (np. `"ulica Marszałkowska"`) - żeby
	porównanie z `adres.ulica` (zwykle bez prefiksu) nie fałszowało
	niedopasowania."""
	tekst = tekst.strip()
	for prefiks in ("ulica ", "ul. ", "ul "):
		if tekst.lower().startswith(prefiks):
			return tekst[len(prefiks) :].strip()
	return tekst


def _numer_pasuje(kandydat_number: str | None, nr_domu: str) -> bool:
	"""Porównanie numeru domu, normalizacja: bez spacji, bez wielkości liter.
	Puste == puste jest DOPASOWANIEM (nie odrzuceniem) - zapytanie "sama
	ulica" (`zapytanie_gugik`, wariant bez numeru) celowo nie niesie numeru,
	a GUGiK w takich odpowiedziach zwraca `number: null` - to zgodność, nie
	brak danych."""
	a = (kandydat_number or "").strip().lower().replace(" ", "")
	b = (nr_domu or "").strip().lower().replace(" ", "")
	return a == b


def _kandydat_adresowo_pasuje(kandydat: dict, adres: Adres) -> bool:
	"""Krok 1 nowej reguły QA #102 (runda 2, 2026-09-18) dla `type == "address"`:
	kandydat wchodzi do dalszego rozstrzygania TYLKO gdy jego `street`+`number`
	faktycznie odpowiadają zapytaniu - GUGiK potrafi dopasować fuzzy inną
	ulicę o podobnej pisowni w tym samym zapytaniu (sprawdzone 2026-09-18:
	"Bielsko-Biała, Miernicza 35" zwraca DWA wyniki, `Miernicza 35` i fuzzy
	`Sternicza 35`, każdy z innym kodem pocztowym - bez tego filtra oba
	trafiałyby do dalszej logiki na równych prawach).

	Wieś bez ulicy (`adres.ulica` puste albo równe `adres.miejscowosc`):
	kandydat pasuje, gdy jego `street` jest puste ORAZ `city` == miejscowość
	leada (bez wielkości liter). Prawdziwa ulica: kandydat pasuje, gdy jego
	`street` (po zdjęciu prefiksu „ul.”/„ulica” i normalizacji wielkości
	liter/białych znaków) == `adres.ulica`. W obu przypadkach `number` musi
	się zgadzać z `adres.nr_domu` (normalizacja: bez spacji, bez wielkości
	liter). Kandydat z pustym `street`, gdy zapytanie MIAŁO ulicę, zawsze
	odpada - GUGiK czasem zwraca dopasowanie samej miejscowości jako
	fallback w tym samym zapytaniu adresowym."""
	if not _numer_pasuje(kandydat.get("number"), adres.nr_domu):
		return False

	ulica = (adres.ulica or "").strip()
	miejscowosc = (adres.miejscowosc or "").strip()
	kandydat_street = kandydat.get("street")

	if _wies_bez_ulicy(adres):
		return not kandydat_street and (kandydat.get("city") or "").strip().lower() == miejscowosc.lower()

	if not kandydat_street:
		return False
	return _bez_prefiksu_ulicy(kandydat_street).lower() == ulica.lower()


def parsuj_gugik(
	odpowiedz: dict | None,
	adres: Adres,
	*,
	powiat: str | None = None,
	wojewodztwo: str | None = None,
) -> "Wynik | None":
	"""Rozbiera odpowiedź GUGiK UUG GetAddress na `Wynik` albo `None`.

	`powiat`/`wojewodztwo` (oba opcjonalne - dane leada mogą, ale nie muszą
	je nieść) rozstrzygają tylko dwuznaczność `type == "city"`. Nieznany/
	nieobsłużony `type` (np. `"street"`, gdy GUGiK dopasuje samą ulicę bez
	adresu ani miejscowości) -> `None`; obsługiwane są wyłącznie `"address"`
	i `"city"`, zgodnie ze specyfikacją issue #102.

	`type == "address"` - dwa sita, w kolejności (poprawki QA #102, runda 1 i
	runda 2, 2026-09-18):

	1. Street+number: kandydat wchodzi do gry TYLKO gdy jego `street`/`number`
	   faktycznie odpowiadają zapytaniu (patrz `_kandydat_adresowo_pasuje`) -
	   odrzuca fuzzy-dopasowania GUGiK do INNEJ ulicy w tym samym zapytaniu
	   ("Bielsko-Biała, Miernicza 35" zwraca też fuzzy `Sternicza 35`).
	2. Kod pocztowy (tylko gdy lead go ma): wśród kandydatów, którzy przeszli
	   sito 1, kandydaci z `code == adres.kod` mają pierwszeństwo. Gdy żaden
	   nie pasuje kodem, ALE po sicie 1 został DOKŁADNIE jeden kandydat, a
	   jego `city` zgadza się z miejscowością leada -> przyjmowany mimo
	   różnicy kodu (kody bywają per ulica, lead ma często kod ogólny
	   miasta). Gdy po sicie 1 zostało wielu kandydatów i żaden nie pasuje
	   kodem -> `None` (nie ma jak rozstrzygnąć, które miejsce to właściwe -
	   nazwy miejscowości/ulic się powtarzają, "Zakrzewo 45" istnieje w
	   ośmiu różnych województwach). Lead bez kodu wcale -> sito 2 pomijane
	   całkowicie, zachowanie jak przed poprawką QA #102-1.

	Promień 300 m rozstrzyga wyłącznie WŚRÓD kandydatów, którzy przeszły oba
	sita powyżej i nadal jest ich więcej niż jeden (duplikat rekordu w
	GUGiK pod tym samym adresem, nie różne miejsca).

	`type == "city"` (poprawka QA #102-2): przy wielu kandydatach kolejność
	sit jest stała - najpierw `voivodeship` (gdy podane), potem `county`
	wśród tego, co zostało (gdy podane); jeśli po obu krokach zostaje
	dokładnie jeden kandydat -> `Wynik`, inaczej `None`. Gdy kandydat jest
	od początku tylko jeden, a lead ma województwo, które się nie zgadza z
	`voivodeship` kandydata -> `None` (ta sama logika bezpieczeństwa
	powtarzających się nazw co przy `"address"` wyżej; `powiat` NIE jest
	sprawdzany w tej gałęzi z jednym kandydatem, tak jak przed poprawką).
	"""
	if not isinstance(odpowiedz, dict):
		return None
	wyniki = odpowiedz.get("results")
	if not wyniki:
		return None

	typ = odpowiedz.get("type")
	kandydaci = list(wyniki.values())

	if typ == "address":
		# Krok 1 (QA #102, runda 2): tylko kandydaci, których street+number
		# faktycznie odpowiadają zapytaniu - odrzuca fuzzy-dopasowania GUGiK
		# (patrz docstring `_kandydat_adresowo_pasuje`).
		kandydaci = [k for k in kandydaci if _kandydat_adresowo_pasuje(k, adres)]
		if not kandydaci:
			return None

		if adres.kod:
			po_kodzie = [k for k in kandydaci if k.get("code") == adres.kod]
			if po_kodzie:
				kandydaci = po_kodzie
			elif len(kandydaci) == 1:
				# Dokładnie jeden kandydat po dopasowaniu ulicy/numeru, ale z
				# innym kodem niż lead - akceptowany, gdy jego `city` zgadza
				# się z miejscowością leada (kody w miastach bywają per ulica,
				# lead ma często kod ogólny miasta - sprawdzone 2026-09-18,
				# "Bielsko-Biała, Miernicza 35": lead 43-300, właściwa ulica
				# 43-318). Gdy `city` się NIE zgadza, to prawdziwa kolizja
				# nazw (różne miejscowości o tej samej nazwie) - `None`.
				jedyny = kandydaci[0]
				if (jedyny.get("city") or "").strip().lower() != (adres.miejscowosc or "").strip().lower():
					return None
			else:
				# Wielu kandydatów po dopasowaniu ulicy/numeru, żaden nie ma
				# kodu leada - nie ma jak rozstrzygnąć, które to miejsce.
				return None

		if len(kandydaci) == 1:
			kandydat = kandydaci[0]
			return _wynik_z_kandydata_gugik(kandydat, _dokladnosc_gugik_adres(kandydat))
		if len(kandydaci) > 1 and _wszystkie_w_promieniu(kandydaci, _PROMIEN_NIEJEDNOZNACZNOSCI_M):
			kandydat = kandydaci[0]
			return _wynik_z_kandydata_gugik(kandydat, _dokladnosc_gugik_adres(kandydat))
		return None

	if typ == "city":
		if len(kandydaci) == 1:
			kandydat = kandydaci[0]
			if wojewodztwo and not _wojewodztwo_pasuje(kandydat, wojewodztwo):
				return None
			return _wynik_z_kandydata_gugik(kandydat, "miejscowosc")

		if wojewodztwo:
			kandydaci = [k for k in kandydaci if _wojewodztwo_pasuje(k, wojewodztwo)]
		if powiat:
			kandydaci = [
				k for k in kandydaci if (k.get("county") or "").strip().lower() == powiat.strip().lower()
			]
		if len(kandydaci) == 1:
			return _wynik_z_kandydata_gugik(kandydaci[0], "miejscowosc")
		return None

	return None


def zapytanie_nominatim(adres: Adres) -> dict:
	"""Buduje parametry structured search Nominatim.

	`format=jsonv2`, `countrycodes=pl`, `limit=1` zawsze. `postalcode`/`city`
	dołączane, gdy niepuste. Wieś bez ulicy: `street = "<Nr> <Miejscowość>"`
	(dokładnie tak samo jak zapytanie GUGiK bez przecinka - to konwencja
	Nominatim dla adresów bez nazwy ulicy), tylko gdy jest numer; bez numeru
	pole `street` jest pomijane i zapytanie opiera się na `city`+`postalcode`
	(dokładność `miejscowosc`, nie gorsza niż nic). Prawdziwa ulica: `street
	= "<Ulica> <Nr>"` albo sama `"<Ulica>"` bez numeru.
	"""
	parametry: dict = {"format": "jsonv2", "countrycodes": "pl", "limit": 1}

	kod = (adres.kod or "").strip()
	if kod:
		parametry["postalcode"] = kod

	miejscowosc = (adres.miejscowosc or "").strip()
	if miejscowosc:
		parametry["city"] = miejscowosc

	ulica = (adres.ulica or "").strip()
	nr_domu = (adres.nr_domu or "").strip()
	wies = _wies_bez_ulicy(adres)

	if wies:
		if nr_domu and miejscowosc:
			parametry["street"] = f"{nr_domu} {miejscowosc}"
	elif ulica and nr_domu:
		parametry["street"] = f"{ulica} {nr_domu}"
	elif ulica:
		parametry["street"] = ulica

	return parametry


def _dokladnosc_z_rank(place_rank: int) -> str | None:
	"""`place_rank` Nominatim -> nasza dokładność. Progi wg issue #102:
	30 = budynek/adres, 26..29 = ulica, 16..25 = miejscowość/gmina; wszystko
	poniżej 16 (powiat, województwo, kraj) jest za grube, żeby cokolwiek
	znaczyć na mapie D2D, więc traktowane jak brak trafienia."""
	if place_rank >= 30:
		return "adres"
	if 26 <= place_rank <= 29:
		return "ulica"
	if 16 <= place_rank <= 25:
		return "miejscowosc"
	return None


def parsuj_nominatim(lista: list | None, adres: Adres) -> "Wynik | None":
	"""Rozbiera odpowiedź Nominatim `search` (lista wyników, `limit=1` więc
	najwyżej jeden element) na `Wynik` albo `None`.

	Poprawka QA #102-3 (2026-09-18): gdy lead MA kod pocztowy, `display_name`
	MUSI go zawierać - to jedyne akceptowalne dopasowanie, analogicznie do
	`parsuj_gugik` (`type == "address"`) wyżej. Nazwy miejscowości się
	powtarzają, więc sprawdzanie miejscowości JAKO ALTERNATYWY dla kodu
	(dawne zachowanie: kod LUB miejscowość) przepuszczało dokładnie ten sam
	błąd - trafienie w złą miejscowość o tej samej nazwie, ale z pasującym
	tekstem miejscowości w `display_name` mimo zupełnie innego kodu. Kod
	pocztowy rozstrzyga sam, gdy jest; miejscowość jest sprawdzana TYLKO gdy
	lead nie ma kodu wpisanego wcale - to jedyny przypadek, w którym nie ma
	nic silniejszego do sprawdzenia."""
	if not isinstance(lista, list) or not lista:
		return None
	kandydat = lista[0]

	try:
		lat = float(kandydat["lat"])
		lng = float(kandydat["lon"])
		place_rank = int(kandydat.get("place_rank", 0))
	except (KeyError, TypeError, ValueError):
		return None

	dokladnosc = _dokladnosc_z_rank(place_rank)
	if dokladnosc is None:
		return None

	display_name = (kandydat.get("display_name") or "").lower()
	kod = (adres.kod or "").strip().lower()
	if kod:
		if kod not in display_name:
			return None
	else:
		miejscowosc = (adres.miejscowosc or "").strip().lower()
		if not miejscowosc or miejscowosc not in display_name:
			return None

	return Wynik(lat=lat, lng=lng, dokladnosc=dokladnosc, zrodlo="osm")


def hash_adresu(adres: Adres) -> str:
	"""Skrót SHA-1 czterech pól adresu (po `strip().lower()`, złączonych
	`"|"`), do porównania z zapisanym `custom_geo_adres_hash` - decyduje, czy
	adres zmienił się od ostatniego udanego geokodowania. Kolejność pól jest
	stała (`ulica`, `nr_domu`, `kod`, `miejscowosc`), więc ten sam `Adres`
	zawsze daje ten sam skrót niezależnie od tego, skąd woła się tę funkcję."""
	czesci = [
		(adres.ulica or "").strip().lower(),
		(adres.nr_domu or "").strip().lower(),
		(adres.kod or "").strip().lower(),
		(adres.miejscowosc or "").strip().lower(),
	]
	return hashlib.sha1("|".join(czesci).encode("utf-8")).hexdigest()


def zapytanie_gugik_przysiolek(adres: Adres) -> str | None:
	"""Zapytanie GUGiK dla hipotezy przysiółka (QA #102, runda 2, 2026-09-18):
	adresy wiejskie typu "Zalesie 14, 77-400 Święta" mają w `Ulica` nazwę
	przysiółka/wsi, a w `Miejscowość` nazwę poczty - zapytanie pełnego adresu
	("Święta, Zalesie 14") wtedy nie trafia NIC, bo GUGiK nie zna takiej
	kombinacji miejscowość+ulica. Ten krok próbuje samą parę
	"<Ulica> <Nr>" (bez miejscowości), traktując `Ulica` jak nazwę
	miejscowości - sprawdzone 2026-09-18, GUGiK rozpoznaje przysiółki jako
	samodzielne miejscowości adresowe.

	Zwraca `None` (pomiń krok), gdy: lead nie ma kodu pocztowego (bez kodu
	nie ma jak bezpiecznie zweryfikować, które z wielu identycznie
	nazwanych miejsc to właściwe - patrz `parsuj_gugik_przysiolek`), `Ulica`
	pusta, `Ulica` równa `Miejscowość` (to zwykła wieś-bez-ulicy, już
	obsłużona w `zapytanie_gugik`, nie hipoteza przysiółka), albo `Nr`
	pusty."""
	if not adres.kod:
		return None
	ulica = (adres.ulica or "").strip()
	nr_domu = (adres.nr_domu or "").strip()
	miejscowosc = (adres.miejscowosc or "").strip()
	if not ulica or not nr_domu:
		return None
	if ulica.lower() == miejscowosc.lower():
		return None
	return f"{ulica} {nr_domu}"


def parsuj_gugik_przysiolek(odpowiedz: dict | None, adres: Adres) -> "Wynik | None":
	"""Rozbiera odpowiedź GUGiK dla zapytania przysiółka. Celowo BEZ
	leniencji "jeden kandydat + city pasuje" z `parsuj_gugik` powyżej - tu
	nie ma miejscowości do porównania (zapytanie to sama nazwa przysiółka),
	więc jedynym bezpiecznym sitem jest DOKŁADNA zgodność `code`. GUGiK
	zwraca maksymalnie 15 wyników ("max results limit": 15) - gdy prawdziwy
	przysiółek jest poza tym limitem, żaden kandydat nie będzie miał
	pasującego kodu i funkcja i tak zwróci `None`, bez zgadywania."""
	if not isinstance(odpowiedz, dict) or odpowiedz.get("type") != "address":
		return None
	wyniki = odpowiedz.get("results")
	if not wyniki:
		return None
	kandydaci = [k for k in wyniki.values() if k.get("code") == adres.kod]
	if len(kandydaci) == 1:
		return _wynik_z_kandydata_gugik(kandydaci[0], "adres")
	if len(kandydaci) > 1 and _wszystkie_w_promieniu(kandydaci, _PROMIEN_NIEJEDNOZNACZNOSCI_M):
		return _wynik_z_kandydata_gugik(kandydaci[0], "adres")
	return None


def geokoduj(
	adres: Adres,
	http_get,
	*,
	uzyj_nominatim: bool = True,
	powiat: str | None = None,
	wojewodztwo: str | None = None,
) -> "Wynik | None":
	"""Łańcuch czterokrokowy (decyzja właściciela 2026-09-10, rozszerzony QA
	#102 rundą 2, 2026-09-18), w tej kolejności:

	1. GUGiK, pełny adres (`zapytanie_gugik` - wieś bez ulicy, ulica+numer,
	   sama ulica albo sama miejscowość).
	2. GUGiK, hipoteza przysiółka (`zapytanie_gugik_przysiolek`) - tylko gdy
	   `Ulica` niepusta i różna od `Miejscowość`, `Nr` niepusty i lead ma
	   kod pocztowy; akceptowane WYŁĄCZNIE po dokładnej zgodności kodu.
	3. OSM Nominatim - wymaga nagłówka `User-Agent` i maks. 1 zapytania/s
	   (polityka Nominatim); pomijany całkowicie, gdy `uzyj_nominatim=False`.
	4. GUGiK, sama miejscowość (`type == "city"`, dokładność `"miejscowosc"`)
	   - ostatnia deska ratunku przed `None`: punkt środka miejscowości jest
	     lepszy niż nic (centroid kodu pocztowego to poza tym modułem, patrz
	     `dokladnosc="kod"` w wołającym); NIE zależy od `uzyj_nominatim`,
	     bo to GUGiK, nie Nominatim, więc żaden budżet zapytań/s tu nie
	     obowiązuje.

	Zwraca pierwszy wystarczający `Wynik` z dowolnego kroku, albo `None`,
	gdy żaden nie dał trafienia w granicach Polski - w takim razie wołający
	zostaje przy dotychczasowym centroidzie kodu pocztowego
	(`dokladnosc="kod"`) albo, gdy go też nie ma, `dokladnosc="brak"`.

	`http_get(url, params, headers) -> dict | None` jest jedynym punktem
	wejścia/wyjścia I/O - dostarczany przez wołającego (prawdziwy
	`requests.get(...).json()` na produkcji, nagrana odpowiedź w testach).
	Nigdy nie rzuca: każdy wyjątek z `http_get`, ORAZ każdy wyjątek z
	parsowania jego odpowiedzi (sieć, timeout, JSON niepoprawny, kształt
	odpowiedzi niezgodny z oczekiwanym), jest łapany i traktowany jak brak
	trafienia z tego kroku, więc jeden zepsuty adres w wsadzie 200 leadów
	nie przerywa partii.

	`powiat`/`wojewodztwo` przekazywane dalej do `parsuj_gugik` (patrz jego
	docstring) - rozstrzygają dwuznaczność `type == "city"` po stronie
	GUGiK, w krokach 1 i 4; Nominatim i krok 2 (przysiółek) nie mają
	odpowiednika tych parametrów."""
	wynik = _sprobuj_gugik(adres, http_get, powiat, wojewodztwo)
	if wynik is not None:
		return wynik

	wynik = _sprobuj_gugik_przysiolek(adres, http_get)
	if wynik is not None:
		return wynik

	if uzyj_nominatim:
		wynik = _sprobuj_nominatim(adres, http_get)
		if wynik is not None:
			return wynik

	return _sprobuj_gugik_miejscowosc(adres, http_get, powiat, wojewodztwo)


def _sprobuj_gugik(
	adres: Adres, http_get, powiat: str | None, wojewodztwo: str | None = None
) -> "Wynik | None":
	zapytanie = zapytanie_gugik(adres)
	if not zapytanie:
		return None
	try:
		odpowiedz = http_get(GUGIK_URL, {"request": "GetAddress", "address": zapytanie, "srid": "4326"}, None)
		wynik = parsuj_gugik(odpowiedz, adres, powiat=powiat, wojewodztwo=wojewodztwo)
	except Exception:
		return None
	if wynik is not None and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None


def _sprobuj_gugik_przysiolek(adres: Adres, http_get) -> "Wynik | None":
	zapytanie = zapytanie_gugik_przysiolek(adres)
	if not zapytanie:
		return None
	try:
		odpowiedz = http_get(GUGIK_URL, {"request": "GetAddress", "address": zapytanie, "srid": "4326"}, None)
		wynik = parsuj_gugik_przysiolek(odpowiedz, adres)
	except Exception:
		return None
	if wynik is not None and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None


def _sprobuj_nominatim(adres: Adres, http_get) -> "Wynik | None":
	parametry = zapytanie_nominatim(adres)
	try:
		odpowiedz = http_get(NOMINATIM_URL, parametry, {"User-Agent": NOMINATIM_USER_AGENT})
		wynik = parsuj_nominatim(odpowiedz, adres)
	except Exception:
		return None
	if wynik is not None and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None


def _sprobuj_gugik_miejscowosc(
	adres: Adres, http_get, powiat: str | None, wojewodztwo: str | None
) -> "Wynik | None":
	"""Krok 4 łańcucha (QA #102, runda 2): GUGiK samą nazwą miejscowości,
	`type == "city"` - ostatnia deska ratunku przed `None`. Rozstrzyganie
	wieloznaczności identyczne jak w kroku 1 (`powiat`/`wojewodztwo`
	przekazane do `parsuj_gugik`); jedyna różnica to wynik ograniczony do
	dokładności `"miejscowosc"` - inne dokładności nie powinny się tu
	pojawić (zapytanie to sama nazwa miejscowości), ale sprawdzamy jawnie,
	żeby ta funkcja nigdy nie zwróciła czegoś dokładniejszego niż faktycznie
	wie (środek miejscowości, nic więcej)."""
	miejscowosc = (adres.miejscowosc or "").strip()
	if not miejscowosc:
		return None
	try:
		odpowiedz = http_get(GUGIK_URL, {"request": "GetAddress", "address": miejscowosc, "srid": "4326"}, None)
		wynik = parsuj_gugik(odpowiedz, adres, powiat=powiat, wojewodztwo=wojewodztwo)
	except Exception:
		return None
	if wynik is not None and wynik.dokladnosc == "miejscowosc" and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None
