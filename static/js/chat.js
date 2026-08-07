/**
 * Messagerie en temps réel — Django Channels (WebSocket)
 * Remplace l'ancienne version en AJAX polling.
 */
function initChat(conversationId) {
  const messagesContainer = document.getElementById('messages-container');
  const input = document.getElementById('message-input');
  const btnEnvoyer = document.getElementById('btn-envoyer');
  const statutConnexion = document.getElementById('statut-connexion');
  const wsErreur = document.getElementById('ws-erreur');

  let socket = null;
  let tentativesReconnexion = 0;

  scrollEnBas();

  function scrollEnBas() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function connecter() {
    const protocole = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const url = protocole + window.location.host + '/ws/messagerie/' + conversationId + '/';

    socket = new WebSocket(url);

    socket.onopen = function () {
      tentativesReconnexion = 0;
      if (statutConnexion) statutConnexion.textContent = 'En ligne';
      if (wsErreur) wsErreur.classList.add('d-none');
    };

    socket.onmessage = function (event) {
      const data = JSON.parse(event.data);
      afficherMessage(data);
      scrollEnBas();
    };

    socket.onclose = function (event) {
      if (statutConnexion) statutConnexion.textContent = 'Hors ligne';

      // Fermeture volontaire (accès refusé, non authentifié) : ne pas retenter
      if (event.code === 4001 || event.code === 4003) {
        if (wsErreur) {
          wsErreur.textContent = "Impossible d'accéder à cette conversation.";
          wsErreur.classList.remove('d-none');
        }
        return;
      }

      // Sinon, tentative de reconnexion (perte réseau, redémarrage serveur...)
      if (wsErreur) wsErreur.classList.remove('d-none');
      tentativesReconnexion += 1;
      const delai = Math.min(1000 * tentativesReconnexion, 5000);
      setTimeout(connecter, delai);
    };

    socket.onerror = function () {
      socket.close();
    };
  }

  function afficherMessage(data) {
    const estMoi = data.est_moi;
    const wrapper = document.createElement('div');
    wrapper.className = 'd-flex mb-2 ' + (estMoi ? 'justify-content-end' : 'justify-content-start');

    const bulle = document.createElement('div');
    bulle.className = 'px-3 py-2 rounded-3';
    bulle.style.maxWidth = '70%';
    if (estMoi) {
      bulle.style.backgroundColor = '#1B263B';
      bulle.style.color = 'white';
    } else {
      bulle.style.backgroundColor = 'white';
      bulle.style.color = '#1B263B';
      bulle.style.border = '1px solid #D6E4EC';
    }

    const contenu = document.createElement('div');
    contenu.style.whiteSpace = 'pre-wrap';
    contenu.textContent = data.contenu;

    const heure = document.createElement('div');
    heure.className = 'text-end';
    heure.style.fontSize = '10px';
    heure.style.opacity = '0.7';
    heure.style.marginTop = '2px';
    heure.textContent = data.date_heure;

    bulle.appendChild(contenu);
    bulle.appendChild(heure);
    wrapper.appendChild(bulle);
    messagesContainer.appendChild(wrapper);
  }

  function envoyer() {
    const contenu = input.value.trim();
    if (!contenu) return;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      if (wsErreur) {
        wsErreur.textContent = 'Connexion perdue, tentative de reconnexion...';
        wsErreur.classList.remove('d-none');
      }
      return;
    }

    socket.send(JSON.stringify({ contenu: contenu }));
    input.value = '';
    input.style.height = 'auto';
    input.focus();
  }

  btnEnvoyer.addEventListener('click', envoyer);

  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      envoyer();
    }
  });

  connecter();
}
