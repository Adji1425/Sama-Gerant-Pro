# Nettoyage base de données : suppression de 2 champs jamais utilisés
# nulle part dans le code (ni lus, ni écrits, ni affichés) :
# - Produit.attribut ("Ex: Matière, marque...") — resté invisible côté
#   client et retiré du formulaire d'ajout.
# - ImageProd.nom — jamais renseigné ni affiché.
#
# (ImageProd.couleur existe déjà réellement en base — pas besoin de la
# recréer ici, contrairement à ce qu'une vérification précédente laissait
# penser.)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0008_imageprod_couleur_produit_couleurs_disponibles_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='produit',
            name='attribut',
        ),
        migrations.RemoveField(
            model_name='imageprod',
            name='nom',
        ),
    ]
