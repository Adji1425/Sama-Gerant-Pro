from .models import Commercant


def boutique(request):
    """
    Rend le commerçant unique de la plateforme disponible dans tous les
    templates sous la variable `commercant_boutique` (utile pour le footer,
    le bouton WhatsApp flottant, etc. — sans avoir à le repasser dans
    chaque vue).
    """
    return {
        'commercant_boutique': Commercant.objects.select_related('utilisateur').first()
    }


def notifications_commercant(request):
    """
    Petits compteurs affichés dans la navbar pour le commerçant connecté :
    - nb de commandes en attente (badge sur "Commandes")
    - nb de messages non lus (badge sur "Messages" + pastille sur l'avatar)
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'commercant'):
        return {}

    from apps.commandes.models import Commande
    from apps.messagerie.models import Message

    commercant = request.user.commercant

    nb_commandes_attente = Commande.objects.filter(
        lignes__produit__commercant=commercant,
        statut='en_attente'
    ).distinct().count()

    nb_messages_non_lus = Message.objects.filter(
        conversation__commercant=commercant,
        lu=False
    ).exclude(expediteur=request.user).count()

    return {
        'nb_commandes_attente': nb_commandes_attente,
        'nb_messages_non_lus': nb_messages_non_lus,
    }