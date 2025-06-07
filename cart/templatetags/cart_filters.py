from django import template

# Tworzymy instancję klasy Library, która będzie przechowywać nasze niestandardowe filtry i tagi.
register = template.Library()

# Dekorator @register.filter(name='get_item') rejestruje funkcję get_item jako filtr szablonu o nazwie 'get_item'.
@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Zwraca wartość z dictionary dla danego klucza.
    Używane w szablonach do dostępu do elementów słownika, np. {{ my_dict|get_item:my_key }}

    Argumenty:
    dictionary: Słownik, z którego chcemy pobrać wartość.
    key: Klucz, którego wartość chcemy pobrać.

    Zwraca:
    Wartość powiązaną z kluczem w słowniku, lub None, jeśli klucz nie istnieje.
    """
    # Ważne: Klucze w słownikach POST, GET, sesji, a często i w koszyku
    # są traktowane jako stringi. product.id jest zazwyczaj liczbą (int).
    # Upewnij się, że klucz używany do lookupu w słowniku quantities
    # ma taki sam typ jak klucze w tym słowniku.
    # Jeśli quantities ma klucze jako stringi ID (np. '1', '2'), konwersja product.id na string jest potrzebna.
    # product.id|slugify w szablonie konwertuje na string i usuwa niebezpieczne znaki, co jest zazwyczaj OK dla ID.
    # Jeśli quantities ma klucze jako int, usuń str() lub upewnij się, że klucz jest int.
    # Najbezpieczniej jest zazwyczaj używać stringów jako kluczy w słownikach pochodzących z żądań/sesji.

    # Używamy metody .get() zamiast dictionary[key], aby uniknąć błędu KeyError,
    # jeśli klucz nie istnieje. .get() zwraca None w takim przypadku (lub inną wartość domyślną, jeśli podana).
    try:
        # Spróbujmy pobrać klucz jako string
        return dictionary.get(str(key))
    except TypeError:
        # Jeśli key nie może być przekonwertowany na string, spróbujmy pobrać bez konwersji
        try:
             return dictionary.get(key)
        except Exception:
             # Jeśli nadal błąd, zwróć None
             return None


# Możesz dodać inne niestandardowe filtry w tym samym pliku,
# używając @register.filter dla każdego z nich.
# Przykład prostego filtra do konwersji na string (jeśli product.id|slugify nie działa lub go nie potrzebujesz)
# @register.filter(name='to_str')
# def to_str(value):
#    return str(value)

# Przykład filtra do obliczenia subtotal dla elementu koszyka (wymaga przekazania elementu koszyka)
# @register.filter(name='item_subtotal')
# def item_subtotal(item):
#     # Zakładając, że item to słownik lub obiekt z kluczami/atrybutami 'qty' i 'price'
#     try:
#         return item['qty'] * item['price']
#     except (TypeError, KeyError):
#         return 0 # Zwróć 0 w przypadku błędu