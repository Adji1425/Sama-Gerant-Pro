from django.db import models
from apps.users.models import Client, Commercant, Utilisateur


class Conversation(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='conversations'
    )
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='conversations'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conversation"
        unique_together = ('client', 'commercant')

    def __str__(self):
        return f"{self.client} <-> {self.commercant}"

    def dernier_message(self):
        return self.messages.order_by('-date_heure').first()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    expediteur = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE
    )
    contenu = models.TextField()
    date_heure = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Message"
        ordering = ['date_heure']

    def __str__(self):
        return f"{self.expediteur} : {self.contenu[:40]}"
