"""
URL configuration for config project.

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
# In your_project/urls.py


from django.contrib import admin
from django.urls import path, include
# Make sure to import the views from your quiz_app
from quiz_app import views as quiz_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # The main URL for your dashboard
    path('dashboard/', quiz_views.teacher_dashboard_view, name='teacher_dashboard'),

    # Include your other apps
    path('quiz/', include("quiz_app.urls")),
    path('accounts/', include("accounts.urls")),
    path('', include('pages.urls')),
]