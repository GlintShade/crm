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

Łańcuch (`geokoduj`):
  1. GUGiK UUG (`https://services.gugik.gov.pl/uug/`) - darmowy, bez limitu
     zapytań, oficjalne dane adresowe państwa; próbowany pierwszy.
  2. OSM Nominatim (`https://nominatim.openstreetmap.org/search`) - wymaga
     nagłówka `User-Agent` z adresem kontaktowym i maks. 1 zapytania/s
     (polityka użytkowania Nominatim); próbowany tylko gdy GUGiK nie dał
     wystarczającego trafienia.
  3. Centroid kodu pocztowego (`Postal Code.lat`/`lng`, już zasilony przez
     `ops/crm-kody-geo.py` z GeoNames od b52) - poza tym modułem: gdy oba
     kroki wyżej zwrócą `None`, wołający zostawia dotychczasowe
     `custom_lat`/`custom_lng` (centroid) i zapisuje tylko
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

	`type == "address"` (poprawka QA #102-1, 2026-09-18): nazwy miejscowości
	się powtarzają w Polsce, więc gdy lead MA kod pocztowy, ten kod jest
	jedynym akceptowalnym sitem - kandydat, który go nie ma, nigdy nie jest
	przyjmowany, NAWET jeśli jest jedynym zwróconym przez GUGiK ("Zakrzewo
	45" z jednym wynikiem w 63-910 dla leada w 84-223 to zła wieś, nie
	przybliżenie). Gdy po odfiltrowaniu po kodzie nie zostaje ŻADEN kandydat
	-> `None` od razu, bez próby promienia 300 m na niefiltrowanej liście.
	Promień 300 m rozstrzyga wyłącznie WŚRÓD kandydatów, którzy już
	dzielą kod (albo, gdy lead nie ma kodu wpisanego wcale, wśród
	wszystkich zwróconych - jedyny wyjątek od reguły kodu powyżej).

	`type == "city"` (poprawka QA #102-2): przy wielu kandydatach kolejność
	sit jest stała - najpierw `voivodeship` (gdy podane), potem `county`
	wśród tego, co zostało (gdy podane); jeśli po obu krokach zostaje
	dokładnie jeden kandydat -> `Wynik`, inaczej `None`. Gdy kandydat jest
	od początku tylko jeden, a lead ma województwo, które się nie zgadza z
	`voivodeship` kandydata -> `None` (ta sama logika bezpieczeństwa
	powtarzających się nazw co przy `"address"` wyżej; `powiat` NIE jest
	sprawdzany w tej gałęzi z jednym kandydatem, tak jak przed poprawką).
	"""
	if not odpowiedz:
		return None
	wyniki = odpowiedz.get("results")
	if not wyniki:
		return None

	typ = odpowiedz.get("type")
	kandydaci = list(wyniki.values())

	if typ == "address":
		if adres.kod:
			kandydaci = [k for k in kandydaci if k.get("code") == adres.kod]
			if not kandydaci:
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
	if not lista:
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


def geokoduj(
	adres: Adres,
	http_get,
	*,
	uzyj_nominatim: bool = True,
	powiat: str | None = None,
	wojewodztwo: str | None = None,
) -> "Wynik | None":
	"""Łańcuch GUGiK -> Nominatim (decyzja właściciela 2026-09-10). Zwraca
	pierwszy wystarczający `Wynik` albo `None`, gdy żadne z dwóch źródeł nie
	dało trafienia w granicach Polski - w takim razie wołający zostaje przy
	dotychczasowym centroidzie kodu pocztowego (`dokladnosc="kod"`) albo,
	gdy go też nie ma, `dokladnosc="brak"`; to poza tym modułem.

	`http_get(url, params, headers) -> dict | None` jest jedynym punktem
	wejścia/wyjścia I/O - dostarczany przez wołającego (prawdziwy
	`requests.get(...).json()` na produkcji, nagrana odpowiedź w testach).
	Nigdy nie rzuca: każdy wyjątek z `http_get` (sieć, timeout, JSON
	niepoprawny) jest łapany i traktowany jak brak trafienia z tego źródła,
	więc jeden zepsuty adres w wsadzie 200 leadów nie przerywa partii.

	`uzyj_nominatim=False` pomija krok 2 całkowicie (przydatne np. w próbce
	DRY_RUN, żeby nie zużywać budżetu 1 zapytania/s Nominatim na podgląd).

	`powiat`/`wojewodztwo` przekazywane dalej do `parsuj_gugik` (patrz jego
	docstring) - rozstrzygają wyłącznie dwuznaczność `type == "city"` po
	stronie GUGiK; Nominatim nie ma odpowiednika tych parametrów."""
	wynik = _sprobuj_gugik(adres, http_get, powiat, wojewodztwo)
	if wynik is not None:
		return wynik
	if not uzyj_nominatim:
		return None
	return _sprobuj_nominatim(adres, http_get)


def _sprobuj_gugik(
	adres: Adres, http_get, powiat: str | None, wojewodztwo: str | None = None
) -> "Wynik | None":
	zapytanie = zapytanie_gugik(adres)
	if not zapytanie:
		return None
	try:
		odpowiedz = http_get(GUGIK_URL, {"request": "GetAddress", "address": zapytanie, "srid": "4326"}, None)
	except Exception:
		return None
	wynik = parsuj_gugik(odpowiedz, adres, powiat=powiat, wojewodztwo=wojewodztwo)
	if wynik is not None and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None


def _sprobuj_nominatim(adres: Adres, http_get) -> "Wynik | None":
	parametry = zapytanie_nominatim(adres)
	try:
		odpowiedz = http_get(NOMINATIM_URL, parametry, {"User-Agent": NOMINATIM_USER_AGENT})
	except Exception:
		return None
	wynik = parsuj_nominatim(odpowiedz, adres)
	if wynik is not None and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None
