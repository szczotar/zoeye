from .models import Material, Category # Upewnij się, że importujesz Material i Category

def site_data(request):
    """
    Context processor, który dodaje często używane dane do kontekstu szablonu.
    """
    return {
        'all_materials': Material.objects.all().order_by('name'),
        'all_categories': Category.objects.all().order_by('name'), # Możesz też dodać wszystkie kategorie
    }