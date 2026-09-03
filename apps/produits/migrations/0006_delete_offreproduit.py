from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0005_favori'),  # ← mets ici le nom de ta dernière migration produits
    ]

    operations = [
        migrations.DeleteModel(
            name='OffreProduit',
        ),
    ]