import random
from django.core.management.base import BaseCommand, CommandError
from apps.users.models import Commercant
from apps.produits.models import Categorie, Produit


# (nom, catégorie, prix_achat, prix_vente, attribut)
# Prix cohérents : prix_vente toujours > prix_achat (respecte la
# validation anti-vente-à-perte du formulaire produit).
PRODUITS_EXEMPLE = [
    ("Sac à main cuir", "sac", 6000, 9500, "Couleur : Noir"),
    ("Sac bandoulière toile", "sac", 3000, 5000, "Couleur : Beige"),
    ("Sac week-end", "sac", 8000, 13000, "Taille : L"),
    ("Pochette soirée", "sac", 2500, 4500, "Couleur : Doré"),
    ("Sac à dos scolaire", "sac", 4000, 7000, "Couleur : Bleu"),
    ("Basket blanche unisexe", "chaussures", 7000, 11000, "Pointure : 40-44"),
    ("Sandales cuir homme", "chaussures", 5000, 8500, "Pointure : 41-45"),
    ("Escarpins femme", "chaussures", 6000, 10000, "Couleur : Noir"),
    ("Tongs plage", "chaussures", 1000, 2000, "Pointure : 36-45"),
    ("Bottines femme", "chaussures", 8000, 13500, "Couleur : Marron"),
    ("Boubou wax homme", "vêtements", 9000, 15000, "Taille : M-XL"),
    ("Robe wax femme", "vêtements", 7000, 12000, "Taille : S-L"),
    ("Chemise coton homme", "vêtements", 4000, 7000, "Taille : M-XXL"),
    ("Ensemble taille haute", "vêtements", 5000, 9000, "Taille : S-M"),
    ("Jean slim unisexe", "vêtements", 4500, 8000, "Taille : 30-38"),
    ("Montre classique", "montres", 5000, 9000, "Couleur : Argent"),
    ("Montre connectée", "montres", 12000, 19500, "Couleur : Noir"),
    ("Bracelet perles", "bijoux", 1500, 3000, "Matière : Perles naturelles"),
    ("Collier doré", "bijoux", 2000, 4000, "Couleur : Doré"),
    ("Boucles d'oreilles", "bijoux", 1000, 2500, "Matière : Acier inoxydable"),
    ("Crème hydratante visage", "beauté", 2000, 3500, "Volume : 50ml"),
    ("Huile capillaire naturelle", "beauté", 1500, 3000, "Volume : 100ml"),
    ("Parfum femme", "beauté", 4000, 7500, "Volume : 50ml"),
    ("Savon noir traditionnel", "beauté", 800, 1800, "Poids : 250g"),
    ("Rouge à lèvres mat", "beauté", 1200, 2500, "Couleur : Rouge"),
    ("Écouteurs sans fil", "high-tech", 5000, 9000, "Couleur : Noir"),
    ("Powerbank 10000mAh", "high-tech", 6000, 10500, ""),
    ("Chargeur rapide type-C", "high-tech", 2000, 4000, ""),
    ("Coque téléphone universelle", "high-tech", 1000, 2200, "Couleur : Transparent"),
    ("Enceinte Bluetooth portable", "high-tech", 8000, 14000, "Couleur : Rouge"),
    ("Casquette brodée", "accessoires", 1500, 3000, "Taille unique"),
    ("Ceinture cuir homme", "accessoires", 2500, 4500, "Taille : 85-105"),
    ("Lunettes de soleil", "accessoires", 2000, 4000, "Couleur : Noir"),
    ("Foulard imprimé wax", "accessoires", 1500, 3200, "Taille unique"),
    ("Portefeuille cuir", "accessoires", 3000, 5500, "Couleur : Marron"),
]


class Command(BaseCommand):
    """
    Crée en masse des produits d'exemple (nom, catégorie, prix, attribut)
    pour un commerçant donné, sans photo — le commerçant les ajoutera
    lui-même ensuite depuis "Modifier produit".

    Usage :
        python manage.py seed_produits --commercant <username>
        python manage.py seed_produits --commercant <username> --nombre 40
    """
    help = "Crée des produits d'exemple pour un commerçant (sans photos)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--commercant', type=str, required=True,
            help="Username de l'utilisateur commerçant."
        )
        parser.add_argument(
            '--nombre', type=int, default=30,
            help="Nombre de produits à créer (30 par défaut)."
        )

    def handle(self, *args, **options):
        username = options['commercant']
        nombre = options['nombre']

        try:
            commercant = Commercant.objects.get(utilisateur__username=username)
        except Commercant.DoesNotExist:
            raise CommandError(
                f"Aucun commerçant trouvé avec le username '{username}'."
            )

        source = PRODUITS_EXEMPLE.copy()
        random.shuffle(source)

        # Si on demande plus de produits que la liste d'exemple n'en
        # contient, on recycle la liste en variant légèrement le nom.
        produits_a_creer = []
        i = 0
        while len(produits_a_creer) < nombre:
            nom, cat, achat, vente, attribut = source[i % len(source)]
            tour = i // len(source)
            nom_final = nom if tour == 0 else f"{nom} ({tour + 1})"
            produits_a_creer.append((nom_final, cat, achat, vente, attribut))
            i += 1

        crees = 0
        for nom, cat_nom, prix_achat, prix_vente, attribut in produits_a_creer:
            categorie, _ = Categorie.objects.get_or_create(nom=cat_nom)

            if Produit.objects.filter(commercant=commercant, nom=nom).exists():
                continue

            Produit.objects.create(
                commercant=commercant,
                categorie=categorie,
                nom=nom,
                description="",
                prix_achat=prix_achat,
                prix_vente=prix_vente,
                frais_packaging=0,
                attribut=attribut,
                quantite=random.randint(5, 25),
                statut='actif',
            )
            crees += 1

        self.stdout.write(self.style.SUCCESS(
            f"✓ {crees} produit(s) créé(s) pour '{commercant.nom_boutique}' "
            f"(sans photo — à ajouter ensuite depuis l'espace commerçant)."
        ))