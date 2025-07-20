from django import forms
from .models import ShippingAddress

class CheckoutForm(forms.Form):
    first_name = forms.CharField(label="Imię", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Nazwisko", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label="Adres e-mail", required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(label="Numer telefonu", max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    address1 = forms.CharField(label="Ulica i numer domu", max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address2 = forms.CharField(label="Numer mieszkania (opcjonalnie)", max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    city = forms.CharField(label="Miasto", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    zipcode = forms.CharField(label="Kod pocztowy", max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    country = forms.CharField(label="Kraj", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'value': 'Polska'}))

# Formularz dla opcjonalnego, innego adresu dostawy
# Używa prefiksu 'shipping_', aby uniknąć konfliktów nazw pól
class ShippingForm(forms.Form):
    shipping_first_name = forms.CharField(label="Imię", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_last_name = forms.CharField(label="Nazwisko", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_address1 = forms.CharField(label="Ulica i numer domu", max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_address2 = forms.CharField(label="Numer mieszkania (opcjonalnie)", max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_city = forms.CharField(label="Miasto", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_zipcode = forms.CharField(label="Kod pocztowy", max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipping_country = forms.CharField(label="Kraj", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'value': 'Polska'}))
		
class PaymentForm(forms.Form):
	card_name =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Name On Card'}), required=True)
	card_number =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Card Number'}), required=True)
	card_exp_date =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Expiration Date'}), required=True)
	card_cvv_number =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'CVV Code'}), required=True)
	card_address1 =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Billing Address 1'}), required=True)
	card_address2 =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Billing Address 2'}), required=False)
	card_city =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Billing City'}), required=True)
	card_state = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Billing State'}), required=True)
	card_zipcode =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Billing Zipcode'}), required=True)
	card_country =  forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Billing Country'}), required=True)