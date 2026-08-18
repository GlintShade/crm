"""Whitelisted API biblioteki dokumentów (doctypes `Volteo Dokument` i
`Volteo Dokument Ustawienia`).

Model bezpieczeństwa
---------------------
`Volteo Dokument` trzyma tylko `plik` -- `file_url` prywatnego pliku `File`
podpiętego (`attached_to_doctype`/`attached_to_name`) pod ten konkretny
dokument. Reps (`Volteo D2D Sales`, `Volteo Backend`) mają na `Volteo Dokument`
wyłącznie odczyt, ale prawdziwa ochrona pliku leży w Frappe: plik prywatny
serwowany jest tylko temu, kto ma odczyt na dokumencie, do którego jest
podpięty. Dlatego `dodaj_dokument`/`zamien_plik` odrzucają każdy `plik_url`,
który nie zaczyna się od `/private/files/` -- dopuszczenie publicznego pliku
ominęłoby całą tę ochronę.

`Volteo Dokument Ustawienia` (wybrane województwa + znaczniki "przeczytane")
nie ma NIGDY bezpośrednich uprawnień dla repów -- to czysto prywatny stan UI
jednego użytkownika. Ten moduł jest jedyną ścieżką dostępu do tego doctype'u i
zawsze skopuje zapytania do `frappe.session.user` (przez filtr `uzytkownik`),
nigdy nie przyjmując cudzego identyfikatora z przeglądarki -- stąd bezpieczne
jest tu użycie `ignore_permissions=True` na zapisie.

Admin-only operacje zarządzania katalogiem (`dodaj_dokument`, `zamien_plik`,
`usun_dokument`) używają `frappe.only_for` jako pierwszej instrukcji, wzorem
`crm.api.automatyzacje` / `crm.api.volteo_panele`.
"""

import io
import json
import zipfile
from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, get_datetime, now_datetime

WOJEWODZTWA = (
	"dolnośląskie",
	"kujawsko-pomorskie",
	"lubelskie",
	"lubuskie",
	"łódzkie",
	"małopolskie",
	"mazowieckie",
	"opolskie",
	"podkarpackie",
	"podlaskie",
	"pomorskie",
	"śląskie",
	"świętokrzyskie",
	"warmińsko-mazurskie",
	"wielkopolskie",
	"zachodniopomorskie",
)

# Szeroka bramka -- każdy, kto w ogóle może korzystać z biblioteki dokumentów.
DOKUMENTY_ROLE = {"Volteo D2D Sales", "Volteo Backend", "Volteo Core Admin", "System Manager"}
# Bramka administracyjna -- zarządzanie katalogiem (dodawanie/podmiana/usuwanie).
ADMIN_ROLE = ["Volteo Core Admin", "System Manager"]

DOCTYPE = "Volteo Dokument"
USTAWIENIA_DOCTYPE = "Volteo Dokument Ustawienia"

LINIE = {"OZE", "Czyste Powietrze"}

# Ile dni od `zaktualizowano` dokument/folder liczy się jako "nowy".
NOWOSC_DNI = 7


def _role_uzytkownika() -> set[str]:
	"""Sprawdza szeroką bramkę dostępu (dowolna rola z `DOKUMENTY_ROLE`) i zwraca
	zestaw ról wołającego do dalszych, węższych sprawdzeń (np. `_czy_admin`)."""
	role = set(frappe.get_roles(frappe.session.user))
	if not DOKUMENTY_ROLE & role:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)
	return role


def _czy_admin(role: set[str]) -> bool:
	"""Administrator ma z definicji rolę System Manager, więc sprawdzenie samego
	przecięcia ról już go obejmuje -- jawne porównanie z 'Administrator' jest
	tu dodatkowym, tanim zabezpieczeniem, nie obejściem."""
	if frappe.session.user == "Administrator":
		return True
	return bool(set(ADMIN_ROLE) & role)


def _sparsuj_liste_wojewodztw(surowe: Any) -> list[str]:
	"""Defensywnie parsuje `wojewodztwa` (JSON) z `Volteo Dokument Ustawienia`.
	Brak wartości albo uszkodzony JSON -> pusta lista, nigdy błąd."""
	if not surowe:
		return []
	try:
		wartosc = json.loads(surowe)
	except (TypeError, ValueError):
		return []
	if not isinstance(wartosc, list):
		return []
	return [pozycja for pozycja in wartosc if isinstance(pozycja, str)]


def _sparsuj_mape_odczytow(surowe: Any) -> dict[str, str]:
	"""Defensywnie parsuje `odczyty` (JSON, mapa klucz -> znacznik czasu ISO).
	Brak wartości albo uszkodzony JSON -> pusta mapa, nigdy błąd."""
	if not surowe:
		return {}
	try:
		wartosc = json.loads(surowe)
	except (TypeError, ValueError):
		return {}
	if not isinstance(wartosc, dict):
		return {}
	return {str(klucz): str(wart) for klucz, wart in wartosc.items() if isinstance(klucz, str)}


def _wczytaj_ustawienia(uzytkownik: str) -> dict[str, Any]:
	"""Odczytuje wybrane województwa i znaczniki odczytu wołającego wprost z bazy
	(`get_value` ignoruje uprawnienia, ale filtr jest zawsze na `uzytkownik`, więc
	zakres jest z definicji ograniczony do wołającego). Brak wiersza (użytkownik
	jeszcze niczego nie skonfigurował) albo nieistniejący jeszcze doctype (świeży
	dev-site przed uruchomieniem skryptu ops) dają puste wartości, nigdy błąd."""
	if not frappe.db.table_exists(USTAWIENIA_DOCTYPE):
		return {"wojewodztwa": [], "odczyty": {}}

	nazwa = frappe.db.get_value(USTAWIENIA_DOCTYPE, {"uzytkownik": uzytkownik}, "name")
	if not nazwa:
		return {"wojewodztwa": [], "odczyty": {}}

	wiersz = frappe.db.get_value(USTAWIENIA_DOCTYPE, nazwa, ["wojewodztwa", "odczyty"], as_dict=True)
	return {
		"wojewodztwa": _sparsuj_liste_wojewodztw(wiersz.get("wojewodztwa")),
		"odczyty": _sparsuj_mape_odczytow(wiersz.get("odczyty")),
	}


def _wczytaj_lub_utworz_ustawienia(uzytkownik: str) -> "frappe.model.document.Document":
	"""Zwraca dokument Ustawień wołającego, tworząc go przy pierwszym zapisie.
	Zawsze operuje na `frappe.session.user` -- wołający nie ma sposobu przekazać
	innego identyfikatora, bo funkcja nie przyjmuje go jako parametru."""
	nazwa = frappe.db.get_value(USTAWIENIA_DOCTYPE, {"uzytkownik": uzytkownik}, "name")
	if nazwa:
		return frappe.get_doc(USTAWIENIA_DOCTYPE, nazwa)

	doc = frappe.get_doc(
		{
			"doctype": USTAWIENIA_DOCTYPE,
			"uzytkownik": uzytkownik,
			"wojewodztwa": "[]",
			"odczyty": "{}",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _czy_nowy(zaktualizowano: Any, granica: Any, seen_iso: str | None) -> bool:
	"""Dokument/folder jest "nowy", gdy `zaktualizowano` mieści się w oknie
	`NOWOSC_DNI` dni ORAZ (nigdy nie oznaczono jako przeczytane, albo znacznik
	przeczytania jest starszy niż `zaktualizowano`). Uszkodzony/niesparsowalny
	znacznik przeczytania traktujemy jak jego brak (nowość widoczna), zamiast
	wywalać cały endpoint listy przez jeden zepsuty wpis."""
	if not zaktualizowano or zaktualizowano < granica:
		return False
	if not seen_iso:
		return True
	try:
		seen = get_datetime(seen_iso)
	except Exception:
		return True
	return zaktualizowano > seen


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def dokumenty_lista(linia: str) -> dict[str, Any]:
	"""Zwraca dokumenty danej linii produktowej wraz ze znacznikami "nowości"
	względem własnych odczytów wołającego, jego wybranymi województwami
	(tylko istotne dla Czystego Powietrza) i -- dla Czystego Powietrza --
	podsumowaniem per folder-województwo (nowość folderu, data ostatniej
	aktualizacji w folderze).

	Zwraca pusty, ale poprawny kształt, gdy doctype jeszcze nie istnieje
	(świeży dev-site przed uruchomieniem skryptu ops), zamiast wywalać się
	błędem 500 -- wzorzec z `crm.api.automatyzacje.volteo_automatyzacje_lista`.
	"""
	role_uzytkownika = _role_uzytkownika()

	if linia not in LINIE:
		frappe.throw(_("Nieznana linia produktowa."))

	if not frappe.db.table_exists(DOCTYPE):
		return {
			"dokumenty": [],
			"foldery": {},
			"wojewodztwa_uzytkownika": [],
			"wojewodztwa_opcje": list(WOJEWODZTWA),
			"czy_admin": _czy_admin(role_uzytkownika),
		}

	ustawienia = _wczytaj_ustawienia(frappe.session.user)
	odczyty = ustawienia["odczyty"]

	wiersze = frappe.get_all(
		DOCTYPE,
		filters={"linia": linia},
		fields=["name", "tytul", "wojewodztwo", "plik", "kolejnosc", "zaktualizowano"],
		order_by="kolejnosc asc, tytul asc",
	)

	granica = add_days(now_datetime(), -NOWOSC_DNI)

	dokumenty = []
	for wiersz in wiersze:
		zaktualizowano = wiersz.get("zaktualizowano")
		dokumenty.append(
			{
				"name": wiersz["name"],
				"tytul": wiersz.get("tytul"),
				"wojewodztwo": wiersz.get("wojewodztwo") or "",
				"plik": wiersz.get("plik") or "",
				"kolejnosc": wiersz.get("kolejnosc") or 0,
				"zaktualizowano": zaktualizowano,
				"nowosc": _czy_nowy(zaktualizowano, granica, odczyty.get(f"dokument:{wiersz['name']}")),
			}
		)

	foldery: dict[str, dict[str, Any]] = {}
	if linia == "Czyste Powietrze":
		znaczniki_per_woj: dict[str, list[Any]] = {}
		for wiersz in wiersze:
			woj = wiersz.get("wojewodztwo") or ""
			if not woj:
				continue
			znaczniki_per_woj.setdefault(woj, []).append(wiersz.get("zaktualizowano"))

		for woj, znaczniki in znaczniki_per_woj.items():
			seen_iso = odczyty.get(f"folder:{woj}")
			ustawione = [znacznik for znacznik in znaczniki if znacznik]
			foldery[woj] = {
				"folder_nowosc": any(_czy_nowy(znacznik, granica, seen_iso) for znacznik in znaczniki),
				"ostatnia_aktualizacja": max(ustawione) if ustawione else None,
			}

	return {
		"dokumenty": dokumenty,
		"foldery": foldery,
		"wojewodztwa_uzytkownika": ustawienia["wojewodztwa"],
		"wojewodztwa_opcje": list(WOJEWODZTWA),
		"czy_admin": _czy_admin(role_uzytkownika),
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60)
def zapisz_wojewodztwa(wojewodztwa: str) -> list[str]:
	"""Nadpisuje listę województw, którymi interesuje się wołający (filtr
	widoku Czystego Powietrza). `wojewodztwa` przychodzi jako string JSON --
	lista musi być podzbiorem `WOJEWODZTWA`, inaczej cały zapis jest odrzucany."""
	_role_uzytkownika()

	try:
		wartosc = json.loads(wojewodztwa)
	except (TypeError, ValueError):
		frappe.throw(_("Nieprawidłowy format listy województw."))

	if not isinstance(wartosc, list) or not all(isinstance(pozycja, str) for pozycja in wartosc):
		frappe.throw(_("Lista województw musi być listą tekstów."))

	nieznane = [woj for woj in wartosc if woj not in WOJEWODZTWA]
	if nieznane:
		frappe.throw(_("Nieznane województwa: {0}").format(", ".join(nieznane)))

	doc = _wczytaj_lub_utworz_ustawienia(frappe.session.user)
	doc.wojewodztwa = json.dumps(wartosc, ensure_ascii=False)
	doc.save(ignore_permissions=True)

	return wartosc


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=120, seconds=60)
def oznacz_odczyty(rodzaj: str, klucze: str) -> dict[str, str]:
	"""Oznacza dokumenty lub foldery jako przeczytane -- idempotentnie ustawia
	znacznik czasu "teraz" dla każdego klucza `f"{rodzaj}:{klucz}"`. Nie waliduje,
	czy każdy klucz odpowiada istniejącemu dokumentowi/folderowi -- to czysto
	prywatny stan UI wołającego, więc nadmiarowy/nieistniejący klucz jest
	nieszkodliwy."""
	_role_uzytkownika()

	if rodzaj not in {"dokument", "folder"}:
		frappe.throw(_("Nieznany rodzaj odczytu."))

	try:
		lista_kluczy = json.loads(klucze)
	except (TypeError, ValueError):
		frappe.throw(_("Nieprawidłowy format listy kluczy."))

	if not isinstance(lista_kluczy, list):
		frappe.throw(_("Lista kluczy musi być listą."))
	if len(lista_kluczy) > 200:
		frappe.throw(_("Zbyt wiele kluczy naraz (maksymalnie 200)."))
	if not all(isinstance(klucz, str) and klucz.strip() for klucz in lista_kluczy):
		frappe.throw(_("Każdy klucz odczytu musi być niepustym tekstem."))

	doc = _wczytaj_lub_utworz_ustawienia(frappe.session.user)
	odczyty = _sparsuj_mape_odczytow(doc.odczyty)
	teraz_iso = now_datetime().isoformat()
	for klucz in lista_kluczy:
		odczyty[f"{rodzaj}:{klucz}"] = teraz_iso

	doc.odczyty = json.dumps(odczyty, ensure_ascii=False)
	doc.save(ignore_permissions=True)

	return odczyty


def _bezpieczna_nazwa_wpisu(tytul: str, nazwa_pliku_zrodlowego: str, juz_uzyte: set[str]) -> str:
	"""Buduje nazwę wpisu w archiwum ZIP z tytułu dokumentu (czytelniejsze niż
	nazwa pliku na dysku), zachowując oryginalne rozszerzenie i deduplikując
	kolizje przyrostkiem ` (2)`, ` (3)`, ..."""
	rozszerzenie = ""
	if nazwa_pliku_zrodlowego and "." in nazwa_pliku_zrodlowego:
		rozszerzenie = "." + nazwa_pliku_zrodlowego.rsplit(".", 1)[-1]

	baza = (tytul or nazwa_pliku_zrodlowego or "dokument").strip() or "dokument"
	kandydat = f"{baza}{rozszerzenie}"
	licznik = 1
	while kandydat in juz_uzyte:
		licznik += 1
		kandydat = f"{baza} ({licznik}){rozszerzenie}"
	juz_uzyte.add(kandydat)
	return kandydat


@frappe.whitelist(methods=["GET"])
@rate_limit(limit=10, seconds=60)
def pobierz_zip(linia: str, wojewodztwo: str = "") -> None:
	"""Pakuje pliki dokumentów danej linii (dla Czystego Powietrza -- danego
	województwa) w jedno archiwum ZIP i zwraca je jako pobranie. Endpoint GET
	celowo nie zapisuje niczego w bazie (Frappe nie commituje po żądaniach GET) --
	pojedyncze uszkodzone/brakujące pliki są po cichu pomijane, nie wywalają
	całego pobrania."""
	_role_uzytkownika()

	if linia not in LINIE:
		frappe.throw(_("Nieznana linia produktowa."))
	if linia == "Czyste Powietrze" and wojewodztwo not in WOJEWODZTWA:
		frappe.throw(_("Wybierz województwo, aby pobrać dokumenty Czystego Powietrza."))

	filtry: dict[str, Any] = {"linia": linia}
	if linia == "Czyste Powietrze":
		filtry["wojewodztwo"] = wojewodztwo

	wiersze = frappe.get_all(
		DOCTYPE,
		filters=filtry,
		fields=["name", "tytul", "plik"],
		order_by="kolejnosc asc, tytul asc",
	)

	bufor = io.BytesIO()
	nazwy_w_archiwum: set[str] = set()
	dodano = 0
	with zipfile.ZipFile(bufor, mode="w", compression=zipfile.ZIP_DEFLATED) as archiwum:
		for wiersz in wiersze:
			plik_url = wiersz.get("plik")
			if not plik_url:
				continue
			try:
				nazwa_pliku = frappe.db.get_value(
					"File",
					{
						"file_url": plik_url,
						"attached_to_doctype": DOCTYPE,
						"attached_to_name": wiersz["name"],
					},
					"name",
				)
				if not nazwa_pliku:
					continue
				plik_doc = frappe.get_doc("File", nazwa_pliku)
				tresc = plik_doc.get_content()
			except Exception:
				continue

			nazwa_wpisu = _bezpieczna_nazwa_wpisu(wiersz.get("tytul"), plik_doc.file_name, nazwy_w_archiwum)
			archiwum.writestr(nazwa_wpisu, tresc)
			dodano += 1

	if dodano == 0:
		frappe.throw(_("Brak dokumentów do pobrania."))

	nazwa_archiwum = f"dokumenty-cp-{wojewodztwo}.zip" if linia == "Czyste Powietrze" else "dokumenty-oze.zip"

	frappe.local.response.filename = nazwa_archiwum
	frappe.local.response.filecontent = bufor.getvalue()
	frappe.local.response.type = "download"


def _wiersz_dokumentu(doc: "frappe.model.document.Document") -> dict[str, Any]:
	return {
		"name": doc.name,
		"tytul": doc.tytul,
		"linia": doc.linia,
		"wojewodztwo": doc.wojewodztwo or "",
		"plik": doc.plik,
		"kolejnosc": doc.kolejnosc or 0,
		"zaktualizowano": doc.zaktualizowano,
	}


def _przepnij_plik(plik_url: str, nazwa_dokumentu: str) -> str:
	"""Podpina już przesłany prywatny plik pod dokument biblioteki i zwraca
	nazwę (`File.name`) wiersza, który faktycznie skończył podpięty pod ten
	dokument -- wywołujący (`zamien_plik`) tego potrzebuje, żeby przy sprzątaniu
	starego pliku nie usunąć właśnie przypiętego wiersza.

	Frappe dedupuje uploady po `content_hash`: przesłanie treści identycznej z
	już istniejącym plikiem TWORZY NOWY wiersz `File`, ale z tym samym
	`file_url` co oryginał (patrz `file.py` w rdzeniu Frappe). Dlatego wśród
	wierszy o tym `file_url` może być więcej niż jeden, i mogą one należeć do
	zupełnie innych rekordów.

	Jeśli istnieje wiersz jeszcze nieprzypięty (świeżo przesłany, `attached_to_name`
	puste) -- podpinamy właśnie ten. W PRZECIWNYM razie NIE odrywamy pliku od
	tego, do czego już należy (inny `Volteo Dokument`, `CRM Deal`, cokolwiek) --
	zamiast tego tworzymy nowy wiersz `File` z tym samym `file_url`, podpięty
	wyłącznie pod nasz dokument (wzorzec z `crm.api.comment.add_attachments`).
	Dzięki temu każdy dokument ma własny wiersz `File`, więc usunięcie jednego
	dokumentu nigdy nie usuwa pliku fizycznego spod innego -- `File.on_trash`
	kasuje plik z dysku dopiero, gdy żaden wiersz nie dzieli już jego
	`content_hash`."""
	kandydaci = frappe.get_all(
		"File",
		filters={"file_url": plik_url},
		fields=["name", "attached_to_name"],
		order_by="creation desc",
	)
	if not kandydaci:
		frappe.throw(_("Nie znaleziono przesłanego pliku."))

	wolny = next((wiersz for wiersz in kandydaci if not wiersz.get("attached_to_name")), None)

	if wolny is not None:
		frappe.db.set_value(
			"File",
			wolny["name"],
			{
				"attached_to_doctype": DOCTYPE,
				"attached_to_name": nazwa_dokumentu,
				"attached_to_field": "plik",
				"is_private": 1,
			},
			update_modified=False,
		)
		return wolny["name"]

	nowy_plik = frappe.new_doc("File")
	nowy_plik.update(
		{
			"file_url": plik_url,
			"is_private": 1,
			"attached_to_doctype": DOCTYPE,
			"attached_to_name": nazwa_dokumentu,
			"attached_to_field": "plik",
		}
	)
	nowy_plik.save(ignore_permissions=True)
	return nowy_plik.name


def _usun_zdublowane_wiersze(nazwa_dokumentu: str, plik_url: str, zachowaj: str) -> None:
	"""Frappe sam dokłada wiersz File dla pola Attach przy insert/save dokumentu --
	zostawiamy dokładnie jeden wiersz (ten z `_przepnij_plik`), resztę usuwamy.
	Plik na dysku jest bezpieczny: File.on_trash kasuje go dopiero, gdy żaden
	wiersz nie dzieli już content_hash."""
	for nazwa in frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": DOCTYPE,
			"attached_to_name": nazwa_dokumentu,
			"file_url": plik_url,
			"name": ["!=", zachowaj],
		},
		pluck="name",
	):
		try:
			frappe.delete_doc("File", nazwa, ignore_permissions=True, delete_permanently=True)
		except Exception:
			frappe.log_error(title="Volteo Dokumenty: nie udało się usunąć zdublowanego wiersza File")


def _wymagaj_prywatnego_pliku(plik_url: str) -> str:
	plik_url = (plik_url or "").strip()
	if not plik_url.startswith("/private/files/"):
		frappe.throw(_("Plik musi być prywatnym załącznikiem."))
	return plik_url


@frappe.whitelist(methods=["POST"])
def dodaj_dokument(
	tytul: str,
	linia: str,
	plik_url: str,
	wojewodztwo: str = "",
	kolejnosc: int = 0,
) -> dict[str, Any]:
	"""Dodaje nowy dokument do biblioteki i podpina pod niego już przesłany
	prywatny plik. Admin-only."""
	frappe.only_for(ADMIN_ROLE, True)

	tytul = (tytul or "").strip()
	if not tytul:
		frappe.throw(_("Tytuł dokumentu jest wymagany."))

	if linia not in LINIE:
		frappe.throw(_("Nieznana linia produktowa."))

	if linia == "Czyste Powietrze":
		if wojewodztwo not in WOJEWODZTWA:
			frappe.throw(_("Wybierz województwo dla dokumentu linii Czyste Powietrze."))
	else:
		wojewodztwo = ""

	plik_url = _wymagaj_prywatnego_pliku(plik_url)

	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"tytul": tytul,
			"linia": linia,
			"wojewodztwo": wojewodztwo,
			"plik": plik_url,
			"kolejnosc": cint(kolejnosc),
			"zaktualizowano": now_datetime(),
		}
	)
	doc.insert()

	# Frappe sam dokłada wiersz File dla pola Attach przy insert() -- _przepnij_plik
	# podpina uploadowany wiersz, a _usun_zdublowane_wiersze sprząta ten dołożony
	# automatycznie, zostawiając dokładnie jeden wiersz File na dokument.
	nazwa_nowego = _przepnij_plik(plik_url, doc.name)
	_usun_zdublowane_wiersze(doc.name, plik_url, nazwa_nowego)

	return _wiersz_dokumentu(doc)


@frappe.whitelist(methods=["POST"])
def zamien_plik(dokument: str, plik_url: str) -> dict[str, Any]:
	"""Podmienia plik istniejącego dokumentu na nowo przesłany, aktualizuje
	`zaktualizowano` (co odświeża znaczniki "nowości" dla wszystkich, którzy już
	widzieli poprzednią wersję) i usuwa stary plik z dysku. Admin-only.

	Uwaga na deduplikację uploadów: jeśli nowa treść jest identyczna ze starą,
	`plik_url` (nowy) może wyjść RÓWNY `stary_url` -- Frappe dedupuje po
	`content_hash` i nowy upload dostaje `file_url` istniejącego pliku. Wiersz
	`File`, który `_przepnij_plik` faktycznie przypięło pod ten dokument
	(`nazwa_nowego`), jest dlatego JAWNIE wykluczony z zapytania usuwającego
	stare wiersze poniżej -- inaczej przy równych URL-ach zapytanie złapałoby
	też świeżo przypięty wiersz i skasowałoby go razem ze starym."""
	frappe.only_for(ADMIN_ROLE, True)

	doc = frappe.get_doc(DOCTYPE, dokument)

	plik_url = _wymagaj_prywatnego_pliku(plik_url)
	stary_url = doc.plik

	nazwa_nowego = _przepnij_plik(plik_url, doc.name)

	doc.plik = plik_url
	doc.zaktualizowano = now_datetime()
	doc.save()

	# Frappe sam dokłada wiersz File dla pola Attach przy save() -- posprzątaj ten
	# dołożony automatycznie PRZED czyszczeniem starego URL-a poniżej (ten blok już
	# wyklucza nazwa_nowego, więc kolejność nie wpływa na jego poprawność).
	_usun_zdublowane_wiersze(doc.name, plik_url, nazwa_nowego)

	if stary_url:
		stare_pliki = frappe.get_all(
			"File",
			filters={
				"file_url": stary_url,
				"attached_to_doctype": DOCTYPE,
				"attached_to_name": dokument,
				"name": ["!=", nazwa_nowego],
			},
			pluck="name",
		)
		for nazwa in stare_pliki:
			try:
				frappe.delete_doc("File", nazwa, ignore_permissions=True, delete_permanently=True)
			except Exception:
				frappe.log_error(title="Volteo Dokumenty: nie udało się usunąć starego pliku")

	return _wiersz_dokumentu(doc)


@frappe.whitelist(methods=["POST"])
def usun_dokument(dokument: str) -> dict[str, str]:
	"""Usuwa dokument biblioteki wraz z podpiętym plikiem. Admin-only."""
	frappe.only_for(ADMIN_ROLE, True)

	pliki = frappe.get_all(
		"File",
		filters={"attached_to_doctype": DOCTYPE, "attached_to_name": dokument},
		pluck="name",
	)
	for nazwa in pliki:
		try:
			frappe.delete_doc("File", nazwa, ignore_permissions=True, delete_permanently=True)
		except Exception:
			frappe.log_error(title="Volteo Dokumenty: nie udało się usunąć pliku dokumentu")

	frappe.delete_doc(DOCTYPE, dokument, ignore_permissions=True)

	return {"usunieto": dokument}
