# In accounts/views.py
# (Make sure all the imports are at the top)
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # This is CORRECT. It uses the URL's proper name.
            return redirect('accounts:dashboard') 
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def dashboard_view(request):
    return render(request, 'quiz_app/dashboard.html')