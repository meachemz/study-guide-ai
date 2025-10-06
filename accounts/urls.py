from django.urls import path,include
from . import views

app_name = 'accounts'  
urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

]