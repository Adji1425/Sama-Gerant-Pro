import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Conversation, Message
from apps.users.models import Commercant


@login_required
def liste_conversations(request):
    """
    Liste toutes les conversations de l'utilisateur connecté.
    Fonctionne pour Client ET Commerçant.
    """
    utilisateur = request.user

    if hasattr(utilisateur, 'client'):
        conversations = Conversation.objects.filter(
            client=utilisateur.client
        ).select_related('commercant__utilisateur').order_by('-date_creation')

    elif hasattr(utilisateur, 'commercant'):
        conversations = Conversation.objects.filter(
            commercant=utilisateur.commercant
        ).select_related('client__utilisateur').order_by('-date_creation')

    else:
        conversations = []

    # Ajouter le dernier message et nb non lus pour chaque conversation
    conversations_data = []
    for conv in conversations:
        dernier = conv.dernier_message()
        non_lus = conv.messages_non_lus(utilisateur)
        conversations_data.append({
            'conv': conv,
            'dernier_message': dernier,
            'non_lus': non_lus,
        })

    context = {
        'conversations_data': conversations_data,
    }
    return render(request, 'messagerie/liste_conversations.html', context)


@login_required
def demarrer_conversation(request, commercant_id):
    """
    Démarre ou récupère une conversation entre le client
    connecté et un commerçant.
    """
    if not hasattr(request.user, 'client'):
        return redirect('home')

    commercant = get_object_or_404(Commercant, pk=commercant_id)
    client = request.user.client

    # Récupérer ou créer la conversation
    conversation, created = Conversation.objects.get_or_create(
        client=client,
        commercant=commercant,
    )

    return redirect('messagerie:chat', conv_id=conversation.id)


@login_required
def chat(request, conv_id):
    """
    Page de chat — les messages sont chargés via AJAX.
    """
    conversation = get_object_or_404(Conversation, pk=conv_id)

    # Vérifier que l'utilisateur fait partie de cette conversation
    utilisateur = request.user
    est_participant = (
        (hasattr(utilisateur, 'client') and
         conversation.client == utilisateur.client)
        or
        (hasattr(utilisateur, 'commercant') and
         conversation.commercant == utilisateur.commercant)
    )

    if not est_participant:
        return redirect('home')

    # Marquer les messages reçus comme lus
    Message.objects.filter(
        conversation=conversation,
        lu=False
    ).exclude(expediteur=utilisateur).update(lu=True)

    # Déterminer l'interlocuteur
    if hasattr(utilisateur, 'client'):
        interlocuteur = conversation.commercant.utilisateur
    else:
        interlocuteur = conversation.client.utilisateur

    context = {
        'conversation': conversation,
        'interlocuteur': interlocuteur,
    }
    return render(request, 'messagerie/chat.html', context)


@login_required
def get_messages_json(request, conv_id):
    """
    Endpoint AJAX — retourne les messages en JSON.
    Appelé toutes les 2 secondes par le JS pour simuler le temps réel.
    """
    conversation = get_object_or_404(Conversation, pk=conv_id)
    utilisateur = request.user

    # Vérification participation
    est_participant = (
        (hasattr(utilisateur, 'client') and
         conversation.client == utilisateur.client)
        or
        (hasattr(utilisateur, 'commercant') and
         conversation.commercant == utilisateur.commercant)
    )
    if not est_participant:
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    # Récupérer uniquement les nouveaux messages si ?depuis= est fourni
    depuis_id = request.GET.get('depuis', 0)
    messages_qs = Message.objects.filter(
        conversation=conversation,
        id__gt=depuis_id
    ).select_related('expediteur').order_by('date_heure')

    # Marquer comme lus
    messages_qs.exclude(expediteur=utilisateur).update(lu=True)

    messages_data = []
    for msg in messages_qs:
        messages_data.append({
            'id': msg.id,
            'contenu': msg.contenu,
            'expediteur': msg.expediteur.get_full_name() or msg.expediteur.username,
            'date_heure': msg.date_heure.strftime('%H:%M'),
            'est_moi': msg.expediteur == utilisateur,
            'lu': msg.lu,
        })

    return JsonResponse({
        'messages': messages_data,
        'total': messages_qs.count(),
    })


@login_required
@require_POST
def envoyer_message(request, conv_id):
    """
    Endpoint AJAX — reçoit et enregistre un message.
    Appelé en POST par le JS quand l'utilisateur envoie un message.
    """
    conversation = get_object_or_404(Conversation, pk=conv_id)
    utilisateur = request.user

    est_participant = (
        (hasattr(utilisateur, 'client') and
         conversation.client == utilisateur.client)
        or
        (hasattr(utilisateur, 'commercant') and
         conversation.commercant == utilisateur.commercant)
    )
    if not est_participant:
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    try:
        data = json.loads(request.body)
        contenu = data.get('contenu', '').strip()
    except json.JSONDecodeError:
        contenu = request.POST.get('contenu', '').strip()

    if not contenu:
        return JsonResponse({'error': 'Message vide'}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        expediteur=utilisateur,
        contenu=contenu,
    )

    return JsonResponse({
        'success': True,
        'message': {
            'id': message.id,
            'contenu': message.contenu,
            'expediteur': utilisateur.get_full_name() or utilisateur.username,
            'date_heure': message.date_heure.strftime('%H:%M'),
            'est_moi': True,
        }
    })