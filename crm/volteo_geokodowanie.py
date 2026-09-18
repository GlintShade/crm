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
import re
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

PROMIEN_ODNIESIENIA_KM = 30
"""QA #102 runda 4 (2026-09-18): gdy dotychczasowe sita (kod / ulica+numer /
województwo / powiat) nadal zostawiają więcej niż jednego kandydata,
`punkt_odniesienia` (centroid kodu pocztowego leada, gdy `custom_geo_zrodlo
== "kod"`) rozstrzyga po odległości - patrz `_najblizszy_kandydat`."""

_PROMIEN_MIEJSCOWOSCI_ODNIESIENIA_KM = 60
"""Próg bezpieczeństwa dla `type == "city"` z JEDNYM kandydatem (nawet po
wszystkich innych sitach): gdy jest `punkt_odniesienia`, a jedyny kandydat
leży dalej niż to - `None`, zamiast zaakceptować odległą miejscowość o tej
samej nazwie w tym samym województwie (np. "Bydgoszcz" - patrz
`_w_zasiegu_miejscowosci`)."""


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


def _wspolrzedne_kandydata(kandydat: dict) -> "tuple[float, float] | None":
	try:
		return (float(kandydat["y"]), float(kandydat["x"]))
	except (KeyError, TypeError, ValueError):
		return None


def _najblizszy_kandydat(
	kandydaci: list[dict], punkt_odniesienia: "tuple[float, float] | None"
) -> "dict | None":
	"""QA #102 runda 4: ostatnia deska ratunku, gdy dotychczasowe sita nadal
	zostawiają >1 kandydata (i, dla `type == "address"`, promień 300 m też
	nie rozstrzygnął - kandydaci NIE leżą praktycznie w jednym miejscu).
	Bez `punkt_odniesienia` (lead nie ma jeszcze żadnych współrzędnych,
	nawet centroidu kodu) - `None`, nic do porównania.

	Wybiera kandydata najbliższego `punkt_odniesienia`, TYLKO gdy: jest w
	promieniu `PROMIEN_ODNIESIENIA_KM` ORAZ (drugi najbliższy leży poza tym
	promieniem ALBO jest dalej niż 2x od najbliższego) - inaczej `None`,
	bo oba kandydaci są "wystarczająco blisko" punktu odniesienia, żeby
	zgadywanie między nimi było ryzykowne. Kandydat bez parsowalnych
	współrzędnych (`y`/`x`) unieważnia całe porównanie (`None`) - nie
	ryzykujemy wyboru na podstawie niepełnych danych."""
	if not punkt_odniesienia:
		return None

	wspolrzedne = [_wspolrzedne_kandydata(k) for k in kandydaci]
	if any(w is None for w in wspolrzedne):
		return None

	lat0, lng0 = punkt_odniesienia
	odleglosci = sorted(
		((_odleglosc_m(lat0, lng0, lat, lng), k) for (lat, lng), k in zip(wspolrzedne, kandydaci, strict=True)),
		key=lambda para: para[0],
	)

	prog_m = PROMIEN_ODNIESIENIA_KM * 1000.0
	najblizszy_m, najblizszy = odleglosci[0]
	if najblizszy_m > prog_m:
		return None
	if len(odleglosci) == 1:
		return najblizszy

	drugi_m = odleglosci[1][0]
	if drugi_m > prog_m or drugi_m > 2 * najblizszy_m:
		return najblizszy
	return None


def _w_zasiegu_miejscowosci(kandydat: dict, punkt_odniesienia: "tuple[float, float] | None") -> bool:
	"""QA #102 runda 4: dla `type == "city"` z jednym (ostatecznym) kandydatem
	- gdy jest `punkt_odniesienia`, a kandydat leży dalej niż
	`_PROMIEN_MIEJSCOWOSCI_ODNIESIENIA_KM`, odrzuca go (`False`). Bez
	`punkt_odniesienia`, albo gdy współrzędnych kandydata nie da się
	sparsować, nie blokuje na tej podstawie (`True`) - `_wynik_z_kandydata_gugik`
	i tak odrzuci kandydata z niepoprawnymi współrzędnymi osobno."""
	if not punkt_odniesienia:
		return True
	wspolrzedne = _wspolrzedne_kandydata(kandydat)
	if wspolrzedne is None:
		return True
	lat0, lng0 = punkt_odniesienia
	lat, lng = wspolrzedne
	return _odleglosc_m(lat0, lng0, lat, lng) <= _PROMIEN_MIEJSCOWOSCI_ODNIESIENIA_KM * 1000.0


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


_PREFIKSY_ULICY = (
	"ulica ",
	"ul. ",
	"ul ",
	"aleja ",
	"al. ",
	"al ",
	"plac ",
	"pl. ",
	"pl ",
	"osiedle ",
	"os. ",
	"os ",
)
"""Prefiksy typu ulicy zdejmowane przy normalizacji - GUGiK i `adres.ulica`
oba potrafią je nieść (np. `"ulica Marszałkowska"`, `"al. Bema"`, `"os.
Słoneczne"`) albo nie nieść wcale; porównanie musi działać niezależnie od
tego, po której stronie prefiks się znalazł."""


def _znormalizuj_ulice(tekst: str | None) -> str:
	"""Normalizacja nazwy ulicy do porównania: zdjęcie prefiksu typu ulicy
	(`_PREFIKSY_ULICY`, bez wielkości liter), małe litery, pojedyncze spacje
	(bez wiodących/końcowych). Stosowana symetrycznie do obu stron
	porównania (kandydat GUGiK i `adres.ulica`) - lead bywa zapisany z
	prefiksem tak samo jak odpowiedź GUGiK."""
	tekst = re.sub(r"\s+", " ", (tekst or "").strip()).lower()
	for prefiks in _PREFIKSY_ULICY:
		if tekst.startswith(prefiks):
			return tekst[len(prefiks) :].strip()
	return tekst


def _ulica_pasuje(ulica_gugik_norm: str, ulica_lead_norm: str) -> bool:
	"""QA #102 runda 3, 2026-09-18: równość ALBO dopasowanie sufiksowe na
	granicy słowa, w obie strony. GUGiK zwraca pełne nazwy urzędowe
	("Piotra Michałowskiego", "Generała Józefa Bema"), podczas gdy lead ma
	często skróconą, potoczną nazwę ("Michałowskiego", "Bema") - sprawdzone
	realnym dry-runem 2026-09-18: "Michałowskiego 38, 64-920 Piła" nie
	trafiał, bo GUGiK zwraca `street = "Piotra Michałowskiego"` i ścisła
	równość to odrzucała.

	Dopasowanie jest PO SŁOWACH, nie po znakach - "Podpolna" nie może
	dopasować "Polna" mimo że string kończy się tymi znakami, bo w
	"Podpolna" nie ma spacji przed "polna" (to jedno słowo, inna ulica).
	"Krakowska Nowa" dopasowuje "Nowa" (dwa słowa, ostatnie słowo się
	zgadza), "Sternicza" nie dopasowuje "Miernicza" (jedno słowo, różne
	słowo) - pokrywa się to z fuzzy-dopasowaniem GUGiK odrzuconym w rundzie
	2 (QA #102), ta reguła go nie osłabia."""
	if ulica_gugik_norm == ulica_lead_norm:
		return True

	slowa_gugik = ulica_gugik_norm.split()
	slowa_lead = ulica_lead_norm.split()
	if not slowa_gugik or not slowa_lead:
		return False

	if len(slowa_lead) <= len(slowa_gugik) and slowa_gugik[-len(slowa_lead) :] == slowa_lead:
		return True
	if len(slowa_gugik) <= len(slowa_lead) and slowa_lead[-len(slowa_gugik) :] == slowa_gugik:
		return True
	return False


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
	`street` i `adres.ulica`, oba znormalizowane (`_znormalizuj_ulice`),
	dają zgodność wg `_ulica_pasuje` - równość ALBO sufiks na granicy słowa
	w obie strony (QA #102 runda 3: GUGiK zwraca pełną nazwę urzędową,
	"Piotra Michałowskiego", lead często ma skróconą potoczną,
	"Michałowskiego" - sprawdzone realnym dry-runem 2026-09-18). W obu
	przypadkach `number` musi się zgadzać z `adres.nr_domu` (normalizacja:
	bez spacji, bez wielkości liter). Kandydat z pustym `street`, gdy
	zapytanie MIAŁO ulicę, zawsze odpada - GUGiK czasem zwraca dopasowanie
	samej miejscowości jako fallback w tym samym zapytaniu adresowym."""
	if not _numer_pasuje(kandydat.get("number"), adres.nr_domu):
		return False

	ulica = (adres.ulica or "").strip()
	miejscowosc = (adres.miejscowosc or "").strip()
	kandydat_street = kandydat.get("street")

	if _wies_bez_ulicy(adres):
		return not kandydat_street and (kandydat.get("city") or "").strip().lower() == miejscowosc.lower()

	if not kandydat_street:
		return False
	return _ulica_pasuje(_znormalizuj_ulice(kandydat_street), _znormalizuj_ulice(ulica))


def parsuj_gugik(
	odpowiedz: dict | None,
	adres: Adres,
	*,
	powiat: str | None = None,
	wojewodztwo: str | None = None,
	punkt_odniesienia: "tuple[float, float] | None" = None,
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

	`punkt_odniesienia` (QA #102 runda 4, opcjonalna para `(lat, lng)` -
	zwykle centroid kodu pocztowego leada) to OSTATNIA deska ratunku, gdy
	dotychczasowe sita nadal zostawiają >1 kandydata: `type == "address"`
	próbuje go PO promieniu 300 m (gdy kandydaci nie leżą praktycznie w
	jednym miejscu), `type == "city"` PO filtrach województwo/powiat (patrz
	`_najblizszy_kandydat`). Dodatkowo, `type == "city"` z JEDNYM
	(ostatecznym) kandydatem odrzuca go, gdy leży dalej niż
	`_PROMIEN_MIEJSCOWOSCI_ODNIESIENIA_KM` od `punkt_odniesienia` - ochrona
	przed odległą miejscowością o tej samej nazwie w tym samym województwie
	(np. "Bydgoszcz": dwóch kandydatów GUGiK, ten sam region, lead bez
	powiatu na karcie).
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
			# else: kod nie zawęził niczego (wielu kandydatów, żaden nie
			# pasuje) - `kandydaci` zostaje pełnym zbiorem po sicie 1,
			# rozstrzyganie schodzi do promienia/punktu odniesienia niżej,
			# zamiast poddawać się od razu (QA #102 runda 4).

		if len(kandydaci) == 1:
			kandydat = kandydaci[0]
			return _wynik_z_kandydata_gugik(kandydat, _dokladnosc_gugik_adres(kandydat))
		if len(kandydaci) > 1:
			if _wszystkie_w_promieniu(kandydaci, _PROMIEN_NIEJEDNOZNACZNOSCI_M):
				kandydat = kandydaci[0]
				return _wynik_z_kandydata_gugik(kandydat, _dokladnosc_gugik_adres(kandydat))
			wybrany = _najblizszy_kandydat(kandydaci, punkt_odniesienia)
			if wybrany is not None:
				return _wynik_z_kandydata_gugik(wybrany, _dokladnosc_gugik_adres(wybrany))
		return None

	if typ == "city":
		if len(kandydaci) == 1:
			kandydat = kandydaci[0]
			if wojewodztwo and not _wojewodztwo_pasuje(kandydat, wojewodztwo):
				return None
			if not _w_zasiegu_miejscowosci(kandydat, punkt_odniesienia):
				return None
			return _wynik_z_kandydata_gugik(kandydat, "miejscowosc")

		if wojewodztwo:
			kandydaci = [k for k in kandydaci if _wojewodztwo_pasuje(k, wojewodztwo)]
		if powiat:
			kandydaci = [
				k for k in kandydaci if (k.get("county") or "").strip().lower() == powiat.strip().lower()
			]

		if len(kandydaci) == 1:
			kandydat = kandydaci[0]
			if not _w_zasiegu_miejscowosci(kandydat, punkt_odniesienia):
				return None
			return _wynik_z_kandydata_gugik(kandydat, "miejscowosc")

		if len(kandydaci) > 1:
			wybrany = _najblizszy_kandydat(kandydaci, punkt_odniesienia)
			if wybrany is not None:
				return _wynik_z_kandydata_gugik(wybrany, "miejscowosc")
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


_SKROTY_MIEJSCOWOSCI = (
	("Wlkp.", "Wielkopolski"),
	("Wlkp", "Wielkopolski"),
	("Maz.", "Mazowiecki"),
	("Śl.", "Śląski"),
)
"""QA #102 runda 4, 2026-09-18: skróty przymiotnika wojewódzkiego na końcu
nazwy miejscowości, rozwijane przez `warianty_miejscowosci` - dry-run
lokalny pokazał nazwy bez polskich znaków, w tym "Gorzow Wlkp" (GUGiK
zwraca 0 wyników dla samego skrótu). Kolejność ma znaczenie: `"Wlkp."` (z
kropką) sprawdzany PRZED `"Wlkp"` (bez kropki), żeby nie zostawić kropki w
dopasowanym rdzeniu przez pomyłkę."""


def warianty_miejscowosci(miejscowosc: str, miejscowosc_z_kodu: str | None) -> list[str]:
	"""Lista unikalnych nazw miejscowości do kolejnych prób w `geokoduj`, w
	kolejności: (1) nazwa leada, (2) nazwa z tabeli kodów pocztowych - tylko
	gdy niepusta i różna od (1) (bez wielkości liter), (3) nazwa leada z
	rozwiniętym skrótem przymiotnika wojewódzkiego na końcu (`_SKROTY_MIEJSCOWOSCI`,
	np. "Gorzow Wlkp" -> "Gorzow Wielkopolski"), gdy taki skrót faktycznie
	występuje. Duplikaty (bez wielkości liter) pomijane, więc lista ma
	NAJWYŻEJ 3 elementy - pusta, gdy obie nazwy wejściowe są puste.

	QA #102 runda 4, uwaga lokalna: dla leada "Poznan" z kodem 60-185 tabela
	kodów pocztowych daje "Skórzewo" (sąsiednia wieś, nie samo miasto) -
	to ZAMIERZONE: wariant (2) nie musi być tą samą miejscowością, ma być
	geokodowalną nazwą blisko prawdziwego adresu, dokładniejszą niż brak
	współrzędnych w ogóle."""
	warianty: list[str] = []

	nazwa_leada = (miejscowosc or "").strip()
	if nazwa_leada:
		warianty.append(nazwa_leada)

	nazwa_z_kodu = (miejscowosc_z_kodu or "").strip()
	if nazwa_z_kodu and nazwa_z_kodu.lower() != nazwa_leada.lower():
		warianty.append(nazwa_z_kodu)

	if nazwa_leada:
		for skrot, rozwiniecie in _SKROTY_MIEJSCOWOSCI:
			if nazwa_leada.endswith(skrot):
				rdzen = nazwa_leada[: -len(skrot)].rstrip()
				rozwiniety = re.sub(r"\s+", " ", f"{rdzen} {rozwiniecie}").strip()
				warianty.append(rozwiniety)
				break

	wynik: list[str] = []
	widziane: set[str] = set()
	for wariant in warianty:
		klucz = wariant.lower()
		if klucz not in widziane:
			widziane.add(klucz)
			wynik.append(wariant)
	return wynik[:3]


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


def parsuj_gugik_przysiolek(
	odpowiedz: dict | None,
	adres: Adres,
	*,
	punkt_odniesienia: "tuple[float, float] | None" = None,
) -> "Wynik | None":
	"""Rozbiera odpowiedź GUGiK dla zapytania przysiółka. Celowo BEZ
	leniencji "jeden kandydat + city pasuje" z `parsuj_gugik` powyżej - tu
	nie ma miejscowości do porównania (zapytanie to sama nazwa przysiółka),
	więc jedynym bezpiecznym sitem jest DOKŁADNA zgodność `code`. GUGiK
	zwraca maksymalnie 15 wyników ("max results limit": 15) - gdy prawdziwy
	przysiółek jest poza tym limitem, żaden kandydat nie będzie miał
	pasującego kodu i funkcja i tak zwróci `None`, bez zgadywania.

	`punkt_odniesienia` (QA #102 runda 4): ostatnia deska ratunku, gdy po
	dokładnym dopasowaniu kodu wciąż zostaje >1 kandydat, a promień 300 m
	(duplikat rekordu) nie rozstrzyga - patrz `_najblizszy_kandydat`."""
	if not isinstance(odpowiedz, dict) or odpowiedz.get("type") != "address":
		return None
	wyniki = odpowiedz.get("results")
	if not wyniki:
		return None
	kandydaci = [k for k in wyniki.values() if k.get("code") == adres.kod]
	if len(kandydaci) == 1:
		return _wynik_z_kandydata_gugik(kandydaci[0], "adres")
	if len(kandydaci) > 1:
		if _wszystkie_w_promieniu(kandydaci, _PROMIEN_NIEJEDNOZNACZNOSCI_M):
			return _wynik_z_kandydata_gugik(kandydaci[0], "adres")
		wybrany = _najblizszy_kandydat(kandydaci, punkt_odniesienia)
		if wybrany is not None:
			return _wynik_z_kandydata_gugik(wybrany, "adres")
	return None


def _adres_z_miejscowoscia(adres: Adres, wariant: str) -> Adres:
	"""Podmienia `Miejscowość` na `wariant` (QA #102 runda 4,
	`warianty_miejscowosci`). Gdy oryginalny adres był wsią-bez-ulicy
	(`_wies_bez_ulicy` - `Ulica` puste albo równe starej `Miejscowość`),
	wariant zastępuje OBA pola, żeby ta klasyfikacja została prawdziwa
	także dla nowej nazwy - inaczej `_wies_bez_ulicy` przestałaby wykrywać
	wieś po podmianie (stare `Ulica` nie zgadzałoby się z nowym
	`Miejscowość`), co fałszywie przełączyłoby zapytanie na tryb
	"prawdziwa ulica"."""
	if _wies_bez_ulicy(adres):
		return Adres(ulica=wariant, nr_domu=adres.nr_domu, kod=adres.kod, miejscowosc=wariant)
	return Adres(ulica=adres.ulica, nr_domu=adres.nr_domu, kod=adres.kod, miejscowosc=wariant)


def _adresy_do_probowania(adres: Adres, miejscowosc_z_kodu: str | None) -> "list[Adres]":
	"""Oryginalny `adres` ZAWSZE pierwszy (nawet gdy `Miejscowość` jest pusta
	- `warianty_miejscowosci` wtedy nie zwróci go jako elementu listy, a
	krok Nominatim i tak działa bez miejscowości), potem każdy kolejny
	wariant nazwy z `warianty_miejscowosci`, pomijając ten identyczny z
	oryginałem (już wypróbowany jako pierwszy element)."""
	proby = [adres]
	miejscowosc_oryginalna = (adres.miejscowosc or "").strip().lower()
	for wariant in warianty_miejscowosci(adres.miejscowosc, miejscowosc_z_kodu):
		if wariant.strip().lower() == miejscowosc_oryginalna:
			continue
		proby.append(_adres_z_miejscowoscia(adres, wariant))
	return proby


def geokoduj(
	adres: Adres,
	http_get,
	*,
	uzyj_nominatim: bool = True,
	powiat: str | None = None,
	wojewodztwo: str | None = None,
	punkt_odniesienia: "tuple[float, float] | None" = None,
	miejscowosc_z_kodu: str | None = None,
) -> "Wynik | None":
	"""Łańcuch czterokrokowy (decyzja właściciela 2026-09-10, rozszerzony QA
	#102 rundami 2 i 4, 2026-09-18), w tej kolejności:

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

	Gdy WSZYSTKIE cztery kroki dadzą `None` dla nazwy miejscowości leada,
	QA #102 runda 4 dodaje pętlę wariantów nazwy (`_adresy_do_probowania`,
	`warianty_miejscowosci`): cały czterokrokowy łańcuch powtarza się dla
	kolejnej nazwy (najpierw z tabeli kodów pocztowych, `miejscowosc_z_kodu`,
	potem z rozwiniętym skrótem przymiotnika wojewódzkiego typu "Wlkp." ->
	"Wielkopolski"), maks. 3 próby łącznie licząc oryginał (limit narzucony
	przez `warianty_miejscowosci`). Dla wsi-bez-ulicy wariant zastępuje
	zarówno `Miejscowość`, jak i `Ulica` (patrz `_adres_z_miejscowoscia`).
	Dokładność zwróconego `Wynik` jest zawsze tym, co dał faktycznie trafiony
	krok (`adres`/`ulica`/`miejscowosc`) - podmiana nazwy nie zmienia
	znaczenia dokładności.

	Zwraca pierwszy wystarczający `Wynik` z dowolnej próby (adresu/wariantu)
	i dowolnego kroku, albo `None`, gdy żadna kombinacja nie dała trafienia
	w granicach Polski - w takim razie wołający zostaje przy dotychczasowym
	centroidzie kodu pocztowego (`dokladnosc="kod"`) albo, gdy go też nie
	ma, `dokladnosc="brak"`.

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
	GUGiK, w krokach 1, 2 i 4; Nominatim nie ma odpowiednika tych
	parametrów. `punkt_odniesienia` (QA #102 runda 4, para `(lat, lng)` -
	zwykle centroid kodu pocztowego leada, przekazywany przez wołającego
	tylko gdy `custom_geo_zrodlo == "kod"`) trafia do WSZYSTKICH kroków
	GUGiK (1, 2, 4) jako ostatnia deska ratunku przy >1 kandydacie po
	dotychczasowych sitach; Nominatim ma `limit=1`, więc nigdy nie zwraca
	wielu kandydatów do rozstrzygnięcia - stąd bez odpowiednika tam."""
	for adres_proby in _adresy_do_probowania(adres, miejscowosc_z_kodu):
		wynik = _geokoduj_jeden_adres(
			adres_proby,
			http_get,
			uzyj_nominatim=uzyj_nominatim,
			powiat=powiat,
			wojewodztwo=wojewodztwo,
			punkt_odniesienia=punkt_odniesienia,
		)
		if wynik is not None:
			return wynik
	return None


def _geokoduj_jeden_adres(
	adres: Adres,
	http_get,
	*,
	uzyj_nominatim: bool,
	powiat: str | None,
	wojewodztwo: str | None,
	punkt_odniesienia: "tuple[float, float] | None",
) -> "Wynik | None":
	"""Cztery kroki łańcucha dla JEDNEGO konkretnego adresu (oryginał albo
	jeden z wariantów nazwy miejscowości z `geokoduj`) - wydzielone z
	`geokoduj`, żeby pętla wariantów mogła powtórzyć te same cztery kroki
	bez duplikowania ich kolejności w dwóch miejscach."""
	wynik = _sprobuj_gugik(adres, http_get, powiat, wojewodztwo, punkt_odniesienia)
	if wynik is not None:
		return wynik

	wynik = _sprobuj_gugik_przysiolek(adres, http_get, punkt_odniesienia)
	if wynik is not None:
		return wynik

	if uzyj_nominatim:
		wynik = _sprobuj_nominatim(adres, http_get)
		if wynik is not None:
			return wynik

	return _sprobuj_gugik_miejscowosc(adres, http_get, powiat, wojewodztwo, punkt_odniesienia)


def _sprobuj_gugik(
	adres: Adres,
	http_get,
	powiat: str | None,
	wojewodztwo: str | None = None,
	punkt_odniesienia: "tuple[float, float] | None" = None,
) -> "Wynik | None":
	zapytanie = zapytanie_gugik(adres)
	if not zapytanie:
		return None
	try:
		odpowiedz = http_get(GUGIK_URL, {"request": "GetAddress", "address": zapytanie, "srid": "4326"}, None)
		wynik = parsuj_gugik(
			odpowiedz, adres, powiat=powiat, wojewodztwo=wojewodztwo, punkt_odniesienia=punkt_odniesienia
		)
	except Exception:
		return None
	if wynik is not None and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None


def _sprobuj_gugik_przysiolek(
	adres: Adres, http_get, punkt_odniesienia: "tuple[float, float] | None" = None
) -> "Wynik | None":
	zapytanie = zapytanie_gugik_przysiolek(adres)
	if not zapytanie:
		return None
	try:
		odpowiedz = http_get(GUGIK_URL, {"request": "GetAddress", "address": zapytanie, "srid": "4326"}, None)
		wynik = parsuj_gugik_przysiolek(odpowiedz, adres, punkt_odniesienia=punkt_odniesienia)
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
	adres: Adres,
	http_get,
	powiat: str | None,
	wojewodztwo: str | None,
	punkt_odniesienia: "tuple[float, float] | None" = None,
) -> "Wynik | None":
	"""Krok 4 łańcucha (QA #102, runda 2): GUGiK samą nazwą miejscowości,
	`type == "city"` - ostatnia deska ratunku przed `None`. Rozstrzyganie
	wieloznaczności identyczne jak w kroku 1 (`powiat`/`wojewodztwo`/
	`punkt_odniesienia` przekazane do `parsuj_gugik`); jedyna różnica to
	wynik ograniczony do dokładności `"miejscowosc"` - inne dokładności nie
	powinny się tu pojawić (zapytanie to sama nazwa miejscowości), ale
	sprawdzamy jawnie, żeby ta funkcja nigdy nie zwróciła czegoś
	dokładniejszego niż faktycznie wie (środek miejscowości, nic więcej)."""
	miejscowosc = (adres.miejscowosc or "").strip()
	if not miejscowosc:
		return None
	try:
		odpowiedz = http_get(GUGIK_URL, {"request": "GetAddress", "address": miejscowosc, "srid": "4326"}, None)
		wynik = parsuj_gugik(
			odpowiedz, adres, powiat=powiat, wojewodztwo=wojewodztwo, punkt_odniesienia=punkt_odniesienia
		)
	except Exception:
		return None
	if wynik is not None and wynik.dokladnosc == "miejscowosc" and _w_polsce(wynik.lat, wynik.lng):
		return wynik
	return None
