from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Case, When, DecimalField, Avg, Count, Min, Max
from django.http import HttpResponseRedirect
from django.urls import reverse
import json

# Importy modeli z bieżącej aplikacji
from .models import Product, Category, Profile, Material, ProductVariation, Review
# Importy formularzy z bieżącej aplikacji
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm

# Importy z innych aplikacji
from cart.cart import Cart
from payment.forms import ShippingForm
from payment.models import ShippingAddress, Order, OrderItem

# --- Widoki publiczne i związane z produktami ---

def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'home.html', {'products': products, 'categories': categories})

def about(request):
    return render(request, 'about.html', {})

def search(request):
    if request.method == "POST":
        searched = request.POST.get('searched', '')
        if not searched:
            messages.info(request, "Proszę wpisać frazę do wyszukania.")
            return render(request, "search.html", {})
            
        products = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
        
        if not products.exists():
            messages.success(request, "Nie znaleziono produktów pasujących do zapytania.")
            return render(request, "search.html", {})
        else:
            return render(request, "search.html", {'searched': products})
    else:
        return render(request, "search.html", {})

def product(request, pk):
    product_obj = get_object_or_404(Product, pk=pk)
    variations = product_obj.variations.all().order_by('size')
    
    # Recenzje i oceny
    all_reviews = product_obj.reviews.all().order_by('-created_at')
    paginator = Paginator(all_reviews, 5)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)
    
    reviews_with_rating = all_reviews.filter(rating__isnull=False)
    average_rating_agg = reviews_with_rating.aggregate(Avg('rating'))
    average_rating = round(average_rating_agg['rating__avg'], 1) if average_rating_agg['rating__avg'] is not None else None
    rating_count = reviews_with_rating.count()
    
    rating_distribution = reviews_with_rating.values('rating').annotate(count=Count('rating')).order_by('rating')
    rating_distribution_dict = {item['rating']: item['count'] for item in rating_distribution}
    full_rating_distribution = {i: rating_distribution_dict.get(i, 0) for i in range(1, 6)}

    # Podobne produkty
    product_materials = product_obj.materials.all()
    similar_products = Product.objects.none()
    if product_materials.exists():
        material_q_objects = Q()
        for material in product_materials:
            material_q_objects |= Q(materials=material)
        similar_products = Product.objects.filter(material_q_objects).distinct().exclude(pk=product_obj.pk)[:6]

    context = {
        'product': product_obj,
        'variations': variations,
        'similar_products': similar_products,
        'reviews_page': reviews_page,
        'average_rating': average_rating,
        'rating_count': rating_count,
        'rating_distribution': full_rating_distribution,
        'rating_values': range(5, 0, -1),
    }
    return render(request, 'product.html', context)

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

def categories_all(request):
    categories = Category.objects.all()
    return render(request, 'cat.html', {'categories': categories})

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

def add_review(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        rating_str = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not comment:
            messages.error(request, "Komentarz nie może być pusty.")
            return HttpResponseRedirect(reverse('product', args=[product.id]))

        rating = None
        if rating_str:
            try:
                rating = int(rating_str)
                if not (1 <= rating <= 5):
                    raise ValueError()
            except ValueError:
                messages.error(request, "Nieprawidłowa wartość oceny.")
                return HttpResponseRedirect(reverse('product', args=[product.id]))

        Review.objects.create(
            product=product,
            comment=comment,
            rating=rating,
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(request, "Twoja recenzja została dodana.")
        return HttpResponseRedirect(reverse('product', args=[product.id]))
    
    return redirect('home')

def get_reviews_page(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    all_reviews = product.reviews.all().order_by('-created_at')
    paginator = Paginator(all_reviews, 5)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)
    return render(request, 'partials/reviews_section.html', {'reviews_page': reviews_page, 'product': product})

# --- Widoki związane z uwierzytelnianiem ---

def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Logika ładowania koszyka z profilu
            cart = Cart(request) # To wywoła _load_from_db w __init__
            messages.success(request, "Zostałeś pomyślnie zalogowany!")
            
            # Przekieruj na poprzednią stronę lub na stronę główną
            next_page = request.GET.get('next')
            if next_page:
                return redirect(next_page)
            return redirect('home')
        else:
            messages.error(request, "Nieprawidłowa nazwa użytkownika lub hasło.")
            return redirect('login')
    else:
        return render(request, 'login.html', {})

def Logout_user(request):
    logout(request)
    messages.success(request, "Zostałeś pomyślnie wylogowany.")
    return redirect('home')

def register_user(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Konto zostało utworzone! Uzupełnij swoje dane poniżej.")
            return redirect("update_info")
        else:
            # Przekaż błędy do szablonu, zamiast tylko komunikatu
            return render(request, 'register.html', {'form': form})
    else:
        form = SignUpForm()
        return render(request, 'register.html', {'form': form})

# --- NOWE, SKONSOLIDOWANE WIDOKI PANELU KLIENTA ---

@login_required
def account_dashboard(request):
    """Główny widok panelu klienta."""
    return render(request, 'account_dashboard.html', {})

@login_required
def order_history(request):
    """Wyświetla historię zamówień zalogowanego użytkownika."""
    orders = Order.objects.filter(user=request.user).order_by('-date_ordered')
    return render(request, 'order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    """Wyświetla szczegóły konkretnego zamówienia użytkownika."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'order_detail.html', {'order': order, 'items': items})

@login_required
def update_info(request):
    """
    Obsługuje aktualizację danych profilu (UserInfoForm) i adresu wysyłki (ShippingForm).
    """
    profile = get_object_or_404(Profile, user=request.user)
    shipping_address, created = ShippingAddress.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Sprawdzamy, który formularz został wysłany, na podstawie nazwy przycisku submit
        if 'update_profile_submit' in request.POST:
            form = UserInfoForm(request.POST, instance=profile)
            shipping_form = ShippingForm(request.POST, instance=shipping_address)
            if form.is_valid() and shipping_form.is_valid():
                form.save()
                shipping_form.save()
                messages.success(request, "Twoje dane zostały zaktualizowane!")
                return redirect('update_info')
        else:
            # Jeśli nie jest to submit profilu, to musi być to formularz hasła,
            # ale jego obsługa jest w `update_password`. Tutaj po prostu tworzymy puste formularze.
            form = UserInfoForm(instance=profile)
            shipping_form = ShippingForm(instance=shipping_address)
    else:
        form = UserInfoForm(instance=profile)
        shipping_form = ShippingForm(instance=shipping_address)

    # Zawsze przekazujemy też pusty formularz zmiany hasła do szablonu
    password_form = ChangePasswordForm(request.user)

    context = {
        'form': form,
        'shipping_form': shipping_form,
        'password_form': password_form
    }
    return render(request, "update_info.html", context)


@login_required
def update_password(request):
    """
    Obsługuje tylko logikę zmiany hasła.
    """
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Ważne, aby nie wylogować użytkownika!
            messages.success(request, "Twoje hasło zostało pomyślnie zmienione.")
            return redirect('update_info')
        else:
            # Przekaż błędy formularza hasła z powrotem do widoku `update_info`
            # To jest bardziej złożone, więc na razie użyjemy komunikatów flash
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
            return redirect('update_info')
    
    # Jeśli metoda to GET, po prostu przekieruj, bo formularz jest na stronie `update_info`
    return redirect('update_info')