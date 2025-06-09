from django import template

register = template.Library()

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