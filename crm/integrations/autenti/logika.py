"""Rdzeń logiki integracji Autenti dla podpisu elektronicznego UMOWY — frappe-free.

Jedyne źródło prawdy o mapowaniu statusów zdalnego procesu dokumentu Autenti na
statusy `Volteo Umowa.autenti_status`, o tym które statusy blokują ponowne
wysłanie, i o regule nazewnictwa plików PDF umowy — dzielonej z `crm/api/umowa.py`,
żeby nazwa oryginalnego PDF-u wysyłanego do podpisu i nazwa PDF-u generowanego
przez `volteo_umowa_pdf` nigdy nie mogły się rozjechać.
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
	"Umowa ProEnergy — " z pustym ogonem.
	"""
	if not signer_name:
		return "Umowa ProEnergy"
	return f"Umowa ProEnergy — {signer_name}"


def nazwa_pliku_umowy(deal: str) -> str:
	"""Nazwa pliku PDF-u umowy (niepodpisanej) dla danej szansy — wspólna z `crm/api/umowa.py`."""
	return f"Umowa-{deal.replace('/', '-')}.pdf"


def nazwa_pliku_podpisanego(deal: str) -> str:
	"""Nazwa pliku podpisanego PDF-u umowy pobranego z Autenti po zakończeniu procesu."""
	return f"Umowa-{deal.replace('/', '-')}-podpisana.pdf"
