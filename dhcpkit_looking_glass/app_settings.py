"""
Handle app settings in a central place
"""
import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Limit the maximum number of transactions per client/server combination
MAX_TRANSACTIONS = getattr(settings, 'DHCPKIT_LG_MAX_TRANSACTIONS', 20)
if MAX_TRANSACTIONS and not isinstance(MAX_TRANSACTIONS, int):
    raise ImproperlyConfigured("DHCPKIT_LG_MAX_TRANSACTIONS must be None or an integer")

# Limit the maximum age of transactions
MAX_TRANSACTION_AGE = getattr(settings, 'DHCPKIT_LG_MAX_TRANSACTION_AGE', datetime.timedelta(days=7))
if MAX_TRANSACTION_AGE and not isinstance(MAX_TRANSACTION_AGE, datetime.timedelta):
    raise ImproperlyConfigured("DHCPKIT_LG_MAX_TRANSACTIONS must be None or a timedelta")
