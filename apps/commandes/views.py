import logging
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F
from .models import Panier, LignePanier, Commande, Region
from apps.produits.models import Produit, Categorie
from django.http import JsonResponse
from apps.facturation.models import Facture
from django.db.models import Q
from urllib.parse import urlencode
from django.urls import reverse
from django.utils.html import format_html

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_or_create_panier(client):
    panier, _ = Panier.objects.get_or_create(client=client)
    return panier


# ── PANIER ────────────────────────────────────────────────────────────────────
@login_required
def voir_panier(request):
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    panier = get_or_create_panier(request.user.client)
    lignes = panier.lignes.filter(
        commande=None
    ).select_related('produit').all()

    context = {
        'panier': panier,
        'lignes': lignes,
        'total': sum(l.sous_total() for l in lignes),
        'nombre_articles': sum(l.quantite for l in lignes),
    }
    return render(request, 'commandes/panier.html', context)


@login_required
def ajouter_panier(request, produit_id):
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    if request.method == 'POST':
        produit = get_object_or_404(Produit, pk=produit_id, statut='actif')

        try:
            quantite = int(request.POST.get('quantite', 1))
        except (TypeError, ValueError):
            messages.error(request, "Quantité invalide.")
            return redirect('produits:fiche_produit', pk=produit_id)

        if quantite < 1:
            messages.error(request, "La quantité doit être d'au moins 1.")
            return redirect('produits:fiche_produit', pk=produit_id)

        # ── Couleur / taille choisies (simples champs texte, stock global) ──
        couleur = request.POST.get('couleur', '').strip()
        taille = request.POST.get('taille', '').strip()

        if couleur and couleur not in produit.liste_couleurs():
            messages.error(request, "Couleur invalide.")
            return redirect('produits:fiche_produit', pk=produit_id)
        if taille and taille not in produit.liste_tailles():
            messages.error(request, "Taille invalide.")
            return redirect('produits:fiche_produit', pk=produit_id)
        if produit.liste_couleurs() and not couleur:
            messages.error(request, "Veuillez choisir une couleur.")
            return redirect('produits:fiche_produit', pk=produit_id)
        if produit.liste_tailles() and not taille:
            messages.error(request, "Veuillez choisir une taille.")
            return redirect('produits:fiche_produit', pk=produit_id)

        stock_disponible = produit.quantite

        if quantite > stock_disponible:
            messages.error(
                request,
                f"Stock insuffisant. Seulement "
                f"{stock_disponible} unité(s) disponible(s)."
            )
            return redirect('produits:fiche_produit', pk=produit_id)

        panier = get_or_create_panier(request.user.client)

        # ✅ Chercher ligne existante sans commande (dans le panier actif),
        # en tenant compte de la couleur/taille choisies
        ligne_existante = panier.lignes.filter(
            produit=produit, couleur_choisie=couleur,
            taille_choisie=taille, commande=None
        ).first()

        if ligne_existante:
            nouvelle_qte = ligne_existante.quantite + quantite
            if nouvelle_qte > stock_disponible:
                messages.error(
                    request,
                    f"Vous avez déjà {ligne_existante.quantite} de ce "
                    f"produit dans votre panier."
                )
                return redirect('produits:fiche_produit', pk=produit_id)
            ligne_existante.quantite = nouvelle_qte
            ligne_existante.save()
        else:
            LignePanier.objects.create(
                panier=panier,
                produit=produit,
                couleur_choisie=couleur,
                taille_choisie=taille,
                quantite=quantite,
                # ✅ CORRIGÉ : prix_unitaire_vente
                prix_unitaire_vente=produit.prix_vente,
            )

        libelle = produit.nom
        variante_label = " · ".join(filter(None, [couleur, taille]))
        if variante_label:
            libelle = f"{produit.nom} ({variante_label})"

        messages.success(
            request,
            format_html(
                '✓ {} ajouté au panier ! '
                '<a href="{}" class="alert-link-right">Voir le panier <i class="bi bi-arrow-right"></i></a>',
                libelle, reverse('commandes:voir_panier')
            )
        )
        return redirect('produits:fiche_produit', pk=produit_id)

    return redirect('produits:catalogue')


@login_required
def modifier_panier(request, ligne_id):
    ligne = get_object_or_404(
        LignePanier,
        pk=ligne_id,
        panier__client=request.user.client,
        commande=None
    )

    if request.method == 'POST':
        try:
            quantite = int(request.POST.get('quantite', 1))
        except (TypeError, ValueError):
            messages.error(request, "Quantité invalide.")
            return redirect('commandes:voir_panier')

        if quantite < 1:
            ligne.delete()
            messages.info(request, "Article retiré du panier.")
        elif quantite > ligne.produit.quantite:
            messages.error(
                request,
                f"Stock insuffisant. Max : {ligne.produit.quantite}"
            )
        else:
            ligne.quantite = quantite
            ligne.save()
            messages.success(request, "Panier mis à jour.")

    return redirect('commandes:voir_panier')


@login_required
def supprimer_panier(request, ligne_id):
    ligne = get_object_or_404(
        LignePanier,
        pk=ligne_id,
        panier__client=request.user.client,
        commande=None
    )
    nom_produit = ligne.produit.nom
    ligne.delete()
    messages.info(request, f"{nom_produit} retiré du panier.")
    return redirect('commandes:voir_panier')


# ── COMMANDE ──────────────────────────────────────────────────────────────────
@login_required
def valider_commande(request):
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    client = request.user.client
    panier = get_or_create_panier(client)
    lignes = panier.lignes.filter(commande=None)

    if not lignes.exists():
        messages.error(request, "Votre panier est vide.")
        return redirect('commandes:voir_panier')

    if request.method == 'POST':
        adresse = request.POST.get('adresse_livraison', client.adresse_livraison)
        telephone = request.POST.get('telephone', request.user.telephone)
        commune = request.POST.get('commune', '').strip()
        region_id = request.POST.get('region')
        region = Region.objects.filter(pk=region_id).first() if region_id else None

        if not adresse or not telephone:
            messages.error(
                request,
                "Veuillez renseigner l'adresse et le téléphone."
            )
            return redirect('commandes:voir_panier')

        if not region:
            messages.error(request, "Veuillez sélectionner votre région de livraison.")
            return redirect('commandes:voir_panier')

        for ligne in lignes:
            if ligne.produit and ligne.quantite > ligne.produit.quantite:
                messages.error(
                    request,
                    f"Stock insuffisant pour {ligne.produit.nom}."
                )
                return redirect('commandes:voir_panier')

        # On ne crée PAS encore la commande : les infos de livraison sont
        # gardées en session le temps du paiement (simulé). La
        # commande n'est créée — et le commerçant notifié — qu'une fois le
        # paiement "réussi" dans paiement() ci-dessous.
        request.session['livraison_pending'] = {
            'adresse': adresse,
            'telephone': telephone,
            'commune': commune,
            'region_id': region.id,
        }
        return redirect('commandes:paiement')

    context = {
        'panier': panier,
        'lignes': lignes,
        'total': sum(l.sous_total() for l in lignes),
        'client': client,
        'regions': Region.objects.all(),
    }
    return render(request, 'commandes/recap_commande.html', context)


@login_required
def paiement(request):
    """
    Simulation du paiement (Wave, Orange Money ou carte bancaire) avant la
    création définitive de la commande. Aucun appel réel à une API de
    paiement n'est fait (pas de clé marchande dans ce projet académique) :
    le temps de traitement est simulé côté front (voir paiement.html).

    Sécurité : les données de carte bancaire ne sont JAMAIS envoyées au
    serveur (les champs du formulaire n'ont pas d'attribut name) ; seul le
    moyen de paiement choisi est transmis et enregistré.
    """
    if not hasattr(request.user, 'client'):
        messages.error(request, "Accès réservé aux clients.")
        return redirect('home')

    from apps.sad.utils import verifier_stock_produit
    client = request.user.client
    infos = request.session.get('livraison_pending')
    if not infos:
        messages.error(request, "Session de paiement expirée, veuillez réessayer.")
        return redirect('commandes:voir_panier')

    panier = get_or_create_panier(client)
    lignes = panier.lignes.filter(commande=None)
    if not lignes.exists():
        messages.error(request, "Votre panier est vide.")
        return redirect('commandes:voir_panier')

    total = sum(l.sous_total() for l in lignes)
    modes = dict(Commande.MODE_PAIEMENT_CHOICES)
    mode_choisi = 'wave'
    numero_saisi = infos['telephone']

    if request.method == 'POST':
        mode_choisi = request.POST.get('mode_paiement', '')
        numero_saisi = request.POST.get('numero', '').strip()

        erreur = None
        if mode_choisi not in modes:
            erreur = "Veuillez choisir un moyen de paiement."
            mode_choisi = 'wave'
        elif mode_choisi in ('wave', 'orange_money'):
            numero = _normaliser_numero_sn(numero_saisi)
            if not numero:
                erreur = (
                    f"Numéro {modes[mode_choisi]} invalide : saisissez "
                    f"9 chiffres (ex : 77 000 00 00)."
                )
            elif mode_choisi == 'orange_money' and numero[:2] not in ('77', '78'):
                erreur = (
                    "Un numéro Orange Money commence par 77 ou 78. "
                    "Choisissez Wave si votre numéro est différent."
                )

        if erreur:
            messages.error(request, erreur)
        else:
            region = Region.objects.filter(pk=infos['region_id']).first()
            try:
                commande, alertes = _creer_commande_atomique(
                    client, panier, infos, region, mode_choisi
                )
            except CommandeImpossible as erreur_commande:
                messages.error(request, f"{erreur_commande} Paiement annulé, vous n'avez pas été débité.")
                request.session.pop('livraison_pending', None)
                return redirect('commandes:voir_panier')

            # Une fois la commande validée en base (hors transaction, pour ne
            # pas garder les verrous pendant l'envoi des emails) : prévenir le
            # commerçant. Ces envois ne doivent jamais faire échouer la commande.
            for produit, ancienne_quantite in alertes:
                try:
                    verifier_stock_produit(produit, ancienne_quantite)
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Alerte stock bas impossible pour %s", produit
                    )
            _notifier_commercant(commande)

            request.session.pop('livraison_pending', None)

            messages.success(
                request,
                f"✓ Paiement {modes[mode_choisi]} accepté — "
                f"commande #{commande.id} passée avec succès !"
            )
            return redirect('commandes:confirmation', commande_id=commande.id)

    context = {
        'total': total,
        'lignes': lignes,
        'numero_saisi': numero_saisi,
        'mode_choisi': mode_choisi,
    }
    return render(request, 'commandes/paiement.html', context)


class CommandeImpossible(Exception):
    """Commande refusée au moment du paiement (stock insuffisant, panier vide...)."""


def _creer_commande_atomique(client, panier, infos, region, mode_paiement):
    """
    Crée la commande ET décrémente le stock en UNE SEULE transaction, avec
    verrous de ligne PostgreSQL. Garanties :
      - deux clients qui paient la dernière unité en même temps : un seul
        réussit, l'autre reçoit « stock insuffisant » (jamais de stock < 0) ;
      - un double clic sur « Payer » ne crée qu'UNE commande (le panier est
        verrouillé, la 2e requête le trouve déjà vidé) ;
      - si une étape échoue, tout est annulé (pas de commande « à moitié »
        créée, pas de stock perdu).
    Retourne (commande, [(produit, ancienne_quantite), ...]).
    """
    with transaction.atomic():
        # 1) Verrou sur le panier du client, puis relecture des lignes sous verrou
        Panier.objects.select_for_update().get(pk=panier.pk)
        lignes = list(LignePanier.objects.filter(panier=panier, commande=None))
        if not lignes:
            raise CommandeImpossible(
                "Votre panier est vide ou cette commande vient déjà d'être enregistrée."
            )

        # 2) Quantité totale demandée par produit (un même produit peut être
        #    présent dans plusieurs lignes : couleurs / tailles différentes)
        demande = {}
        for ligne in lignes:
            if ligne.produit_id:
                demande[ligne.produit_id] = demande.get(ligne.produit_id, 0) + ligne.quantite

        # 3) Verrou sur les produits, TOUJOURS dans le même ordre (pk croissant)
        #    pour éviter les blocages croisés entre deux commandes simultanées
        produits = {
            p.pk: p for p in
            Produit.objects.select_for_update().filter(pk__in=demande).order_by('pk')
        }

        # 4) Validation sous verrou : le stock lu ici ne peut plus changer
        for pk, quantite in demande.items():
            produit = produits.get(pk)
            if produit is None or produit.statut != 'actif':
                nom = produit.nom if produit else "Un produit de votre panier"
                raise CommandeImpossible(f"« {nom} » n'est plus disponible à la vente.")
            if quantite > produit.quantite:
                raise CommandeImpossible(
                    f"Stock insuffisant pour « {produit.nom} » "
                    f"(il en reste {produit.quantite}, vous en demandez {quantite})."
                )

        # 5) Création de la commande, rattachement des lignes, décrément du stock
        commande = Commande.objects.create(
            client=client,
            adresse_livraison_reel=infos['adresse'],
            telephone=infos['telephone'],
            region=region,
            commune=infos['commune'],
            statut='en_attente',
            mode_paiement=mode_paiement,
        )
        for ligne in lignes:
            ligne.commande = commande
            ligne.save()

        alertes = []
        for pk, quantite in demande.items():
            produit = produits[pk]
            ancienne = produit.quantite
            produit.quantite = ancienne - quantite
            produit.save()
            alertes.append((produit, ancienne))

        commande.calculer_montant()
    return commande, alertes


def _normaliser_numero_sn(brut):
    """
    Numéro mobile sénégalais -> 9 chiffres commençant par 7, ou None.
    Accepte les espaces, tirets, et les préfixes +221 / 221.
    """
    chiffres = re.sub(r'\D', '', brut or '')
    if len(chiffres) == 12 and chiffres.startswith('221'):
        chiffres = chiffres[3:]
    if len(chiffres) == 9 and chiffres.startswith('7'):
        return chiffres
    return None


def _notifier_commercant(commande):
    """Notification commerçant — utilise commande.lignes"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from apps.notifications.models import Notification
        # ✅ CORRIGÉ : commande.lignes au lieu de commande.details
        lignes = commande.lignes.select_related('produit__commercant').all()
        commercants_notifies = set()
        for ligne in lignes:
            if ligne.produit:
                commercant = ligne.produit.commercant
                if commercant.id not in commercants_notifies:
                    message = (
                        f"Le client {commande.client} vient de passer "
                        f"une commande de {commande.montant_total:.0f} FCFA."
                    )
                    Notification.objects.create(
                        commercant=commercant,
                        titre=f"Nouvelle commande #{commande.id}",
                        message=message,
                        type='commande',
                    )
                    # Email en plus de la notification interne (le
                    # commerçant n'est pas toujours connecté à l'app).
                    _envoyer_email_nouvelle_commande(commercant, commande)
                    commercants_notifies.add(commercant.id)
    except Exception:
        logger.exception(
            "Échec de la notification (interne/email) du commerçant pour la commande #%s",
            commande.id,
        )


def _envoyer_email_nouvelle_commande(commercant, commande):
    """
    Email HTML soigné envoyé au commerçant à chaque nouvelle commande
    (+ repli texte brut). N'échoue jamais bruyamment : les erreurs SMTP
    sont journalisées, pas levées (voir _notifier_commercant ci-dessus).
    """
    import logging
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.urls import reverse

    logger = logging.getLogger(__name__)

    destinataire = getattr(commercant.utilisateur, 'email', None)
    if not destinataire:
        return False

    # Lien ABSOLU (http://domaine/...) : un chemin relatif ne fonctionne pas
    # dans un email, Gmail le transforme en "http:///commandes/...".
    lien_commande = settings.SITE_URL + reverse(
        'commandes:detail_commande_commercant', args=[commande.id]
    )

    texte_brut = (
        f"Bonjour {commercant.utilisateur.first_name or commercant.nom_boutique},\n\n"
        f"Vous avez reçu une nouvelle commande #{commande.id} de "
        f"{commande.client} pour un montant de {commande.montant_total:.0f} FCFA.\n\n"
        f"Traitez-la depuis votre tableau de bord : {lien_commande}"
    )

    try:
        html_body = render_to_string('commandes/email/nouvelle_commande.html', {
            'commercant': commercant,
            'commande': commande,
            'lien_commande': lien_commande,
        })
        email = EmailMultiAlternatives(
            subject=f"🛒 Nouvelle commande #{commande.id} — {commande.montant_total:.0f} FCFA",
            body=texte_brut,
            from_email=settings.EMAIL_FROM,
            to=[destinataire],
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception:
        logger.exception(
            "Échec de l'envoi de l'email de nouvelle commande #%s au commerçant %s",
            commande.id, commercant,
        )
        return False


@login_required
def confirmation(request, commande_id):
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )
    return render(request, 'commandes/confirmation.html', {'commande': commande})


@login_required
def mes_commandes(request):
    if not hasattr(request.user, 'client'):
        return redirect('home')

    commandes = Commande.objects.filter(
        client=request.user.client
    ).prefetch_related('lignes__produit__categorie').distinct().order_by('-date_commande')

    q_produit = request.GET.get('produit', '').strip()
    q_categorie = request.GET.get('categorie', '')
    q_date = request.GET.get('date', '').strip()

    if q_produit:
        commandes = commandes.filter(lignes__produit__nom__icontains=q_produit)
    if q_categorie:
        commandes = commandes.filter(lignes__produit__categorie_id=q_categorie)
    if q_date:
        commandes = commandes.filter(date_commande__date=q_date)

    commandes = commandes.distinct()

    paginator = Paginator(commandes, 10)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'commandes/mes_commandes.html', {
        'commandes': page,
        'categories': Categorie.objects.all(),
        'q_produit': q_produit,
        'q_categorie': q_categorie,
        'q_date': q_date,
    })


@login_required
def detail_commande(request, commande_id):
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )
    # ✅ CORRIGÉ : commande.lignes
    details = commande.lignes.select_related('produit').all()

    avis_par_produit = {}
    if commande.statut == 'livree':
        from apps.avis.models import Avis
        produit_ids = [d.produit_id for d in details if d.produit_id]
        avis_par_produit = {
            a.produit_id: a
            for a in Avis.objects.filter(client=commande.client, produit_id__in=produit_ids)
        }

    return render(request, 'commandes/detail_commande.html', {
        'commande': commande,
        'details': details,
        'avis_par_produit': avis_par_produit,
    })


@login_required
def get_statut_json(request, commande_id):
    commande = get_object_or_404(
        Commande,
        pk=commande_id,
        client=request.user.client
    )

    statuts_ordre = {
        'en_attente': 1,
        'en_preparation': 2,
        'livree': 3,
        'annulee': -1,
    }

    return JsonResponse({
        'statut': commande.statut,
        'statut_display': commande.get_statut_display(),
        'ordre': statuts_ordre.get(commande.statut, 0),
        'montant_total': commande.montant_total,
        'date_commande': commande.date_commande.strftime('%d/%m/%Y à %H:%M'),
    })



# Décorateur commerçant
def commercant_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not hasattr(request.user, 'commercant'):
            messages.error(request, "Accès réservé aux commerçants.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

@login_required
def commandes_commercant(request):
    """Liste des commandes reçues par le commerçant"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    commercant = request.user.commercant
    # Commandes contenant des produits de ce commerçant
    commandes = Commande.objects.filter(
        lignes__produit__commercant=commercant
    ).distinct().prefetch_related(
        'lignes__produit', 'client__utilisateur'
    ).order_by('-date_commande')

    # Filtrer par statut
    statut_filtre = request.GET.get('statut', '')
    if statut_filtre:
        commandes = commandes.filter(statut=statut_filtre)

    # Recherche par client ou n° de commande, pour retrouver vite une
    # commande précise quand il y en a beaucoup.
    recherche = request.GET.get('q', '').strip()
    if recherche:
        filtre_recherche = (
            Q(client__utilisateur__first_name__icontains=recherche) |
            Q(client__utilisateur__last_name__icontains=recherche)
        )
        if recherche.lstrip('#').isdigit():
            filtre_recherche |= Q(id=int(recherche.lstrip('#')))
        commandes = commandes.filter(filtre_recherche)

    # Filtre par plage de dates
    date_debut = request.GET.get('date_debut', '').strip()
    date_fin = request.GET.get('date_fin', '').strip()
    if date_debut:
        commandes = commandes.filter(date_commande__date__gte=date_debut)
    if date_fin:
        commandes = commandes.filter(date_commande__date__lte=date_fin)

    # Query string des filtres actifs (hors statut), pour les préserver
    # en changeant d'onglet de statut.
    extra_params = {}
    if recherche:
        extra_params['q'] = recherche
    if date_debut:
        extra_params['date_debut'] = date_debut
    if date_fin:
        extra_params['date_fin'] = date_fin
    extra_qs = urlencode(extra_params)

    context = {
        'commandes': commandes,
        'statut_filtre': statut_filtre,
        'recherche': recherche,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'extra_qs': extra_qs,
        'total_en_attente': Commande.objects.filter(
            lignes__produit__commercant=commercant,
            statut='en_attente'
        ).distinct().count(),
        'total_en_preparation': Commande.objects.filter(
            lignes__produit__commercant=commercant,
            statut='en_preparation'
        ).distinct().count(),
    }
    return render(request, 'commandes/commandes_commercant.html', context)

@login_required
def detail_commande_commercant(request, commande_id):
    """Détail d'une commande côté commerçant"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    commande = get_object_or_404(Commande, pk=commande_id)
    lignes = commande.lignes.filter(
        produit__commercant=request.user.commercant
    ).select_related('produit')

    return render(request, 'commandes/detail_commande_commercant.html', {
        'commande': commande,
        'lignes': lignes,
    })


@login_required
def changer_statut(request, commande_id):
    """Changer le statut d'une commande"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    if request.method == 'POST':
        get_object_or_404(Commande, pk=commande_id)
        nouveau_statut = request.POST.get('statut')
        statuts_finaux = ['livree', 'annulee']
        statuts_valides = ['en_attente', 'en_preparation', 'livree', 'annulee']

        # La commande est VERROUILLÉE pendant le changement : deux clics
        # simultanés sur « Annuler » ne peuvent pas restituer le stock deux fois.
        with transaction.atomic():
            commande = Commande.objects.select_for_update().get(pk=commande_id)

            # Une commande livrée ou annulée est définitive : on bloque tout
            # changement ultérieur (entre autres pour éviter un remboursement
            # de stock en double si on annule plusieurs fois).
            if commande.statut in statuts_finaux:
                messages.error(
                    request,
                    f"✗ Commande #{commande.id} : le statut « "
                    f"{commande.get_statut_display()} » est définitif et ne peut plus être modifié."
                )
                return redirect('commandes:commandes_commercant')

            statut_change = nouveau_statut in statuts_valides
            ancien_statut = commande.statut
            if statut_change:
                commande.statut = nouveau_statut
                commande.save()

                # Annulation : on restitue le stock décrémenté à la commande
                # (mise à jour atomique côté base : pas d'écrasement d'une vente
                # ou d'un approvisionnement simultané)
                if nouveau_statut == 'annulee':
                    for ligne in commande.lignes.all():
                        if ligne.produit_id:
                            Produit.objects.filter(pk=ligne.produit_id).update(
                                quantite=F('quantite') + ligne.quantite
                            )

        if statut_change:
            # Notifier le client
            try:
                from apps.notifications.models import Notification
                if hasattr(commande.client, 'utilisateur'):
                    pass  # notifications client à implémenter si besoin
            except Exception:
                pass

            # Générer facture si livrée
            if nouveau_statut == 'livree' and ancien_statut != 'livree':
                _generer_facture_auto(commande)

            messages.success(
                request,
                f"✓ Statut de la commande #{commande.id} → "
                f"{commande.get_statut_display()}"
            )

    return redirect('commandes:commandes_commercant')


def _generer_facture_auto(commande):
    """
    Génère automatiquement la facture PDF quand la commande passe à
    'livrée', puis l'envoie par email au client (§5.2.4 du cahier des
    charges : envoi automatique du reçu après livraison).
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from apps.facturation.services import generer_et_envoyer_facture
        # Le commerçant est déduit du produit de la première ligne
        premiere_ligne = commande.lignes.select_related(
            'produit__commercant'
        ).first()
        if premiere_ligne and premiere_ligne.produit:
            commercant = premiere_ligne.produit.commercant
            generer_et_envoyer_facture(commande, commercant)
    except Exception:
        # Une erreur de génération/envoi de facture ne doit jamais
        # bloquer le changement de statut de la commande, mais on la
        # journalise pour ne pas perdre la trace du problème.
        logger.exception(
            "Échec de la génération/envoi automatique de la facture pour la commande #%s",
            commande.id,
        )


@login_required
def generer_facture(request, commande_id):
    """Génère et affiche la facture PDF"""
    if not hasattr(request.user, 'commercant'):
        return redirect('home')

    commande = get_object_or_404(Commande, pk=commande_id)

    # Créer la facture si elle n'existe pas
    facture, created = Facture.objects.get_or_create(commande=commande)

    # Générer le PDF avec xhtml2pdf
    from django.template.loader import get_template
    from django.http import HttpResponse
    try:
        from xhtml2pdf import pisa
        template = get_template('facturation/facture_pdf.html')
        html = template.render({
            'commande': commande,
            'facture': facture,
            'lignes': commande.lignes.select_related('produit').all(),
        })
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="facture_{commande.id}.pdf"'
        )
        pisa.CreatePDF(html, dest=response)
        return response
    except Exception as e:
        messages.error(request, f"Erreur génération PDF : {e}")
        return redirect('commandes:commandes_commercant')