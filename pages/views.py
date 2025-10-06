from django.shortcuts import render

# Create your views here.
# In pages/views.py

def home_page_view(request):
    # This view just renders your home page template.
    return render(request, 'pages/home_page_AI.html')
