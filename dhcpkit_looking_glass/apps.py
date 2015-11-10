"""
App configuration
"""

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DHCPKitLookingGlassConfig(AppConfig):
    """
    DHCPKit Looking Glass config
    """
    name = 'dhcpkit_looking_glass'
    verbose_name = _('DHCPKit Looking Glass')
