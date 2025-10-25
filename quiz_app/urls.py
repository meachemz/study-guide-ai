# In quiz_app/urls.py
from django.urls import path
from . import views

app_name = 'quiz_app'

urlpatterns = [
    # --- SPECIFIC paths come FIRST ---
    path('submit/', views.submit_quiz_view, name='submit_quiz'),
    path('api/dashboard-data/', views.dashboard_data_view, name='api_dashboard_data'),
    path('api/quiz/save/', views.save_quiz_view, name='api_save_quiz'),
    path('api/quiz/generate-ai/', views.generate_ai_quiz_view, name='api_generate_ai'),
    path('api/quiz/delete/', views.delete_quiz_view, name='api_delete_quiz'),

    # --- GENERAL (variable) path comes LAST ---
    path('<str:access_code>/', views.quiz_display_view, name='quiz_display'),
]