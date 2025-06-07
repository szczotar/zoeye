from django.contrib import admin
from .models import Category, Customer, Product,Order, Profile, ProductImage 
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
# admin.site.register(Product)
admin.site.register(Order)

admin.site.register(Profile)


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
@admin.register(Product) # Alternatywnie: admin.site.register(Product, ProductAdmin)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline] # Dodaj inline do listy inlinek
    # ... Twoje inne ustawienia ProductAdmin, np.:
    list_display = ('name', 'price', 'display_image_count') # Opcjonalnie: dodaj kolumnę pokazującą liczbę zdjęć

    # Opcjonalna metoda dla list_display
    def display_image_count(self, obj):
        return obj.images.count() # Używamy related_name='images'
    display_image_count.short_description = 'Liczba zdjęć'

# Unregister the old way
admin.site.unregister(User)

# Re-Register the new way
admin.site.register(User, UserAdmin)


