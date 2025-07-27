
from django.urls import path
from . import views

urlpatterns = [
    path('payment_success', views.payment_success, name='payment_success'),
    path('checkout', views.checkout, name='checkout'),
    path('billing_info', views.billing_info, name="billing_info"),
    path('process_order', views.process_order, name="process_order"),
    path('shipped_dash', views.shipped_dash, name="shipped_dash"),
    path('not_shipped_dash', views.not_shipped_dash, name="not_shipped_dash"),
    path('orders/<int:pk>', views.orders, name='orders'),
    path('terms', views.terms_page, name='terms_page'),

    path('payment-success/', views.payment_success_stripe, name='payment_success_stripe'),
    path('payment-cancelled/', views.payment_cancelled, name='payment_cancelled'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),

]