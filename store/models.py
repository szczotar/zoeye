from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.models import Case, When, DecimalField, Sum # Dodaj Sum do agregacji stocku
from django.core.validators import MinValueValidator, MaxValueValidator 

# Create Customer Profile
class Profile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modified = models.DateTimeField(auto_now=True)
    phone = models.CharField(max_length=20, blank=True)
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

class Review(models.Model):
    """
    Model reprezentujący recenzję (komentarz z opcjonalną oceną) dla produktu.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews' # Umożliwi dostęp do recenzji produktu przez product.reviews.all()
    )
    # Powiązanie z użytkownikiem (opcjonalnie - jeśli tylko zalogowani mogą pisać recenzje)
    # Jeśli chcesz pozwolić niezarejestrowanym, rozważ pola CharField dla imienia/emaila
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # Co się stanie, gdy użytkownik zostanie usunięty? SET_NULL zachowa recenzję
        null=True, blank=True # Umożliwia recenzje od niezarejestrowanych (jeśli nie ma powiązania z User)
    )
    # Jeśli chcesz pozwolić niezarejestrowanym, dodaj pola:
    # name = models.CharField(max_length=100, blank=True)
    # email = models.EmailField(blank=True)

    comment = models.TextField() # Treść komentarza
    # Ocena (opcjonalna) - użyj IntegerField z walidatorami
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True # Umożliwia komentarze bez oceny
    )
    created_at = models.DateTimeField(auto_now_add=True) # Data utworzenia recenzji

    class Meta:
        ordering = ['-created_at'] # Sortuj recenzje od najnowszych

    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username if self.user else 'Anonymous'} ({self.rating}/5)"


class PageView(models.Model):
    path = models.CharField(max_length=255) # Ścieżka URL, np. '/product/5'
    timestamp = models.DateTimeField(auto_now_add=True) # Kiedy nastąpiła odsłona
    
    # Opcjonalnie, aby śledzić unikalnych użytkowników
    session_key = models.CharField(max_length=40, null=True, blank=True) # Klucz sesji dla gości
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL) # Zalogowany użytkownik

    def __str__(self):
        return f"View on {self.path} at {self.timestamp}"