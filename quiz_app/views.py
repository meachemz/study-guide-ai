from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def home(request):
    context = {"name" : "World"}
    return render(request,"quiz_app/helloworld.html",context)

