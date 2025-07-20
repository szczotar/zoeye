from django.shortcuts import render, redirect, get_object_or_404 # Import get_object_or_404
from cart.cart import Cart
# Import forms and models from your payment app
from payment.forms import ShippingForm, PaymentForm, CheckoutForm
from payment.models import ShippingAddress, Order, OrderItem # Assuming Order and OrderItem are here
# Import models from your store app
from store.models import Product, Profile, ProductVariation # Import ProductVariation
from django.contrib.auth.models import User
from django.contrib import messages
import datetime
from decimal import Decimal # Import Decimal for price calculations
from django.db import transaction # Import transaction for atomic operations
from django.http import JsonResponse # Import JsonResponse if needed for AJAX (though these are full page views)


# --- Admin Dashboard Views (No major changes needed here for variations,
#     but templates will need to access variation details) ---

def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        # Get the order
        order = get_object_or_404(Order, id=pk) # Use get_object_or_404
        # Get the order items
        # These items are now linked to ProductVariation
        items = OrderItem.objects.filter(order=order) # Filter by the order object

        if request.method == 'POST': # Check for POST request
            status = request.POST.get('shipping_status') # Use .get() for safety
            # Check if true or false
            if status == "true":
                # Get the order again (or just use the 'order' object fetched earlier)
                # order = Order.objects.filter(id=pk) # No need to filter again
                now = datetime.datetime.now()
                order.shipped = True # Update fields directly on the object
                order.date_shipped = now
                order.save() # Save the object
            else:
                # order = Order.objects.filter(id=pk) # No need to filter again
                order.shipped = False
                order.date_shipped = None # Clear date_shipped if not shipped
                order.save() # Save the object

            messages.success(request, "Shipping Status Updated")
            # Redirect back to the same order detail page, or a list
            return redirect('orders', pk=pk) # Redirect to itself or another relevant page

        # For GET request, render the template
        # Template needs to access item.variation.product.name, item.variation.size etc.
        return render(request, 'payment/orders.html', {"order":order, "items":items})

    else:
        messages.success(request, "Access Denied")
        return redirect('home')


def not_shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        # Filter Orders where shipped is False
        orders = Order.objects.filter(shipped=False).order_by('-date_ordered') # Order by date

        if request.method == 'POST': # Check for POST request
            num = request.POST.get('num') # Get order ID
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

            return redirect('not_shipped_dash') # Redirect back to the not shipped list

        # Template needs to access order.user, order.amount_paid, order.date_ordered etc.
        return render(request, "payment/not_shipped_dash.html", {"orders":orders})
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        # Filter Orders where shipped is True
        orders = Order.objects.filter(shipped=True).order_by('-date_shipped') # Order by shipping date

        if request.method == 'POST': # Check for POST request
            num = request.POST.get('num') # Get order ID
            if num:
                try:
                    order_to_unship = get_object_or_404(Order, id=num)
                    order_to_unship.shipped = False
                    order_to_unship.date_shipped = None # Clear shipping date
                    order_to_unship.save()
                    messages.success(request, f"Order {num} Shipping Status Updated to Not Shipped")
                except Exception as e:
                    messages.error(request, f"Error updating order {num}: {e}")
            else:
                 messages.error(request, "No order ID provided.")

            return redirect('shipped_dash') # Redirect back to the shipped list

        # Template needs to access order.user, order.amount_paid, order.date_shipped etc.
        return render(request, "payment/shipped_dash.html", {"orders":orders})
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

# --- End Admin Dashboard Views ---


def checkout(request):
    cart = Cart(request)
    cart_items = list(cart.__iter__())
    totals = cart.cart_total()

    if not cart_items:
        messages.warning(request, "Twój koszyk jest pusty.")
        return redirect('cart_summary')

    if request.method == 'POST':
        # Przetwarzanie danych z całego formularza
        checkout_form = CheckoutForm(request.POST)
        shipping_form = ShippingForm(request.POST, prefix='shipping') # Używamy prefiksu

        # Sprawdzamy, czy checkbox "inny adres" był zaznaczony
        is_different_shipping = 'shipping-address-checkbox' in request.POST

        if checkout_form.is_valid() and (not is_different_shipping or shipping_form.is_valid()):
            # Logika tworzenia zamówienia (przeniesiona z process_order)
            try:
                with transaction.atomic():
                    # Tworzenie adresu do zapisu w modelu Order
                    if is_different_shipping:
                        # Użyj danych z formularza wysyłki
                        data = shipping_form.cleaned_data
                        full_name = f"{data['shipping_first_name']} {data['shipping_last_name']}"
                        shipping_address_str = (
                            f"{full_name}\n"
                            f"{data['shipping_address1']}\n"
                            f"{data.get('shipping_address2', '')}\n"
                            f"{data['shipping_zipcode']} {data['shipping_city']}\n"
                            f"{data['shipping_country']}"
                        )
                    else:
                        # Użyj danych z głównego formularza
                        data = checkout_form.cleaned_data
                        full_name = f"{data['first_name']} {data['last_name']}"
                        shipping_address_str = (
                            f"{full_name}\n"
                            f"{data['address1']}\n"
                            f"{data.get('address2', '')}\n"
                            f"{data['zipcode']} {data['city']}\n"
                            f"{data['country']}"
                        )

                    # Pobranie kosztu dostawy z formularza
                    delivery_cost = 0
                    if request.POST.get('delivery_method') == 'courier':
                        delivery_cost = 15.00
                    elif request.POST.get('delivery_method') == 'locker':
                        delivery_cost = 12.00
                    
                    amount_paid = totals + decimal.Decimal(delivery_cost)

                    # Tworzenie obiektu Order
                    order = Order.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        full_name=full_name,
                        email=checkout_form.cleaned_data['email'],
                        shipping_address=shipping_address_str.strip(),
                        amount_paid=amount_paid,
                    )

                    # Tworzenie OrderItem dla każdego produktu w koszyku
                    for item in cart_items:
                        variation = item['variation']
                        OrderItem.objects.create(
                            order=order,
                            variation=variation,
                            user=request.user if request.user.is_authenticated else None,
                            quantity=item['quantity'],
                            price=item['variation'].get_effective_price(),
                        )
                        # Opcjonalnie: zmniejszanie stanu magazynowego
                        variation.stock -= item['quantity']
                        variation.save()

                # Czyszczenie koszyka i przekierowanie
                cart.clear()
                messages.success(request, "Zamówienie zostało złożone pomyślnie!")
                return redirect('payment_success')

            except Exception as e:
                messages.error(request, f"Wystąpił błąd podczas składania zamówienia: {e}")
                return redirect('checkout')
        else:
            # Jeśli formularze są nieprawidłowe, renderuj stronę ponownie z błędami
            messages.error(request, "Proszę poprawić błędy w formularzu.")
            # Przekaż formularze z błędami do szablonu
            context = {
                "cart_items": cart_items,
                "totals": totals,
                "checkout_form": checkout_form,
                "shipping_form": shipping_form,
            }
            return render(request, "payment/checkout.html", context)

    else: # Metoda GET
        # Przygotowanie pustych formularzy
        # Można wstępnie wypełnić danymi zalogowanego użytkownika
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {'email': request.user.email, 'first_name': request.user.first_name, 'last_name': request.user.last_name}
        
        checkout_form = CheckoutForm(initial=initial_data)
        shipping_form = ShippingForm(prefix='shipping')

        context = {
            "cart_items": cart_items,
            "totals": totals,
            "checkout_form": checkout_form,
            "shipping_form": shipping_form,
        }
        return render(request, "payment/checkout.html", context)

def billing_info(request):
    """
    Handles submission of the shipping form and displays billing information.
    Saves shipping info to session.
    """
    # Get the cart
    cart = Cart(request)

    # Get cart items using the __iter__() method
    cart_items = list(cart.__iter__())

    # Check if the cart is empty (should have been checked in checkout, but good safety)
    if not cart_items:
        messages.warning(request, "Twój koszyk jest pusty.")
        return redirect('cart_summary')

    # Get the total price
    totals = cart.cart_total()

    # Process the shipping form submission
    if request.method == 'POST':
        # Initialize form with POST data
        shipping_form = ShippingForm(request.POST)

        if shipping_form.is_valid():
            # Save shipping info to session
            # Use shipping_form.cleaned_data to get validated data
            request.session['my_shipping'] = shipping_form.cleaned_data

            # Check if user is logged in to pre-fill billing form if needed
            billing_form = PaymentForm() # Initialize billing form (no instance needed typically)

            context = {
                "cart_items": cart_items, # Pass cart items
                "totals": totals,         # Pass total
                "shipping_info": request.session.get('my_shipping'), # Pass shipping info from session
                "billing_form": billing_form, # Pass the billing form
            }

            return render(request, "payment/billing_info.html", context)
        else:
            # If shipping form is NOT valid, re-render the checkout page with errors
            messages.error(request, "Please correct the shipping information errors.")
            # Re-initialize the form with POST data to show errors
            shipping_form = ShippingForm(request.POST)
            context = {
                "cart_items": cart_items,
                "totals": totals,
                "shipping_form": shipping_form, # Pass form with errors
            }
            return render(request, "payment/checkout.html", context)

    else:
        # If not a POST request, redirect back to checkout
        messages.warning(request, "Proszę wypełnić formularz wysyłki.")
        return redirect('checkout')


def process_order(request):
    """
    Handles the final order processing, including creating Order and OrderItem objects,
    deducting stock, and clearing the cart.
    This view should be the target of the billing form submission.
    """
    if request.method == 'POST':
        # Get the cart
        cart = Cart(request)

        # Get cart items using the __iter__() method
        cart_items = list(cart.__iter__())

        # Check if the cart is empty (safety check)
        if not cart_items:
            messages.warning(request, "Twój koszyk jest pusty.")
            return redirect('cart_summary')

        # Get the total price
        totals = cart.cart_total() # This is the total amount to be paid

        # Get Billing Info from the last page (PaymentForm submission)
        payment_form = PaymentForm(request.POST) # Initialize with POST data

        # Get Shipping Session Data
        my_shipping = request.session.get('my_shipping')

        # Validate both forms (shipping info should be in session, but payment form is submitted now)
        # You might want to re-validate shipping form data from session if necessary
        # Here we primarily validate the payment form
        if payment_form.is_valid() and my_shipping: # Check if payment form is valid and shipping info exists in session

            # --- Final Stock Check before creating order (Optional but Recommended) ---
            # This is crucial in multi-user environments
            stock_errors = []
            variations_to_update = {} # Store variations and quantities for deduction

            for item in cart_items:
                 variation = item['variation']
                 quantity = item['quantity']
                 # Re-fetch variation to get the latest stock info
                 try:
                     current_variation = ProductVariation.objects.get(id=variation.id)
                     if current_variation.stock < quantity:
                         stock_errors.append(f"Brak wystarczającej ilości dla: {current_variation.product.name} ({current_variation.size}). Dostępnych: {current_variation.stock}.")
                     else:
                         # Store for deduction later
                         variations_to_update[current_variation.id] = quantity
                 except ProductVariation.DoesNotExist:
                      stock_errors.append(f"Produkt ({variation.product.name} - {variation.size}) nie jest już dostępny.")
                      # You might want to remove this item from the cart here

            if stock_errors:
                 # If there are stock errors, display them and redirect back to cart or checkout
                 for error in stock_errors:
                     messages.error(request, error)
                 # You might want to clear the cart items that caused errors
                 # and redirect back to cart summary.
                 return redirect('cart_summary') # Or 'checkout'


            # --- Create Order and Order Items (within a transaction) ---
            # Using a transaction ensures that if any step fails (e.g., saving OrderItem, deducting stock),
            # all changes made within the block are rolled back.
            try:
                with transaction.atomic():
                    # Gather Order Info from shipping session data
                    full_name = my_shipping.get('shipping_full_name', '')
                    email = my_shipping.get('shipping_email', '')
                    # Format shipping address
                    shipping_address_str = f"{my_shipping.get('shipping_address1', '')}\n{my_shipping.get('shipping_address2', '')}\n{my_shipping.get('shipping_city', '')}\n{my_shipping.get('shipping_state', '')}\n{my_shipping.get('shipping_zipcode', '')}\n{my_shipping.get('shipping_country', '')}"
                    amount_paid = totals # Use the calculated total from the cart

                    # Create the main Order object
                    create_order = Order(
                        user=request.user if request.user.is_authenticated else None, # Link to user if logged in
                        full_name=full_name,
                        email=email,
                        shipping_address=shipping_address_str,
                        amount_paid=amount_paid,
                        # Add other Order fields like date_ordered (should default in model)
                    )
                    create_order.save() # Save the Order object first to get its ID (pk)

                    # Add order items by iterating through the cart items
                    for item in cart_items:
                        variation = item['variation'] # This is the ProductVariation object
                        quantity = item['quantity']   # This is the quantity for this variation
                        price_at_order = item['variation'].get_effective_price() # Price at the time of order

                        # Create OrderItem object
                        # Link OrderItem to the created Order and the ProductVariation
                        create_order_item = OrderItem(
                            order=create_order, # Link to the main Order
                            variation=variation, # Link to the ProductVariation
                            user=request.user if request.user.is_authenticated else None, # Link item to user if logged in
                            quantity=quantity,
                            price=price_at_order, # Store the price at the time of order
                            # Add other OrderItem fields if needed
                        )
                        create_order_item.save()

                        # Deduct stock for the variation
                        # We already checked if stock is sufficient above
                        variation.stock -= quantity
                        variation.save() # Save the updated stock

                    # --- Order and Order Items created successfully ---

                    # Clear the session cart
                    cart.clear() # Assuming cart.clear() method exists and works

                    # Clear the old_cart field in the user's profile if logged in
                    if request.user.is_authenticated:
                        try:
                            profile = Profile.objects.get(user=request.user)
                            profile.old_cart = "" # Clear the database cart
                            profile.save()
                        except Profile.DoesNotExist:
                            # Should not happen if user is authenticated, but handle gracefully
                            print(f"Warning: Profile not found for user {request.user.username} during cart clear.")
                        except Exception as e:
                             print(f"Error clearing old_cart for user {request.user.username}: {e}")


                    # Clear shipping info from session after successful order
                    if 'my_shipping' in request.session:
                        del request.session['my_shipping']
                        request.session.modified = True


                    messages.success(request, "Order Placed Successfully!")
                    # Redirect to a success page or order detail page
                    return redirect('payment_success') # Assuming you have a payment_success URL name

            except Exception as e:
                # If any error occurred within the atomic block, the transaction is rolled back.
                messages.error(request, f"Wystąpił błąd podczas przetwarzania zamówienia: {e}")
                # Log the error for debugging
                print(f"Error processing order: {e}")
                # Redirect back to checkout or cart summary
                return redirect('checkout')


        else:
            # If payment form is NOT valid or shipping info is missing from session
            messages.error(request, "Proszę poprawić błędy w informacjach płatności lub wysyłki.")
            # Re-render the billing_info page with payment form errors
            context = {
                "cart_items": cart_items,
                "totals": totals,
                "shipping_info": my_shipping, # Pass shipping info back
                "billing_form": payment_form, # Pass form with errors
            }
            return render(request, "payment/billing_info.html", context)

    else:
        # If not a POST request, redirect to home or checkout
        messages.success(request, "Access Denied")
        return redirect('home')


def payment_success(request):
    """
    Renders the payment success page.
    """
    # You might want to pass order details to this page
    # For example, retrieve the last order for the current user or from session
    # last_order = Order.objects.filter(user=request.user).order_by('-date_ordered').first()
    # context = {'last_order': last_order}
    return render(request, "payment/payment_success.html", {})

def terms_page(request):
    """
    Renders the terms and conditions page.
    """
    return render(request, "payment/terms_page.html", {})