#!/bin/bash
# ============================================================
#  Sama-Gérant Pro — Script de création de la structure
#  Licence 3 Informatique — UCAD 2025-2026
#  Adji Mbaw NDIAYE & Mame Diarra Bousso VILANE
# ============================================================

echo "============================================"
echo "  Sama-Gérant Pro — Setup du projet"
echo "============================================"

# ── 1. Dossiers ──────────────────────────────────────────────
echo "[1/5] Création des dossiers..."

mkdir -p config
mkdir -p apps/users/templates/users
mkdir -p apps/produits/templates/produits
mkdir -p apps/commandes/templates/commandes
mkdir -p apps/facturation/templates/facturation
mkdir -p apps/messagerie/templates/messagerie
mkdir -p apps/avis/templates/avis
mkdir -p apps/notifications/templates/notifications
mkdir -p apps/sad/templates/sad
mkdir -p apps/evenements/templates/evenements
mkdir -p static/css
mkdir -p static/js
mkdir -p static/img
mkdir -p media/produits
mkdir -p media/factures
mkdir -p media/profils
mkdir -p media/logos
mkdir -p templates

echo "  ✓ Dossiers créés"

# ── 2. Fichiers racine ───────────────────────────────────────
echo "[2/5] Création des fichiers racine..."

touch manage.py
touch requirements.txt

cat > .env.example << 'EOF'
SECRET_KEY=change_moi_en_production
DEBUG=True
DB_NAME=sama_gerant_db
DB_USER=postgres
DB_PASSWORD=ton_mot_de_passe
DB_HOST=localhost
DB_PORT=5432
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=ton_email@gmail.com
EMAIL_HOST_PASSWORD=ton_mot_de_passe_app
EOF

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*.pyo
venv/
env/
.env
*.sqlite3

# Media et fichiers uploadés
media/

# IDE
.vscode/
.idea/
*.swp

# Node (si besoin)
node_modules/
dist/

# OS
.DS_Store
Thumbs.db
EOF

echo "  ✓ Fichiers racine créés"

# ── 3. Config Django ─────────────────────────────────────────
echo "[3/5] Création de la config Django..."

touch config/__init__.py
touch config/wsgi.py

cat > config/urls.py << 'EOF'
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.produits.urls')),
    path('users/', include('apps.users.urls')),
    path('commandes/', include('apps.commandes.urls')),
    path('facturation/', include('apps.facturation.urls')),
    path('messagerie/', include('apps.messagerie.urls')),
    path('avis/', include('apps.avis.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('sad/', include('apps.sad.urls')),
    path('evenements/', include('apps.evenements.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
EOF

cat > config/settings.py << 'EOF'
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps du projet
    'apps.users',
    'apps.produits',
    'apps.commandes',
    'apps.facturation',
    'apps.messagerie',
    'apps.avis',
    'apps.notifications',
    'apps.sad',
    'apps.evenements',
    # Packages
    'crispy_forms',
    'crispy_bootstrap5',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'sama_gerant_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_USER_MODEL = 'users.Utilisateur'

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/users/login/'
EOF

echo "  ✓ Config Django créée"

# ── 4. Apps ──────────────────────────────────────────────────
echo "[4/5] Création des apps..."

# Fonction pour créer une app
create_app() {
    APP=$1
    touch apps/$APP/__init__.py
    touch apps/$APP/admin.py
    touch apps/$APP/forms.py
    touch apps/$APP/views.py
    touch apps/$APP/urls.py
    cat > apps/$APP/apps.py << APPEOF
from django.apps import AppConfig

class $(echo "${APP^}")Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.$APP'
APPEOF
}

# ── users ──
create_app users
cat > apps/users/models.py << 'EOF'
from django.db import models
from django.contrib.auth.models import AbstractUser


class Utilisateur(AbstractUser):
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('commercant', 'Commerçant'),
        ('admin', 'Administrateur'),
    ]
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    photo_profile = models.ImageField(upload_to='profils/', blank=True, null=True)

    class Meta:
        verbose_name = "Utilisateur"

    def __str__(self):
        return f"{self.username} ({self.role})"


class Client(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, on_delete=models.CASCADE, related_name='client'
    )
    adresse_livraison = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Client"

    def __str__(self):
        return f"Client : {self.utilisateur.get_full_name()}"


class Commercant(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, on_delete=models.CASCADE, related_name='commercant'
    )
    nom_boutique = models.CharField(max_length=150)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)

    class Meta:
        verbose_name = "Commerçant"

    def __str__(self):
        return self.nom_boutique


class Administrateur(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, on_delete=models.CASCADE, related_name='administrateur'
    )

    class Meta:
        verbose_name = "Administrateur"

    def __str__(self):
        return f"Admin : {self.utilisateur.get_full_name()}"
EOF

# ── produits ──
create_app produits
cat > apps/produits/models.py << 'EOF'
from django.db import models
from apps.users.models import Commercant


class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Catégorie"

    def __str__(self):
        return self.nom


class Produit(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('archive', 'Archivé'),
    ]
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='produits'
    )
    categorie = models.ForeignKey(
        Categorie, on_delete=models.SET_NULL, null=True, related_name='produits'
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prix_achat = models.FloatField()
    prix_vente = models.FloatField()
    frais_packaging = models.FloatField(default=0)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='actif')
    quantite = models.IntegerField(default=0)
    seuil_alerte = models.IntegerField(default=5)
    seuil_dormant = models.IntegerField(default=60)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produit"

    def __str__(self):
        return self.nom

    def marge_nette(self):
        return self.prix_vente - self.prix_achat - self.frais_packaging

    def est_en_alerte(self):
        return self.quantite <= self.seuil_alerte

    def note_moyenne(self):
        avis = self.avis_set.all()
        if avis.exists():
            return round(sum(a.note for a in avis) / avis.count(), 1)
        return 0


class ImageProd(models.Model):
    produit = models.ForeignKey(
        Produit, on_delete=models.CASCADE, related_name='images'
    )
    url = models.ImageField(upload_to='produits/')
    nom = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Image Produit"

    def __str__(self):
        return f"Image de {self.produit.nom}"


class OffreProduit(models.Model):
    produit = models.OneToOneField(
        Produit, on_delete=models.CASCADE, related_name='offre'
    )
    titre = models.CharField(max_length=150)
    taux = models.FloatField(help_text="Taux de réduction en %")
    description = models.TextField(blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField()

    class Meta:
        verbose_name = "Offre Produit"

    def __str__(self):
        return f"{self.titre} - {self.taux}%"

    def est_active(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.date_debut <= today <= self.date_fin


class Depense(models.Model):
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='depenses'
    )
    montant = models.FloatField()
    date = models.DateField()
    type = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Dépense"

    def __str__(self):
        return f"{self.type} - {self.montant} FCFA"
EOF

# ── commandes ──
create_app commandes
cat > apps/commandes/models.py << 'EOF'
from django.db import models
from apps.users.models import Client
from apps.produits.models import Produit, OffreProduit


class Panier(models.Model):
    client = models.OneToOneField(
        Client, on_delete=models.CASCADE, related_name='panier'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Panier"

    def __str__(self):
        return f"Panier de {self.client}"

    def total(self):
        return sum(ligne.sous_total() for ligne in self.lignes.all())

    def vider(self):
        self.lignes.all().delete()


class LignePanier(models.Model):
    panier = models.ForeignKey(
        Panier, on_delete=models.CASCADE, related_name='lignes'
    )
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.IntegerField(default=1)
    prix_unitaire_snapshot = models.FloatField()

    class Meta:
        verbose_name = "Ligne Panier"

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom}"

    def sous_total(self):
        return self.quantite * self.prix_unitaire_snapshot


class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_preparation', 'En préparation'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='commandes'
    )
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='en_attente'
    )
    adresse_livraison_reel = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20)
    montant_total = models.FloatField(default=0)

    class Meta:
        verbose_name = "Commande"
        ordering = ['-date_commande']

    def __str__(self):
        return f"Commande #{self.id} - {self.client}"

    def calculer_montant(self):
        total = sum(d.sous_total() for d in self.details.all())
        self.montant_total = total
        self.save()


class DetailsCommande(models.Model):
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name='details'
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.SET_NULL, null=True
    )
    offre = models.ForeignKey(
        OffreProduit, on_delete=models.SET_NULL, null=True, blank=True
    )
    quantite = models.IntegerField()
    prix_unitaire_vente = models.FloatField()

    class Meta:
        verbose_name = "Détail Commande"

    def __str__(self):
        return f"{self.quantite} x {self.produit}"

    def sous_total(self):
        if self.offre and self.offre.est_active():
            remise = self.prix_unitaire_vente * (self.offre.taux / 100)
            return self.quantite * (self.prix_unitaire_vente - remise)
        return self.quantite * self.prix_unitaire_vente
EOF

# ── facturation ──
create_app facturation
cat > apps/facturation/models.py << 'EOF'
from django.db import models
from apps.commandes.models import Commande


class Facture(models.Model):
    commande = models.OneToOneField(
        Commande, on_delete=models.CASCADE, related_name='facture'
    )
    pdf_url = models.FileField(upload_to='factures/', blank=True, null=True)
    date_facture = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Facture"

    def __str__(self):
        return f"Facture #{self.id} - Commande #{self.commande.id}"
EOF

# ── messagerie ──
create_app messagerie
cat > apps/messagerie/models.py << 'EOF'
from django.db import models
from apps.users.models import Client, Commercant, Utilisateur


class Conversation(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='conversations'
    )
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='conversations'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conversation"
        unique_together = ('client', 'commercant')

    def __str__(self):
        return f"{self.client} <-> {self.commercant}"

    def dernier_message(self):
        return self.messages.order_by('-date_heure').first()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    expediteur = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE
    )
    contenu = models.TextField()
    date_heure = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Message"
        ordering = ['date_heure']

    def __str__(self):
        return f"{self.expediteur} : {self.contenu[:40]}"
EOF

# ── avis ──
create_app avis
cat > apps/avis/models.py << 'EOF'
from django.db import models
from apps.users.models import Client
from apps.produits.models import Produit
from apps.commandes.models import DetailsCommande


class Avis(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='avis'
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.CASCADE, related_name='avis_set'
    )
    details_commande = models.ForeignKey(
        DetailsCommande, on_delete=models.SET_NULL,
        null=True, related_name='avis'
    )
    note = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaire = models.TextField(blank=True)
    date_avis = models.DateField(auto_now_add=True)
    verifie_achat = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Avis"
        unique_together = ('client', 'produit')

    def __str__(self):
        return f"Avis {self.note}/5 sur {self.produit.nom}"
EOF

# ── notifications ──
create_app notifications
cat > apps/notifications/models.py << 'EOF'
from django.db import models
from apps.users.models import Commercant


class Notification(models.Model):
    TYPE_CHOICES = [
        ('stock_bas', 'Stock bas'),
        ('stock_dormant', 'Stock dormant'),
        ('evenement', 'Événement'),
        ('commande', 'Nouvelle commande'),
        ('saison', 'Alerte saison'),
    ]
    commercant = models.ForeignKey(
        Commercant, on_delete=models.CASCADE, related_name='notifications'
    )
    titre = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Notification"
        ordering = ['-date_envoi']

    def __str__(self):
        return f"[{self.type}] {self.titre}"
EOF

# ── sad ──
create_app sad
touch apps/sad/models.py
cat > apps/sad/utils.py << 'EOF'
from django.utils import timezone
from datetime import timedelta
from apps.produits.models import Produit
from apps.commandes.models import DetailsCommande

# Saisons sénégalaises (constantes dans settings, pas de table BDD)
SAISONS_SENEGAL = {
    "hivernage":   {"debut": (6, 1),  "fin": (10, 31)},
    "saison_seche": {"debut": (11, 1), "fin": (5, 31)},
}


def calculer_marge_nette(produit):
    return produit.prix_vente - produit.prix_achat - produit.frais_packaging


def identifier_top_produits(commercant, limite=5):
    from django.db.models import Sum
    return (
        DetailsCommande.objects
        .filter(produit__commercant=commercant)
        .values('produit__nom', 'produit__id')
        .annotate(total_vendu=Sum('quantite'))
        .order_by('-total_vendu')[:limite]
    )


def identifier_stocks_dormants(commercant, jours=60):
    date_limite = timezone.now().date() - timedelta(days=jours)
    produits_actifs = Produit.objects.filter(
        commercant=commercant, statut='actif'
    )
    dormants = []
    for produit in produits_actifs:
        derniere_vente = (
            DetailsCommande.objects
            .filter(produit=produit)
            .order_by('-commande__date_commande')
            .first()
        )
        if not derniere_vente or \
           derniere_vente.commande.date_commande.date() < date_limite:
            dormants.append(produit)
    return dormants


def get_saison_actuelle():
    mois = timezone.now().date().month
    if 6 <= mois <= 10:
        return "hivernage"
    return "saison_seche"
EOF

# ── evenements ──
create_app evenements
cat > apps/evenements/models.py << 'EOF'
from django.db import models


class EvenementSAD(models.Model):
    nom_evenement = models.CharField(max_length=150)
    date_debut = models.DateField()
    date_fin = models.DateField()
    conseil_affiche = models.TextField(
        help_text="Conseil affiché au commerçant avant cet événement"
    )

    class Meta:
        verbose_name = "Événement SAD"
        ordering = ['date_debut']

    def __str__(self):
        return self.nom_evenement

    def est_proche(self, jours=21):
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now().date()
        return today <= self.date_debut <= today + timedelta(days=jours)
EOF

echo "  ✓ Apps créées avec models.py"

# ── 5. Templates de base ──────────────────────────────────────
echo "[5/5] Création des templates de base..."

cat > templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Sama-Gérant Pro{% endblock %}</title>
  <!-- Bootstrap 5 -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  {% load static %}
  <link rel="stylesheet" href="{% static 'css/custom.css' %}">
  {% block extra_css %}{% endblock %}
</head>
<body class="bg-gray-50">

  <!-- Navbar -->
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container">
      <a class="navbar-brand fw-bold" href="/">🛍️ Sama-Gérant Pro</a>
      <div class="collapse navbar-collapse">
        <ul class="navbar-nav ms-auto">
          {% if user.is_authenticated %}
            <li class="nav-item">
              <a class="nav-link" href="/users/profil/">Mon profil</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="/users/logout/">Déconnexion</a>
            </li>
          {% else %}
            <li class="nav-item">
              <a class="nav-link" href="/users/login/">Connexion</a>
            </li>
            <li class="nav-item">
              <a class="nav-link" href="/users/register/">Inscription</a>
            </li>
          {% endif %}
        </ul>
      </div>
    </div>
  </nav>

  <!-- Messages Django -->
  <div class="container mt-2">
    {% for message in messages %}
      <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    {% endfor %}
  </div>

  <!-- Contenu principal -->
  <main class="container my-4">
    {% block content %}{% endblock %}
  </main>

  <!-- Footer -->
  <footer class="bg-dark text-white text-center py-3 mt-5">
    <small>Sama-Gérant Pro &copy; 2025 — UCAD Licence 3 Informatique</small>
  </footer>

  <!-- Bootstrap JS -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
EOF

cat > static/css/custom.css << 'EOF'
/* Sama-Gérant Pro — Styles personnalisés */

:root {
  --navy: #1B263B;
  --gold: #E0A458;
  --rose: #C47B8A;
  --mist: #D6E4EC;
  --bg: #FEF9F6;
}

body {
  font-family: 'Segoe UI', Tahoma, sans-serif;
}

.btn-primary {
  background-color: var(--navy);
  border-color: var(--navy);
}

.btn-primary:hover {
  background-color: var(--gold);
  border-color: var(--gold);
  color: var(--navy);
}

.card {
  border: none;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.navbar {
  background-color: var(--navy) !important;
}
EOF

cat > static/js/chat.js << 'EOF'
// Sama-Gérant Pro — Messagerie AJAX
// Charge les messages toutes les 2 secondes sans recharger la page

function chargerMessages(conversationId) {
  fetch(`/messagerie/messages/${conversationId}/`)
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('messages-container');
      container.innerHTML = '';
      data.messages.forEach(msg => {
        const div = document.createElement('div');
        div.className = `message ${msg.est_moi ? 'moi' : 'autre'}`;
        div.innerHTML = `<p>${msg.contenu}</p><small>${msg.date_heure}</small>`;
        container.appendChild(div);
      });
      container.scrollTop = container.scrollHeight;
    });
}

function envoyerMessage(conversationId, csrfToken) {
  const contenu = document.getElementById('message-input').value;
  if (!contenu.trim()) return;

  fetch(`/messagerie/envoyer/${conversationId}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify({ contenu: contenu }),
  })
  .then(res => res.json())
  .then(() => {
    document.getElementById('message-input').value = '';
    chargerMessages(conversationId);
  });
}
EOF

cat > requirements.txt << 'EOF'
django==4.2
psycopg2-binary==2.9
Pillow==10.2
xhtml2pdf==0.2.13
python-dotenv==1.0
django-crispy-forms==2.1
crispy-bootstrap5==0.7
EOF

echo "  ✓ Templates et fichiers statiques créés"

# ── Résumé final ─────────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ Structure créée avec succès !"
echo "============================================"
echo ""
echo "Prochaines étapes :"
echo ""
echo "  1. Copie .env.example en .env et remplis les variables :"
echo "     cp .env.example .env"
echo ""
echo "  2. Crée un environnement virtuel Python :"
echo "     python -m venv venv"
echo "     source venv/bin/activate   (Mac/Linux)"
echo "     venv\\Scripts\\activate      (Windows)"
echo ""
echo "  3. Installe les dépendances :"
echo "     pip install -r requirements.txt"
echo ""
echo "  4. Lance les migrations :"
echo "     python manage.py makemigrations"
echo "     python manage.py migrate"
echo ""
echo "  5. Crée un superutilisateur :"
echo "     python manage.py createsuperuser"
echo ""
echo "  6. Lance le serveur :"
echo "     python manage.py runserver"
echo ""
echo "============================================"
