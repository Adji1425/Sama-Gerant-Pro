from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import (
    InscriptionForm, InscriptionCommercantForm, InscriptionAdminForm,
    ConnexionForm, ModifierProfilForm, ChangerMotDePasseForm
)
from .models import Client, Commercant, Administrateur, Utilisateur


# ── Décorateur administrateur ───────────────────────────────────────────────
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not hasattr(request.user, 'administrateur'):
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


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


def register_commercant(request):
    """
    Inscription commerçant désactivée : la plateforme ne gère
    qu'un seul commerçant, déjà créé. La création du compte
    passe désormais uniquement par l'admin (users:creer_commercant).
    """
    messages.error(
        request,
        "L'inscription commerçant n'est pas disponible : "
        "cette plateforme est réservée à un commerçant unique."
    )
    return redirect('home')


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
                return redirect('users:admin_dashboard')
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


def compte(request):
    """
    Page 'Mon compte' : hub central (panier, favoris, commandes,
    livraison, paiement). Accessible même sans connexion, pour
    afficher la carte de bienvenue + inviter à se connecter/s'inscrire.
    """
    nb_panier = 0
    nb_favoris = 0

    if request.user.is_authenticated and hasattr(request.user, 'client'):
        client = request.user.client
        if hasattr(client, 'panier'):
            nb_panier = client.panier.lignes.filter(commande=None).count()
        nb_favoris = client.favoris.count()

    return render(request, 'users/compte.html', {
        'nb_panier': nb_panier,
        'nb_favoris': nb_favoris,
    })


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

# ── Espace Administrateur ───────────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    """Vue d'ensemble : le commerçant unique de la plateforme + statistiques"""
    commercant = Commercant.objects.select_related('utilisateur').first()

    stats = {
        'total_clients': Client.objects.count(),
        'total_admins': Administrateur.objects.count(),
    }

    return render(request, 'users/admin_dashboard.html', {
        'commercant': commercant,
        'stats': stats,
    })


@admin_required
def toggle_actif_commercant(request, pk):
    """Bloque / débloque le compte d'un commerçant"""
    commercant = Commercant.objects.select_related('utilisateur').filter(
        pk=pk
    ).first()
    if commercant:
        commercant.utilisateur.is_active = not commercant.utilisateur.is_active
        commercant.utilisateur.save()
        statut = "réactivé" if commercant.utilisateur.is_active else "bloqué"
        messages.success(
            request,
            f"Le compte de « {commercant.nom_boutique} » a été {statut}."
        )
    return redirect('users:admin_dashboard')


@admin_required
def register_admin(request):
    """
    Un administrateur crée le compte d'un AUTRE administrateur
    (ex: un autre étudiant de l'équipe qui doit gérer la plateforme).
    Ne connecte PAS la personne créée : c'est un tiers qui se connectera
    lui-même ensuite avec les identifiants transmis.
    """
    if request.method == 'POST':
        form = InscriptionAdminForm(request.POST)
        if form.is_valid():
            utilisateur = form.save(commit=False)
            utilisateur.role = 'admin'
            utilisateur.telephone = form.cleaned_data['telephone']
            utilisateur.is_staff = True
            utilisateur.save()

            Administrateur.objects.create(utilisateur=utilisateur)

            messages.success(
                request,
                f"Le compte administrateur « {utilisateur.username} » a été créé. "
                f"Transmettez-lui ses identifiants."
            )
            return redirect('users:admin_dashboard')
        else:
            messages.error(
                request,
                "Veuillez corriger les erreurs dans le formulaire."
            )
    else:
        form = InscriptionAdminForm()

    return render(request, 'users/register_admin.html', {'form': form})


@admin_required
def creer_commercant(request):
    """
    Un administrateur crée le compte du commerçant.
    Ne connecte PAS la personne créée : c'est un tiers qui se connectera
    lui-même ensuite avec les identifiants transmis.
    La plateforme ne gérant qu'un seul commerçant, cette page se
    bloque dès qu'un commerçant existe déjà.
    """
    if Commercant.objects.exists():
        messages.error(
            request,
            "Un commerçant existe déjà sur cette plateforme. "
            "Elle est réservée à un commerçant unique."
        )
        return redirect('users:admin_dashboard')

    if request.method == 'POST':
        form = InscriptionCommercantForm(request.POST, request.FILES)
        if form.is_valid():
            utilisateur = form.save(commit=False)
            utilisateur.role = 'commercant'
            utilisateur.telephone = form.cleaned_data['telephone']
            utilisateur.save()

            Commercant.objects.create(
                utilisateur=utilisateur,
                nom_boutique=form.cleaned_data['nom_boutique'],
                logo=form.cleaned_data.get('logo')
            )

            messages.success(
                request,
                f"La boutique « {form.cleaned_data['nom_boutique']} » a été créée. "
                f"Transmettez les identifiants à {utilisateur.first_name}."
            )
            return redirect('users:admin_dashboard')
        else:
            messages.error(
                request,
                "Veuillez corriger les erreurs dans le formulaire."
            )
    else:
        form = InscriptionCommercantForm()

    return render(request, 'users/creer_commercant.html', {'form': form})


@admin_required
def liste_clients(request):
    """Vue d'ensemble : tous les clients de la plateforme"""
    recherche = request.GET.get('q', '')

    clients = Client.objects.select_related('utilisateur').order_by(
        '-utilisateur__date_joined'
    )
    if recherche:
        clients = clients.filter(
            utilisateur__first_name__icontains=recherche
        ) | clients.filter(
            utilisateur__last_name__icontains=recherche
        ) | clients.filter(
            utilisateur__email__icontains=recherche
        )

    return render(request, 'users/liste_clients.html', {
        'clients': clients,
        'recherche': recherche,
    })