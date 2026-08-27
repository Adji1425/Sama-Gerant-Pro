from django.db import migrations


def seed_saisons(apps, schema_editor):
    ConfigurationClimatique = apps.get_model('sad', 'ConfigurationClimatique')
    ConfigurationClimatique.objects.get_or_create(
        code='hivernage',
        defaults=dict(
            nom='Hivernage',
            mois_debut=6, jour_debut=1,
            mois_fin=10, jour_fin=31,
            conseil="Pensez aux imperméables, bottes et parapluies !",
            icone='bi-cloud-rain-heavy',
            actif=True,
        ),
    )
    ConfigurationClimatique.objects.get_or_create(
        code='saison_seche',
        defaults=dict(
            nom='Saison sèche',
            mois_debut=11, jour_debut=1,
            mois_fin=5, jour_fin=31,
            conseil="Saison sèche : forte demande en ventilateurs et crèmes.",
            icone='bi-sun',
            actif=True,
        ),
    )


def unseed_saisons(apps, schema_editor):
    ConfigurationClimatique = apps.get_model('sad', 'ConfigurationClimatique')
    ConfigurationClimatique.objects.filter(
        code__in=['hivernage', 'saison_seche']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sad', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_saisons, unseed_saisons),
    ]
