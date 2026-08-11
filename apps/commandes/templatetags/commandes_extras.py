from django import template

register = template.Library()


@register.filter
def dictattr(d, key):
    """Accès à un dict avec une clé variable : {{ mon_dict|dictattr:ma_cle }}"""
    if not d:
        return None
    return d.get(key)