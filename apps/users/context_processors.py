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