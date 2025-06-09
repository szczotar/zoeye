from django.contrib import admin
from .models import Category, Customer, Product,Order, Profile, ProductImage, Material
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
# admin.site.register(Product)
admin.site.register(Order)

admin.site.register(Profile)
admin.site.register(Material)

# Mix profile info and user info
class ProfileInline(admin.StackedInline):
	model = Profile

# Extend User Model
class UserAdmin(admin.ModelAdmin):
	model = User
	field = ["username", "first_name", "last_name", "email"]
	inlines = [ProfileInline]

class ProductImageInline(admin.TabularInline): # Możesz też użyć admin.StackedInline dla innego wyglądu
    model = ProductImage
    extra = 3 # Ile pustych formularzy zdjęć ma być wyświetlanych domyślnie
    fields = ['image', 'alt_text', 'order'] # Pola do wyświetlenia w inline

# Zarejestruj model Product z Inline

class ProductAdmin(admin.ModelAdmin):
    # Dodaj inline dla zdjęć produktu
    inlines = [ProductImageInline]

    # Pola do wyświetlenia w formularzu edycji produktu
    # Upewnij się, że wszystkie pola, które chcesz edytować, są tutaj
    fields = [
        'name', 'category', 'price', 'is_sale', 'sale_price',
        'description', 'gender', 'materials', # Dodane pola gender i materials
    ]

    # Opcjonalnie: Użyj filter_horizontal/filter_vertical dla pola ManyToMany 'materials'
    # filter_horizontal jest często lepsze dla relacji ManyToMany
    filter_horizontal = ('materials',) # Dodaj to dla lepszego widgetu wyboru materiałów

    # Pola do wyświetlenia na liście produktów w adminie
    list_display = ('name', 'category', 'price', 'is_sale', 'gender', 'display_materials', 'display_image_count') # Dodaj gender i materials do listy
    # Dodaj 'display_materials' metodę, aby wyświetlić materiały na liście

    # Pola, po których można filtrować na liście produktów
    list_filter = ('category', 'is_sale', 'gender', 'materials') # Dodaj filtry dla nowych pól

    # Pola, po których można wyszukiwać na liście produktów
    search_fields = ('name', 'description', 'materials__name') # Możesz wyszukiwać po nazwie produktu, opisie i nazwie materiału

    # Metoda dla list_display do pokazania liczby zdjęć
    def display_image_count(self, obj):
        return obj.images.count() # Używamy related_name='images' z modelu ProductImage
    display_image_count.short_description = 'Liczba zdjęć'

    # Metoda dla list_display do pokazania materiałów
    def display_materials(self, obj):
        # Zwraca string z nazwami materiałów oddzielonymi przecinkami
        return ", ".join([m.name for m in obj.materials.all()])
    display_materials.short_description = 'Materiały' # Nagłówek kolumny

admin.site.register(Product, ProductAdmin)
   
# Unregister the old way
admin.site.unregister(User)

# Re-Register the new way
admin.site.register(User, UserAdmin)


