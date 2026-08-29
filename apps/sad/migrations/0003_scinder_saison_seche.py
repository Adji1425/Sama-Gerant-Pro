from django.db import migrations


def migrer_saisons(apps, schema_editor):
    """
    Découpe l'ancienne "Saison sèche" (nov→mai, un seul conseil générique)
    en deux saisons distinctes, plus réalistes pour le Sénégal :
      - Saison sèche fraîche (harmattan, déc→fév) : conseils vêtements chauds
      - Saison sèche chaude (mars→mai) : conseils ventilateurs / hydratation
    """
    ConfigurationClimatique = apps.get_model('sad', 'ConfigurationClimatique')

    # On réutilise la ligne "saison_seche" existante pour devenir la
    # "saison sèche fraîche" (nov→fév), plutôt que de la dupliquer.
    ancienne = ConfigurationClimatique.objects.filter(code='saison_seche').first()
    if ancienne:
        ancienne.code = 'saison_seche_fraiche'
        ancienne.nom = 'Saison sèche fraîche'
        ancienne.mois_debut, ancienne.jour_debut = 11, 1
        ancienne.mois_fin, ancienne.jour_fin = 2, 29
        ancienne.conseil = (
            "Harmattan : nuits et matinées fraîches. Forte demande de "
            "pulls, vestes légères et vêtements chauds."
        )
        ancienne.icone = 'bi-cloud-fog2'
        ancienne.save()
    else:
        ConfigurationClimatique.objects.get_or_create(
            code='saison_seche_fraiche',
            defaults=dict(
                nom='Saison sèche fraîche',
                mois_debut=11, jour_debut=1,
                mois_fin=2, jour_fin=29,
                conseil=(
                    "Harmattan : nuits et matinées fraîches. Forte demande "
                    "de pulls, vestes légères et vêtements chauds."
                ),
                icone='bi-cloud-fog2',
                actif=True,
            ),
        )

    ConfigurationClimatique.objects.get_or_create(
        code='saison_seche_chaude',
        defaults=dict(
            nom='Saison sèche chaude',
            mois_debut=3, jour_debut=1,
            mois_fin=5, jour_fin=31,
            conseil=(
                "Chaleur sèche : forte demande en ventilateurs, crèmes "
                "solaires et boissons fraîches."
            ),
            icone='bi-sun',
            actif=True,
        ),
    )


def revenir_en_arriere(apps, schema_editor):
    ConfigurationClimatique = apps.get_model('sad', 'ConfigurationClimatique')
    ConfigurationClimatique.objects.filter(code='saison_seche_chaude').delete()
    fraiche = ConfigurationClimatique.objects.filter(code='saison_seche_fraiche').first()
    if fraiche:
        fraiche.code = 'saison_seche'
        fraiche.nom = 'Saison sèche'
        fraiche.mois_debut, fraiche.jour_debut = 11, 1
        fraiche.mois_fin, fraiche.jour_fin = 5, 31
        fraiche.conseil = "Saison sèche : forte demande en ventilateurs et crèmes."
        fraiche.icone = 'bi-sun'
        fraiche.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sad', '0002_seed_saisons_defaut'),
    ]

    operations = [
        migrations.RunPython(migrer_saisons, revenir_en_arriere),
    ]