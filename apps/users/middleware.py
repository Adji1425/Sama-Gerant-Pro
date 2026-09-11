class AdminSessionExpiryMiddleware:
    """
    §5.3 du cahier des charges : « Déconnexion Automatique : Le compte
    [administrateur] se déconnecte tout seul dès que l'administrateur
    quitte le site ou ferme son navigateur, pour éviter que quelqu'un
    d'autre n'utilise son accès. »

    On force ici une session "de navigateur" (qui expire à la fermeture
    de l'onglet/navigateur) UNIQUEMENT pour les comptes administrateur.
    Les clients et commerçants gardent une session persistante normale
    (SESSION_COOKIE_AGE), pour ne pas les déconnecter à chaque fermeture
    d'onglet — ce serait une gêne inutile pour eux, et rien dans le
    cahier des charges ne le demande pour ces rôles.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        utilisateur = getattr(request, 'user', None)
        if (
            utilisateur is not None
            and utilisateur.is_authenticated
            and getattr(utilisateur, 'role', None) == 'admin'
        ):
            # 0 = expire à la fermeture du navigateur (comportement
            # standard Django pour une session "non persistante").
            request.session.set_expiry(0)

        return response
