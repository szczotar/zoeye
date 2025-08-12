from django import template

register = template.Library()

# --- Twoje istniejące filtry ---
@register.filter(name='iterable')
def is_iterable(value):
    """
    Sprawdza, czy wartość jest iterowalna (nie jest stringiem).
    Przydatne w szablonach do odróżnienia list/tuple od pojedynczych wartości.
    """
    if isinstance(value, str):
        return False
    try:
        iter(value)
        return True
    except TypeError:
        return False

# --- NOWY FILTR get_item ---
@register.filter(name='get_item') # Upewnij się, że nazwa filtra to 'get_item'
def get_item(dictionary, key):
    """Allows accessing dictionary items by key in templates."""
    # Dodano sprawdzenie, czy wejście jest słownikiem, aby uniknąć błędów
    if not isinstance(dictionary, dict):
        # Opcjonalnie: zwróć None lub pusty string, jeśli wejście nie jest słownikiem
        return None
    return dictionary.get(key)

@register.filter(name='is_list')
def is_list(value):
    """
    Filtr szablonu, który sprawdza, czy przekazana wartość jest listą.
    """
    return isinstance(value, list)