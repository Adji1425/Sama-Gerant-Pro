from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden

from .models import Notification


@login_required
def liste_notifications(request):
    if not hasattr(request.user, 'commercant'):
        return HttpResponseForbidden("Réservé aux commerçants.")

    notifications = Notification.objects.filter(commercant=request.user.commercant)
    return render(request, 'notifications/liste_notifications.html', {'notifications': notifications})


@login_required
def marquer_toutes_lues(request):
    if not hasattr(request.user, 'commercant'):
        return HttpResponseForbidden("Réservé aux commerçants.")

    Notification.objects.filter(commercant=request.user.commercant, lu=False).update(lu=True)
    return redirect('notifications:liste_notifications')
