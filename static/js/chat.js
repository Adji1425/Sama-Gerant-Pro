// ── Sama-Gérant Pro — Messagerie AJAX ────────────────────────────────────────
// Polling toutes les 2 secondes pour simuler le temps réel sans WebSocket

let dernierMessageId = 0;
let intervalPolling = null;

/**
 * Charge les nouveaux messages depuis le serveur
 */
function chargerNouveauxMessages(convId) {
    fetch(`/messagerie/messages/${convId}/json/?depuis=${dernierMessageId}`)
        .then(res => res.json())
        .then(data => {
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    afficherMessage(msg);
                    dernierMessageId = Math.max(dernierMessageId, msg.id);
                });
                scrollEnBas();
            }
        })
        .catch(err => console.error('Erreur chargement messages:', err));
}

/**
 * Crée et affiche une bulle de message dans le conteneur
 */
function afficherMessage(msg) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    // Éviter les doublons
    if (document.getElementById(`msg-${msg.id}`)) return;

    const div = document.createElement('div');
    div.id = `msg-${msg.id}`;
    div.className = `d-flex mb-3 ${msg.est_moi ? 'justify-content-end' : 'justify-content-start'}`;

    div.innerHTML = `
        <div style="
            max-width: 70%;
            background-color: ${msg.est_moi ? '#1B263B' : '#F0F0F0'};
            color: ${msg.est_moi ? 'white' : '#1B263B'};
            border-radius: ${msg.est_moi ? '18px 18px 4px 18px' : '18px 18px 18px 4px'};
            padding: 10px 14px;
            word-wrap: break-word;
        ">
            <div style="font-size: 13px; line-height: 1.4;">${escapeHtml(msg.contenu)}</div>
            <div style="
                font-size: 10px;
                opacity: 0.7;
                margin-top: 4px;
                text-align: right;
            ">
                ${msg.date_heure}
                ${msg.est_moi ? (msg.lu ? ' ✓✓' : ' ✓') : ''}
            </div>
        </div>
    `;

    container.appendChild(div);
}

/**
 * Envoie un message via AJAX
 */
function envoyerMessage(convId, csrfToken) {
    const input = document.getElementById('message-input');
    if (!input) return;

    const contenu = input.value.trim();
    if (!contenu) return;

    // Désactiver le bouton pendant l'envoi
    const btn = document.getElementById('btn-envoyer');
    if (btn) btn.disabled = true;

    fetch(`/messagerie/envoyer/${convId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ contenu: contenu }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            input.value = '';
            afficherMessage(data.message);
            dernierMessageId = Math.max(dernierMessageId, data.message.id);
            scrollEnBas();
        }
    })
    .catch(err => console.error('Erreur envoi message:', err))
    .finally(() => {
        if (btn) btn.disabled = false;
        input.focus();
    });
}

/**
 * Scroll automatique vers le bas
 */
function scrollEnBas() {
    const container = document.getElementById('messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Échappe le HTML pour éviter les injections XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

/**
 * Initialisation au chargement de la page chat
 */
function initChat(convId, csrfToken) {
    // Charger les messages existants au démarrage
    chargerTousLesMessages(convId);

    // Démarrer le polling toutes les 2 secondes
    intervalPolling = setInterval(() => {
        chargerNouveauxMessages(convId);
    }, 2000);

    // Envoi avec le bouton
    const btn = document.getElementById('btn-envoyer');
    if (btn) {
        btn.addEventListener('click', () => {
            envoyerMessage(convId, csrfToken);
        });
    }

    // Envoi avec Entrée (Shift+Entrée pour saut de ligne)
    const input = document.getElementById('message-input');
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                envoyerMessage(convId, csrfToken);
            }
        });
    }
}

/**
 * Charge tous les messages existants au premier chargement
 */
function chargerTousLesMessages(convId) {
    fetch(`/messagerie/messages/${convId}/json/?depuis=0`)
        .then(res => res.json())
        .then(data => {
            if (data.messages) {
                data.messages.forEach(msg => {
                    afficherMessage(msg);
                    if (msg.id > dernierMessageId) {
                        dernierMessageId = msg.id;
                    }
                });
                scrollEnBas();
            }
        })
        .catch(err => console.error('Erreur chargement initial:', err));
}

// Arrêter le polling quand on quitte la page
window.addEventListener('beforeunload', () => {
    if (intervalPolling) clearInterval(intervalPolling);
});