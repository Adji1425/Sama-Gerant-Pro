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
