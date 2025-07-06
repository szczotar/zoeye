from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.models import Case, When, DecimalField, Sum # Dodaj Sum do agregacji stocku

# Create Customer Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modified = models.DateTimeField(auto_now=True)
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
    price = models.DecimalField(default=0, decimal_places=2, max_digits=6) # Cena bazowa
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
    description = models.CharField(max_length=2500, default='', blank=True, null = True)

    # Add Sale stuff
    is_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(default=0, decimal_places=2, max_digits=6)

    # --- NOWE POLE STOCK DLA PRODUKTÓW BEZ WARIAcji ---
    stock = models.PositiveIntegerField(default=0)
    # --------------------------------------------------

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
        # Zwraca cenę wyprzedażową produktu bazowego jeśli jest na wyprzedaży, w przeciwnym razie normalną cenę
        if self.is_sale:
            return self.sale_price
        return self.price

    def has_variations(self):
        # Metoda pomocnicza do sprawdzenia, czy produkt ma wariacje (WIĘCEJ NIŻ JEDNĄ lub JEDNĄ z ustawionym rozmiarem?)
        # Lepsze sprawdzenie: czy ma wariacje, które powinny być wyświetlone jako opcje wyboru?
        # Zakładamy, że produkt z wariacjami to taki, który ma powiązane obiekty ProductVariation.
        # Produkt bez wariacji to taki, który nie ma żadnych powiązanych ProductVariation.
        return self.variations.exists()

    # Metoda do sprawdzenia, czy produkt ma WIELE wariacji (więcej niż 1), co sugeruje potrzebę dropdownu
    def has_multiple_variations(self):
         return self.variations.count() > 1


    # Metoda do sprawdzenia, czy produkt jest dostępny (sumując stock wariacji lub sprawdzając stock produktu bazowego)
    def is_available(self):
        if self.has_variations():
            # Jeśli produkt ma wariacje, jest dostępny jeśli *jakakolwiek* wariacja ma stock > 0
            # Możesz też chcieć sprawdzić sumę stocku:
            # total_stock = self.variations.aggregate(Sum('stock'))['stock__sum'] or 0
            # return total_stock > 0
            # Ale Twoje wymaganie "dostępne" w filtrze sugeruje, że wystarczy, że choć jedna wariacja jest dostępna.
            # Sprawdzamy, czy istnieje wariacja ze stock > 0
            return self.variations.filter(stock__gt=0).exists()
        else:
            # Jeśli produkt nie ma wariacji, jego dostępność zależy od jego własnego pola stock
            return self.stock > 0


    # Metoda do zwracania ceny dla wyświetlenia na liście (zawsze cena produktu bazowego)
    # Zmieniamy jej logikę, bo wszystkie wariacje mają tę samą cenę
    def get_display_price(self):
        # Na liście produktów zawsze pokazujemy cenę bazową produktu (uwzględniając wyprzedaż)
        return self.get_effective_price()

    # Metoda get_min_variation_price jest teraz redundantna, jeśli wszystkie wariacje mają tę samą cenę.
    # Możemy ją uprościć lub usunąć, jeśli nigdzie nie jest używana do logicznego wyboru ceny, a tylko do wyświetlenia.
    # Jeśli jednak jest używana w adnotacjach w widoku, musimy ją zachować, ale uprościć.
    # Uproszczona wersja zakłada, że cena wariacji jest zawsze taka sama jak cena produktu bazowego.
    def get_min_variation_price(self):
         # Zwraca efektywną cenę produktu bazowego
        return self.get_effective_price()


    def __str__(self):
        return self.name

# --- NOWY MODEL DLA WARIAcji PRODUKTU ---
class ProductVariation(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variations'
    )
    # size może być pusty dla wariacji reprezentującej produkt jednowariantowy (choć lepiej używać stock na Product)
    # Zmieniamy null=True na False, bo pusty CharField powinien być pustym stringiem
    size = models.CharField(max_length=50, help_text="Np. 17cm, 18cm, S, M, L", blank=True, null=False)

    # --- USUŃ POLA CEN Z WARIAcji ---
    # price = models.DecimalField(...) # Usunięte
    # is_sale = models.BooleanField(...) # Usunięte
    # sale_price = models.DecimalField(...) # Usunięte
    # ---------------------------------

    # Stan magazynowy (ważne dla wariacji!) - POZOSTAJE
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        # Upewnij się, że nie ma dwóch wariacji z tym samym rozmiarem (lub pustym rozmiarem) dla tego samego produktu
        # Unique_together z pustym/null polem może działać różnie w zależności od bazy danych.
        # Jeśli produkt bez wariacji ma jedną wariację z pustym rozmiarem, upewnij się, że tylko jedna taka istnieje.
        unique_together = ('product', 'size')
        ordering = ['size'] # Sortuj wariacje np. po rozmiarze

    def __str__(self):
        # Ładna reprezentacja wariacji
        # Użyjemy 'Brak rozmiaru' lub podobnie, jeśli size jest pusty
        display_size = self.size if self.size else 'Brak rozmiaru'
        return f"{self.product.name} - {display_size}"

    # Metoda get_effective_price wariacji jest teraz bardzo prosta
    def get_effective_price(self):
        # Wariacja zawsze dziedziczy cenę od produktu bazowego
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
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, null=True, blank=True) # Dodano null/blank=True na wypadek usunięcia wariacji
    # Alternatywnie, jeśli chcesz zamawiać produkty bez wariacji bezpośrednio:
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True) # Dodaj pole Product
    # Musisz upewnić się, że albo variation, albo product jest ustawione, ale nie oba.
    # Możesz dodać clean() metodę do modelu, aby to sprawdzić.

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    address = models.CharField(max_length=150, default='', blank=True)
    phone = models.CharField(max_length=20, default='', blank = True)
    date = models.DateField(default=datetime.datetime.today)
    status = models.BooleanField(default=False) # Czy zamówienie zostało zrealizowane?

    def __str__(self):
        # Zwracaj reprezentację wariacji lub produktu
        if self.variation:
            return f"Order for {self.variation.__str__()} (x{self.quantity})"
        elif self.product:
             return f"Order for {self.product.name} (x{self.quantity})"
        return f"Order (ID: {self.pk})" # Fallback

    # Dodaj metodę clean, aby upewnić się, że tylko jedno z pól (variation lub product) jest ustawione
    def clean(self):
        if self.variation and self.product:
            from django.core.exceptions import ValidationError
            raise ValidationError("Zamówienie musi dotyczyć albo wariacji, albo produktu, ale nie obu.")
        if not self.variation and not self.product:
             from django.core.exceptions import ValidationError
             raise ValidationError("Zamówienie musi dotyczyć wariacji lub produktu.")