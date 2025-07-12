from django.contrib import admin
from .models import Category, Customer, Product, Order, Profile, ProductImage, Material, ProductVariation,Review
from django.contrib.auth.models import User
from django.db.models.aggregates import Sum


# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
# admin.site.register(Product) 
# admin.site.register(Order) 

admin.site.register(Profile)
admin.site.register(Material)

# Mix profile info and user info
class ProfileInline(admin.StackedInline):
    model = Profile

# Extend User Model
class UserAdmin(admin.ModelAdmin):
    model = User
    fields = ["username", "first_name", "last_name", "email"]
    inlines = [ProfileInline]

# --- INLINE DLA ZDJĘĆ PRODUKTU ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']

# --- NOWY INLINE DLA WARIAcji PRODUKTU ---
# Zmieniono pola, usunięto pola cen
class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1
    # Pola do wyświetlenia w formularzu inline wariacji
    fields = ['size', 'stock'] # Usunięto price, is_sale, sale_price

# ------------------------------------------

# Zarejestruj model Product z Inline dla zdjęć i wariacji
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariationInline]

    # Pola do wyświetlenia w formularzu edycji produktu
    fields = [
        'name', 'category', 'price', 'is_sale', 'sale_price',
        'stock', # DODANO pole stock dla produktu bazowego
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
        'display_stock_info', # DODANO kolumnę z informacją o stocku
        'gender',
        'display_materials',
        'display_image_count',
        'display_variation_count',
    )

    # Pola, po których można filtrować na liście produktów
    # Można filtrować po stocku produktu bazowego i stocku wariacji
    list_filter = ('category', 'is_sale', 'gender', 'materials', 'stock', 'variations__stock')

    # Pola, po których można wyszukiwać na liście produktów
    search_fields = ('name', 'description', 'materials__name', 'variations__size')

    # Metoda dla list_display do pokazania liczby zdjęć
    def display_image_count(self, obj):
        return obj.images.count()
    display_image_count.short_description = 'Zdjęcia'

    # Metoda dla list_display do pokazania materiałów
    def display_materials(self, obj):
        return ", ".join([m.name for m in obj.materials.all()])
    display_materials.short_description = 'Materiały'

    # --- NOWA METODA DLA LIST_DISPLAY DO POKAZANIA WARIAcji ---
    def display_variation_count(self, obj):
        return obj.variations.count()
    display_variation_count.short_description = 'Liczba Wariacji'

    # --- NOWA METODA DLA LIST_DISPLAY DO POKAZANIA INFORMACJI O STOCKU ---
    def display_stock_info(self, obj):
        if obj.has_variations():
            # Jeśli ma wariacje, pokaż sumę stocku wariacji
            total_stock = obj.variations.aggregate(Sum('stock'))['stock__sum'] or 0
            return f"Wariacje: {total_stock}"
        else:
            # Jeśli nie ma wariacji, pokaż stock produktu bazowego
            return f"Produkt: {obj.stock}"
    display_stock_info.short_description = 'Stock'
    # Umożliwia sortowanie po stocku produktu bazowego
    # Sortowanie po sumie stocku wariacji jest bardziej złożone i wymaga adnotacji w admin queryset
    display_stock_info.admin_order_field = 'stock'


    # --- NOWA METODA DLA LIST_DISPLAY DO POKAZANIA CENY ---
    # Zmieniono logikę, bo wszystkie wariacje mają tę samą cenę bazową
    def display_price_info(self, obj):
        price = obj.get_effective_price() # Zawsze używamy efektywnej ceny produktu bazowego
        if obj.has_variations():
            # Jeśli produkt ma wariacje, pokazujemy "Od X" z ceną bazową
            return f"Od {price}"
        else:
            # Jeśli nie ma wariacji, pokazujemy po prostu cenę bazową
            return str(price) # Konwertuj Decimal na string dla wyświetlenia

    display_price_info.short_description = 'Cena'
    display_price_info.admin_order_field = 'price' # Umożliwia sortowanie po bazowej cenie

admin.site.register(Product, ProductAdmin)

# --- OPCJONALNIE: Zmień OrderAdmin aby wyświetlał wariację lub produkt ---
# Jeśli chcesz zobaczyć wariację/produkt na liście zamówień
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ('display_item', 'customer', 'quantity', 'date', 'status') # Zmieniono na display_item
#     list_filter = ('status', 'date') # Możesz dodać filtry po produkcie/wariacji jeśli potrzebujesz

#     def display_item(self, obj):
#         if obj.variation:
#             return f"Wariacja: {obj.variation.__str__()}"
#         elif obj.product:
#             return f"Produkt: {obj.product.name}"
#         return "Nieznany przedmiot"
#     display_item.short_description = 'Przedmiot'

# admin.site.unregister(Order) # Odrejestruj stary OrderAdmin
# admin.site.register(Order, OrderAdmin) # Zarejestruj nowy OrderAdmin

# Unregister the old way
admin.site.unregister(User)

# Re-Register the new way
admin.site.register(User, UserAdmin)


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at', 'product__name') # Filtruj po ocenie, dacie, nazwie produktu
    search_fields = ('comment', 'product__name', 'user__username') # Wyszukuj w komentarzach, nazwie produktu, nazwie użytkownika
    date_hierarchy = 'created_at' # Dodaj pasek nawigacji po dacie

# Opcjonalnie: Dodaj recenzje jako inline w ProductAdmin
class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0 # Nie pokazuj pustych formularzy domyślnie
    readonly_fields = ('user', 'created_at') # Te pola nie powinny być edytowalne w inline
    fields = ('user', 'rating', 'comment', 'created_at') # Pola do wyświetlenia

# Zmodyfikuj ProductAdmin, aby dodać ReviewInline
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariationInline, ReviewInline] # DODANO ReviewInline

    # ... (pozostałe ustawienia ProductAdmin: fields, filter_horizontal, list_display, list_filter, search_fields, metody display_...) ...

# Zarejestruj nowy model Admin
admin.site.register(Review, ReviewAdmin)
