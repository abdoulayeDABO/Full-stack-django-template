from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import DeleteAccountForm, ProfileForm, SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("index")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Vos informations ont été mises à jour.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "delete_form": DeleteAccountForm(user=request.user),
            "editing": request.method == "POST",
        },
    )


@login_required
@require_POST
def delete_account(request):
    form = DeleteAccountForm(request.POST, user=request.user)
    if form.is_valid():
        request.user.soft_delete()
        logout(request)
        messages.success(request, "Votre compte a été supprimé.")
        return redirect("index")

    messages.error(request, "Mot de passe incorrect.")
    return redirect("profile")
