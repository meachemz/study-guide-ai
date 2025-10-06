from django.urls import path
from . import views

urlpatterns = [
    path('save/', views.save_quiz_view, name='save_quiz'),
    path('submit/', views.submit_quiz_view, name='submit_quiz'),
    path('<str:access_code>/', views.quiz_display_view, name='quiz_display'),
    ]

