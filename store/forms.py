from django.contrib.auth.models import User  
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from django import forms
from .models import Profile

class UserBaseInfoForm(forms.ModelForm):
    """Formularz do edycji imienia i nazwiska."""
    first_name = forms.CharField(required=True, label="Imię", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, label="Nazwisko", widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name')

class UserProfileForm(forms.ModelForm):
    """Formularz do edycji danych z profilu (tylko telefon)."""
    class Meta:
        model = Profile
        fields = ('phone',)
        labels = {
            'phone': 'Numer telefonu',
        }
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UserEmailForm(forms.ModelForm):
    """Formularz do edycji adresu e-mail."""
    email = forms.EmailField(required=True, label="Adres e-mail", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('email',)

class ChangePasswordForm(SetPasswordForm):
	class Meta:
		model = User
		fields = ['new_password1', 'new_password2']

	def __init__(self, *args, **kwargs):
		super(ChangePasswordForm, self).__init__(*args, **kwargs)

		self.fields['new_password1'].widget.attrs['class'] = 'form-control'
		self.fields['new_password1'].widget.attrs['placeholder'] = 'Hasło'
		self.fields['new_password1'].label = ''
		self.fields['new_password1'].help_text = '<ul class="form-text text-muted" style="text-align: left;"><li><small>Twoje hasło nie może być zbyt podobne do innych Twoich danych osobowych.</small></li><li><small>Twoje hasło musi zawierać co najmniej 8 znaków.</small></li><li><small>Twoje hasło nie może być powszechnie używanym hasłem.</small></li><li><small>Twoje hasło nie może składać się wyłącznie z cyfr.</small></li></ul>'

		self.fields['new_password2'].widget.attrs['class'] = 'form-control'
		self.fields['new_password2'].widget.attrs['placeholder'] = 'Potwierdź hasło'
		self.fields['new_password2'].label = ''
		self.fields['new_password2'].help_text = '<span class="form-text text-muted"><small>W celu weryfikacji wprowadź to samo hasło co poprzednio.</small></span>'


class UpdateUserForm(UserChangeForm):
	# Hide Password stuff
	password = None
	# Get other fields
	email = forms.EmailField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Email'}))
	first_name = forms.CharField(label="", max_length=100, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Imię'}))
	last_name = forms.CharField(label="", max_length=100, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Nazwisko'}))

	class Meta:
		model = User
		fields = ('username', 'first_name', 'last_name', 'email')

	def __init__(self, *args, **kwargs):
		super(UpdateUserForm, self).__init__(*args, **kwargs)

		self.fields['username'].widget.attrs['class'] = 'form-control'
		self.fields['username'].widget.attrs['placeholder'] = 'User Name'
		self.fields['username'].label = ''
		self.fields['username'].help_text = '<span class="form-text text-muted"><small>Wymagane. Maksymalnie 150 znaków. Tylko litery, cyfry i @/./+/-/_.</small></span>'
              
 
class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="", widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Email'}))
    first_name = forms.CharField(label="", max_length=100, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Imię'}))
    last_name = forms.CharField(label="", max_length=100, widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'Nazwisko'}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


    def __init__(self, *args, **kwargs):
            super(SignUpForm, self).__init__(*args, **kwargs)
            self.fields['username'].widget.attrs['class'] = 'form-control'
            self.fields['username'].widget.attrs['placeholder'] = 'Użytkownik'
            self.fields['username'].label = ''
            self.fields['username'].help_text = '<span class="form-text text-muted"><small>Wymagane. Maksymalnie 150 znaków. Tylko litery, cyfry i @/./+/-/_.</small></span>'

            self.fields['password1'].widget.attrs['class'] = 'form-control'
            self.fields['password1'].widget.attrs['placeholder'] = 'Hasło'
            self.fields['password1'].label = ''
            self.fields['password1'].help_text = '<ul class="form-text text-muted" style="text-align: left;"><li><small>Twoje hasło nie może być zbyt podobne do innych Twoich danych osobowych.</small></li><li><small>Twoje hasło musi zawierać co najmniej 8 znaków.</small></li><li><small>Twoje hasło nie może być powszechnie używanym hasłem.</small></li><li><small>Twoje hasło nie może składać się wyłącznie z cyfr.</small></li></ul>'
            self.fields['password2'].widget.attrs['class'] = 'form-control'
            self.fields['password2'].widget.attrs['placeholder'] = 'Potwierdź hasło'
            self.fields['password2'].label = ''
            self.fields['password2'].help_text = '<span class="form-text text-muted"><small>W celu weryfikacji wprowadź to samo hasło co poprzednio.</small></span>'
