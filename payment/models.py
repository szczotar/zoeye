
from django.db import models
from django.contrib.auth.models import User
from store.models import Product, ProductVariation
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver 
import datetime
from django.conf import settings
from django.templatetags.static import static
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.db.models.signals import post_save, pre_save
# --- Funkcja pomocnicza do generowania numeru zamówienia ---
def generate_order_number():
    """
    Generuje unikalny, 12-cyfrowy numer zamówienia w formacie 00RRMMDDXXXX.
    """
    today = datetime.date.today()
    date_prefix = f"00{today.strftime('%y%m%d')}" # Format: 00RRMMDD

    # Znajdź ostatnie zamówienie z dzisiaj, aby określić następny numer sekwencyjny
    last_order = Order.objects.filter(order_number__startswith=date_prefix).order_by('order_number').last()

    if last_order and last_order.order_number:
        try:
            last_seq_num = int(last_order.order_number[-4:])
            new_seq_num = last_seq_num + 1
        except (ValueError, IndexError):
            new_seq_num = 1 # W razie problemu z formatem, zacznij od 1
    else:
        new_seq_num = 1
    
    new_seq_str = f"{new_seq_num:04d}"

    if len(new_seq_str) > 4:
        raise ValueError("Przekroczono limit zamówień na dzisiaj.")

    return f"{date_prefix}{new_seq_str}"


# --- Modele ---

class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    shipping_full_name = models.CharField(max_length=255)
    shipping_email = models.CharField(max_length=255)
    shipping_address1 = models.CharField(max_length=255)
    shipping_address2 = models.CharField(max_length=255, null=True, blank=True)
    shipping_city = models.CharField(max_length=255)
    shipping_state = models.CharField(max_length=255, null=True, blank=True)
    shipping_zipcode = models.CharField(max_length=255, null=True, blank=True)
    shipping_country = models.CharField(max_length=255)

    # === NOWE POLA ===
    default_billing = models.BooleanField(default=False)
    default_shipping = models.BooleanField(default=False)
    # =================

    class Meta:
        verbose_name_plural = "Shipping Address"

    def __str__(self):
        return f'Shipping Address for {self.user.username}'

    def save(self, *args, **kwargs):
        """
        Nadpisana metoda save, aby zapewnić, że tylko jeden adres
        może być domyślnym adresem rozliczeniowym/wysyłkowym.
        """
        # Jeśli ten adres jest ustawiany jako domyślny wysyłkowy...
        if self.default_shipping:
            # ...znajdź wszystkie INNE adresy tego użytkownika i odznacz je.
            # exclude(pk=self.pk) jest kluczowe, aby nie odznaczyć samego siebie.
            ShippingAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(default_shipping=False)

        # Ta sama logika dla adresu rozliczeniowego
        if self.default_billing:
            ShippingAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(default_billing=False)
        
        # Wywołaj oryginalną metodę save
        super(ShippingAddress, self).save(*args, **kwargs)


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
	# Ostateczna, poprawna definicja pola
    order_number = models.CharField(max_length=12, unique=True, editable=False) 
    full_name = models.CharField(max_length=250)
    email = models.EmailField(max_length=250)
    shipping_address = models.TextField(max_length=15000)
    amount_paid = models.DecimalField(max_digits=7, decimal_places=2)
    date_ordered = models.DateTimeField(auto_now_add=True)	
    shipped = models.BooleanField(default=False)
    date_shipped = models.DateTimeField(blank=True, null=True)
    payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f'Order - {self.order_number}'

class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
	product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
	variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, null=True, blank=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
	quantity = models.PositiveBigIntegerField(default=1)
	price = models.DecimalField(max_digits=7, decimal_places=2)

	def __str__(self):
		if self.variation:
			return f'Item: {self.variation.product.name} ({self.variation.size})'
		elif self.product:
			return f'Item: {self.product.name}'
		return f'Order Item - {str(self.id)}'

# --- Sygnały ---

def create_shipping(sender, instance, created, **kwargs):
	if created:
		user_shipping = ShippingAddress(user=instance)
		user_shipping.save()

post_save.connect(create_shipping, sender=User)

@receiver(pre_save, sender=Order)
def set_order_details_on_save(sender, instance, **kwargs):
    # Przypisz numer tylko wtedy, gdy tworzone jest nowe zamówienie
    if not instance.pk:
        instance.order_number = generate_order_number()

    # Ustaw datę wysyłki, jeśli status się zmienia
    if instance.pk:
        try:
            obj = sender._default_manager.get(pk=instance.pk)
            if instance.shipped and not obj.shipped:
                instance.date_shipped = datetime.datetime.now()
        except sender.DoesNotExist:
            pass

@receiver(pre_save, sender=Order)
def before_order_save(sender, instance, **kwargs):
    """
    Logika wykonywana tuż PRZED zapisaniem obiektu Order.
    1. Przypisuje numer zamówienia dla nowych obiektów.
    2. Sprawdza zmianę statusu 'shipped' i wysyła e-mail.
    3. Ustawia datę wysyłki.
    """
    # 1. Przypisz numer zamówienia, jeśli to nowy obiekt
    if not instance.pk:
        instance.order_number = generate_order_number()
        return # Zakończ, nie ma sensu sprawdzać statusu wysyłki dla nowego zamówienia

    # 2. Sprawdź zmianę statusu i wyślij e-mail (tylko dla istniejących obiektów)
    try:
        # Pobierz stan obiektu prosto z bazy danych (stan PRZED zapisem)
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return # Obiekt jeszcze nie istnieje, nic nie rób

    # Sprawdź, czy status 'shipped' zmienił się z False na True
    if instance.shipped and not old_instance.shipped:
        # 3. Ustaw datę wysyłki
        instance.date_shipped = datetime.datetime.now()
        
        # Wyślij e-mail z powiadomieniem
        print(f"WARUNEK SPEŁNIONY: Wysyłanie e-maila o wysyłce do {instance.email}...")
        try:
            subject = f"Twoje zamówienie nr {instance.order_number} zostało wysłane!"
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = instance.email
            logo_url = settings.SITE_URL + static('images/logo.png')
            context = {'order': instance, 'logo_url': logo_url}
            html_template = get_template('emails/shipping_notification.html')
            html_content = html_template.render(context)
            text_content = f"Witaj {instance.full_name},\n\nTwoje zamówienie o numerze {instance.order_number} zostało wysłane."

            msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            print("E-MAIL O WYSYŁCE POMYŚLNIE PRZEKAZANY DO WYSŁANIA!")
        except Exception as e:
            print(f"BŁĄD KRYTYCZNY PODCZAS WYSYŁANIA E-MAILA O WYSYŁCE: {e}")
