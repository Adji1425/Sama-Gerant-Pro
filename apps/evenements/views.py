from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from apps.users.views import admin_required
from .models import EvenementSAD
from .forms import EvenementSADForm


@admin_required
def liste_evenements(request):
    """
    Maintenance du calendrier des événements sociaux et religieux
    (§5.3.2 du cahier des charges : Tabaski, Magal, Korité, etc.)
    """
    evenements = EvenementSAD.objects.all().order_by('date_debut')
    return render(request, 'evenements/liste_evenements.html', {
        'evenements': evenements,
    })


@admin_required
def creer_evenement(request):
    if request.method == 'POST':
        form = EvenementSADForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✓ Événement ajouté au calendrier.")
            return redirect('evenements:liste_evenements')
    else:
        form = EvenementSADForm()
    return render(request, 'evenements/form_evenement.html', {
        'form': form, 'titre': "Ajouter un événement",
    })


@admin_required
def modifier_evenement(request, pk):
    evenement = get_object_or_404(EvenementSAD, pk=pk)
    if request.method == 'POST':
        form = EvenementSADForm(request.POST, instance=evenement)
        if form.is_valid():
            form.save()
            messages.success(request, "✓ Événement mis à jour.")
            return redirect('evenements:liste_evenements')
    else:
        form = EvenementSADForm(instance=evenement)
    return render(request, 'evenements/form_evenement.html', {
        'form': form, 'titre': f"Modifier « {evenement.nom_evenement} »",
    })


@admin_required
def supprimer_evenement(request, pk):
    evenement = get_object_or_404(EvenementSAD, pk=pk)
    if request.method == 'POST':
        nom = evenement.nom_evenement
        evenement.delete()
        messages.success(request, f"✓ « {nom} » a été retiré du calendrier.")
        return redirect('evenements:liste_evenements')
    return render(request, 'evenements/confirmer_suppression.html', {
        'evenement': evenement,
    })