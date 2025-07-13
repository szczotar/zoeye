from django import template
from django.utils.safestring import mark_safe # Do oznaczania HTML jako bezpiecznego
import math # <-- DODAJ TEN IMPORT

register = template.Library()

# Użyj tagów <i> z klasami Font Awesome
FULL_STAR_HTML = '<i class="fas fa-star"></i>' # Pełna gwiazdka (solid)
EMPTY_STAR_HTML = '<i class="far fa-star"></i>' # Pusta gwiazdka (regular)

# Możesz dodać style inline tutaj, ale lepiej stylizować w CSS
# FULL_STAR_HTML = '<i class="fas fa-star" style="color: #dcb14a;"></i>'
# EMPTY_STAR_HTML = '<i class="far fa-star" style="color: #dcb14a;"></i>'


@register.filter
def render_stars(rating, max_rating=5):
    """
    Renders a rating as a string of Font Awesome star icons (HTML).
    Accepts float or int. Rounds UP the rating for display.
    """
    if rating is None:
        return "" # Zwróć pusty string jeśli ocena nie jest ustawiona

    try:
        # Konwertuj wejściową ocenę na float, aby obsłużyć wartości dziesiętne
        rating_float = float(rating)
    except (ValueError, TypeError):
        return "" # Zwróć pusty string jeśli ocena nie jest liczbą

    # --- Zaokrąglanie w górę ---
    # Oblicz liczbę pełnych gwiazdek przez zaokrąglenie w górę
    rounded_rating = round(rating_float) # <-- Użyj math.ceil()
    # Upewnij się, że zaokrąglona wartość mieści się w zakresie 0 do max_rating
    rounded_rating = max(0, min(rounded_rating, max_rating))
    # -------------------------

    # Generowanie HTML ikon na podstawie zaokrąglonej wartości
    full_stars_html = FULL_STAR_HTML * rounded_rating
    empty_stars_html = EMPTY_STAR_HTML * (max_rating - rounded_rating)
    stars_html_string = full_stars_html + empty_stars_html

    # Oznacz wygenerowany HTML jako bezpieczny, aby Django go nie escapował
    return mark_safe(stars_html_string)