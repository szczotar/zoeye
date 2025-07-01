from django.contrib import admin
from .models import Category, Customer, Product, Order, Profile, ProductImage, Material, ProductVariation # Importuj ProductVariation
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
# admin.site.register(Product) - odkomentujemy poniżej z CustomAdmin
# admin.site.register(Order) - odkomentujemy poniżej z CustomAdmin

admin.site.register(Profile)
admin.site.register(Material)

# Mix profile info and user info
class ProfileInline(admin.StackedInline):
    model = Profile

# Extend User Model
class UserAdmin(admin.ModelAdmin):
    model = User
    # field = ["username", "first_name", "last_name", "email"] # 'field' should be 'fields'
    fields = ["username", "first_name", "last_name", "email"]
    inlines = [ProfileInline]

# --- INLINE DLA ZDJĘĆ PRODUKTU ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1 # Zmniejszone do 1, aby nie było za dużo pustych formularzy
    fields = ['image', 'alt_text', 'order']

# --- NOWY INLINE DLA WARIAcji PRODUKTU ---
class ProductVariationInline(admin.TabularInline): # Użyj TabularInline, jest bardziej kompaktowy
    model = ProductVariation
    extra = 1 # Ile pustych formularzy wariacji ma być domyślnie
    # Pola do wyświetlenia w formularzu inline wariacji
    fields = ['size', 'price', 'is_sale', 'sale_price', 'stock'] # Dodaj 'stock'

# ------------------------------------------

# Zarejestruj model Product z Inline dla zdjęć i wariacji
class ProductAdmin(admin.ModelAdmin):
    # Dodaj inline dla zdjęć i wariacji
    inlines = [ProductImageInline, ProductVariationInline] # Dodaj ProductVariationInline

    # Pola do wyświetlenia w formularzu edycji produktu
    fields = [
        'name', 'category', 'price', 'is_sale', 'sale_price',
        'description', 'gender', 'materials',
    ]

    # Użyj filter_horizontal dla pola ManyToMany 'materials'
    filter_horizontal = ('materials',)

    # Pola do wyświetlenia na liście produktów w adminie
    list_display = (
        'name',
        'category',
        'display_price_info', # Zmieniamy wyświetlanie ceny
        'is_sale',
        'gender',
        'display_materials',
        'display_image_count',
        'display_variation_count', # Nowa kolumna dla wariacji
    )

    # Pola, po których można filtrować na liście produktów
    list_filter = ('category', 'is_sale', 'gender', 'materials', 'variations__size') # Można filtrować po rozmiarze wariacji

    # Pola, po których można wyszukiwać na liście produktów
    search_fields = ('name', 'description', 'materials__name', 'variations__size') # Można wyszukiwać po rozmiarze wariacji

    # Metoda dla list_display do pokazania liczby zdjęć
    def display_image_count(self, obj):
        return obj.images.count()
    display_image_count.short_description = 'Zdjęcia' # Skrócona nazwa kolumny

    # Metoda dla list_display do pokazania materiałów
    def display_materials(self, obj):
        return ", ".join([m.name for m in obj.materials.all()])
    display_materials.short_description = 'Materiały'

    # --- NOWA METODA DLA LIST_DISPLAY DO POKAZANIA WARIAcji ---
    def display_variation_count(self, obj):
        return obj.variations.count()
    display_variation_count.short_description = 'Wariacje (Rozmiary)' # Skrócona nazwa kolumny

    # --- NOWA METODA DLA LIST_DISPLAY DO POKAZANIA CENY Z UWZGLĘDNIENIEM WARIAcji ---
    def display_price_info(self, obj):
        if obj.has_variations():
            # Jeśli produkt ma wariacje, pokaż najniższą cenę wariacji
            min_price = obj.get_min_variation_price()
            return f"Od {min_price}" if min_price is not None else "Wariacje"
        else:
            # Jeśli nie ma wariacji, pokaż cenę bazową (uwzględniając wyprzedaż)
            price = obj.get_effective_price()
            if obj.is_sale:
                 return f"{price} (Wyprzedaż)"
            return str(price) # Konwertuj Decimal na string dla wyświetlenia

    display_price_info.short_description = 'Cena' # Skrócona nazwa kolumny
    display_price_info.admin_order_field = 'price' # Umożliwia sortowanie po bazowej cenie

admin.site.register(Product, ProductAdmin)

# --- OPCJONALNIE: Zmień OrderAdmin aby wyświetlał wariację ---
# Jeśli chcesz zobaczyć wariację na liście zamówień
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ('variation', 'customer', 'quantity', 'date', 'status') # Zmieniono 'product' na 'variation'
#     list_filter = ('status', 'date', 'variation__product__category') # Możesz filtrować po kategorii produktu wariacji

# admin.site.unregister(Order) # Odrejestruj stary OrderAdmin
# admin.site.register(Order, OrderAdmin) # Zarejestruj nowy OrderAdmin

# Unregister the old way
admin.site.unregister(User)

# Re-Register the new way
admin.site.register(User, UserAdmin)