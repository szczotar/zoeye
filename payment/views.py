from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
import datetime
from decimal import Decimal
from django.db import transaction

# Importy z innych aplikacji
from cart.cart import Cart
from store.models import Product, Profile, ProductVariation

# Importy z bieżącej aplikacji (payment)
from .forms import ShippingForm, PaymentForm, CheckoutForm
from .models import ShippingAddress, Order, OrderItem

# --- Widoki panelu admina (Dashboard) ---

def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        order = get_object_or_404(Order, id=pk)
        items = OrderItem.objects.filter(order=order)

        if request.method == 'POST':
            status = request.POST.get('shipping_status')
            if status == "true":
                now = datetime.datetime.now()
                order.shipped = True
                order.date_shipped = now
                order.save()
            else:
                order.shipped = False
                order.date_shipped = None
                order.save()
            messages.success(request, "Shipping Status Updated")
            return redirect('orders', pk=pk)

        return render(request, 'payment/orders.html', {"order": order, "items": items})
    else:
        messages.error(request, "Access Denied")
        return redirect('home')

def not_shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False).order_by('-date_ordered')
        if request.method == 'POST':
            num = request.POST.get('num')
            if num:
                try:
                    order_to_ship = get_object_or_404(Order, id=num)
                    now = datetime.datetime.now()
                    order_to_ship.shipped = True
                    order_to_ship.date_shipped = now
                    order_to_ship.save()
                    messages.success(request, f"Order {num} Shipping Status Updated to Shipped")
                except Exception as e:
                    messages.error(request, f"Error updating order {num}: {e}")
            else:
                messages.error(request, "No order ID provided.")
            return redirect('not_shipped_dash')
        return render(request, "payment/not_shipped_dash.html", {"orders": orders})
    else:
        messages.error(request, "Access Denied")
        return redirect('home')

def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True).order_by('-date_shipped')
        if request.method == 'POST':
            num = request.POST.get('num')
            if num:
                try:
                    order_to_unship = get_object_or_404(Order, id=num)
                    order_to_unship.shipped = False
                    order_to_unship.date_shipped = None
                    order_to_unship.save()
                    messages.success(request, f"Order {num} Shipping Status Updated to Not Shipped")
                except Exception as e:
                    messages.error(request, f"Error updating order {num}: {e}")
            else:
                messages.error(request, "No order ID provided.")
            return redirect('shipped_dash')
        return render(request, "payment/shipped_dash.html", {"orders": orders})
    else:
        messages.error(request, "Access Denied")
        return redirect('home')

# --- Widoki procesu składania zamówienia ---

def checkout(request):
    cart = Cart(request)
    cart_items = list(cart.__iter__())
    totals = cart.cart_total()

    if not cart_items:
        messages.warning(request, "Twój koszyk jest pusty.")
        return redirect('cart_summary')

    if request.method == 'POST':
        checkout_form = CheckoutForm(request.POST)
        shipping_form = ShippingForm(request.POST, prefix='shipping')
        is_different_shipping = 'shipping-address-checkbox' in request.POST

        if checkout_form.is_valid() and (not is_different_shipping or shipping_form.is_valid()):
            try:
                with transaction.atomic():
                    billing_data = checkout_form.cleaned_data
                    
                    if is_different_shipping:
                        shipping_data = shipping_form.cleaned_data
                        full_name = shipping_data['shipping_full_name']
                        shipping_address_str = (
                            f"{full_name}\n"
                            f"{shipping_data['shipping_address1']}\n"
                            f"{shipping_data.get('shipping_address2', '')}\n"
                            f"{shipping_data['shipping_zipcode']} {shipping_data['shipping_city']}\n"
                            f"{shipping_data['shipping_country']}"
                        ).strip()
                    else:
                        full_name = f"{billing_data['first_name']} {billing_data['last_name']}"
                        shipping_address_str = (
                            f"{full_name}\n"
                            f"{billing_data['address1']}\n"
                            f"{billing_data.get('address2', '')}\n"
                            f"{billing_data['zipcode']} {billing_data['city']}\n"
                            f"{billing_data['country']}"
                        ).strip()

                    delivery_cost = 0
                    if request.POST.get('delivery_method') == 'courier':
                        delivery_cost = 15.00
                    elif request.POST.get('delivery_method') == 'locker':
                        delivery_cost = 12.00
                    
                    amount_paid = totals + Decimal(str(delivery_cost))

                    order = Order.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        full_name=full_name,
                        email=billing_data['email'],
                        shipping_address=shipping_address_str,
                        amount_paid=amount_paid,
                    )

                    for item in cart_items:
                        if item.get('item_type') == 'variation':
                            variation = item.get('item_object')
                            OrderItem.objects.create(order=order, variation=variation, product=variation.product, user=request.user if request.user.is_authenticated else None, quantity=item.get('quantity'), price=variation.get_effective_price())
                            variation.stock -= item.get('quantity')
                            variation.save()
                        else:
                            product = item.get('item_object')
                            OrderItem.objects.create(order=order, product=product, user=request.user if request.user.is_authenticated else None, quantity=item.get('quantity'), price=product.price)

                cart.clear()
                if request.user.is_authenticated:
                    try:
                        profile = Profile.objects.get(user=request.user)
                        profile.old_cart = ""
                        profile.save()
                    except Profile.DoesNotExist:
                        pass

                messages.success(request, "Zamówienie zostało złożone pomyślnie!")
                return redirect('payment_success')

            except Exception as e:
                print(f"Błąd podczas tworzenia zamówienia: {e}")
                messages.error(request, f"Wystąpił błąd podczas składania zamówienia: {e}")
                return redirect('checkout')
        else:
            messages.error(request, "Proszę poprawić błędy w formularzu.")
            context = {"cart_items": cart_items, "totals": totals, "checkout_form": checkout_form, "shipping_form": shipping_form}
            return render(request, "payment/checkout.html", context)
    else: # Metoda GET
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            try:
                profile = request.user.profile
                initial_data['phone'] = profile.phone
            except Profile.DoesNotExist:
                pass
            
            default_shipping_address = ShippingAddress.objects.filter(user=request.user, default_shipping=True).first()
            if default_shipping_address:
                initial_data['address1'] = default_shipping_address.shipping_address1
                initial_data['address2'] = default_shipping_address.shipping_address2
                initial_data['city'] = default_shipping_address.shipping_city
                initial_data['zipcode'] = default_shipping_address.shipping_zipcode
                initial_data['country'] = default_shipping_address.shipping_country
        
        checkout_form = CheckoutForm(initial=initial_data)
        shipping_form = ShippingForm(prefix='shipping')
        context = {"cart_items": cart_items, "totals": totals, "checkout_form": checkout_form, "shipping_form": shipping_form}
        return render(request, "payment/checkout.html", context)

def payment_success(request):
    return render(request, "payment/payment_success.html", {})

def terms_page(request):
    return render(request, "payment/terms_page.html", {})

# --- STARE, NIEUŻYWANE WIDOKI (można je usunąć) ---
# Widoki billing_info i process_order zostały zastąpione przez logikę w checkout

def billing_info(request):
    messages.info(request, "This page is deprecated.")
    return redirect('checkout')

def process_order(request):
    messages.info(request, "This page is deprecated.")
    return redirect('checkout')