# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Decyzja: czy zalogowanego użytkownika trzeba wysłać na stronę ustawienia
hasła (`/update-password?key=...`), issue ops#154, wariant B.

Konta zakładane z `CRM Invitation` powstają bez hasła: zaproszony jest
logowany od razu po przyjęciu zaproszenia, podpisuje NDA i pracuje, ale po
wygaśnięciu sesji nie ma jak wrócić. Wariant B (decyzja właściciela): hasło
ustawia się zaraz PO podpisaniu NDA, więc dopóki NDA nie jest podpisane,
nie przekierowujemy.

Moduł celowo nie importuje ``frappe`` (jak ``crm.volteo_naming``), żeby dało
się go przetestować lokalnie bez benchu. Zbieranie faktów z bazy (wpis w
``__Auth``, ustawienia systemowe, LDAP, SSO, bramka NDA) mieszka w
``crm.api.user.needs_password_setup``.
"""

from urllib.parse import urlsplit

KONTA_TECHNICZNE = ("Guest", "Administrator")
"""Konta, których nigdy nie wysyłamy na stronę ustawienia hasła: gość nie ma
sesji, a Administrator jest kontem technicznym z własnym hasłem z instalacji."""


def czy_konto_osobiste(user: str | None) -> bool:
	"""True dla niepustego usera, który nie jest kontem technicznym.

	Wydzielone, żeby `needs_password_setup` mogło odciąć gościa i
	Administratora jeszcze przed jakimkolwiek zapytaniem do bazy.
	"""
	return bool(user) and user not in KONTA_TECHNICZNE


def czy_wymusic_haslo(
	user: str | None,
	ma_haslo: bool,
	wymaga_nda: bool,
	logowanie_haslem_wylaczone: bool,
	ldap_wlaczone: bool,
	ma_sso: bool,
) -> bool:
	"""Czy `user` ma zostać przekierowany na stronę ustawienia hasła.

	Args:
	        user: nazwa usera z sesji (`User.name`).
	        ma_haslo: czy w `__Auth` jest zapisane hasło tego usera.
	        wymaga_nda: czy user musi jeszcze podpisać oświadczenie (NDA);
	                wariant B ustawia hasło dopiero po podpisaniu.
	        logowanie_haslem_wylaczone: `System Settings.disable_user_pass_login`;
	                hasło i tak nie dałoby się użyć.
	        ldap_wlaczone: `LDAP Settings.enabled`; hasło trzyma LDAP, nie Frappe.
	        ma_sso: user loguje się przez zewnętrznego dostawcę (User Social Login);
	                brak hasła to dla niego stan poprawny.

	Returns:
	        True tylko wtedy, gdy żaden z powyższych wyjątków nie zachodzi.
	"""
	if not czy_konto_osobiste(user):
		return False
	if ma_haslo:
		return False
	if wymaga_nda:
		return False
	if logowanie_haslem_wylaczone:
		return False
	if ldap_wlaczone:
		return False
	if ma_sso:
		return False
	return True


def sciezka_wzgledna(url: str) -> str:
	"""Względny adres (ścieżka plus query) z pełnego linku.

	Frappe buduje link resetu hasła z `host_name` (`get_url`), co lokalnie gubi
	port (`http://crm.localhost/update-password?key=...` zamiast `:8080`).
	Przekierowanie na samą ścieżkę trafia na ten sam host i port, z którego
	przyszło żądanie. Schemat, host i fragment są odrzucane; pusta ścieżka
	daje "/".
	"""
	czesci = urlsplit(url)
	sciezka = czesci.path or "/"
	if czesci.query:
		return f"{sciezka}?{czesci.query}"
	return sciezka
