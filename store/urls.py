"""
URL configuration for practice project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

urlpatterns = [
    # --- Główne ścieżki Twojej strony ---
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('search/', views.search, name='search'),
    
    # --- Ścieżki związane z produktami i kategoriami ---
    path('product/<int:pk>', views.product, name='product'),
    path('category/<str:foo>', views.category, name='category'),
    path('categories/', views.categories_all, name="categories_all"),
    path('stones/<str:material_name>/', views.stones_detail, name='stones_detail'),
    
    # --- Ścieżki związane z recenzjami ---
    path('product/<int:product_id>/add_review/', views.add_review, name='add_review'),
    path('product/<int:product_id>/reviews/', views.get_reviews_page, name='get_reviews_page'),

    # --- Ścieżki związane z uwierzytelnianiem ---
    path('login/', views.login_user, name='login'),
    path('logout/', views.Logout_user, name='logout'),
    path('register/', views.register_user, name='register'),

    # ===================================================================
    # === NOWE, SKONSOLIDOWANE URL-e DLA PANELU KLIENTA ===
    # ===================================================================
    
    # Główne widoki panelu
    path('account/', views.account_dashboard, name='account_dashboard'),
    path('account/orders/', views.order_history, name='order_history'),
    path('account/orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('account/my-data/', views.my_data_view, name='my_data'),
    path('account/addresses/', views.account_addresses, name='account_addresses'),
    
    # Ścieżki do przetwarzania formularzy (akcje POST)
    path('account/add-address/', views.add_address, name='add_address'),
    path('account/edit-address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('account/delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('account/update-personal-info/', views.update_personal_info, name='update_personal_info'),
    path('account/update-email/', views.update_email, name='update_email'),
    path('account/update_password/', views.update_password, name='update_password'),

    # STARE ŚCIEŻKI, KTÓRE ZOSTAŁY USUNIĘTE, PONIEWAŻ SĄ TERAZ CZĘŚCIĄ NOWEGO PANELU:
    # path('update_user/', views.update_user, name='update_user'),
    # path('update_info/', views.update_info, name='update_info'),
]