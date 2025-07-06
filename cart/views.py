# --- START OF FILE views.py ---

from django.shortcuts import render, get_object_or_404, redirect
# Importuj Product i ProductVariation z Twojej aplikacji store
from store.models import Product, ProductVariation
from .cart import Cart
from django.http import JsonResponse
from django.contrib import messages
import json # Nadal potrzebne, np. do logowania
from decimal import Decimal # Import Decimal for price calculations
from django.db.models import Q # Może być potrzebne do bardziej złożonych zapytań, ale w tych widokach raczej nie

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 
# Views for Cart

def cart_summary(request):
    """
    Renders the cart summary page.
    Retrieves cart items (Product/ProductVariation with quantity and subtotal)
    and the total price from the Cart object.
    """
    cart = Cart(request)

    # The Cart.__iter__() method is designed to yield items in the format
    # {'item_key': ..., 'item_object': ..., 'item_type': ..., 'quantity': ..., 'subtotal': ...}
    # We convert this iterator to a list for easy use in the template.
    cart_items = list(cart.__iter__())

    # Get the total price from the Cart object
    totals = cart.cart_total()

    context = {
        "cart_items": cart_items, # Pass the list of cart items
        "totals": totals,         # Pass the total cart price
        # "quantities" and "cart_products" are no longer needed separately
        # as the necessary data is available within each item in cart_items
    }

    return render(request, "cart_summary.html", context)


def cart_add(request):
    """
    Handles adding a Product or ProductVariation to the cart via AJAX POST.
    Expects 'variation_id' (for variations) OR 'product_id' (for products without variations)
    and 'quantity' in POST data.
    Includes basic validation and stock check.
    """
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        # Get the item ID and quantity from the POST data
        # Expecting either 'variation_id' or 'product_id'
        variation_id_str = request.POST.get('variation_id')
        product_id_str = request.POST.get('product_id') # Now expecting product_id too
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
            # Must have exactly one ID type
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
                item_object = ProductVariation.objects.get(id=item_id)
                # Ensure the variation belongs to a product that exists
                if not item_object.product:
                     raise Product.DoesNotExist # Treat as product not found
            elif item_type == 'product':
                item_object = Product.objects.get(id=item_id)
            # item_object is now either a Product or ProductVariation instance
        except (Product.DoesNotExist, ProductVariation.DoesNotExist):
             return JsonResponse({'error': f'Przedmiot ({item_type} ID: {item_id}) nie znaleziony.'}, status=404)
        except Exception as e:
             print(f"Error getting item object (type: {item_type}, id: {item_id}): {e}")
             return JsonResponse({'error': 'Wystąpił błąd podczas pobierania danych przedmiotu.'}, status=500)


        # --- Stock Check ---
        # Determine available stock based on item type
        available_stock = item_object.stock if isinstance(item_object, Product) else item_object.stock # Both models now have .stock

        # Construct the item_key for the cart dictionary
        item_key = f"{'p' if item_type == 'product' else 'v'}_{item_id}"

        # Calculate current quantity of this item already in the cart
        current_cart_quantity = cart.cart.get(item_key, 0)
        requested_total_quantity = current_cart_quantity + quantity # Total quantity after adding

        if available_stock < requested_total_quantity:
            # Return an error response indicating insufficient stock
            return JsonResponse({'error': f'Brak wystarczającej ilości w magazynie. Dostępnych: {available_stock}. Masz już {current_cart_quantity} w koszyku.'}, status=400)
        # --- End Stock Check ---

        # Add the item to the cart using the updated cart.add method
        # The add method now accepts the item object (Product or ProductVariation)
        cart.add(item=item_object, quantity=quantity)

        # Get the new total quantity of items in the cart (sum of all quantities)
        cart_quantity = cart.get_total_quantity() # Użyj helpera

        # Return a JSON response with the updated total cart quantity
        response_data = {'qty': cart_quantity}

        # Optional: Add a success message (frontend JS needs to handle displaying it)
        messages.success(request, f"Dodano {item_object.product.name if item_type == 'variation' else item_object.name} do koszyka.")


        return JsonResponse(response_data)

    # Handle non-POST requests or invalid actions
    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)


def cart_delete(request):
    """
    Handles deleting an item (Product or ProductVariation) from the cart via AJAX POST.
    Expects 'item_key' in POST data.
    """
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        # Get the item key from the POST data
        item_key = request.POST.get('item_key') # Expecting 'p_123' or 'v_456'

        # --- Validation ---
        if not item_key:
             return JsonResponse({'error': 'Brak klucza przedmiotu w żądaniu.'}, status=400)

        # Optional: Validate item_key format (starts with p_ or v_ followed by digits)
        if not (item_key.startswith('p_') or item_key.startswith('v_')) or '_' not in item_key:
             return JsonResponse({'error': 'Nieprawidłowy format klucza przedmiotu.'}, status=400)
        try:
             item_id = int(item_key.split('_')[1]) # Just check if ID part is integer
        except (IndexError, ValueError):
             return JsonResponse({'error': 'Nieprawidłowe ID w kluczu przedmiotu.'}, status=400)
        # --- End Validation ---


        # Call the delete method in the Cart class
        # The delete method now expects the item_key (string)
        cart.delete(item_key=item_key)

        # Get updated data for the response
        cart_quantity = cart.get_total_quantity()
        cart_total = cart.cart_total()

        # Return a JSON response
        response_data = {
            'qty': cart_quantity,
            'cart_total': cart_total,
            'item_key': item_key # Return the key so JS knows which row was deleted
        }

        # Optional: Message for full page reload scenario
        messages.success(request, "Przedmiot usunięty z koszyka.")

        return JsonResponse(response_data)

    # Handle non-POST requests or invalid actions
    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)


def cart_update(request):
    """
    Handles updating the quantity of an item (Product or ProductVariation) in the cart via AJAX POST.
    Expects 'item_key' and 'quantity' in POST data.
    Includes validation and stock check.
    """
    cart = Cart(request)

    if request.method == 'POST' and request.POST.get('action') == 'post':
         # Get the item key and new quantity from the POST data
         item_key = request.POST.get('item_key') # Expecting 'p_123' or 'v_456'
         quantity_str = request.POST.get('quantity')

         # --- Validation ---
         if not item_key:
              return JsonResponse({'error': 'Brak klucza przedmiotu w żądaniu.'}, status=400)

         # Optional: Validate item_key format
         if not (item_key.startswith('p_') or item_key.startswith('v_')) or '_' not in item_key:
              return JsonResponse({'error': 'Nieprawidłowy format klucza przedmiotu.'}, status=400)

         if not quantity_str:
              return JsonResponse({'error': 'Brak ilości w żądaniu.'}, status=400)

         try:
             quantity = int(quantity_str)
             if quantity < 0: # Allow quantity 0 to trigger deletion
                  return JsonResponse({'error': 'Ilość nie może być ujemna.'}, status=400)
         except ValueError:
              return JsonResponse({'error': 'Nieprawidłowa ilość.'}, status=400)
         # --- End Validation ---

         # If the requested quantity is 0, delegate to the delete view logic directly
         if quantity == 0:
             # Call the delete method in the Cart class
             cart.delete(item_key=item_key)
             cart_quantity = cart.get_total_quantity()
             cart_total = cart.cart_total()
             # Optional: messages.success(request, "Przedmiot usunięty z koszyka.")
             # Return success response indicating deletion
             return JsonResponse({
                 'qty': cart_quantity,
                 'item_key': item_key,
                 'cart_total': cart_total,
                 'deleted': True # Indicate that the item was deleted
                 })


         # Get the item object (Product or ProductVariation) for stock check and subtotal calculation
         item_object = None
         try:
             if item_key.startswith('p_'):
                 product_id = int(item_key.split('_')[1])
                 item_object = Product.objects.get(id=product_id)
             elif item_key.startswith('v_'):
                  variation_id = int(item_key.split('_')[1])
                  item_object = ProductVariation.objects.get(id=variation_id)
             # item_object is now the instance
         except (IndexError, ValueError, Product.DoesNotExist, ProductVariation.DoesNotExist):
              return JsonResponse({'error': f'Przedmiot o kluczu {item_key} nie znaleziony.'}, status=404)
         except Exception as e:
              print(f"Error getting item object (key: {item_key}): {e}")
              return JsonResponse({'error': 'Wystąpił błąd podczas pobierania danych przedmiotu.'}, status=500)


         # --- Stock Check ---
         # Determine available stock based on item type
         available_stock = item_object.stock if isinstance(item_object, Product) else item_object.stock

         # For update, check if the new requested quantity exceeds available stock
         if quantity > available_stock:
             # Return an error response indicating insufficient stock
             return JsonResponse({'error': f'Brak wystarczającej ilości w magazynie. Dostępnych: {available_stock}.'}, status=400)
         # --- End Stock Check ---


         # Update the item quantity in the cart using the updated cart.update method
         # The update method now expects item_key and the new quantity
         cart.update(item_key=item_key, quantity=quantity)

         # Get updated data for the response
         cart_quantity = cart.get_total_quantity() # Total quantity of items
         cart_total = cart.cart_total()   # Total price of the cart
         item_subtotal = item_object.get_effective_price() * Decimal(quantity) # Subtotal for this specific item

         # Prepare data for JSON response
         response_data = {
             'item_key': item_key, # Key of the updated item
             'quantity': quantity, # New quantity for this item
             'cart_quantity': cart_quantity, # New global total quantity
             'cart_total': cart_total, # New total cart price
             'item_subtotal': item_subtotal, # New subtotal for this item
             'deleted': False # Indicate that the item was not deleted
         }

         # Optional: Message for full page reload scenario
         # messages.success(request, f"Ilość dla {item_object.product.name if isinstance(item_object, ProductVariation) else item_object.name} zaktualizowana.")


         return JsonResponse(response_data)

    # Handle non-POST requests or invalid actions
    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)