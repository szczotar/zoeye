from django.shortcuts import render, redirect,  get_object_or_404
from .models import Product, Category, Profile, Material 
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
from django.db.models import Case, When
from django.db.models import Case, When, DecimalField

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
    # --- Pobierz Kategorię ---
    category = get_object_or_404(Category, name=foo)

    # --- Pobierz Wszystkie Materiały dla Sidebar ---
    all_materials = Material.objects.all().order_by('name')


    # --- Pobierz Produkty dla Kategorii ---
    # Zaczynamy od produktów w danej kategorii
    product_list = Product.objects.filter(category=category)


    # --- DODAJ ADNOTACJĘ DLA EFEKTYWNEJ CENY ---
    # Tworzymy tymczasowe pole 'effective_price' do sortowania
    product_list = product_list.annotate(
        effective_price=Case(
            When(is_sale=True, then='sale_price'),
            default='price',
            output_field=DecimalField()
        )
    )


    # --- Logika Filtrowania ---
    # Pobieramy wartości filtrów z request.GET
    selected_gender = request.GET.get('gender')
    selected_min_price = request.GET.get('min_price')
    selected_max_price = request.GET.get('max_price')
    selected_materials = request.GET.getlist('material') # Użyj getlist dla checkboxów
    selected_sale_only = request.GET.get('sale_only') == 'true' # <-- POBIERZ NOWY PARAMETR FILTRA

    print(f"Selected 'Gender': {selected_gender}")
    print(f"Selected 'Material': {selected_materials}")
    print(f"Price Min: {selected_min_price}, Price Max: {selected_max_price}")
    print(f"Sale Only: {selected_sale_only}") # <-- WYDRUK NOWEGO FILTRA
    print(f"Product list count before filtering: {product_list.count()}")


    # Zastosuj filtry na product_list PRZED sortowaniem i paginacją
    try:
        # Filtr płci (gender)
        if selected_gender and selected_gender != 'all':
            # Zakładamy, że w modelu Product masz pole 'gender'
            product_list = product_list.filter(gender=selected_gender)
            print(f"Applied Gender filter: {selected_gender}. Count: {product_list.count()}")
        elif selected_gender == 'all':
             print("Gender filter 'all' selected.")
             pass

        # Filtr ceny (min_price, max_price)
        if selected_min_price:
            try:
                min_price_float = float(selected_min_price)
                product_list = product_list.filter(effective_price__gte=min_price_float)
                print(f"Applied Min Price filter: {min_price_float}. Count: {product_list.count()}")
            except ValueError:
                print(f"Invalid min_price value: {selected_min_price}")
                pass
        if selected_max_price:
            try:
                max_price_float = float(selected_max_price)
                product_list = product_list.filter(effective_price__lte=max_price_float)
                print(f"Applied Max Price filter: {max_price_float}. Count: {product_list.count()}")
            except ValueError:
                 print(f"Invalid max_price value: {selected_max_price}")
                 pass

        # Filtr materiału (material)
        if selected_materials:
            material_q_objects = Q()
            for material_name in selected_materials:
                material_q_objects |= Q(materials__name=material_name) # Dostosuj 'materials__name' jeśli trzeba
            product_list = product_list.filter(material_q_objects).distinct()
            print(f"Applied Material filter: {selected_materials}. Count: {product_list.count()}")

        # --- ZASTOSUJ NOWY FILTR PROMOCJI ---
        if selected_sale_only:
            product_list = product_list.filter(is_sale=True)
            print(f"Applied Sale Only filter. Count: {product_list.count()}")

    except Exception as e:
        print(f"Error during filtering: {e}")
        pass

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
             # product_list = product_list.order_by('-sales_count', 'pk')
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
    except PageNotAnInteger:
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


    # Przygotuj kontekst
    context = {
        'category': category,
        'products_page': products_page,
        'current_sorting': sort_by,
        'request': request,

        'all_materials': all_materials,
        'selected_gender': selected_gender,
        'selected_min_price': selected_min_price,
        'selected_max_price': selected_max_price,
        'selected_materials': selected_materials,
        'selected_sale_only': selected_sale_only, # <-- DODAJ NOWY STAN FILTRA DO KONTEKSTU
    }

    print(f"Context keys: {context.keys()}")
    print(f"--- End category view ---")

    return render(request, 'category.html', context)


def categories_all(request):
    # Fetch all categories
	categories = Category.objects.all()
	return render(request, 'cat.html', {'categories': categories})

def stones_detail(request, material_name):
    """
    Widok wyświetlający szczegóły materiału (kamienia) i listę produktów z tym materiałem,
    z paginacją, sortowaniem i filtrami.
    Argument 'material_name' przyjmuje nazwę materiału z URL.
    """
    print(f"--- Debugging stones_detail view ---")
    print(f"Requested material name: {material_name}")

    # --- Pobierz Materiał ---
    # Pobieramy obiekt Material po polu 'name'
    try:
        material = get_object_or_404(Material, name=material_name)
        print(f"Material found: {material.name}")
    except Exception as e:
         print(f"Error getting material by name '{material_name}': {e}")
         raise # Zgłoś błąd 404


    # --- Pobierz Wszystkie Materiały dla Sidebar ---
    # TA LINIJKA MUSI BYĆ OBECNA I NIE SKOMENTOWANA
    all_materials = Material.objects.all().order_by('name')
    print(f"Fetched {all_materials.count()} materials for sidebar.")


    # --- Pobierz Produkty z Tym Materiałem ---
    # Zaczynamy od produktów, które mają ten konkretny materiał w relacji ManyToMany
    # Upewnij się, że 'materials' to poprawna nazwa pola ManyToMany w modelu Product
    try:
        product_list = Product.objects.filter(materials=material)
        print(f"Initial product list count for material '{material.name}': {product_list.count()}")
    except Exception as e:
         print(f"Error filtering products by material: {e}")
         product_list = Product.objects.none() # Zwróć pusty QuerySet w przypadku błędu


    # --- DODAJ ADNOTACJĘ DLA EFEKTYWNEJ CENY ---
    # Tworzymy tymczasowe pole 'effective_price' do sortowania
    product_list = product_list.annotate(
        effective_price=Case(
            When(is_sale=True, then='sale_price'),
            default='price',
            output_field=DecimalField()
        )
    )


    # --- Logika Filtrowania (Gender, Price, Sale) ---
    # Pobieramy wartości filtrów z request.GET
    selected_gender = request.GET.get('gender')
    selected_min_price = request.GET.get('min_price')
    selected_max_price = request.GET.get('max_price')
    selected_materials = request.GET.getlist('material') # <-- NIE POTRZEBUJEMY TEGO FILTRA TUTAJ
    selected_sale_only = request.GET.get('sale_only') == 'true'

    print(f"Selected 'Gender': {selected_gender}")
    print(f"Selected 'Material': {selected_materials}") # <-- NIE POTRZEBNE
    print(f"Price Min: {selected_min_price}, Price Max: {selected_max_price}")
    print(f"Sale Only: {selected_sale_only}")
    print(f"Product list count before filtering: {product_list.count()}")


    # Zastosuj filtry na product_list PRZED sortowaniem i paginacją
    try:
        # Filtr płci (gender)
        # Zakładamy, że w modelu Product masz pole 'gender'
        # i że przechowuje wartości 'men', 'women', 'unisex'
        if selected_gender and selected_gender != 'all':
            # Zakładamy, że w modelu Product masz pole 'gender'
            product_list = product_list.filter(gender=selected_gender)
            print(f"Applied Gender filter: {selected_gender}. Count: {product_list.count()}")
        elif selected_gender == 'all':
             print("Gender filter 'all' selected.")
             pass

        # Filtr ceny (min_price, max_price)
        if selected_min_price:
            try:
                min_price_float = float(selected_min_price)
                product_list = product_list.filter(effective_price__gte=min_price_float)
                print(f"Applied Min Price filter: {min_price_float}. Count: {product_list.count()}")
            except ValueError:
                print(f"Invalid min_price value: {selected_min_price}")
                pass
        if selected_max_price:
            try:
                max_price_float = float(selected_max_price)
                product_list = product_list.filter(effective_price__lte=max_price_float)
                print(f"Applied Max Price filter: {max_price_float}. Count: {product_list.count()}")
            except ValueError:
                 print(f"Invalid max_price value: {selected_max_price}")
                 pass

        # Filtr materiału (material) - NIE ZASTOSOWUJEMY TUTAJ FILTRU PO MATERIAŁACH Z SIDEBAR
        # Strona JUŻ jest przefiltrowana po jednym materiale.
        # if selected_materials:
        #     ... logika filtrowania po materialach ...
        #     pass


        # --- ZASTOSUJ FILTR PROMOCJI ---
        if selected_sale_only:
            product_list = product_list.filter(is_sale=True)
            print(f"Applied Sale Only filter. Count: {product_list.count()}")

    except Exception as e:
        print(f"Error during filtering: {e}")
        pass

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
             # product_list = product_list.order_by('-sales_count', 'pk')
             product_list = product_list.order_by('name', 'pk')
             print("Popularity sort selected, falling back to default (name, pk).")
        else: # 'default'
             product_list = product_list.order_by('name', 'pk')
             print("Sorted by default (name, pk).")

    except Exception as e:
        product_list = product_list.order_by('name', 'pk')
        print(f"Error during sorting, applying default sort (name, pk). Error: {e}")


    # --- Logika Paginacji ---
    products_per_page = 9 # Ustaw liczbę produktów na stronę

    paginator = Paginator(product_list, products_per_page)

    page_number = request.GET.get('page')

    try:
        products_page = paginator.get_page(page_number)
        print(f"Total items for pagination: {paginator.count}")
        print(f"Total pages: {paginator.num_pages}")
        print(f"Products on current page ({products_page.number}): {len(products_page.object_list) if hasattr(products_page, 'object_list') else 'N/A'}")
    except PageNotAnInteger:
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


    # Przygotuj kontekst
    context = {
        'material': material,           # <-- PRZEKAZUJEMY OBIEKT MATERIAL
        'products_page': products_page, # Obiekt Page z produktami na bieżącej stronie
        'current_sorting': sort_by,     # Aktualnie wybrane sortowanie
        'request': request,             # Nadal potrzebne do generowania URL-i w szablonie

        # --- DODAJ WARTOŚCI FILTRÓW DO KONTEKSTU (DLA SIDEBAR) ---
        'all_materials': all_materials, # Lista wszystkich obiektów Material (dla checkboxów w sidebar)
        'selected_gender': selected_gender, # Pojedyncza wartość ('men', 'women', 'unisex', 'all' lub None)
        'selected_min_price': selected_min_price, # Wartość min ceny (string lub None)
        'selected_max_price': selected_max_price, # Wartość max ceny (string lub None)
        'selected_materials': selected_materials, # Lista zaznaczonych nazw materiałów (dla checkboxów w sidebar)
        'selected_sale_only': selected_sale_only, # Stan filtra promocji
    }

    print(f"Context keys: {context.keys()}")
    print(f"--- End stones_detail view ---")

    # Renderuj nowy szablon stones.html
    return render(request, 'stones.html', context)

def product(request, pk):
    product = Product.objects.get(id=pk)
    return render(request, 'product.html', {'product': product})

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

# Załóżmy, że Twoja funkcja widoku nazywa się category_detail
# Przyjmuje slug kategorii jako argument, np. /category/electronics/
