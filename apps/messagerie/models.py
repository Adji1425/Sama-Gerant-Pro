from django.db import models
from apps.users.models import Utilisateur, Client, Commercant
from apps.produits.models import Produit


class Conversation(models.Model):
    """Un fil de discussion unique entre un client et un commerçant"""
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    commercant = models.ForeignKey(
        Commercant,
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    produit_contexte = models.ForeignKey(
        Produit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations_associees',
        help_text="Dernier produit à l'origine du contact — affiché en haut du chat."
    )

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        # Un seul fil par couple client/commerçant
        unique_together = ('client', 'commercant')

    def __str__(self):
        return f"{self.client} ↔ {self.commercant}"

    def dernier_message(self):
        return self.messages.order_by('-date_heure').first()

    def messages_non_lus(self, utilisateur):
        return self.messages.filter(lu=False).exclude(
            expediteur=utilisateur
        ).count()


class Message(models.Model):
    """Message envoyé dans une conversation — diffusé en temps réel via WebSocket (Django Channels)"""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    expediteur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='messages_envoyes'
    )
    contenu = models.TextField()
    date_heure = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    produit = models.ForeignKey(
        Produit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        help_text="Produit concerné si ce message provient d'un clic 'Contacter le vendeur'."
    )

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['date_heure']

    def __str__(self):
        return f"{self.expediteur.username} : {self.contenu[:50]}"