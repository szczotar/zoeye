from django.contrib import admin
# Z linii importu usunięto 'Customer' i 'Order'
from .models import Category, Product, Profile, ProductImage, Material, ProductVariation, Review
from django.contrib.auth.models import User
from django.db.models.aggregates import Sum

# Rejestracja modeli, które istnieją
admin.site.register(Category)
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

# --- INLINES DLA PRODUKTU ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']

class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1
    fields = ['size', 'stock']

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('user', 'created_at')
    fields = ('user', 'rating', 'comment', 'created_at')

# --- GŁÓWNY ADMIN DLA PRODUKTU ---
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariationInline, ReviewInline]
    fields = [
        'name', 'category', 'price', 'is_sale', 'sale_price',
        'stock', 'description', 'gender', 'materials',
    ]
    filter_horizontal = ('materials',)
    list_display = (
        'name', 'category', 'display_price_info', 'is_sale',
        'display_stock_info', 'gender', 'display_materials',
        'display_image_count', 'display_variation_count',
    )
    list_filter = ('category', 'is_sale', 'gender', 'materials', 'stock', 'variations__stock')
    search_fields = ('name', 'description', 'materials__name', 'variations__size')

    def display_image_count(self, obj):
        return obj.images.count()
    display_image_count.short_description = 'Zdjęcia'

    def display_materials(self, obj):
        return ", ".join([m.name for m in obj.materials.all()])
    display_materials.short_description = 'Materiały'

    def display_variation_count(self, obj):
        return obj.variations.count()
    display_variation_count.short_description = 'Liczba Wariacji'

    def display_stock_info(self, obj):
        if obj.has_variations():
            total_stock = obj.variations.aggregate(Sum('stock'))['stock__sum'] or 0
            return f"Wariacje: {total_stock}"
        else:
            return f"Produkt: {obj.stock}"
    display_stock_info.short_description = 'Stock'
    display_stock_info.admin_order_field = 'stock'

    def display_price_info(self, obj):
        price = obj.get_effective_price()
        if obj.has_variations():
            return f"Od {price}"
        else:
            return str(price)
    display_price_info.short_description = 'Cena'
    display_price_info.admin_order_field = 'price'

# Rejestracja Product z nowym adminem
admin.site.register(Product, ProductAdmin)

# --- ADMIN DLA RECENZJI ---
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at', 'product__name')
    search_fields = ('comment', 'product__name', 'user__username')
    date_hierarchy = 'created_at'

admin.site.register(Review, ReviewAdmin)

# Unregister i Re-Register User z nowym adminem
admin.site.unregister(User)
admin.site.register(User, UserAdmin)