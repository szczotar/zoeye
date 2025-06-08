from django.shortcuts import render, redirect,  get_object_or_404
from .models import Product, Category, Profile
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


def category(request, foo): # Nazwa funkcji i argument 'foo' muszą pasować do urls.py
    """
    Widok wyświetlający szczegóły kategorii i listę produktów z paginacją i sortowaniem.
    Argument 'foo' przyjmuje nazwę kategorii z URL.
    """
    # --- Pobierz Kategorię ---
    # Pobieramy kategorię po polu 'name', bo Twój URL pattern używa nazwy (<str:foo>)
    category = get_object_or_404(Category, name=foo)

    # --- Pobierz Produkty dla Kategorii ---
    # Używamy Product.objects.filter(category=category), gdzie 'category' to nazwa pola ForeignKey w Twoim modelu Product
    product_list = Product.objects.filter(category=category)

    # --- DODAJ ADNOTACJĘ DLA EFEKTYWNEJ CENY ---
    # Tworzymy tymczasowe pole 'effective_price', które będzie używane do sortowania.
    # Jeśli is_sale jest True, effective_price = sale_price, w przeciwnym razie effective_price = price.
    # Używamy DecimalField, aby upewnić się, że sortowanie będzie liczbowe.
    product_list = product_list.annotate(
        effective_price=Case(
            When(is_sale=True, then='sale_price'), # Gdy is_sale jest True, użyj sale_price
            default='price',                       # W przeciwnym razie (gdy is_sale jest False), użyj price
            output_field=DecimalField()            # Zapewnij, że wynikiem jest Decimal
        )
    )

    # --- Logika Sortowania ---
    # Pobierz parametr sortowania z zapytania GET (np. ?sorting=low-high)
    sort_by = request.GET.get('sorting', 'default') # Domyślnie 'default'

    try:
        if sort_by == 'low-high':
            # Sortuj rosnąco po nowym polu 'effective_price'
            product_list = product_list.order_by('effective_price')
        elif sort_by == 'high-low':
            # Sortuj malejąco po nowym polu 'effective_price'
            product_list = product_list.order_by('-effective_price')
        elif sort_by == 'popularity':
             # Sortowanie "popularność" nie ma dedykowanego pola w modelu.
             # Można zastosować inne domyślne sortowanie, np. po nazwie.
             # Jeśli masz pole 'sales_count' lub podobne, użyj go tutaj:
             # product_list = product_list.order_by('-sales_count')
             product_list = product_list.order_by('name') # Przykład domyślnego sortowania
        else: # 'default' lub jakakolwiek inna wartość
             # Domyślne sortowanie (np. po nazwie)
             product_list = product_list.order_by('name') # Użyj pola, które chcesz jako domyślne

    except Exception:
        # W przypadku błędu sortowania, zastosuj sortowanie domyślne
        product_list = product_list.order_by('name')


    # --- Logika Paginacji ---
    # Określ, ile produktów ma być na stronie (dopasuj do swojego szablonu)
    products_per_page = 9 # lub 12, w zależności od układu kolumn

    paginator = Paginator(product_list, products_per_page)

    # Pobierz numer strony z zapytania GET (np. ?page=2)
    page_number = request.GET.get('page')

    # Pobierz obiekt Page dla żądanego numeru strony
    try:
        products_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        # Jeśli numer strony nie jest liczbą, pokaż pierwszą stronę
        products_page = paginator.get_page(1)
    except EmptyPage:
        # Jeśli strona jest poza zakresem, pokaż ostatnią stronę
        products_page = paginator.get_page(paginator.num_pages)

    # Przygotuj kontekst do przekazania do szablonu
    context = {
        'category': category,           # Obiekt Category
        'products_page': products_page, # Obiekt Page z produktami na bieżącej stronie
        'current_sorting': sort_by,     # Aktualnie wybrane sortowanie (dla zaznaczenia w dropdownie)
        'request': request,             # Przekazujemy obiekt request, aby w szablonie odtworzyć inne parametry GET w linkach paginacji
    }

    # Renderuj szablon category.html
    return render(request, 'category.html', context)

def categories_all(request):
    # Fetch all categories
	categories = Category.objects.all()
	return render(request, 'cat.html', {'categories': categories})


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
