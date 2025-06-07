from django.shortcuts import render, get_object_or_404
from .cart import Cart
from store.models import Product
from django.http import JsonResponse
from django.contrib import messages
import json
from cart.cart import Cart


def cart_summary(request):
	# Get the cart
	cart = Cart(request)
	cart_products = cart.get_prods
	quantities = cart.get_quants
	totals = cart.cart_total()
	return render(request, "cart_summary.html", {"cart_products":cart_products, "quantities":quantities, "totals": totals})


def cart_add(request):
	# Get the cart
	cart = Cart(request)
	# test for POST
	if request.POST.get('action') == 'post':
		# Get stuff
		product_id = int(request.POST.get('product_id'))
		product_qty = int(request.POST.get('product_qty'))

		# lookup product in DB
		product = get_object_or_404(Product, id=product_id)
		
		# Save to session
		cart.add(product=product, quantity=product_qty)

		# Get Cart Quantity
		cart_quantity = cart.__len__()

		# Return resonse
		# response = JsonResponse({'Product Name: ': product.name})
		response = JsonResponse({'qty': cart_quantity})
		messages.success(request, ("Product added to Cart.."))
		return response


def cart_delete(request):
	cart = Cart(request)
	if request.POST.get('action') == 'post':
		# Get stuff
		product_id = int(request.POST.get('product_id'))
		# Call delete Function in Cart
		cart.delete(product=product_id)

		response = JsonResponse({'product':product_id})
		messages.success(request, ("Product removed from cart"))
		#return redirect('cart_summary')
		return response

def cart_update(request):
    cart = Cart(request)
    if request.method == 'POST' and request.POST.get('action') == 'post':
         try:
             product_id = int(request.POST.get('product_id'))
             product_qty = int(request.POST.get('product_qty'))

             # Upewnij się, że cart.update modyfikuje koszyk i ZAPISUJE SESJĘ (np. przez self.save() w Cart)
             cart.update(product=product_id, quantity=product_qty)

             # Przygotuj dane do odpowiedzi JSON
             response_data = {
                 'product_id': product_id,
                 'product_qty': product_qty, # Nowa ilość dla tego produktu
                 'cart_quantity': cart.__len__(), # Nowa globalna liczba różnych produktów
                 'cart_total': cart.cart_total(), # Nowa całkowita suma koszyka (wymaga metody cart_total w Cart)
                 # Opcjonalnie: 'item_subtotal': cart.get_item_subtotal(product_id) # Nowa suma dla tej linii produktu
             }

             messages.success(request, ("Product quantity updated")) # Wiadomość nadal będzie dodana, ale nie będzie widoczna bez przeładowania/dodatkowej logiki JS

             return JsonResponse(response_data)

         except (ValueError, Exception) as e:
             # ... obsługa błędów ...
             return JsonResponse({'error': str(e)}, status=400) # Zwróć błąd w JSON

    # ... obsługa nieprawidłowego żądania ...
    return JsonResponse({'error': 'Invalid request'}, status=400)