# store/templatetags/rating_filters.py
from django import template
from django.utils.safestring import mark_safe # Do oznaczania HTML jako bezpiecznego

register = template.Library()

# Możesz użyć znaków Unicode gwiazdek
FULL_STAR = '⭐️' # Pełna gwiazdka
EMPTY_STAR = '☆' # Pusta gwiazdka

# Alternatywnie, użyj ikon Font Awesome (wymaga załadowania Font Awesome CSS)
# FULL_STAR = '<i class="fas fa-star" style="color: gold;"></i>' # Przykładowy styl
# EMPTY_STAR = '<i class="far fa-star" style="color: gold;"></i>' # Przykładowy styl

@register.filter
def render_stars(rating, max_rating=5):
    """
    Renders a rating as a string of stars.
    e.g., 3 | render_stars -> '⭐️⭐️⭐️☆☆'
    If using Font Awesome, returns HTML string.
    """
    if rating is None:
        return "" # Zwróć pusty string jeśli ocena nie jest ustawiona

    try:
        rating = int(rating)
    except (ValueError, TypeError):
        return "" # Zwróć pusty string jeśli ocena nie jest liczbą

    if not (0 <= rating <= max_rating):
         return "" # Zwróć pusty string jeśli ocena poza zakresem

    # Tworzenie stringa z gwiazdkami
    full_stars = FULL_STAR * rating
    empty_stars = EMPTY_STAR * (max_rating - rating)
    stars_string = full_stars + empty_stars

    # Jeśli używasz HTML (np. ikony Font Awesome), oznacz jako bezpieczne
    # return mark_safe(stars_string) # Użyj tego jeśli FULL_STAR/EMPTY_STAR to HTML

    return stars_string # Jeśli używasz znaków Unicode