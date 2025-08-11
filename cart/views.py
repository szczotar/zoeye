from django.shortcuts import render, get_object_or_404, redirect
# Importuj Product i ProductVariation z Twojej aplikacji store
from store.models import Product, ProductVariation
from .cart import Cart
from django.http import JsonResponse
from django.contrib import messages # Zachowujemy import dla komunikatów przy pełnych przeładowaniach
import json
from decimal import Decimal
from django.urls import reverse
from django.db.models import Q

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Views for Cart

def cart_summary(request):
    """
    Renders the cart summary page.
    Retrieves cart items (Product/ProductVariation with quantity and subtotal)
    and the total price from the Cart object.
    """
    cart = Cart(request)
    cart_items = list(cart.__iter__())
    totals = cart.cart_total()

    context = {
        "cart_items": cart_items,
        "totals": totals,
    }

    return render(request, "cart_summary.html", context)


def cart_add(request):
    """
    Handles adding a Product or ProductVariation to the cart via AJAX POST.
    Expects 'variation_id' (for variations) OR 'product_id' (for products without variations)
    and 'quantity' in POST data.
    Includes basic validation and stock check.
    Returns JSON with data for simple popup and cart update.
    """
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        variation_id_str = request.POST.get('variation_id')
        product_id_str = request.POST.get('product_id')
        quantity_str = request.POST.get('quantity')

        # --- Validation ---
        item_id_str = None
        item_type = None
        item_object = None

        if variation_id_str and not product_id_str:
            item_id_str = variation_id_str
            item_type = 'variation'
        elif product_id_str and not variation_id_str:
             item_id_str = product_id_str
             item_type = 'product'
        else:
            return JsonResponse({'error': 'Brak ID produktu lub wariacji w żądaniu.'}, status=400)

        try:
            item_id = int(item_id_str)
        except ValueError:
             return JsonResponse({'error': f'Nieprawidłowe ID ({item_type}).'}, status=400)

        if not quantity_str:
            return JsonResponse({'error': 'Brak ilości w żądaniu.'}, status=400)

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                 return JsonResponse({'error': 'Ilość musi być większa od zera.'}, status=400)
        except ValueError:
             return JsonResponse({'error': 'Nieprawidłowa ilość.'}, status=400)
        # --- End Validation ---


        # Get the item object (Product or ProductVariation)
        try:
            if item_type == 'variation':
                item_object = get_object_or_404(ProductVariation, id=item_id)
                if not item_object.product:
                     return JsonResponse({'error': f'Wariacja (ID: {item_id}) nie jest przypisana do produktu.'}, status=404)
            elif item_type == 'product':
                item_object = get_object_or_404(Product, id=item_id)
        except Exception as e:
             print(f"Error getting item object (type: {item_type}, id: {item_id}): {e}")
             return JsonResponse({'error': 'Wystąpił błąd podczas pobierania danych przedmiotu.'}, status=404)


        # --- Stock Check ---
        available_stock = item_object.stock

        item_key = f"{'p' if item_type == 'product' else 'v'}_{item_id}"

        current_cart_quantity = cart.cart.get(item_key, {}).get('quantity', 0)
        requested_total_quantity = current_cart_quantity + quantity

        if available_stock < requested_total_quantity:
            return JsonResponse({'error': f'Brak wystarczającej ilości w magazynie. Dostępnych: {available_stock}. Masz już {current_cart_quantity} w koszyku.'}, status=400)
        # --- End Stock Check ---

        cart.add(item=item_object, quantity=quantity)

        cart_quantity = cart.get_total_quantity()
        cart_total = cart.cart_total()

        # Prepare data for simple popup
        item_name = item_object.product.name if isinstance(item_object, ProductVariation) else item_object.name

        response_data = {
            'qty': cart_quantity,
            'cart_total': str(cart_total), # Convert Decimal to string
            'item_key': item_key, # Key of the item added
            'item_name': item_name, # Name for the message
            'quantity_added': quantity, # Quantity added in THIS operation
            'message': f"Dodano {item_name} do koszyka.", # Message for simple popup
            'type': 'add', # <-- DODANO TĘ LINIĘ
        }

        # messages.success(request, f"Dodano {item_name} do koszyka.") # REMOVED messages for AJAX

        return JsonResponse(response_data)

    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)


def cart_delete(request):
    """
    Handles deleting an item (Product or ProductVariation) from the cart via AJAX POST.
    Expects 'item_key' in POST data.
    Returns JSON with data for simple popup and cart update.
    """
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        item_key = request.POST.get('item_key')

        # --- Validation ---
        if not item_key:
             return JsonResponse({'error': 'Brak klucza przedmiotu w żądaniu.'}, status=400)

        if not (item_key.startswith('p_') or item_key.startswith('v_')) or '_' not in item_key:
             return JsonResponse({'error': 'Nieprawidłowy format klucza przedmiotu.'}, status=400)
        try:
             item_id = int(item_key.split('_')[1])
        except (IndexError, ValueError):
             return JsonResponse({'error': 'Nieprawidłowe ID w kluczu przedmiotu.'}, status=400)
        # --- End Validation ---

        # Try to get item name BEFORE deleting
        deleted_item_name = "przedmiot" # Default name
        try:
            item_type_prefix, item_id_str = item_key.split('_')
            item_id_int = int(item_id_str)
            if item_type_prefix == 'p':
                 deleted_item_object = Product.objects.get(id=item_id_int)
                 deleted_item_name = deleted_item_object.name
            elif item_type_prefix == 'v':
                 deleted_item_object = ProductVariation.objects.get(id=item_id_int)
                 # Use product name for variations in message
                 deleted_item_name = deleted_item_object.product.name if deleted_item_object.product else "przedmiot"

        except (ValueError, IndexError, Product.DoesNotExist, ProductVariation.DoesNotExist):
            # Item not found in DB, but might still be in cart session
            pass # Keep default name "przedmiot"

        # Check if the item_key exists in the cart before attempting to delete
        if item_key not in cart.cart:
             # Item not found in cart, maybe it was already deleted?
             response_data = {
                 'qty': cart.get_total_quantity(),
                 'cart_total': str(cart.cart_total()),
                 'item_key': item_key,
                 'message': f"Przedmiot {deleted_item_name} nie znaleziono w koszyku (może już usunięty?).", # Message for simple popup
                 'type': 'delete', # <-- DODANO TĘ LINIĘ (również w przypadku braku itemu w koszyku)
             }
             return JsonResponse(response_data)


        # Call the delete method in the Cart class
        cart.delete(item_key=item_key)

        # Get updated data for the response
        cart_quantity = cart.get_total_quantity()
        cart_total = cart.cart_total()

        # Prepare data for simple popup
        response_data = {
            'qty': cart_quantity,
            'cart_total': str(cart_total), # Convert Decimal to string
            'item_key': item_key,
            'item_name': deleted_item_name, # Pass the name for the message
            'message': f"Przedmiot {deleted_item_name} usunięty z koszyka.", # Message for simple popup
            'type': 'delete', # <-- DODANO TĘ LINIĘ
        }

        # messages.success(request, f"Przedmiot '{deleted_item_name}' usunięty z koszyka.") # REMOVED messages for AJAX

        return JsonResponse(response_data)

    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)


def cart_update(request):
    """
    Handles updating the quantity of an item (Product or ProductVariation) in the cart via AJAX POST.
    Expects 'item_key' and 'quantity' in POST data.
    Includes validation and stock check.
    Returns JSON with data for simple popup and cart update.
    """
    cart = Cart(request)

    if request.method == 'POST' and request.POST.get('action') == 'post':
         item_key = request.POST.get('item_key')
         quantity_str = request.POST.get('quantity')

         # --- Validation ---
         if not item_key:
              return JsonResponse({'error': 'Brak klucza przedmiotu w żądaniu.'}, status=400)

         if not (item_key.startswith('p_') or item_key.startswith('v_')) or '_' not in item_key:
              return JsonResponse({'error': 'Nieprawidłowy format klucza przedmiotu.'}, status=400)

         if not quantity_str:
              return JsonResponse({'error': 'Brak ilości w żądaniu.'}, status=400)

         try:
             quantity = int(quantity_str)
             if quantity <= 0: # This case is handled by JS triggering delete, but good fallback
                  return JsonResponse({'error': 'Ilość musi być większa od zera dla aktualizacji.'}, status=400)
         except ValueError:
              return JsonResponse({'error': 'Nieprawidłowa ilość.'}, status=400)
         # --- End Validation ---

         # Check if the item_key exists in the cart
         if item_key not in cart.cart:
              return JsonResponse({'error': f'Przedmiot o kluczu {item_key} nie znaleziony w koszyku.'}, status=404)


         # Get the item object for stock check and subtotal calculation
         item_object = None
         item_id = int(item_key.split('_')[1])
         try:
             if item_key.startswith('p_'):
                 item_object = get_object_or_404(Product, id=item_id)
             elif item_key.startswith('v_'):
                  item_object = get_object_or_404(ProductVariation, id=item_id)
         except Exception as e:
              print(f"Error getting item object (key: {item_key}): {e}")
              return JsonResponse({'error': f'Przedmiot o kluczu {item_key} nie znaleziony w bazie danych.'}, status=404)


         # --- Stock Check ---
         available_stock = item_object.stock

         if quantity > available_stock:
             return JsonResponse({'error': f'Brak wystarczającej ilości w magazynie. Dostępnych: {available_stock}.'}, status=400)
         # --- End Stock Check ---


         cart.update(item_key=item_key, quantity=quantity)

         cart_quantity = cart.get_total_quantity()
         cart_total = cart.cart_total()
         item_subtotal = item_object.get_effective_price() * Decimal(quantity)

         # Prepare data for simple popup
         item_name = item_object.product.name if isinstance(item_object, ProductVariation) else item_object.name

         response_data = {
             'item_key': item_key,
             'quantity': quantity, # New quantity for this item
             'qty': cart_quantity, # New global total quantity
             'cart_total': str(cart_total), # Convert Decimal to string
             'item_subtotal': str(item_subtotal), # Convert Decimal to string
             'item_name': item_name, # Pass the name for the message
             'new_quantity': quantity, # Pass the new quantity for the message
             'message': f"Ilość dla produktu {item_name} zaktualizowana na {quantity}.", # Message for simple popup
             'type': 'update', # <-- DODANO TĘ LINIĘ
         }

         # messages.success(request, f"Ilość dla {item_name} zaktualizowana.") # REMOVED messages for AJAX


         return JsonResponse(response_data)

    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)