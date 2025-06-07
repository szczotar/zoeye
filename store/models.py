from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# Create Customer Profile

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modified = models.DateTimeField(User, auto_now=True)
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
    
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(default=0, decimal_places=2, max_digits=6)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
    description = models.CharField(max_length=2500, default='', blank=True, null = True)
    # image = models.ImageField(upload_to='uploads/product/')

    #Add Sale stuff
    is_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(default=0, decimal_places=2, max_digits=6)

    def __str__(self):
        return self.name
    
    def get_main_image(self):
        # Zakładając, że pole 'order' = 0 oznacza zdjęcie główne
        main_image = self.images.filter(order=0).first()
        if main_image:
            return main_image.image.url
        # Możesz zwrócić URL do domyślnego obrazka, jeśli brak zdjęć
        # return '/static/path/to/default/image.png'
        return None  
      
class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE, # Jeśli produkt zostanie usunięty, usuń też powiązane zdjęcia
        related_name='images'     # Nazwa, której użyjesz do dostępu do zdjęć z obiektu produktu (np. product.images.all())
    )

    image = models.ImageField(upload_to='product_images/') # Ścieżka do przechowywania zdjęć (wewnątrz MEDIA_ROOT)
    alt_text = models.CharField(max_length=255, blank=True) # Tekst alternatywny dla obrazka (SEO, dostępność)
    order = models.PositiveIntegerField(default=0) # Numer porządkowy zdjęcia (0 może oznaczać główne)

    class Meta:
        # Ustawia domyślne sortowanie zdjęć po polu 'order'
        ordering = ['order']
        # Dodatkowe ograniczenie (opcjonalnie): upewnij się, że dany produkt nie ma dwóch zdjęć z tym samym numerem porządkowym
        # unique_together = ('product', 'order')

    def __str__(self):
        return f"Image for {self.product.name} (Order: {self.order})"
    
    
class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    address = models.CharField(max_length=150, default='', blank=True)
    phone = models.CharField(max_length=20, default='', blank = True)
    date = models.DateField(default=datetime.datetime.today)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.product