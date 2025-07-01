from django.shortcuts import render, get_object_or_404, redirect # Import redirect if needed for messages
from .cart import Cart
# Import Product and ProductVariation from your store app
from store.models import Product, ProductVariation
from django.http import JsonResponse
from django.contrib import messages
import json
from decimal import Decimal # Import Decimal for price calculations

# Views for Cart

def cart_summary(request):
    """
    Renders the cart summary page.
    Retrieves cart items (ProductVariations with quantity and subtotal)
    and the total price from the Cart object.
    """
    cart = Cart(request)

    # The Cart.__iter__() method is designed to yield items in the format
    # {'variation': variation_obj, 'quantity': quantity, 'subtotal': subtotal}
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
    Handles adding a ProductVariation to the cart via AJAX POST.
    Expects 'variation_id' and 'quantity' in POST data.
    Includes basic validation and stock check.
    """
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        # Get the variation ID and quantity from the POST data
        # Use .get() with None default for safety
        variation_id_str = request.POST.get('variation_id')
        quantity_str = request.POST.get('quantity') # Should be named 'quantity' from product.html

        # --- Validation ---
        if not variation_id_str:
            # Use JsonResponse for AJAX errors
            return JsonResponse({'error': 'Brak ID wariacji w żądaniu.'}, status=400) # Bad Request

        try:
            variation_id = int(variation_id_str)
        except ValueError:
             return JsonResponse({'error': 'Nieprawidłowe ID wariacji.'}, status=400)

        if not quantity_str:
            return JsonResponse({'error': 'Brak ilości w żądaniu.'}, status=400)

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                 return JsonResponse({'error': 'Ilość musi być większa od zera.'}, status=400)
        except ValueError:
             return JsonResponse({'error': 'Nieprawidłowa ilość.'}, status=400)
        # --- End Validation ---


        # Get the product variation object
        # Use get_object_or_404 to return 404 if variation doesn't exist
        variation = get_object_or_404(ProductVariation, id=variation_id)

        # --- Stock Check ---
        # Calculate current quantity of this variation already in the cart
        current_cart_quantity = cart.cart.get(str(variation_id), 0) # Get existing quantity, default to 0
        requested_total_quantity = current_cart_quantity + quantity # Total quantity after adding

        if variation.stock < requested_total_quantity:
            # Return an error response indicating insufficient stock
            return JsonResponse({'error': f'Brak wystarczającej ilości w magazynie. Dostępnych: {variation.stock}. Masz już {current_cart_quantity} w koszyku.'}, status=400)
        # --- End Stock Check ---

        # Add the variation to the cart using the updated cart.add method
        # The add method now accepts the variation object and quantity
        cart.add(variation=variation, quantity=quantity)

        # Get the new total quantity of items in the cart (sum of all quantities)
        cart_quantity = cart.__len__()

        # Return a JSON response with the updated total cart quantity
        response = JsonResponse({'qty': cart_quantity})

        # Django messages are typically for full page reloads,
        # but you can keep this if your frontend JS handles displaying them
        # after an AJAX call (which is not standard).
        # If you are reloading the page after success, this will work.
        messages.success(request, f"Dodano {variation.product.name} ({variation.size}) do koszyka.")

        return response

    # Handle non-POST requests or invalid actions
    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)


def cart_delete(request):
    """
    Handles deleting a ProductVariation from the cart via AJAX POST.
    Expects 'variation_id' in POST data.
    """
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        # Get the variation ID from the POST data
        variation_id_str = request.POST.get('variation_id')

        # --- Validation ---
        if not variation_id_str:
             return JsonResponse({'error': 'Brak ID wariacji w żądaniu.'}, status=400)

        try:
            variation_id = int(variation_id_str)
        except ValueError:
             return JsonResponse({'error': 'Nieprawidłowe ID wariacji.'}, status=400)
        # --- End Validation ---

        # Call the delete method in the Cart class
        # The delete method now expects the variation_id (int or str)
        cart.delete(variation=variation_id)

        # Get the new total quantity of items in the cart
        cart_quantity = cart.__len__()

        # Return a JSON response
        response = JsonResponse({'qty': cart_quantity, 'variation_id': variation_id})

        # Message for full page reload scenario
        messages.success(request, "Produkt usunięty z koszyka.")

        return response

    # Handle non-POST requests or invalid actions
    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)


def cart_update(request):
    """
    Handles updating the quantity of a ProductVariation in the cart via AJAX POST.
    Expects 'variation_id' and 'quantity' in POST data.
    Includes validation and stock check.
    """
    cart = Cart(request)

    if request.method == 'POST' and request.POST.get('action') == 'post':
         # Get the variation ID and new quantity from the POST data
         variation_id_str = request.POST.get('variation_id')
         quantity_str = request.POST.get('quantity') # Should be named 'quantity' from cart_summary.html

         # --- Validation ---
         if not variation_id_str:
              return JsonResponse({'error': 'Brak ID wariacji w żądaniu.'}, status=400)

         try:
             variation_id = int(variation_id_str)
         except ValueError:
              return JsonResponse({'error': 'Nieprawidłowe ID wariacji.'}, status=400)

         if not quantity_str:
              return JsonResponse({'error': 'Brak ilości w żądaniu.'}, status=400)

         try:
             quantity = int(quantity_str)
             if quantity < 0: # Allow quantity 0 to potentially trigger deletion
                  return JsonResponse({'error': 'Ilość nie może być ujemna.'}, status=400)
         except ValueError:
              return JsonResponse({'error': 'Nieprawidłowa ilość.'}, status=400)
         # --- End Validation ---

         # If the requested quantity is 0, delegate to the delete view/logic
         if quantity == 0:
             # Call the delete method in the Cart class
             cart.delete(variation=variation_id)
             cart_quantity = cart.__len__()
             cart_total = cart.cart_total()
             messages.success(request, "Produkt usunięty z koszyka.")
             # Return success response indicating deletion
             return JsonResponse({
                 'qty': cart_quantity,
                 'variation_id': variation_id,
                 'cart_total': cart_total,
                 'deleted': True # Indicate that the item was deleted
                 })


         # Get the product variation object for stock check
         variation = get_object_or_404(ProductVariation, id=variation_id)

         # --- Stock Check ---
         # For update, just check if the new requested quantity exceeds stock
         if variation.stock < quantity:
             # Return an error response indicating insufficient stock
             return JsonResponse({'error': f'Brak wystarczającej ilości w magazynie. Dostępnych: {variation.stock}.'}, status=400)
         # --- End Stock Check ---


         # Update the item quantity in the cart using the updated cart.update method
         # The update method now expects variation_id and the new quantity
         cart.update(variation=variation_id, quantity=quantity)

         # Get updated data for the response
         cart_quantity = cart.__len__() # Total quantity of items
         cart_total = cart.cart_total()   # Total price of the cart
         item_subtotal = variation.get_effective_price() * Decimal(quantity) # Subtotal for this specific item

         # Prepare data for JSON response
         response_data = {
             'variation_id': variation_id,
             'quantity': quantity, # New quantity for this item
             'cart_quantity': cart_quantity, # New global total quantity
             'cart_total': cart_total, # New total cart price
             'item_subtotal': item_subtotal, # New subtotal for this item
             'deleted': False # Indicate that the item was not deleted
         }

         # Message for full page reload scenario
         messages.success(request, "Ilość produktu zaktualizowana.")

         return JsonResponse(response_data)

    # Handle non-POST requests or invalid actions
    return JsonResponse({'error': 'Invalid request method or action.'}, status=400)

# ... other cart views like cart_clear if you have them ...