"""Rdzeń logiki integracji Autenti dla podpisu elektronicznego — frappe-free.

Od b47 obsługuje DWA dokumenty: UMOWĘ (`Volteo Umowa`) i formularz kredytowy
(`Volteo Kredyt`). Jedyne źródło prawdy o mapowaniu statusów zdalnego procesu
dokumentu Autenti na statusy lokalne (`autenti_status`), o tym które statusy
blokują ponowne wysłanie, i o regule nazewnictwa plików PDF — dzielonej z
`crm/api/umowa.py` i `crm/api/kredyt.py`, żeby nazwa oryginalnego PDF-u
wysyłanego do podpisu i nazwa PDF-u generowanego przez `volteo_umowa_pdf`/
`volteo_kredyt_pdf` nigdy nie mogły się rozjechać.

Od ops#143 dzieli też z `crm/integrations/autenti/api.py` czystą logikę
decyzyjną odporności wysyłki i pollingu: kiedy ponowna wysyłka odzyskuje
istniejący proces Autenti zamiast tworzyć nowy, kiedy rekord utknięty w
statusie „Wysyłanie” liczy się jako przekroczony czasowo, kiedy brak
podpisanego pliku jest już wart zalogowania, deduplikację logowania
nierozpoznanego statusu i tłumaczenie wyjątków sieciowych na polskie
komunikaty dla użytkownika. Każda z tych funkcji jest czysta (bez `frappe`),
żeby dało się je przetestować lokalnym `unittest` bez działającego bencha.
"""

from datetime import datetime, timedelta

STATUS_MAP = {
	"COMPLETED": "Podpisana",
	"REJECTED": "Odrzucona",
	"EXPIRED": "Wygasła",
	"WITHDRAWN": "Wycofana",
}
"""Mapowanie statusu procesu dokumentu Autenti (zdalny, angielski) na
`Volteo Umowa.autenti_status` (lokalny, polski)."""

PENDING_REMOTE_STATUSES = ("DRAFT", "PROCESSING")
"""Potwierdzone (na sandboxie) nieterminalne statusy procesu dokumentu Autenti:
DRAFT -> PROCESSING -> <terminalny>. Umowa zasadnie stoi w PROCESSING dni
czekając na podpis, więc te statusy NIGDY nie są logowane jako błąd odpytania —
zalogowanie każdego wystąpienia zalałoby Error Log (~144 wpisy/dzień/dokument
przy odpytywaniu co 10 minut). Celowo osobno od `STATUS_MAP` — świadomie nie
mają odpowiednika w CRM."""

SEND_BLOCKED_STATUSES = ("Wysyłanie", "Wysłana", "Podpisana")
"""Statusy, przy których ponowne wysłanie umowy do podpisu jest zablokowane."""


def mozna_wyslac(status: str | None) -> bool:
	"""Czy umowę o danym `autenti_status` można wysłać (po raz pierwszy albo ponownie).

	Prawda dla: nigdy niewysłanej (`None`/pusty string) i dla stanów terminalnych
	nie-sukcesu (`Błąd`, `Odrzucona`, `Wygasła`, `Wycofana`) — po nich ponowne
	wysłanie jest świadomie dozwolone. Fałsz dla `SEND_BLOCKED_STATUSES`
	(`Wysyłanie`/`Wysłana`/`Podpisana`) i dla dowolnego innego, nierozpoznanego
	statusu — bezpieczne domyślne to blokada wysyłki, nie zezwolenie.
	"""
	if not status:
		return True
	return status in {"Błąd", "Odrzucona", "Wygasła", "Wycofana"}


def tytul_dokumentu(signer_name: str | None) -> str:
	"""Tytuł procesu dokumentu Autenti i nazwa pliku widoczna klientowi.

	Czytelny jako sprzedająca marka (ProEnergy), nie jako gołe id wewnętrzne.
	Puste/`None` imię i nazwisko podpisującego daje tytuł bez myślnika — nie
	"Umowa ProEnergy - " z pustym ogonem.
	"""
	if not signer_name:
		return "Umowa ProEnergy"
	return f"Umowa ProEnergy - {signer_name}"


def _zrodlo_klienta(indeks: int) -> str:
	"""Nazwa `zrodlo` dla kandydata na pozycji `indeks` (liczonej od zera) w liście
	podpisujących klientów przekazanej do `zbuduj_odbiorcow` (ops#169): pierwszy
	Zamawiający to `"klient"` (zgodność wsteczna ze sprzed listy, gdy był to
	jedyny argument), drugi to `"klient2"`, kolejni `"klient3"`, `"klient4"` itd.
	W praktyce lista ma dziś co najwyżej dwa elementy (umowa pojedyncza/podwójna),
	ale funkcja nie zakłada górnego limitu."""
	if indeks == 0:
		return "klient"
	return f"klient{indeks + 1}"


def zbuduj_odbiorcow(
	podpisujacy: list[dict[str, str | None] | None],
	prezes: dict[str, str | None] | None,
	handlowiec: dict[str, str | None] | None,
	archiwum: dict[str, str | None] | None,
) -> list[dict[str, str]]:
	"""Buduje uporządkowaną listę odbiorców procesu dokumentu Autenti: `podpisujacy`
	to UPORZĄDKOWANA LISTA kandydatów-klientów (jeden element dla umowy
	pojedynczej, dwa dla umowy podwójnej z drugim Zamawiającym, ops#169; kredyt
	ma zawsze dokładnie jeden element, wnioskodawcę), plus stałe role `prezes`,
	`handlowiec`, `archiwum`. Stała kolejność: wszyscy klienci z `podpisujacy`
	(w kolejności listy) -> prezes -> handlowiec -> archiwum.

	Każdy wejściowy słownik ma klucze `first_name`, `last_name`, `full_name`,
	`email` (dowolny może brakować lub być pusty). Każdy element `podpisujacy`
	i `prezes` stają się SIGNER-ami, `handlowiec` i `archiwum`, VIEWER-ami.
	Każdy wynikowy wpis ma klucze `first_name`, `last_name`, `full_name`,
	`email`, `role`, `zrodlo` (`"klient"`/`"klient2"`/`"prezes"`/`"handlowiec"`/
	`"archiwum"`, patrz `_zrodlo_klienta`).

	Kandydat jest pomijany, gdy jest `None` albo ma pusty/białoznakowy e-mail.
	To zachowanie CELOWO nie odróżnia "ten sam handlowiec figuruje dwa razy"
	(cicha deduplikacja, zamierzona) od "dwie różne osoby fizyczne mają
	identyczny e-mail" (błąd danych): tę drugą sytuację musi wychwycić
	wywołujący PRZED wywołaniem tej funkcji, przez `emaile_podpisujacych_rozlaczne`
	na samej liście `podpisujacy`, i zwrócić czytelny błąd zamiast pozwolić tej
	funkcji po cichu zwinąć obu klientów do jednego odbiorcy.

	Deduplikacja jest po e-mailu, bez rozróżniania wielkości liter: późniejszy
	duplikat jest odrzucany. Ponieważ kolejność wejść stawia wszystkich
	SIGNER-ów przed obu VIEWER-ami, SIGNER zawsze wygrywa z duplikatem
	VIEWER-a o tym samym adresie: podpisujący nigdy nie zostaje po cichu
	zdegradowany do samego podglądu.

	Nie wymyśla brakujących imion/nazwisk — puste pozostają pustymi stringami;
	to wywołujący decyduje, czy dla `archiwum` (typowo generyczny viewer)
	podstawić nazwę zastępczą.
	"""
	kandydaci: list[tuple[dict[str, str | None] | None, str, str]] = [
		(dane, "SIGNER", _zrodlo_klienta(indeks)) for indeks, dane in enumerate(podpisujacy)
	]
	kandydaci.append((prezes, "SIGNER", "prezes"))
	kandydaci.append((handlowiec, "VIEWER", "handlowiec"))
	kandydaci.append((archiwum, "VIEWER", "archiwum"))

	odbiorcy: list[dict[str, str]] = []
	widziane_emaile: set[str] = set()

	for dane, rola, zrodlo in kandydaci:
		if not dane:
			continue
		email = (dane.get("email") or "").strip()
		if not email:
			continue
		klucz = email.lower()
		if klucz in widziane_emaile:
			continue
		widziane_emaile.add(klucz)
		odbiorcy.append(
			{
				"first_name": dane.get("first_name") or "",
				"last_name": dane.get("last_name") or "",
				"full_name": dane.get("full_name") or "",
				"email": email,
				"role": rola,
				"zrodlo": zrodlo,
			}
		)

	return odbiorcy


def emaile_podpisujacych_rozlaczne(podpisujacy: list[dict[str, str | None] | None]) -> bool:
	"""Czy wszyscy kandydaci-klienci na liście `podpisujacy` (parametr
	`zbuduj_odbiorcow` powyżej) mają WZAJEMNIE różne adresy e-mail, bez
	rozróżniania wielkości liter (ops#169).

	W odróżnieniu od deduplikacji wewnątrz `zbuduj_odbiorcow` (która cicho
	zwija duplikat, zamierzone dla "ten sam handlowiec widnieje dwa razy"),
	dwaj RÓŻNI klienci (pierwszy i drugi Zamawiający) dzielący jeden e-mail są
	błędem danych, który wywołujący musi zgłosić jako czytelny komunikat,
	stąd osobna, jawna funkcja zamiast poleganie na cichej deduplikacji.

	Zwraca `True`, gdy lista ma mniej niż dwa elementy z niepustym e-mailem
	(nie ma z czym kolidować), w tym dla pojedynczego formularza kredytowego
	(zawsze jeden element) i dla umowy pojedynczej (jeden Zamawiający).
	`None` i pusty/białoznakowy e-mail są pomijane tak samo jak w
	`zbuduj_odbiorcow`, żeby te dwie funkcje widziały dokładnie ten sam zestaw
	"prawdziwych" kandydatów.
	"""
	widziane: set[str] = set()
	for dane in podpisujacy:
		if not dane:
			continue
		email = (dane.get("email") or "").strip()
		if not email:
			continue
		klucz = email.lower()
		if klucz in widziane:
			return False
		widziane.add(klucz)
	return True


def nazwa_pliku_umowy(deal: str) -> str:
	"""Nazwa pliku PDF-u umowy (niepodpisanej) dla danej szansy — wspólna z `crm/api/umowa.py`."""
	return f"Umowa-{deal.replace('/', '-')}.pdf"


def nazwa_pliku_podpisanego(deal: str) -> str:
	"""Nazwa pliku podpisanego PDF-u umowy pobranego z Autenti po zakończeniu procesu."""
	return f"Umowa-{deal.replace('/', '-')}-podpisana.pdf"


def tytul_dokumentu_kredytu(signer_name: str | None) -> str:
	"""Tytuł procesu dokumentu Autenti dla formularza kredytowego.

	Analogicznie do `tytul_dokumentu` — puste/`None` imię i nazwisko
	podpisującego daje tytuł bez myślnika, nie "Formularz kredytowy ProEnergy - "
	z pustym ogonem.
	"""
	if not signer_name or not signer_name.strip():
		return "Formularz kredytowy ProEnergy"
	return f"Formularz kredytowy ProEnergy - {signer_name}"


def czy_legacy_kredyt(deal: str, kredyt_name: str) -> bool:
	"""Czy `kredyt_name` to rekord `Volteo Kredyt` sprzed migracji na wiele
	formularzy na szansę (ops#159): przed tą migracją doctype miał autoname
	`field:deal`, więc `kredyt_name` był po prostu nazwą szansy. Rekordy
	założone PO migracji dostają nazwę typu hash (10 małych znaków
	alfanumerycznych, generowanych przez Frappe), nigdy równą `deal`.

	Ten rozstrzygnik jest jedynym miejscem, gdzie ta reguła jest zapisana:
	`prefiks_pliku_kredytu` (niżej) i każdy kod wołający ją muszą pytać TU,
	nigdy nie zgadywać po kształcie stringa."""
	return kredyt_name == deal


def prefiks_pliku_kredytu(deal: str, kredyt_name: str) -> str:
	"""Prefiks nazwy pliku PDF-u KONKRETNEGO formularza kredytowego danej szansy.

	JEDYNE źródło prawdy tego prefiksu — dzielone z `crm/api/kredyt.py`
	(generowanie PDF-u i sprzątanie starych plików, `_usun_stare_pliki_kredytu`)
	oraz z odpytywania Autenti po prefiksie (LIKE) przy szukaniu pliku źródłowego
	do wysyłki. Umowy tych trzech miejsc pękają, jeśli ten wzorzec się rozjedzie.

	Reguła zgodności wstecz (ops#159, OBOWIĄZKOWA, osobna gałąź, NIGDY
	realizowana przez `.replace('/', '-')` na całym wejściu): rekord legacy
	(`czy_legacy_kredyt(deal, kredyt_name)` prawdziwe, czyli `kredyt_name ==
	deal`) zachowuje STARY prefiks bez żadnego sufiksu, żeby pięć istniejących
	produkcyjnych plików formularza kredytowego dalej pasowało bajt w bajt.
	Każdy inny rekord (nazwa typu hash, założony po migracji na formularze 1:N)
	dostaje NOWY prefiks z 8-znakowym sufiksem `kredyt_name`: bez tego dwa
	formularze na jednej szansie dzieliłyby jeden prefiks, więc regeneracja
	PDF-u formularza A kasowałaby po cichu plik formularza B
	(`_usun_stare_pliki_kredytu` dopasowuje po prefiksie), a wysyłka formularza
	A do Autenti podpinałaby po cichu plik formularza B (`_pdf_kredytu_plik`
	bierze najnowszy pasujący plik).

	Sufiks jest doklejany do gotowego prefiksu bazowego wprost, BEZ
	`.replace('/', '-')`: nazwy hash to 10 małych znaków alfanumerycznych, bez
	ukośników, więc ta normalizacja byłaby tu no-opem w praktyce, ale
	stosowanie jej i tak ukryłoby błąd, gdyby kiedyś ktoś podał tu coś innego
	niż nazwę rekordu.
	"""
	prefiks_bazowy = f"Formularz-kredytowy-{deal.replace('/', '-')}"
	if czy_legacy_kredyt(deal, kredyt_name):
		return prefiks_bazowy
	return f"{prefiks_bazowy}-{kredyt_name[:8]}"


def nazwa_pliku_kredytu(deal: str, kredyt_name: str) -> str:
	"""Stała, nieznacznikowana nazwa pliku PDF-u formularza kredytowego (niepodpisanego)
	dla danego rekordu `Volteo Kredyt`: to po prostu nazwa, pod którą bajty PDF-u są
	wysyłane do Autenti, czyli nazwa, którą podpisujący widzi w interfejsie Autenti.

	W odróżnieniu od plików generowanych lokalnie przez `volteo_kredyt_pdf`
	(które NADAL mają znacznik czasu w nazwie, żeby ominąć cache przeglądarki —
	patrz komentarz przy `prefiks_nazwy` w `crm/api/kredyt.py`), ta nazwa jest
	stała z konwencji (analogicznie do `nazwa_pliku_umowy`), nie z wymogu
	Autenti — problem cache przeglądarki, który wymusza znacznik czasu na
	plikach zapisywanych lokalnie, nie dotyczy nazwy użytej przy wysyłce.
	"""
	return f"{prefiks_pliku_kredytu(deal, kredyt_name)}.pdf"


def nazwa_pliku_kredytu_podpisanego(deal: str, kredyt_name: str) -> str:
	"""Nazwa pliku podpisanego PDF-u formularza kredytowego pobranego z Autenti
	po zakończeniu procesu, dla danego rekordu `Volteo Kredyt`."""
	return f"{prefiks_pliku_kredytu(deal, kredyt_name)}-podpisany.pdf"


WYSYLANIE_TIMEOUT_MIN = 15
"""Po ilu minutach w lokalnym statusie „Wysyłanie” bez przejścia do „Wysłana” poller
(`api.poll_autenti_status`) uznaje wysyłkę za utkniętą i próbuje ją odzyskać albo
oznacza jako błąd (ops#143, F2). Worker mógł zginąć (OOM, restart kontenera) bez
wejścia w `except`: bez tego rekord blokowałby ponowną wysyłkę i regenerację PDF-u
na zawsze."""

ZALEGLY_PODPISANY_PLIK_LOG_MIN = 60
"""Po ilu minutach od `signed_at` brak podpisanego pliku jest już wart wpisu w Error
Log (ops#143, F3 pkt 3): poller ponawia próbę pobrania co 10 minut, więc logowanie
KAŻDEGO nieudanego przebiegu zalałoby Error Log; logujemy dopiero, gdy zaległość
faktycznie trwa."""

DECYZJA_ODZYSKAJ = "odzyskaj"
DECYZJA_NOWY_PROCES = "nowy_proces"

STATUSY_ODZYSKIWALNE = ("PROCESSING", "COMPLETED")
"""Zdalne statusy procesu dokumentu Autenti, dla których ponowna wysyłka rekordu w
lokalnym stanie „Błąd” z zachowanym `autenti_document_id` odzyskuje istniejący
proces zamiast tworzyć nowy (ops#143, F1 pkt 3). Celowo NIE zawiera DRAFT: DRAFT
oznacza proces utworzony, ale nigdy niewysłany (awaria nastąpiła przed `send()`,
klient nie dostał maila), więc stary DRAFT zostaje w Autenti jako nieszkodliwy
odpad, a wysyłka zaczyna się od nowa."""


def decyzja_ponownej_wysylki(zdalny_status: str | None) -> str:
	"""Decyduje, czy ponowna wysyłka dokumentu w lokalnym stanie „Błąd” z zachowanym
	`autenti_document_id` powinna odzyskać istniejący proces Autenti (`DECYZJA_ODZYSKAJ`),
	czy utworzyć nowy proces od zera (`DECYZJA_NOWY_PROCES`).

	`zdalny_status` to status zwrócony przez `AutentiClient.get_status`, albo `None`,
	gdy zdalne zapytanie zwróciło 404 (proces nie istnieje już po stronie Autenti).

	PROCESSING albo COMPLETED (`STATUSY_ODZYSKIWALNE`): proces idzie naprzód po
	stronie Autenti (albo już się zakończył), odzyskujemy go zamiast dublować
	żądanie podpisu do klienta drugim, równoległym procesem.

	DRAFT, dowolny terminalny status nie-sukces (REJECTED/EXPIRED/WITHDRAWN) albo
	`None` (404): tworzymy NOWY proces, stary (jeśli istnieje) zostaje w Autenti
	nieszkodliwy.
	"""
	if zdalny_status in STATUSY_ODZYSKIWALNE:
		return DECYZJA_ODZYSKAJ
	return DECYZJA_NOWY_PROCES


def czy_wysylanie_przekroczylo_timeout(sent_at: datetime | None, teraz: datetime) -> bool:
	"""Czy rekord w lokalnym statusie „Wysyłanie” przekroczył `WYSYLANIE_TIMEOUT_MIN`
	minut od zakolejkowania wysyłki i powinien zostać odzyskany albo oznaczony jako
	błąd przez poller (ops#143, F2).

	Brak `sent_at` (`None`) jest traktowany jako PRZEKROCZONY timeout, nigdy jako
	"jeszcze nie": to legacy stan sprzed tej poprawki (stary kod stemplował
	`sent_at` dopiero przy sukcesie wysyłki, nigdy przy samym ustawieniu
	„Wysyłanie”), więc taki rekord nie może utknąć w „Wysyłanie” na zawsze tylko
	dlatego, że nigdy nie dostał znacznika czasu.

	Granica jest ostra (`>`, nie `>=`): dokładnie `WYSYLANIE_TIMEOUT_MIN` minut to
	jeszcze NIE przekroczony timeout.
	"""
	if sent_at is None:
		return True
	return teraz - sent_at > timedelta(minutes=WYSYLANIE_TIMEOUT_MIN)


def czy_logowac_brak_podpisanego_pliku(signed_at: datetime | None, teraz: datetime) -> bool:
	"""Czy brak podpisanego pliku (`signed_pdf_file` puste mimo statusu „Podpisana”)
	jest już wart wpisu w Error Log, zamiast cichej kolejnej próby w następnym
	przebiegu pollera (ops#143, F3 pkt 3).

	Brak `signed_at` (`None`) jest traktowany jak zaległość wartą zalogowania od
	razu: to stan, który nie powinien wystąpić (status „Podpisana” zawsze
	stempluje `signed_at` w tym samym zapisie), więc bezpieczne domyślne to
	zalogowanie, nie cisza.
	"""
	if signed_at is None:
		return True
	return teraz - signed_at > timedelta(minutes=ZALEGLY_PODPISANY_PLIK_LOG_MIN)


KOMUNIKAT_TIMEOUT_WYSYLANIA_BEZ_PROCESU = (
	"Wysyłka została przerwana przed utworzeniem procesu w Autenti. Wyślij ponownie."
)
"""Komunikat błędu dla rekordu utkniętego w „Wysyłanie” bez `autenti_document_id`
po przekroczeniu `WYSYLANIE_TIMEOUT_MIN` (ops#143, F2): worker zginął, zanim
proces dokumentu zdążył powstać po stronie Autenti."""

KOMUNIKAT_TIMEOUT_WYSYLANIA_Z_PROCESEM = (
	"Wysyłka do Autenti nie zakończyła się w oczekiwanym czasie i nie udało się "
	"odzyskać procesu. Wyślij ponownie."
)
"""Komunikat błędu dla rekordu utkniętego w „Wysyłanie” z `autenti_document_id`
ustawionym po przekroczeniu `WYSYLANIE_TIMEOUT_MIN`, gdy `decyzja_ponownej_wysylki`
dla zdalnego statusu tego procesu nie zwróciła `DECYZJA_ODZYSKAJ` (ops#143, F2)."""


def komunikat_nierozpoznanego_statusu(zdalny_status: str) -> str:
	"""Treść zapisywana w `error_message`, żeby kolejny przebieg pollera mógł
	rozpoznać, że ten sam nierozpoznany status już został zalogowany raz
	(ops#143, F9), patrz `czy_logowac_nierozpoznany_status`."""
	return f"Nierozpoznany status Autenti: {zdalny_status}"


def czy_logowac_nierozpoznany_status(error_message: str | None, zdalny_status: str) -> bool:
	"""Czy nierozpoznany zdalny status (spoza `STATUS_MAP` i `PENDING_REMOTE_STATUSES`)
	jest wart nowego wpisu w Error Log, czy już był zalogowany dla tego dokumentu
	(ops#143, F9): dedukuje po tym, czy `error_message` zawiera już dokładnie ten
	sam komunikat (`komunikat_nierozpoznanego_statusu`) dla TEGO SAMEGO zdalnego
	statusu: inny nierozpoznany status na tym samym dokumencie musi zostać
	zalogowany osobno, więc porównanie treści, nie samego faktu "jakiś błąd
	zapisany", jest tu celowe."""
	return komunikat_nierozpoznanego_statusu(zdalny_status) not in (error_message or "")


def komunikat_bledu_wysylki(exc: Exception) -> str:
	"""Tłumaczy wyjątek złapany w `_autenti_send_job` na czysty, polski komunikat dla
	handlowca (`error_message`, wyświetlany w `UmowaTab.vue`) zamiast surowego
	`str(exc)` (ops#143, F15): angielski tekst wyjątku (często sam status HTTP albo
	treść odpowiedzi Autenti) nie jest zrozumiały dla użytkownika i nie należy do
	UI. Pełny traceback zostaje bez zmian w Error Log przez wołającego.

	Import `requests` jest lokalny (nie modułowy), żeby ten moduł pozostał
	frappe-free i importowalny nawet bez `requests` zainstalowanego (w praktyce
	`requests` jest zależnością projektu, patrz `client.py`), ale to świadome
	zabezpieczenie, nie wymóg środowiska testowego.
	"""
	try:
		import requests
	except ImportError:
		requests = None  # type: ignore[assignment]

	if requests is not None and isinstance(exc, requests.Timeout):
		return "Przekroczono czas oczekiwania na odpowiedź Autenti. Wyślij ponownie."

	if requests is not None and isinstance(exc, requests.HTTPError):
		response = getattr(exc, "response", None)
		status_code = getattr(response, "status_code", None) if response is not None else None
		if status_code:
			return f"Autenti odpowiedziało błędem HTTP {status_code}. Szczegóły w dzienniku błędów."
		return "Autenti odpowiedziało błędem HTTP. Szczegóły w dzienniku błędów."

	return "Wysyłka do Autenti nie powiodła się. Szczegóły w dzienniku błędów."


def wybierz_id_podpisanego_pliku(pliki: list[dict]) -> str | None:
	"""Wybiera id w pełni podpisanego pliku wyjściowego procesu dokumentu Autenti z
	listy kandydatów (pliki procesu bez `SOURCE_FILE`, patrz `AutentiClient.get_signed_file_id`)
	(ops#143, F3 pkt 2).

	Akceptuje WYŁĄCZNIE plik o `filePurpose == "SIGNED_CONTENT_FILE"`. Zdalny status
	COMPLETED oznacza podpisanie przez WSZYSTKICH sygnatariuszy, więc plik częściowo
	podpisany (`PARTIALLY_SIGNED_CONTENT_FILE`, jeden podpis) nigdy nie jest tu
	dopuszczalnym wynikiem: zapisanie go pod nazwą „...-podpisana.pdf” byłoby cichym
	błędem, nigdy nieodświeżonym (poprzedni fallback na `PARTIALLY_SIGNED_CONTENT_FILE`,
	a potem na „dowolny PDF”, jest usunięty w całości, nie tylko dla tego wywołania).

	Zwraca `None`, gdy taki plik jeszcze nie istnieje: poller ponawia próbę w
	kolejnym przebiegu (patrz `api.poll_autenti_status`), nigdy nie zgaduje
	zamiennika.
	"""
	for plik in pliki:
		if plik.get("filePurpose") == "SIGNED_CONTENT_FILE":
			return plik.get("id")
	return None
