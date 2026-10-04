from django.db import models
from apps.users.models import Commercant


class Notification(models.Model):
    """
    Journal des alertes envoyées au commerçant (stock bas, stock dormant,
    événements, commandes). Il n'y a plus d'écran de lecture : le champ `lu`
    n'est plus utilisé et aucune logique ne dépend de lui.
    """
    TYPE_CHOICES = [
        ('stock_bas', '🔴 Stock bas'),
        ('stock_dormant', '🟡 Stock dormant'),
        ('evenement', '📅 Événement'),
        ('commande', '🛒 Nouvelle commande'),
        ('saison', '🌧️ Alerte saison'),
    ]
    commercant = models.ForeignKey(
        Commercant,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    titre = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-date_envoi']

    def __str__(self):
        return f"[{self.type}] {self.titre}"
