from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import F
import json
# Importy z innych aplikacji
from cart.cart import Cart
from store.models import Product, Profile, ProductVariation
from django.urls import reverse

# Importy z bieżącej aplikacji (payment)
from .forms import ShippingForm, PaymentForm, CheckoutForm
from .models import ShippingAddress, Order, OrderItem

from django.views.decorators.csrf import csrf_exempt
import stripe
from django.http import HttpResponse
from django.conf import settings
from django.templatetags.static import static
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.environ['STRIPE_SECRET_KEY']
# --- Widoki panelu admina (Dashboard) ---

def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        order = get_object_or_404(Order, id=pk)
        items = OrderItem.objects.filter(order=order)

        if request.method == 'POST':
            status = request.POST.get('shipping_status')
            if status == "true":
                order.shipped = True
                order.save() # Sygnał pre_save w modelu ustawi datę
            else:
                order.shipped = False
                order.date_shipped = None # Ręczne wyczyszczenie daty
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
                order_to_ship = get_object_or_404(Order, id=num)
                order_to_ship.shipped = True
                order_to_ship.save()
                messages.success(request, f"Order {order_to_ship.order_number} marked as shipped.")
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
                order_to_unship = get_object_or_404(Order, id=num)
                order_to_unship.shipped = False
                order_to_unship.date_shipped = None
                order_to_unship.save()
                messages.success(request, f"Order {order_to_unship.order_number} marked as not shipped.")
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
            # Zapisz tymczasowo dane z formularza w sesji
            request.session['checkout_data'] = checkout_form.cleaned_data
            if is_different_shipping:
                request.session['shipping_data'] = shipping_form.cleaned_data
            else:
                if 'shipping_data' in request.session:
                    del request.session['shipping_data']
            
            # Oblicz koszt dostawy
            delivery_cost = Decimal('2.00') if request.POST.get('delivery_method') == 'courier' else Decimal('1.00')
            total_amount = totals + delivery_cost
            
            # Przygotuj pozycje dla Stripe Checkout
        line_items = []
        for item in cart_items:
            price_in_cents = int(item['item_object'].get_effective_price() * 100)
            
            # === POPRAWIONA LOGIKA POBIERANIA NAZWY PRODUKTU ===
            if item['item_type'] == 'variation':
                # Jeśli to wariacja, nazwa pochodzi z powiązanego produktu
                product_name = f"{item['item_object'].product.name} ({item['item_object'].size})"
            else:
                # Jeśli to produkt, nazwa pochodzi bezpośrednio z niego
                product_name = item['item_object'].name
            # =====================================================
            
            line_items.append({
                'price_data': {
                    'currency': 'pln',
                    'product_data': {
                        'name': product_name,
                    },
                    'unit_amount': price_in_cents,
                },
                'quantity': item['quantity'],
            })
                    
            # Dodaj koszt dostawy jako osobną pozycję
            line_items.append({
                'price_data': {
                    'currency': 'pln',
                    'product_data': { 'name': 'Dostawa' },
                    'unit_amount': int(delivery_cost * 100),
                },
                'quantity': 1,
            })

            cart_data_for_stripe = {key: value for key, value in cart.cart.items()}
            metadata =  {
                'user_id': request.user.id if request.user.is_authenticated else '',
                'checkout_data': json.dumps(checkout_form.cleaned_data),
                'cart_data': json.dumps(cart_data_for_stripe),
            }

            if 'shipping_data' in request.session:
                metadata['shipping_data'] = json.dumps(shipping_form.cleaned_data)

            # 3. DODAJ PACZKOMAT ID DO ISTNIEJĄCEGO SŁOWNIKA
            if request.POST.get('delivery_method') == 'locker':
                paczkomat_id = request.POST.get('paczkomat_id')
                if paczkomat_id:
                    metadata['paczkomat_id'] = paczkomat_id
            try:

                # Stwórz sesję płatności Stripe Checkout
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card', 'blik'],
                    line_items=line_items,
                    mode='payment',
                    metadata=metadata,
                    success_url=request.build_absolute_uri(reverse('payment_success_stripe')),
                    cancel_url=request.build_absolute_uri(reverse('payment_cancelled')),
         
                )
                # Zapisz ID sesji w sesji Django, aby powiązać ją z zamówieniem
                request.session['stripe_session_id'] = checkout_session.id
                
                # Przekieruj użytkownika na stronę płatności Stripe
                return redirect(checkout_session.url, code=303)
            
            except Exception as e:
                messages.error(request, f"Błąd podczas komunikacji z systemem płatności: {e}")
                return redirect('checkout')

        
        else:
            messages.error(request, "Proszę poprawić błędy w formularzu.")
            context = {"cart_items": cart_items, "totals": totals, "checkout_form": checkout_form, "shipping_form": shipping_form}
            return render(request, "payment/checkout.html", context)
    
    else: # Metoda GET
        initial_data = {}
        if request.user.is_authenticated:
            # Wypełnij danymi z User i Profile
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            try:
                initial_data['phone'] = request.user.profile.phone
            except Profile.DoesNotExist:
                pass
            
            # Spróbuj wypełnić danymi z domyślnego adresu wysyłki
            default_address = ShippingAddress.objects.filter(user=request.user, default_shipping=True).first()
            if default_address:
                # Nadpisz imię i nazwisko, jeśli są w adresie
                if default_address.shipping_full_name:
                    parts = default_address.shipping_full_name.split(' ', 1)
                    initial_data['first_name'] = parts[0]
                    if len(parts) > 1:
                        initial_data['last_name'] = parts[1]
                
                initial_data['address1'] = default_address.shipping_address1
                initial_data['address2'] = default_address.shipping_address2
                initial_data['city'] = default_address.shipping_city
                initial_data['zipcode'] = default_address.shipping_zipcode
                initial_data['country'] = default_address.shipping_country
        
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

def payment_success_stripe(request):
    # Ta strona jest tylko potwierdzeniem dla klienta.
    # Rzeczywiste utworzenie zamówienia odbywa się w webhooku.
    # Możemy wyczyścić koszyk tutaj, jeśli webhook jest niezawodny.
    cart = Cart(request)
    cart.clear()
    
    # Wyczyść dane z sesji
    if 'checkout_data' in request.session:
        del request.session['checkout_data']
    if 'shipping_data' in request.session:
        del request.session['shipping_data']
    if 'stripe_session_id' in request.session:
        del request.session['stripe_session_id']

    messages.success(request, "Płatność zakończona sukcesem! Twoje zamówienie jest przetwarzane.")
    return render(request, "payment/payment_success.html", {})

def payment_cancelled(request):
    messages.error(request, "Płatność została anulowana. Możesz spróbować ponownie.")
    return redirect('checkout')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header,os.environ['STRIPE_WEBHOOK_SECRET'] 
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Obsłuż zdarzenie checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        
        # Sprawdź, czy zamówienie już nie zostało przetworzone
        if Order.objects.filter(payment_intent_id=session.payment_intent).exists():
            return HttpResponse("Zamówienie już istnieje.", status=200)

        try:
            # Odczytaj dane z metadanych
            checkout_data = json.loads(metadata.get('checkout_data'))
            shipping_data = json.loads(metadata.get('shipping_data')) if 'shipping_data' in metadata else None
            cart_data = json.loads(metadata.get('cart_data'))
            user_id = metadata.get('user_id')
            user = User.objects.get(id=user_id) if user_id else None
        except (json.JSONDecodeError, User.DoesNotExist, KeyError) as e:
            print(f"Błąd w metadanych webhooka: {e}")
            return HttpResponse("Błąd w metadanych.", status=400)

        # === POCZĄTEK LOGIKI TWORZENIA ZAMÓWIENIA ===
        try:
            with transaction.atomic():
                # 1. Zbierz dane adresowe
                if shipping_data:
                    full_name = shipping_data['shipping_full_name']
                    shipping_address_str = (f"{full_name}\n{shipping_data['shipping_address1']}\n{shipping_data.get('shipping_address2', '')}\n{shipping_data['shipping_zipcode']} {shipping_data['shipping_city']}\n{shipping_data['shipping_country']}").strip()
                else:
                    full_name = f"{checkout_data['first_name']} {checkout_data['last_name']}"
                    shipping_address_str = (f"{full_name}\n{checkout_data['address1']}\n{checkout_data.get('address2', '')}\n{checkout_data['zipcode']} {checkout_data['city']}\n{checkout_data['country']}").strip()
                
                paczkomat_id = metadata.get('paczkomat_id')
                if paczkomat_id:
                    shipping_address_str += f"\n\nWybrany Paczkomat: {paczkomat_id}"
                # 2. Stwórz obiekt Order
                order = Order.objects.create(
                    user=user,
                    full_name=full_name,
                    email=checkout_data['email'],
                    shipping_address=shipping_address_str,
                    amount_paid=Decimal(session.amount_total / 100), # Pobierz kwotę ze Stripe
                    payment_intent_id=session.payment_intent # Zapisz ID płatności
                )

                # 3. Stwórz OrderItem i zaktualizuj stan magazynowy
                for item_key, quantity in cart_data.items():
                    if item_key.startswith('v_'):
                        variation_id = int(item_key.split('_')[1])
                        variation = get_object_or_404(ProductVariation, id=variation_id)
                        
                        OrderItem.objects.create(
                            order=order,
                            variation=variation,
                            product=variation.product,
                            user=user,
                            quantity=quantity,
                            price=variation.get_effective_price(),
                        )
                        # Zmniejsz stan magazynowy
                        variation.stock = F('stock') - quantity
                        variation.save()
                        
                    elif item_key.startswith('p_'):
                        product_id = int(item_key.split('_')[1])
                        product = get_object_or_404(Product, id=product_id)
                        
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            user=user,
                            quantity=quantity,
                            price=product.get_effective_price(),
                        )
                        # Zmniejsz stan magazynowy
                        product.stock = F('stock') - quantity
                        product.save()

                # mail do klienta
                try:
                    subject = f"Potwierdzenie zamówienia nr {order.order_number}"
                    from_email = settings.DEFAULT_FROM_EMAIL
                    to_email = order.email
                    logo_url = settings.SITE_URL + static('images/logo.png')
                    context = {'order': order, 'logo_url': logo_url}
                    html_template = get_template('emails/order_confirmation.html')
                    html_content = html_template.render(context)

                    msg = EmailMultiAlternatives(subject, "Dziękujemy za zamówienie!", from_email, [to_email])
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                except Exception as e:
                    print(f"Błąd podczas wysyłania e-maila z potwierdzeniem dla zamówienia {order.order_number}: {e}")
                

        except Exception as e:
            print(f"Błąd krytyczny podczas tworzenia zamówienia z webhooka: {e}")
            return HttpResponse(status=500)
        # === KONIEC LOGIKI TWORZENIA ZAMÓWIENIA ===

    return HttpResponse(status=200)