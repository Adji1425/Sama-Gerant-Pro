from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('commandes', '0006_seed_regions_senegal'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lignepanier',
            name='offre',
        ),
    ]