"""Rdzeń logiki integracji Autenti dla podpisu elektronicznego — frappe-free.

Od b47 obsługuje DWA dokumenty: UMOWĘ (`Volteo Umowa`) i formularz kredytowy
(`Volteo Kredyt`). Jedyne źródło prawdy o mapowaniu statusów zdalnego procesu
dokumentu Autenti na statusy lokalne (`autenti_status`), o tym które statusy
blokują ponowne wysłanie, i o regule nazewnictwa plików PDF — dzielonej z
`crm/api/umowa.py` i `crm/api/kredyt.py`, żeby nazwa oryginalnego PDF-u
wysyłanego do podpisu i nazwa PDF-u generowanego przez `volteo_umowa_pdf`/
`volteo_kredyt_pdf` nigdy nie mogły się rozjechać.
"""

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


def zbuduj_odbiorcow(
	klient: dict[str, str | None] | None,
	prezes: dict[str, str | None] | None,
	handlowiec: dict[str, str | None] | None,
	archiwum: dict[str, str | None] | None,
) -> list[dict[str, str]]:
	"""Buduje uporządkowaną listę odbiorców procesu dokumentu Autenti z czterech
	kandydatów, w stałej kolejności: klient -> prezes -> handlowiec -> archiwum.

	Każdy wejściowy słownik ma klucze `first_name`, `last_name`, `full_name`,
	`email` (dowolny może brakować lub być pusty). `klient` i `prezes` stają się
	SIGNER-ami, `handlowiec` i `archiwum` — VIEWER-ami. Każdy wynikowy wpis ma
	klucze `first_name`, `last_name`, `full_name`, `email`, `role`, `zrodlo`
	(`"klient"`/`"prezes"`/`"handlowiec"`/`"archiwum"`).

	Kandydat jest pomijany, gdy jest `None` albo ma pusty/białoznakowy e-mail.
	Deduplikacja jest po e-mailu, bez rozróżniania wielkości liter: późniejszy
	duplikat jest odrzucany. Ponieważ kolejność wejść stawia obu SIGNER-ów przed
	obu VIEWER-ami, SIGNER zawsze wygrywa z duplikatem VIEWER-a o tym samym
	adresie — podpisujący nigdy nie zostaje po cichu zdegradowany do samego
	podglądu.

	Nie wymyśla brakujących imion/nazwisk — puste pozostają pustymi stringami;
	to wywołujący decyduje, czy dla `archiwum` (typowo generyczny viewer)
	podstawić nazwę zastępczą.
	"""
	kandydaci = (
		(klient, "SIGNER", "klient"),
		(prezes, "SIGNER", "prezes"),
		(handlowiec, "VIEWER", "handlowiec"),
		(archiwum, "VIEWER", "archiwum"),
	)

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


def prefiks_pliku_kredytu(deal: str) -> str:
	"""Prefiks nazwy pliku PDF-u formularza kredytowego dla danej szansy.

	JEDYNE źródło prawdy tego prefiksu — dzielone z `crm/api/kredyt.py`
	(generowanie PDF-u i sprzątanie starych plików, `_usun_stare_pliki_kredytu`)
	oraz z odpytywania Autenti po prefiksie (LIKE) przy szukaniu pliku źródłowego
	do wysyłki. Umowy tych trzech miejsc pękają, jeśli ten wzorzec się rozjedzie.
	"""
	return f"Formularz-kredytowy-{deal.replace('/', '-')}"


def nazwa_pliku_kredytu(deal: str) -> str:
	"""Stała, nieznacznikowana nazwa pliku PDF-u formularza kredytowego (niepodpisanego)
	dla danej szansy — to po prostu nazwa, pod którą bajty PDF-u są wysyłane do
	Autenti, czyli nazwa, którą podpisujący widzi w interfejsie Autenti.

	W odróżnieniu od plików generowanych lokalnie przez `volteo_kredyt_pdf`
	(które NADAL mają znacznik czasu w nazwie, żeby ominąć cache przeglądarki —
	patrz komentarz przy `prefiks_nazwy` w `crm/api/kredyt.py`), ta nazwa jest
	stała z konwencji (analogicznie do `nazwa_pliku_umowy`), nie z wymogu
	Autenti — problem cache przeglądarki, który wymusza znacznik czasu na
	plikach zapisywanych lokalnie, nie dotyczy nazwy użytej przy wysyłce.
	"""
	return f"{prefiks_pliku_kredytu(deal)}.pdf"


def nazwa_pliku_kredytu_podpisanego(deal: str) -> str:
	"""Nazwa pliku podpisanego PDF-u formularza kredytowego pobranego z Autenti
	po zakończeniu procesu."""
	return f"{prefiks_pliku_kredytu(deal)}-podpisany.pdf"
