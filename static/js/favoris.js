/**
 * Boutons favoris (cœur) — toggle AJAX sans rechargement de page.
 * Fonctionne sur n'importe quel bouton .btn-favori portant un data-produit-id.
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

document.addEventListener('click', function (e) {
  const btn = e.target.closest('.btn-favori');
  if (!btn) return;

  e.preventDefault();
  e.stopPropagation();

  const produitId = btn.dataset.produitId;
  const icon = btn.querySelector('i');
  const csrftoken = getCookie('csrftoken');

  fetch(`/produits/produit/${produitId}/favori/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json',
    },
  })
    .then((res) => {
      if (!res.ok) throw new Error('Erreur réseau');
      return res.json();
    })
    .then((data) => {
      if (data.est_favori) {
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill');
      } else {
        icon.classList.remove('bi-heart-fill');
        icon.classList.add('bi-heart');
      }
      // Petit effet visuel
      btn.style.transform = 'scale(1.2)';
      setTimeout(() => { btn.style.transform = 'scale(1)'; }, 150);
    })
    .catch(() => {
      // Silencieux : si l'utilisateur n'est pas connecté ou erreur réseau,
      // on ne casse pas la navigation.
    });
});
