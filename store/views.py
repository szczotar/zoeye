from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Category, Profile, Material, ProductVariation # Upewnij się, że ProductVariation jest zaimportowane
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from django.db.models import Q
import json
from cart.cart import Cart
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Case, When, DecimalField, Subquery, OuterRef # Upewnij się, że Subquery i OuterRef też są zaimportowane
from django.db import models # <-- DODAJ TĘ LINIĘ

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


# W Twoim pliku views.py
from django.shortcuts import render, get_object_or_404
from .models import Category, Product, Material # Upewnij się, że importujesz Material
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Case, When, DecimalField, Q # Upewnij się, że importujesz Q i DecimalField

def category(request, foo):
    """
    Widok wyświetlający szczegóły kategorii i listę produktów z paginacją, sortowaniem i filtrami.
    Argument 'foo' przyjmuje nazwę kategorii z URL.
    """
    print(f"--- Debugging category view ---")
    print(f"Requested category name: {foo}")

    category = get_object_or_404(Category, name=foo)
    all_materials = Material.objects.all().order_by('name')

    # Zaczynamy od produktów w danej kategorii
    product_list = Product.objects.filter(category=category)

    # --- ADNOTACJA DLA EFEKTYWNEJ CENY ---
    # Tworzymy tymczasowe pole 'effective_price' do sortowania.
    # Dla produktów z wariacjami użyjemy ceny minimalnej wariacji.
    # Dla produktów bez wariacji użyjemy ich własnej efektywnej ceny.
    product_list = product_list.annotate(
        has_variations_flag=models.Case(
            models.When(variations__isnull=False, then=True),
            default=False,
            output_field=models.BooleanField()
        )
    ).annotate(
         min_variation_price=models.Subquery(
             ProductVariation.objects.filter(product=models.OuterRef('pk'))
             .annotate(
                 effective_var_price=Case(
                     When(is_sale=True, then='sale_price'),
                     When(price__isnull=False, then='price'),
                     default=models.OuterRef('price'), # fallback to parent product's base price
                     output_field=DecimalField()
                 )
             )
             .order_by('effective_var_price')
             .values('effective_var_price')[:1]
         )
    ).annotate(
        effective_price=Case(
            When(has_variations_flag=True, then='min_variation_price'),
            When(is_sale=True, then='sale_price'), # Produkty bez wariacji, ale na wyprzedaży
            default='price', # Produkty bez wariacji i bez wyprzedaży
            output_field=DecimalField()
        )
    )


    # --- Logika Filtrowania ---
    selected_gender = request.GET.get('gender')
    selected_min_price = request.GET.get('min_price')
    selected_max_price = request.GET.get('max_price')
    selected_materials = request.GET.getlist('material')
    selected_sale_only = request.GET.get('sale_only') == 'true'

    print(f"Product list count before filtering: {product_list.count()}")

    try:
        # Filtr płci (gender)
        if selected_gender and selected_gender != 'all':
            product_list = product_list.filter(gender=selected_gender)
            print(f"Applied Gender filter: {selected_gender}. Count: {product_list.count()}")

        # Filtr ceny (min_price, max_price) - TERAZ FILTRUJEMY PO 'effective_price'
        if selected_min_price:
            try:
                min_price_float = float(selected_min_price)
                product_list = product_list.filter(effective_price__gte=min_price_float)
                print(f"Applied Min Price filter: {min_price_float}. Count: {product_list.count()}")
            except ValueError:
                print(f"Invalid min_price value: {selected_min_price}")
        if selected_max_price:
            try:
                max_price_float = float(selected_max_price)
                product_list = product_list.filter(effective_price__lte=max_price_float)
                print(f"Applied Max Price filter: {max_price_float}. Count: {product_list.count()}")
            except ValueError:
                 print(f"Invalid max_price value: {selected_max_price}")

        # Filtr materiału (material)
        if selected_materials:
            material_q_objects = Q()
            for material_name in selected_materials:
                material_q_objects |= Q(materials__name=material_name)
            product_list = product_list.filter(material_q_objects).distinct()
            print(f"Applied Material filter: {selected_materials}. Count: {product_list.count()}")

        # Filtr promocji - TERAZ FILTRUJEMY PRODUKTY, KTÓRE SĄ NA WYPRZEDAŻY (LUB MAJĄ WAR. NA WYPRZEDAŻY)
        # To może być bardziej złożone w przypadku wariacji. Czy chcemy pokazać produkt,
        # jeśli *którakolwiek* jego wariacja jest na wyprzedaży? Czy tylko jeśli produkt bazowy jest?
        # Najprościej: filtruj po is_sale produktu bazowego. Jeśli chcesz uwzględnić wariacje,
        # musisz dodać anotację sprawdzającą, czy którakolwiek wariacja jest na wyprzedaży.
        # Poniższy kod filtruje tylko po is_sale produktu bazowego.
        # ALTERNATYWNIE: Możesz dodać anotację sprawdzającą czy `(is_sale=True) OR (variations__is_sale=True)`
        if selected_sale_only:
            # Filtr na produkty bazowe LUB produkty z wariacją na wyprzedaży
            product_list = product_list.filter(Q(is_sale=True) | Q(variations__is_sale=True)).distinct()
            print(f"Applied Sale Only filter. Count: {product_list.count()}")


    except Exception as e:
        print(f"Error during filtering: {e}")


    # --- Logika Sortowania ---
    sort_by = request.GET.get('sorting', 'default')
    print(f"Sorting requested: {sort_by}")

    try:
        if sort_by == 'low-high':
            # Sortowanie po efektywnej cenie (uwzględniając minimalną cenę wariacji)
            product_list = product_list.order_by('effective_price', 'pk')
            print("Sorted by effective_price low-high.")
        elif sort_by == 'high-low':
            # Sortowanie po efektywnej cenie (uwzględniając minimalną cenę wariacji)
            product_list = product_list.order_by('-effective_price', 'pk')
            print("Sorted by effective_price high-low.")
        elif sort_by == 'popularity':
             # Trzeba dodać logikę popularności, na razie sortowanie domyślne
             product_list = product_list.order_by('name', 'pk')
             print("Popularity sort selected, falling back to default (name, pk).")
        else: # 'default'
             product_list = product_list.order_by('name', 'pk')
             print("Sorted by default (name, pk).")

    except Exception as e:
        product_list = product_list.order_by('name', 'pk')
        print(f"Error during sorting, applying default sort (name, pk). Error: {e}")


    # --- Logika Paginacji ---
    products_per_page = 9

    paginator = Paginator(product_list, products_per_page)

    page_number = request.GET.get('page')

    try:
        products_page = paginator.get_page(page_number)
        print(f"Total items for pagination: {paginator.count}")
        print(f"Total pages: {paginator.num_pages}")
        print(f"Products on current page ({products_page.number}): {len(products_page.object_list) if hasattr(products_page, 'object_list') else 'N/A'}")
    except PageNotInteger: # Zmieniono na PageNotInteger
        products_page = paginator.get_page(1)
        print("Invalid page number, getting page 1.")
    except EmptyPage:
        products_page = paginator.get_page(paginator.num_pages)
        print("Empty page requested, getting last page.")
    except Exception as e:
         print(f"Unexpected error during pagination: {e}")
         # Fallback na pustą stronę, jeśli paginacja zawiedzie
         from django.core.paginator import Page
         products_page = Page([], 1, paginator)
         print("Unexpected pagination error, providing empty page.")


    context = {
        'category': category,
        'products_page': products_page,
        'current_sorting': sort_by,
        'request': request, # Potrzebne do generowania URL z filtrami/sortowaniem

        'all_materials': all_materials,
        'selected_gender': selected_gender,
        'selected_min_price': selected_min_price,
        'selected_max_price': selected_max_price,
        'selected_materials': selected_materials,
        'selected_sale_only': selected_sale_only,
    }

    print(f"Context keys: {context.keys()}")
    print(f"--- End category view ---")

    return render(request, 'category.html', context)


# --- Widok szczegółów produktu ---
def product(request, pk):
    """
    Widok wyświetlający szczegóły produktu, jego wariacje (rozmiary)
    i produkty z tym samym materiałem.
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

    # --- Pobierz Wariacje Produktu (rozmiary) ---
    # Posortuj je np. po polu 'size' (jeśli jest to możliwe, np. jako liczby)
    # Jeśli rozmiary są typu '17cm', '18cm', sortowanie alfabetyczne może być OK.
    # Jeśli chcesz sortować numerycznie '17' przed '18', pole size musiałoby być int/decimal
    # lub wymagać niestandardowego sortowania. Dla prostoty, sortujmy alfabetycznie.
    variations = product.variations.all().order_by('size') # Sortuj wariacje

    print(f"Found {variations.count()} variations for product '{product.name}'.")


    # --- Pobierz Produkty z Tym Samym Materiałem (Podobne Produkty) ---
    product_materials = product.materials.all()
    similar_products = Product.objects.none()

    if product_materials.exists():
        material_q_objects = Q()
        for material in product_materials:
            material_q_objects |= Q(materials=material)

        similar_products = Product.objects.filter(material_q_objects).distinct()
        similar_products = similar_products.exclude(pk=product.pk)
        similar_products = similar_products[:6] # Pokaż np. 6 podobnych produktów

    print(f"Found {similar_products.count()} similar products based on materials.")


    context = {
        'product': product,
        'variations': variations,        # <-- DODAJ WARIAcje DO KONTEKSTU
        'similar_products': similar_products,
    }

    print(f"Context keys: {context.keys()}")
    print(f"--- End product view ---")

    return render(request, 'product.html', context)

# --- Widok szczegółów materiału ---
def stones_detail(request, material_name):
    """
    Widok wyświetlający szczegóły materiału (kamienia) i listę produktów z tym materiałem,
    z paginacją, sortowaniem i filtrami.
    Argument 'material_name' przyjmuje nazwę materiału z URL.
    """
    print(f"--- Debugging stones_detail view ---")
    print(f"Requested material name: {material_name}")

    material = get_object_or_404(Material, name=material_name)
    all_materials = Material.objects.all().order_by('name')

    product_list = Product.objects.filter(materials=material)
    print(f"Initial product list count for material '{material.name}': {product_list.count()}")

    # --- ADNOTACJA DLA EFEKTYWNEJ CENY ---
    # Tak samo jak w widoku category, użyj effective_price z uwzględnieniem wariacji
    product_list = product_list.annotate(
        has_variations_flag=models.Case(
            models.When(variations__isnull=False, then=True),
            default=False,
            output_field=models.BooleanField()
        )
    ).annotate(
         min_variation_price=models.Subquery(
             ProductVariation.objects.filter(product=models.OuterRef('pk'))
             .annotate(
                 effective_var_price=Case(
                     When(is_sale=True, then='sale_price'),
                     When(price__isnull=False, then='price'),
                     default=models.OuterRef('price'),
                     output_field=DecimalField()
                 )
             )
             .order_by('effective_var_price')
             .values('effective_var_price')[:1]
         )
    ).annotate(
        effective_price=Case(
            When(has_variations_flag=True, then='min_variation_price'),
            When(is_sale=True, then='sale_price'),
            default='price',
            output_field=DecimalField()
        )
    )


    # --- Logika Filtrowania ---
    selected_gender = request.GET.get('gender')
    selected_min_price = request.GET.get('min_price')
    selected_max_price = request.GET.get('max_price')
    # selected_materials = request.GET.getlist('material') # Niepotrzebne tutaj
    selected_sale_only = request.GET.get('sale_only') == 'true'

    print(f"Product list count before filtering: {product_list.count()}")

    try:
        # Filtr płci (gender)
        if selected_gender and selected_gender != 'all':
            product_list = product_list.filter(gender=selected_gender)
            print(f"Applied Gender filter: {selected_gender}. Count: {product_list.count()}")

        # Filtr ceny (min_price, max_price) - TERAZ FILTRUJEMY PO 'effective_price'
        if selected_min_price:
            try:
                min_price_float = float(selected_min_price)
                product_list = product_list.filter(effective_price__gte=min_price_float)
                print(f"Applied Min Price filter: {min_price_float}. Count: {product_list.count()}")
            except ValueError:
                print(f"Invalid min_price value: {selected_min_price}")
        if selected_max_price:
            try:
                max_price_float = float(selected_max_price)
                product_list = product_list.filter(effective_price__lte=max_price_float)
                print(f"Applied Max Price filter: {max_price_float}. Count: {product_list.count()}")
            except ValueError:
                 print(f"Invalid max_price value: {selected_max_price}")

        # Filtr promocji
        if selected_sale_only:
             product_list = product_list.filter(Q(is_sale=True) | Q(variations__is_sale=True)).distinct()
             print(f"Applied Sale Only filter. Count: {product_list.count()}")

    except Exception as e:
        print(f"Error during filtering: {e}")

    print(f"Product list count after ALL filtering: {product_list.count()}")


    # --- Logika Sortowania ---
    sort_by = request.GET.get('sorting', 'default')
    print(f"Sorting requested: {sort_by}")

    try:
        if sort_by == 'low-high':
            product_list = product_list.order_by('effective_price', 'pk')
            print("Sorted by effective_price low-high.")
        elif sort_by == 'high-low':
            product_list = product_list.order_by('-effective_price', 'pk')
            print("Sorted by effective_price high-low.")
        elif sort_by == 'popularity':
             product_list = product_list.order_by('name', 'pk')
             print("Popularity sort selected, falling back to default (name, pk).")
        else: # 'default'
             product_list = product_list.order_by('name', 'pk')
             print("Sorted by default (name, pk).")

    except Exception as e:
        product_list = product_list.order_by('name', 'pk')
        print(f"Error during sorting, applying default sort (name, pk). Error: {e}")


    # --- Logika Paginacji ---
    products_per_page = 9

    paginator = Paginator(product_list, products_per_page)

    page_number = request.GET.get('page')

    try:
        products_page = paginator.get_page(page_number)
        print(f"Total items for pagination: {paginator.count}")
        print(f"Total pages: {paginator.num_pages}")
        print(f"Products on current page ({products_page.number}): {len(products_page.object_list) if hasattr(products_page, 'object_list') else 'N/A'}")
    except PageNotInteger:
        products_page = paginator.get_page(1)
        print("Invalid page number, getting page 1.")
    except EmptyPage:
        products_page = paginator.get_page(paginator.num_pages)
        print("Empty page requested, getting last page.")
    except Exception as e:
         print(f"Unexpected error during pagination: {e}")
         from django.core.paginator import Page
         products_page = Page([], 1, paginator)
         print("Unexpected pagination error, providing empty page.")


    context = {
        'material': material,
        'products_page': products_page,
        'current_sorting': sort_by,
        'request': request,

        'all_materials': all_materials,
        'selected_gender': selected_gender,
        'selected_min_price': selected_min_price,
        'selected_max_price': selected_max_price,
        'selected_materials': [], # Na tej stronie nie filtrujemy po wielu materiałach z sidebar
        'selected_sale_only': selected_sale_only,
    }

    print(f"Context keys: {context.keys()}")
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
# Załóżmy, że Twoja funkcja widoku nazywa się category_detail
# Przyjmuje slug kategorii jako argument, np. /category/electronics/
