from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import (
    InscriptionForm, ConnexionForm, ModifierProfilForm, ChangerMotDePasseForm
)
from .models import Client, Utilisateur


def register(request):
    """Inscription d'un nouveau client"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            # Créer l'utilisateur
            utilisateur = form.save(commit=False)
            utilisateur.role = 'client'
            utilisateur.telephone = form.cleaned_data['telephone']
            utilisateur.save()

            # Créer le profil Client associé
            Client.objects.create(
                utilisateur=utilisateur,
                adresse_livraison=form.cleaned_data['adresse_livraison']
            )

            # Connecter directement après inscription
            login(request, utilisateur)
            messages.success(
                request,
                f"Bienvenue {utilisateur.first_name} ! "
                f"Votre compte a été créé avec succès."
            )
            return redirect('home')
        else:
            messages.error(
                request,
                "Veuillez corriger les erreurs dans le formulaire."
            )
    else:
        form = InscriptionForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    """Connexion d'un utilisateur"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = ConnexionForm(request, data=request.POST)
        if form.is_valid():
            utilisateur = form.get_user()
            login(request, utilisateur)
            messages.success(
                request,
                f"Bon retour, {utilisateur.first_name} !"
            )
            # Redirection selon le rôle
            if utilisateur.est_commercant():
                return redirect('produits:gestion_produits')
            elif utilisateur.est_admin():
                return redirect('admin:index')
            else:
                return redirect('home')
        else:
            messages.error(
                request,
                "Identifiants incorrects. Veuillez réessayer."
            )
    else:
        form = ConnexionForm(request)

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    """Déconnexion"""
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('users:login')


@login_required
def profil(request):
    """Page profil du client connecté"""
    utilisateur = request.user
    client = None

    if hasattr(utilisateur, 'client'):
        client = utilisateur.client

    context = {
        'utilisateur': utilisateur,
        'client': client,
    }
    return render(request, 'users/profil.html', context)


@login_required
def modifier_profil(request):
    """Modifier les infos du profil"""
    if request.method == 'POST':
        form = ModifierProfilForm(
            request.POST,
            request.FILES,
            instance=request.user
        )
        if form.is_valid():
            form.save()
            # Mettre à jour l'adresse de livraison si client
            if hasattr(request.user, 'client'):
                adresse = request.POST.get('adresse_livraison', '')
                if adresse:
                    request.user.client.adresse_livraison = adresse
                    request.user.client.save()
            messages.success(request, "Profil mis à jour avec succès !")
            return redirect('users:profil')
        else:
            messages.error(request, "Erreur lors de la mise à jour.")
    else:
        form = ModifierProfilForm(instance=request.user)

    return render(request, 'users/modifier_profil.html', {'form': form})


@login_required
def changer_mot_de_passe(request):
    """Changement du mot de passe de l'utilisateur connecté"""
    if request.method == 'POST':
        form = ChangerMotDePasseForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # Garde l'utilisateur connecté après le changement de mot de passe
            update_session_auth_hash(request, request.user)
            messages.success(request, "Votre mot de passe a été modifié avec succès !")
            return redirect('users:profil')
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = ChangerMotDePasseForm(request.user)

    return render(request, 'users/changer_mot_de_passe.html', {'form': form})