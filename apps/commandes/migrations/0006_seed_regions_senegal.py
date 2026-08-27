from django.db import migrations

REGIONS_SENEGAL = [
    "Dakar", "Thiès", "Diourbel", "Fatick", "Kaolack",
    "Kaffrine", "Kédougou", "Kolda", "Louga", "Matam",
    "Saint-Louis", "Sédhiou", "Tambacounda", "Ziguinchor",
]


def seed_regions(apps, schema_editor):
    Region = apps.get_model('commandes', 'Region')
    for nom in REGIONS_SENEGAL:
        Region.objects.get_or_create(nom=nom)


def unseed_regions(apps, schema_editor):
    Region = apps.get_model('commandes', 'Region')
    Region.objects.filter(nom__in=REGIONS_SENEGAL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('commandes', '0005_region_commande_commune_commande_region'),
    ]

    operations = [
        migrations.RunPython(seed_regions, unseed_regions),
    ]
