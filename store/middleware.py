from .models import PageView
import json

class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # =====================================================================
        # === POCZĄTEK LOGIKI SPRAWDZANIA ZGODY ===
        # =====================================================================

        # Krok 1: Zdefiniuj nazwę cookie, którego szukasz.
        # Tę nazwę musisz znaleźć samodzielnie, postępując zgodnie z instrukcją powyżej!
        consent_cookie_name = '_pk_consent' # <-- ZMIEŃ TĘ NAZWĘ, JEŚLI JEST INNA!

        # Krok 2: Pobierz wartość cookie z żądania użytkownika.
        consent_cookie_value = request.COOKIES.get(consent_cookie_name)

        consent_granted = False
        if consent_cookie_value:
            try:
                # Piwik PRO często przechowuje zgody jako listę w JSON.
                # Przykładowa wartość: "[{"analytics":true,"marketing":false}]"
                # Musimy to sparsować.
                consent_data = json.loads(consent_cookie_value)
                
                # Sprawdź, czy dane są listą i weź pierwszy element
                if isinstance(consent_data, list) and len(consent_data) > 0:
                    consent_dict = consent_data[0]
                    # Sprawdź, czy zgoda na analitykę ('analytics') jest udzielona (ma wartość True)
                    # Nazwa klucza 'analytics' zależy od tego, jak nazwałeś kategorię w Piwik PRO!
                    if consent_dict.get('analytics') is True:
                        consent_granted = True
                        
            except (json.JSONDecodeError, TypeError, IndexError):
                # Jeśli cookie ma nieoczekiwany format, załóż, że nie ma zgody.
                consent_granted = False
        
        # Krok 3: Rejestruj odsłonę tylko wtedy, gdy zgoda została udzielona.
        if consent_granted:
            # Upewnij się, że sesja istnieje, zanim jej użyjesz
            if not request.session.session_key:
                request.session.create()

            # Stwórz i zapisz obiekt PageView
            PageView.objects.create(
                path=request.path,
                session_key=request.session.session_key,
                user=request.user if request.user.is_authenticated else None
            )
        
        # =====================================================================
        # === KONIEC LOGIKI SPRAWDZANIA ZGODY ===
        # =====================================================================

        response = self.get_response(request)
        return response