import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Quiz, Question
from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  # or wherever you want to go
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'accounts/login.html')

def dashboard_view(request):
    return render(request, 'accounts/dashboard.html')

