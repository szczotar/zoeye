from django.shortcuts import render, get_object_or_404, redirect
# Upewnij się, że importujesz ProductVariation i inne potrzebne modele
from .models import Product, Category, Profile, Material, ProductVariation, Review
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
import json
from cart.cart import Cart
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# Upewnij się, że wszystkie potrzebne importy z django.db.models są tutaj
from django.db.models import Q ,Case, When, DecimalField, Subquery, OuterRef, Avg, Count 
from django.db import models
# Dodaj importy dla agregacji - Nadal potrzebne do obliczenia ogólnego zakresu cen dla suwaka
from django.db.models.aggregates import Min, Max
from django.http import HttpResponseRedirect
from django.urls import reverse # Do generowania URL po sukcesie
from django.contrib.auth.decorators import login_required

# ... (pozostałe widoki przed category - bez zmian) ...
def search(request):
	# Determine if they filled out the form
	if request.method == "POST":
		searched = request.POST['searched']
		# Query The Products DB Model
		searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
		# Test for null
		if not searched:
			messages.success(request, "That Product Does Not Exist...Please try Again.")
			return render(request, "search.html", {})
		else:
			return render(request, "search.html", {'searched':searched})
	else:
		return render(request, "search.html", {})	


def update_info(request):
	if request.user.is_authenticated:
		# Get Current User
		current_user = Profile.objects.get(user__id=request.user.id)
		# Get Current User's Shipping Info
		shipping_user = ShippingAddress.objects.get(id=request.user.id)
		
		# Get original User Form
		form = UserInfoForm(request.POST or None, instance=current_user)
		# Get User's Shipping Form
		shipping_form = ShippingForm(request.POST or None, instance=shipping_user)		
		if form.is_valid() or shipping_form.is_valid():
			# Save original form
			form.save()
			# Save shipping form
			shipping_form.save()

			messages.success(request, "Your Info Has Been Updated!!")
			return redirect('home')
		return render(request, "update_info.html", {'form':form, 'shipping_form':shipping_form})
	else:
		messages.success(request, "You Must Be Logged In To Access That Page!!")
		return redirect('home')


def update_password(request):
	if request.user.is_authenticated:
		current_user = request.user
		# Did they fill out the form
		if request.method  == 'POST':
			form = ChangePasswordForm(current_user, request.POST)
			# Is the form valid
			if form.is_valid():
				form.save()
				messages.success(request, "Your Password Has Been Updated...")
				login(request, current_user)
				return redirect('update_user')
			else:
				for error in list(form.errors.values()):
					messages.error(request, error)
					return redirect('update_password')
		else:
			form = ChangePasswordForm(current_user)
			return render(request, "update_password.html", {'form':form})
	else:
		messages.success(request, "You Must Be Logged In To View That Page...")
		return redirect('home')
	
def update_user(request):
	if request.user.is_authenticated:
		current_user = User.objects.get(id=request.user.id)
		user_form = UpdateUserForm(request.POST or None, instance=current_user)

		if user_form.is_valid():
			user_form.save()

			login(request, current_user)
			messages.success(request, "User Has Been Updated!!")
			return redirect('home')
		return render(request, "update_user.html", {'user_form':user_form})
	else:
		messages.success(request, "You Must Be Logged In To Access That Page!!")
		return redirect('home')

# Create your views here.

# def category(request, foo):
# 	# Replace Hyphens with Spaces
# 	foo = foo.replace('-', ' ')
# 	# Grab the category from the url
# 	try:
# 		# Look Up The Category
# 		category = Category.objects.get(name=foo)
# 		products = Product.objects.filter(category=category)
# 		return render(request, 'category.html', {'products':products, 'category':category})
# 	except:
# 		messages.success(request, ("That Category Doesn't Exist..."))
# 		return redirect('home')

def category(request, foo):
    # ... (początek funkcji) ...

    category = get_object_or_404(Category, name=foo)
    all_materials = Material.objects.all().order_by('name')

    # Zaczynamy od produktów w danej kategorii
    all_products_in_category = Product.objects.filter(category=category)
    print(f"DEBUG: Initial products in category '{foo}': {all_products_in_category.count()}") # Debug

    # --- OBLICZ OGÓLNY ZAKRES CEN DLA SUWAKA (TERAZ ZAWSZE Z CENY BAZOWEJ PRODUKTU) ---
    # Obliczamy zakres na podstawie ceny bazowej 'price'
    price_aggregation = all_products_in_category.aggregate(
        min_price=Min('price'), # Zmieniono na 'price'
        max_price=Max('price')  # Zmieniono na 'price'
    )
    overall_min_price = price_aggregation['min_price'] if price_aggregation['min_price'] is not None else 0
    overall_max_price = price_aggregation['max_price'] if price_aggregation['max_price'] is not None else 1000
    print(f"DEBUG: Overall price range: {overall_min_price} - {overall_max_price}") # Debug

    product_list_base = all_products_in_category.annotate(
        effective_price=Case(
            When(is_sale=True, then='sale_price'),
            default='price',
            output_field=DecimalField()
        )
    )

    print(f"DEBUG: Products after price annotation: {product_list_base.count()}") # Debug


    # --- Logika Filtrowania ---
    selected_gender = request.GET.get('gender')
    selected_min_price_str = request.GET.get('min_price')
    selected_max_price_str = request.GET.get('max_price')
    selected_materials = request.GET.getlist('material')
    selected_sale_only = request.GET.get('sale_only') == 'true'
    selected_available_only = request.GET.get('available_only') == 'true'

    # Konwertujemy wybrane ceny na float
    try:
        # Użyj overall_min/max_price jako domyślnych, jeśli parametry GET są puste
        selected_min_price = float(selected_min_price_str) if selected_min_price_str else overall_min_price
    except ValueError:
        selected_min_price = overall_min_price # Fallback w przypadku niepoprawnej wartości
    try:
        selected_max_price = float(selected_max_price_str) if selected_max_price_str else overall_max_price
    except ValueError:
        selected_max_price = overall_max_price # Fallback w przypadku niepoprawnej wartości

    print(f"DEBUG: Selected filters: gender={selected_gender}, min_price={selected_min_price}, max_price={selected_max_price}, materials={selected_materials}, sale_only={selected_sale_only}, available_only={selected_available_only}") # Debug

    # Zaczynamy filtrowanie od product_list_base
    product_list = product_list_base

    try:
        # Filtr płci (gender)
        if selected_gender and selected_gender != 'all':
            product_list = product_list.filter(gender=selected_gender)
            print(f"DEBUG: After Gender filter ({selected_gender}): {product_list.count()}") # Debug

        # Filtr materiału (material)
        if selected_materials:
            material_q_objects = Q()
            for material_name in selected_materials:
                material_q_objects |= Q(materials__name=material_name)
            product_list = product_list.filter(material_q_objects) # Filter on M2M
            print(f"DEBUG: After Material filter (before final distinct): {product_list.count()}") # Debug

        # Filtr promocji
        if selected_sale_only:
            product_list = product_list.filter(is_sale=True) # Sale filter is on Product now
            print(f"DEBUG: After Sale Only filter: {product_list.count()}") # Debug

        # --- ZASTOSUJ NOWY FILTR DOSTĘPNOŚCI ---
        if selected_available_only:
             product_list = product_list.filter(
                Q(variations__isnull=True, stock__gt=0) | # Produkty bez wariacji ORAZ stock > 0
                Q(variations__isnull=False, variations__stock__gt=0) # Produkty Z wariacjami ORAZ przynajmniej jedna wariacja ma stock > 0
             ) # Filter on Reverse FK
             print(f"DEBUG: After Available Only filter (before final distinct): {product_list.count()}") # Debug
        # ---------------------------------------

        # --- APPLY DISTINCT after all filters that might cause duplication ---
        # Stosujemy distinct po wszystkich filtrach, które mogą powielać wyniki
        product_list = product_list.distinct()
        print(f"DEBUG: After applying DISTINCT: {product_list.count()}")
        # --------------------------------------------------------------------

        # --- Apply Price Range filter (uses effective_price annotation) ---
        # Ten filtr jest ZAWSZE stosowany, używając selected_min/max_price
        # które domyślnie przyjmują wartości overall_min/max_price
        print(f"DEBUG: Applying Price Range filter: {selected_min_price} - {selected_max_price}") # Debug
        product_list = product_list.filter(
            effective_price__gte=selected_min_price,
            effective_price__lte=selected_max_price
        )
        print(f"DEBUG: Count after Price Range filter: {product_list.count()}") # Debug
        # -------------------------------------------------------------------


    except Exception as e:
        print(f"DEBUG: Error during filtering: {e}")
        product_list = Product.objects.none() # Ustaw listę na pustą po błędzie


    print(f"DEBUG: Final count before pagination: {product_list.count()}") # Debug

    # --- Logika Sortowania ---
    # Sortowanie powinno być stosowane po wszystkich filtrach i adnotacjach
    sort_by = request.GET.get('sorting', 'default')
    print(f"DEBUG: Sorting requested: {sort_by}")

    try:
        if sort_by == 'low-high':
            # Sortowanie po efektywnej cenie
            product_list = product_list.order_by('effective_price', 'pk')
            print("DEBUG: Sorted by effective_price low-high.")
        elif sort_by == 'high-low':
            # Sortowanie po efektywnej cenie
            product_list = product_list.order_by('-effective_price', 'pk')
            print("DEBUG: Sorted by effective_price high-low.")
        elif sort_by == 'popularity':
             product_list = product_list.order_by('name', 'pk') # Fallback
             print("DEBUG: Popularity sort selected, falling back to default (name, pk).")
        else: # 'default'
             product_list = product_list.order_by('name', 'pk')
             print("DEBUG: Sorted by default (name, pk).")

    except Exception as e:
        print(f"DEBUG: Error during sorting, applying default sort (name, pk). Error: {e}")
        product_list = product_list.order_by('name', 'pk') # Fallback sort


    # --- Logika Paginacji ---
    products_per_page = 9

    # Przekazujemy 'product_list' do paginatora.
    # Jeśli błąd OuterRef nadal występuje, może być konieczne
    # dalsze uproszczenie querysetu przed paginacją, np. poprzez
    # pobranie tylko ID, a następnie wykonanie nowego zapytania.
    # Ale spróbujmy najpierw tego:
    paginator = Paginator(product_list, products_per_page)

    page_number = request.GET.get('page')

    try:
        products_page = paginator.get_page(page_number)
        print(f"DEBUG: Total items for pagination: {paginator.count}")
        print(f"DEBUG: Total pages: {paginator.num_pages}")
        print(f"DEBUG: Products on current page ({products_page.number}): {len(products_page.object_list) if hasattr(products_page, 'object_list') else 'N/A'}")


    except PageNotInteger:
        products_page = paginator.get_page(1)
        print("DEBUG: Invalid page number, getting page 1.")
    except EmptyPage:
        products_page = paginator.get_page(paginator.num_pages)
        print("DEBUG: Empty page requested, getting last page.")
    except Exception as e:
         print(f"DEBUG: Unexpected error during pagination: {e}")
         # Fallback na pustą stronę, jeśli paginacja zawiedzie
         from django.core.paginator import Page
         # Tworzymy pustą listę produktów dla pustej strony
         products_page = paginator.get_page(1) # Spróbuj pobrać pierwszą stronę, jeśli błąd nie jest związany z numerem strony
         products_page.object_list = [] # Ustawiamy listę obiektów na pustą
         products_page.paginator._count = 0 # Resetujemy licznik paginatora dla tej pustej strony
         # products_page = Page([], 1, paginator) # Alternatywnie, jeśli chcesz całkowicie pusty obiekt Page

         print("DEBUG: Unexpected pagination error, providing empty page object with empty list.")
         print(f"DEBUG: Error details: {e}") # Wydrukuj szczegóły błędu


    context = {
        'category': category,
        'products_page': products_page,
        'current_sorting': sort_by,
        'request': request,

        'all_materials': all_materials,
        'selected_gender': selected_gender,
        'selected_min_price': selected_min_price_str,
        'selected_max_price': selected_max_price_str,
        'selected_materials': selected_materials,
        'selected_sale_only': selected_sale_only,
        'selected_available_only': selected_available_only,

        'overall_min_price': float(overall_min_price),
        'overall_max_price': float(overall_max_price),
    }

    print(f"DEBUG: Context keys: {context.keys()}")
    print(f"--- End category view ---")

    return render(request, 'category.html', context)

# --- Widok szczegółów produktu ---
def product(request, pk):
    """
    Widok wyświetlający szczegóły produktu, jego wariacje (rozmiary),
    recenzje/oceny i produkty z tym samym materiałem.
    Argument 'pk' przyjmuje ID produktu z URL.
    """
    print(f"--- Debugging product view ---")
    print(f"Requested product ID (pk): {pk}")

    try:
        product = get_object_or_404(Product, pk=pk)
        print(f"Product found: {product.name}")
    except Exception as e:
        print(f"Error getting product with pk '{pk}': {e}")
        raise # Zgłoś błąd 404

    # --- Pobierz Recenzje dla tego produktu ---
    reviews = product.reviews.all()
    print(f"Found {reviews.count()} total reviews for product '{product.name}'.")

    # --- Oblicz średnią ocenę i liczbę ocen (w widoku) ---
    # Filtruj recenzje, które mają ustawioną ocenę (rating is not null)
    reviews_with_rating = reviews.filter(rating__isnull=False)

    # Oblicz średnią ocenę
    average_rating_agg = reviews_with_rating.aggregate(Avg('rating'))
    average_rating = average_rating_agg['rating__avg'] # Poprawiono klucz

    # Zaokrąglij średnią ocenę do np. 1 miejsca po przecinku
    if average_rating is not None:
        average_rating = round(average_rating, 1)
    print(f"Average rating: {average_rating}")

    # Oblicz liczbę recenzji z oceną
    rating_count = reviews_with_rating.count()
    print(f"Number of reviews with rating: {rating_count}")

    # --- Oblicz rozkład ocen (ile recenzji dla każdej oceny 1-5) ---
    # Użyj annotate i Count z wartościami rating
    # group_by rating i count
    rating_distribution = reviews_with_rating.values('rating').annotate(count=Count('rating')).order_by('rating')

    # Przekształć QuerySet w słownik dla łatwiejszego dostępu w szablonie
    # Słownik będzie wyglądał np. {1: 5, 3: 10, 5: 2}
    rating_distribution_dict = {item['rating']: item['count'] for item in rating_distribution}

    # Upewnij się, że słownik zawiera wszystkie oceny od 1 do 5, nawet jeśli count wynosi 0
    # Aby ułatwić iterację w szablonie
    full_rating_distribution = {i: rating_distribution_dict.get(i, 0) for i in range(1, 6)}
    print(f"Rating distribution: {full_rating_distribution}")


    # --- Pobierz Wariacje Produktu (posortowane) ---
    variations = product.variations.all().order_by('size')
    print(f"Found {variations.count()} variations for product '{product.name}'.")

    # --- Pobierz Produkty z Tym Samym Materiałem (Podobne Produkty) ---
    product_materials = product.materials.all()
    similar_products = Product.objects.none()
    if product_materials.exists():
        material_q_objects = Q()
        for material in product_materials:
            material_q_objects |= Q(materials=material)
        similar_products = Product.objects.filter(material_q_objects).distinct().exclude(pk=product.pk)[:6]
    print(f"Found {similar_products.count()} similar products based on materials.")


    context = {
        'product': product,
        'variations': variations,
        'similar_products': similar_products,
        'reviews': reviews, # Przekazujemy wszystkie recenzje (do wyświetlenia listy komentarzy)
        'average_rating': average_rating, # Przekazujemy obliczoną średnią ocenę
        'rating_count': rating_count, # Przekazanie liczby recenzji z oceną
        'rating_distribution': full_rating_distribution, # DODANO: przekazanie rozkładu ocen
        'rating_values': range(5, 0, -1), # Utwórz range od 5 do 1
    }

    print(f"Context keys: {context.keys()}")
    print(f"--- End product view ---")

    return render(request, 'product.html', context)


def stones_detail(request, material_name):
    # ... (początek funkcji) ...

    material = get_object_or_404(Material, name=material_name)
    all_materials = Material.objects.all().order_by('name')

    # Zaczynamy od produktów z danym materiałem
    all_products_with_material = Product.objects.filter(materials=material)
    print(f"DEBUG: Initial count for material '{material.name}': {all_products_with_material.count()}") # Debug

    # --- OBLICZ OGÓLNY ZAKRES CEN DLA SUWAKA (TERAZ ZAWSZE Z CENY BAZOWEJ PRODUKTU) ---
    price_aggregation = all_products_with_material.aggregate(
        min_price=Min('price'), # Zmieniono na 'price'
        max_price=Max('price')  # Zmieniono na 'price'
    )
    overall_min_price = price_aggregation['min_price'] if price_aggregation['min_price'] is not None else 0
    overall_max_price = price_aggregation['max_price'] if price_aggregation['max_price'] is not None else 1000
    print(f"DEBUG: Overall Price Range calculated: {overall_min_price} - {overall_max_price}") # Debug


    # --- Zaczynamy filtrowanie od pełnej listy produktów z tym materiałem ---
    # Uproszczona adnotacja dla effective_price - BEZ Subquery/OuterRef dla ceny
    product_list = all_products_with_material.annotate(
        effective_price=Case(
            When(is_sale=True, then='sale_price'),
            default='price',
            output_field=DecimalField()
        )
    )
    # USUNIĘTO adnotację min_variation_price


    print(f"DEBUG: Count after annotation: {product_list.count()}") # Debug


    # --- Logika Filtrowania ---
    selected_gender = request.GET.get('gender')
    selected_min_price_str = request.GET.get('min_price')
    selected_max_price_str = request.GET.get('max_price')
    selected_sale_only = request.GET.get('sale_only') == 'true'
    selected_available_only = request.GET.get('available_only') == 'true'

    # Konwertujemy wybrane ceny na float
    try:
        selected_min_price = float(selected_min_price_str) if selected_min_price_str else overall_min_price
    except ValueError:
        selected_min_price = overall_min_price
    try:
        selected_max_price = float(selected_max_price_str) if selected_max_price_str else overall_max_price
    except ValueError:
        selected_max_price = overall_max_price

    print(f"DEBUG: Selected filters: gender={selected_gender}, min_price={selected_min_price}, max_price={selected_max_price}, sale_only={selected_sale_only}, available_only={selected_available_only}") # Debug


    try:
        # Filtr płci (gender)
        if selected_gender and selected_gender != 'all':
            product_list = product_list.filter(gender=selected_gender)
            print(f"DEBUG: Count after Gender filter ('{selected_gender}'): {product_list.count()}") # Debug

        # Filtr promocji
        if selected_sale_only:
             product_list = product_list.filter(is_sale=True)
             print(f"DEBUG: Count after Sale Only filter: {product_list.count()}") # Debug

        # Filtr dostępności
        if selected_available_only:
             product_list = product_list.filter(
                Q(variations__isnull=True, stock__gt=0) |
                Q(variations__isnull=False, variations__stock__gt=0)
             ).distinct()
             print(f"DEBUG: Count after Available Only filter: {product_list.count()}") # Debug

        # --- FILTR CENY (MIN/MAX) ---
        print(f"DEBUG: Applying Price Range filter: {selected_min_price} - {selected_max_price}") # Debug
        product_list = product_list.filter(
            effective_price__gte=selected_min_price,
            effective_price__lte=selected_max_price
        )
        print(f"DEBUG: Count after Price Range filter: {product_list.count()}") # Debug


    except Exception as e:
        print(f"DEBUG: Error during filtering: {e}")
        product_list = Product.objects.none()


    print(f"DEBUG: Final count before pagination: {product_list.count()}") # Debug


    # --- Logika Sortowania ---
    sort_by = request.GET.get('sorting', 'default')
    print(f"DEBUG: Sorting requested: {sort_by}")

    try:
        if sort_by == 'low-high':
            product_list = product_list.order_by('effective_price', 'pk')
            print("DEBUG: Sorted by effective_price low-high.")
        elif sort_by == 'high-low':
            product_list = product_list.order_by('-effective_price', 'pk')
            print("DEBUG: Sorted by effective_price high-low.")
        elif sort_by == 'popularity':
             product_list = product_list.order_by('name', 'pk')
             print("DEBUG: Popularity sort selected, falling back to default (name, pk).")
        else: # 'default'
             product_list = product_list.order_by('name', 'pk')
             print("DEBUG: Sorted by default (name, pk).")

    except Exception as e:
        print(f"DEBUG: Error during sorting, applying default sort (name, pk). Error: {e}")
        product_list = product_list.order_by('name', 'pk')


    # --- Logika Paginacji ---
    products_per_page = 9

    paginator = Paginator(product_list, products_per_page)

    page_number = request.GET.get('page')

    try:
        products_page = paginator.get_page(page_number)
        print(f"DEBUG: Total items for pagination: {paginator.count}")
        print(f"DEBUG: Total pages: {paginator.num_pages}")
        print(f"DEBUG: Products on current page ({products_page.number}): {len(products_page.object_list) if hasattr(products_page, 'object_list') else 'N/A'}")
    except PageNotInteger:
        products_page = paginator.get_page(1)
        print("DEBUG: Invalid page number, getting page 1.")
    except EmptyPage:
        products_page = paginator.get_page(paginator.num_pages)
        print("DEBUG: Empty page requested, getting last page.")
    except Exception as e:
         print(f"DEBUG: Unexpected error during pagination: {e}")
         from django.core.paginator import Page
         products_page = Page([], 1, paginator)
         print("DEBUG: Unexpected pagination error, providing empty page.")


    context = {
        'material': material,
        'products_page': products_page,
        'current_sorting': sort_by,
        'request': request,

        'all_materials': all_materials,
        'selected_gender': selected_gender,
        'selected_min_price': selected_min_price_str,
        'selected_max_price': selected_max_price_str,
        'selected_materials': [], # Na tej stronie nie filtrujemy po wielu materiałach z sidebar
        'selected_sale_only': selected_sale_only,
        'selected_available_only': selected_available_only,

        'overall_min_price': float(overall_min_price),
        'overall_max_price': float(overall_max_price),
    }

    print(f"DEBUG: Context keys: {context.keys()}")
    print(f"--- End stones_detail view ---")

    return render(request, 'stones.html', context)

def home(request):
	products = Product.objects.all()
	categories = Category.objects.all()
	return render(request, 'home.html', {'products': products, 'categories': categories})

def about(request):
    return render(request, 'about.html', {})

def login_user(request):
	if request.method == "POST":
		username = request.POST['username']
		password = request.POST['password']
		user = authenticate(request, username=username, password=password)
		if user is not None:
			login(request, user)

			# Do some shopping cart stuff
			current_user = Profile.objects.get(user__id=request.user.id)
			# Get their saved cart from database
			saved_cart = current_user.old_cart
			# Convert database string to python dictionary
			if saved_cart:
				# Convert to dictionary using JSON
				converted_cart = json.loads(saved_cart)
				# Add the loaded cart dictionary to our session
				# Get the cart
				cart = Cart(request)
				# Loop thru the cart and add the items from the database
				for key,value in converted_cart.items():
					cart.db_add(product=key, quantity=value)

			messages.success(request, ("You Have Been Logged In!"))
			return redirect('home')
		else:
			messages.success(request, ("There was an error, please try again..."))
			return redirect('login')

	else:
		return render(request, 'login.html', {})

def Logout_user(request):
     logout(request)
     messages.success(request,("You have been logged out"))
     return redirect('home')

def register_user(request):
    form = SignUpForm()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            # log in user
            user = authenticate(username=username, password=password)
            login(request,user)
			
            messages.success(request, ("Username Created - Please fill out Your user info below"))
            return redirect("update_info")
        else:
            messages.success(request,("Please try again"))
            return redirect("register")
    else:  
        return render(request, 'register.html', {'form':form})


def categories_all(request):
    # Fetch all categories
	categories = Category.objects.all()
	return render(request, 'cat.html', {'categories': categories})


def add_review(request, product_id):
    """
    Handles adding a new review for a product.
    Expects POST request with 'rating' (optional) and 'comment'.
    Redirects back to the product page after submission.
    """
    # Upewnij się, że żądanie jest POST
    if request.method == 'POST':
        # Pobierz produkt, do którego dodawana jest recenzja
        product = get_object_or_404(Product, id=product_id)

        # Pobierz dane z formularza POST
        rating_str = request.POST.get('rating')
        comment = request.POST.get('comment')

        # Walidacja danych
        if not comment:
            messages.error(request, "Komentarz nie może być pusty.")
            # Przekieruj z powrotem do strony produktu
            return HttpResponseRedirect(reverse('product', args=[product.id]))

        # Walidacja oceny (jeśli jest ustawiona)
        rating = None # Domyślnie brak oceny
        if rating_str:
            try:
                rating = int(rating_str)
                # Użyj walidatorów z modelu lub sprawdź ręcznie
                if not (1 <= rating <= 5):
                    messages.error(request, "Ocena musi być liczbą od 1 do 5.")
                    return HttpResponseRedirect(reverse('product', args=[product.id]))
            except ValueError:
                messages.error(request, "Nieprawidłowa wartość oceny.")
                return HttpResponseRedirect(reverse('product', args=[product.id]))

        # Utwórz nowy obiekt Review
        review = Review(
            product=product,
            comment=comment,
            rating=rating,
            # Ustaw użytkownika tylko jeśli jest zalogowany
            user=request.user if request.user.is_authenticated else None
            # Jeśli pozwalasz niezarejestrowanym, pobierz imię/email z POST
            # name=request.POST.get('name', '') if not request.user.is_authenticated else '',
            # email=request.POST.get('email', '') if not request.user.is_authenticated else '',
        )

        try:
            # Zapisz recenzję do bazy danych
            review.full_clean() # Wywołaj pełną walidację modelu (w tym walidatory)
            review.save()
            messages.success(request, "Twoja recenzja została dodana.")
        except Exception as e:
            # Obsłuż błędy zapisu lub walidacji
            messages.error(request, f"Wystąpił błąd podczas zapisywania recenzji: {e}")
            print(f"Error saving review: {e}") # Logowanie błędu na serwerze


        # Przekieruj z powrotem do strony produktu
        # Użyj HttpResponseRedirect z reverse, aby wygenerować URL
        return HttpResponseRedirect(reverse('product', args=[product.id]))

    # Jeśli żądanie nie jest POST, przekieruj na stronę główną lub stronę produktu
    messages.warning(request, "Nieprawidłowe żądanie dodania recenzji.")
    # Możesz przekierować z powrotem na stronę produktu, nawet jeśli to GET
    return HttpResponseRedirect(reverse('product', args=[product_id]))


# Załóżmy, że Twoja funkcja widoku nazywa się category_detail
# Przyjmuje slug kategorii jako argument, np. /category/electronics/
