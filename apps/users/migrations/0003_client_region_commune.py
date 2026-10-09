from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_administrateur_options_alter_client_options_and_more'),
        ('commandes', '0006_seed_regions_senegal'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='clients', to='commandes.region'),
        ),
        migrations.AddField(
            model_name='client',
            name='commune',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
