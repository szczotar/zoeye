from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.models import Case, When, DecimalField # Upewnij się, że są zaimportowane

# Create Customer Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Zmień to poniżej, powinno być models.DateTimeField, a nie User
    date_modified = models.DateTimeField(auto_now=True) # Usunięto User z argumentów
    phone = models.CharField(max_length=20, blank=True)
    address1 = models.CharField(max_length=200, blank=True)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    old_cart = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.user.username

# Create a user Profile by default when user signs up
def create_profile(sender, instance, created, **kwargs):
    if created:
        user_profile = Profile(user=instance)
        user_profile.save()

# Automate the profile thing
post_save.connect(create_profile, sender=User)

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='uploads/category/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'categories'

class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=10)
    email = models.EmailField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class Material(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    GENDER_CHOICES = [
        ('unisex', 'Unisex'),
        ('women', 'Kobiety'),
        ('men', 'Mężczyźni'),
    ]

    name = models.CharField(max_length=100)
    price = models.DecimalField(default=0, decimal_places=2, max_digits=6) # Cena bazowa (może być nadpisana przez wariacje)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
    description = models.CharField(max_length=2500, default='', blank=True, null = True)

    # Add Sale stuff
    is_sale = models.BooleanField(default=False) # Czy produkt bazowy jest na wyprzedaży (można też dodać is_sale do wariacji)
    sale_price = models.DecimalField(default=0, decimal_places=2, max_digits=6) # Cena wyprzedażowa bazowa

    # --- POLA FILTRÓW ---
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unisex') # Filtr płci
    materials = models.ManyToManyField(Material, blank=True) # Filtr materiałów/kamieni
    # -------------------------

    def get_main_image(self):
        main_image = self.images.filter(order=0).first()
        if main_image:
            return main_image.image.url
        return None

    def get_effective_price(self):
        # Zwraca cenę wyprzedażową jeśli jest na wyprzedaży, w przeciwnym razie normalną cenę
        if self.is_sale:
            return self.sale_price
        return self.price

    def has_variations(self):
        # Metoda pomocnicza do sprawdzenia, czy produkt ma wariacje
        return self.variations.exists()

    def get_min_variation_price(self):
        # Zwraca najniższą cenę wariacji (uwzględniając wyprzedaż wariacji lub bazową cenę produktu)
        if self.has_variations():
            # Najpierw sprawdź cenę/wyprzedaż wariacji
            variations = self.variations.annotate(
                effective_var_price=Case(
                    When(is_sale=True, then='sale_price'), # Sprawdź wyprzedaż wariacji
                    When(price__isnull=False, then='price'), # Jeśli cena wariacji jest ustawiona
                    default=self.get_effective_price(), # Użyj efektywnej ceny produktu bazowego
                    output_field=DecimalField()
                )
            )
            min_price_variation = variations.order_by('effective_var_price').first()
            if min_price_variation:
                 return min_price_variation.effective_var_price
        # Jeśli nie ma wariacji lub nie ma dla nich cen, użyj ceny produktu bazowego
        return self.get_effective_price()


    def __str__(self):
        return self.name

# --- NOWY MODEL DLA WARIAcji PRODUKTU ---
class ProductVariation(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variations' # Użyjemy product.variations.all() aby dostać wariacje
    )
    size = models.CharField(max_length=50, help_text="Np. 17cm, 18cm, S, M, L") # Pole na rozmiar
    # Możesz dodać inne atrybuty wariacji, np:
    # color = models.CharField(max_length=50, blank=True)
    # material_variation = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)

    # Cena wariacji (opcjonalnie, może nadpisywać cenę produktu bazowego)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                help_text="Opcjonalnie. Nadpisuje cenę produktu bazowego. Zostaw puste, aby użyć ceny bazowej.")

    # Stan magazynowy (ważne dla wariacji!)
    stock = models.PositiveIntegerField(default=0)

    # Czy wariacja jest na wyprzedaży (opcjonalne, może nadpisywać is_sale/sale_price produktu bazowego)
    is_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                     help_text="Opcjonalnie. Cena wyprzedaży dla tej wariacji.")


    class Meta:
        # Upewnij się, że nie ma dwóch wariacji z tym samym rozmiarem dla tego samego produktu
        unique_together = ('product', 'size')
        # Możesz dodać sortowanie, np. po rozmiarze (jeśli są liczbowe)
        # ordering = ['size'] # Wymagałoby konwersji na typ liczbowy, jeśli '17cm' vs '18cm'

    def __str__(self):
        # Ładna reprezentacja wariacji
        return f"{self.product.name} - {self.size}" # Dodaj inne atrybuty jeśli są

    def get_effective_price(self):
        # Zwraca efektywną cenę wariacji: najpierw wyprzedaż wariacji, potem cena wariacji, na końcu cena produktu bazowego
        if self.is_sale and self.sale_price is not None:
            return self.sale_price
        elif self.price is not None:
            return self.price
        # Jeśli wariacja nie ma ustawionej ceny ani wyprzedaży, użyj ceny produktu bazowego
        return self.product.get_effective_price()


# ------------------------------------------

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='product_images/')
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.name} (Order: {self.order})"

# --- ZMIANA W MODELU ORDER ---
# Zamiast wskazywać na Product, wskazuje na ProductVariation
# Zakładając, że Twój model Order reprezentuje pojedynczy "item" w zamówieniu
class Order(models.Model):
    # ZMIANA: ForeignKey wskazuje na ProductVariation
    # Pamiętaj o potencjalnej migracji danych dla istniejących zamówień!
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    address = models.CharField(max_length=150, default='', blank=True)
    phone = models.CharField(max_length=20, default='', blank = True)
    date = models.DateField(default=datetime.datetime.today)
    status = models.BooleanField(default=False) # Czy zamówienie zostało zrealizowane?

    def __str__(self):
        # Zwracaj reprezentację wariacji, a nie produktu
        return f"Order for {self.variation.__str__()} (x{self.quantity})"
