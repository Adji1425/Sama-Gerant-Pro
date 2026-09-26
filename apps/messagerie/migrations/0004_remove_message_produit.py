# Nettoyage base de données : Message.produit n'a jamais été renseigné
# ni lu nulle part dans le code (seul Conversation.produit_contexte est
# réellement utilisé pour afficher le produit concerné par une
# conversation). Colonne + clé étrangère supprimées.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('messagerie', '0003_conversation_produit_contexte_message_produit'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='produit',
        ),
    ]
