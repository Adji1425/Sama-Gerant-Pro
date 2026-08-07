import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Gère une connexion WebSocket pour une conversation donnée.
    Un groupe Channels = une conversation ("chat_<id>").
    Tous les onglets/utilisateurs connectés à ce groupe reçoivent
    instantanément chaque nouveau message.
    """

    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f'chat_{self.conversation_id}'

        # Refuser si non authentifié
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Refuser si l'utilisateur ne fait pas partie de la conversation
        autorise = await self._est_participant()
        if not autorise:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Marquer comme lus les messages reçus avant l'ouverture du chat
        await self._marquer_comme_lus()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def receive(self, text_data):
        """Reçoit un message envoyé par le client via le WebSocket"""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        contenu = (data.get('contenu') or '').strip()
        if not contenu:
            return

        message = await self._creer_message(contenu)

        # Diffuse le message à tous les participants connectés au groupe
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'id': message.id,
                'contenu': message.contenu,
                'expediteur_id': self.user.id,
                'expediteur': self.user.get_full_name() or self.user.username,
                'date_heure': message.date_heure.strftime('%H:%M'),
            }
        )

    async def chat_message(self, event):
        """Reçoit un message du groupe et le pousse au client WebSocket"""
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'contenu': event['contenu'],
            'expediteur': event['expediteur'],
            'date_heure': event['date_heure'],
            'est_moi': event['expediteur_id'] == self.user.id,
        }))

    # -- Helpers base de données (synchrones -> exécutés dans un thread) --

    @database_sync_to_async
    def _est_participant(self):
        try:
            conversation = Conversation.objects.select_related(
                'client__utilisateur', 'commercant__utilisateur'
            ).get(pk=self.conversation_id)
        except Conversation.DoesNotExist:
            return False

        return (
            (hasattr(self.user, 'client') and conversation.client_id == self.user.client.id)
            or
            (hasattr(self.user, 'commercant') and conversation.commercant_id == self.user.commercant.id)
        )

    @database_sync_to_async
    def _creer_message(self, contenu):
        return Message.objects.create(
            conversation_id=self.conversation_id,
            expediteur=self.user,
            contenu=contenu,
        )

    @database_sync_to_async
    def _marquer_comme_lus(self):
        Message.objects.filter(
            conversation_id=self.conversation_id, lu=False
        ).exclude(expediteur=self.user).update(lu=True)
