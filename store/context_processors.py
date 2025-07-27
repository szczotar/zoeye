from .models import Material, Category # Upewnij się, że importujesz Material i Category
from django.conf import settings

def site_data(request):
    """
    Context processor, który dodaje często używane dane do kontekstu szablonu.
    """
    return {
        'all_materials': Material.objects.all().order_by('name'),
        'all_categories': Category.objects.all().order_by('name'), # Możesz też dodać wszystkie kategorie
    }


def api_keys(request):
    """
    Dodaje klucze API do kontekstu szablonów.
    """
    return {
        'INPOST_API_TOKEN': settings.INPOST_KEY,
        # W przyszłości możesz tu dodać inne klucze, np. publiczny klucz Stripe
        # 'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
    }
