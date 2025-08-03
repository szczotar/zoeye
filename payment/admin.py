from django.contrib import admin
from .models import ShippingAddress
from .models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from store.admin_site import site

# --- Definicje klas Admin dla modeli z aplikacji 'payment' ---

@admin.register(ShippingAddress, site=site)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'shipping_full_name', 'shipping_city', 'shipping_country')
    search_fields = ('shipping_full_name', 'user__username')

class OrderItemInline(admin.TabularInline): # Używamy TabularInline dla bardziej kompaktowego wyglądu
    model = OrderItem
    readonly_fields = ('product', 'variation', 'user', 'quantity', 'price') # Pozycje zamówienia są tylko do odczytu
    extra = 0
    can_delete = False # Zazwyczaj nie chcemy usuwać pozycji z istniejącego zamówienia

    def has_add_permission(self, request, obj=None):
        return False # Wyłącz przycisk "Add another Order Item"

@admin.register(Order, site=site)
class OrderAdmin(admin.ModelAdmin):
    model = Order
    list_display = ('order_number', 'full_name', 'amount_paid', 'date_ordered', 'shipped')
    list_filter = ('shipped', 'date_ordered')
    search_fields = ('order_number', 'full_name', 'email')
    readonly_fields = ('date_ordered', 'order_number', 'user', 'full_name', 'email', 'shipping_address', 'amount_paid')
    
    # Uporządkowanie pól w panelu edycji
    fieldsets = (
        ('Informacje o zamówieniu', {
            'fields': ('order_number', 'date_ordered', 'amount_paid', 'payment_intent_id')
        }),
        ('Dane klienta', {
            'fields': ('user', 'full_name', 'email')
        }),
        ('Adres wysyłki', {
            'classes': ('collapse',), # Domyślnie zwinięte
            'fields': ('shipping_address',)
        }),
        ('Status wysyłki', {
            'fields': ('shipped', 'date_shipped')
        }),
    )
    
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        return False # Zamówienia powinny być tworzone tylko przez sklep, a nie w panelu admina

# Rejestrujemy OrderItem, aby był widoczny, ale zazwyczaj zarządzamy nim przez Order
@admin.register(OrderItem, site=site)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'variation', 'quantity', 'price')
    readonly_fields = ('order', 'product', 'variation', 'user', 'quantity', 'price')

    def has_add_permission(self, request):
        return False