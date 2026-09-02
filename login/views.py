from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse


# @login_required(login_url="login")
def home(request):
    return render(request, "login/home.html")


def user_login(request):
    if request.user.is_authenticated:
        return redirect("home")  # or use '/' if not named
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url and next_url != reverse("login"):
                return redirect(next_url)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password")
    return render(request, "login/login.html")


def user_logout(request):
    logout(request)
    return redirect("login")
