"""
Admin settings for the dhcpkit looking glass
"""

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Count
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _, ungettext

from dhcpkit_looking_glass.filters import MultipleDUIDFilter, DuplicateDUIDFilter, ResponseFilter
from dhcpkit_looking_glass.models import Client, Server, Transaction


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    """
    Admin interface for servers
    """
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Admin interface for clients
    """
    list_display = ('admin_duid', 'interface_id', 'remote_id', 'admin_transactions_link')
    list_filter = (MultipleDUIDFilter, DuplicateDUIDFilter)
    search_fields = ('interface_id', 'remote_id')

    readonly_fields = ('duid', 'duid_ll', 'duid_ll_org', 'interface_id', 'remote_id')
    fieldsets = (
        ('Client', {
            'fields': (('duid', 'duid_ll', 'duid_ll_org'),
                       'interface_id',
                       'remote_id'),
        }),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Get the transaction counts in one go

        :param request: The incoming request
        :return: The queryset with clients
        """
        qs = super().get_queryset(request)
        return qs.annotate(num_transactions=Count('transaction'))

    # noinspection PyMethodMayBeStatic
    def admin_transactions_link(self, client: Client) -> str:
        """
        Show a link to the transactions for this client

        :param client: The client object
        :return: The HTML link
        """
        return format_html('<a href="{url}?client={client_id}">{label}</a>',
                           client_id=client.id,
                           url=reverse("admin:dhcpkit_looking_glass_transaction_changelist"),
                           label=ungettext(
                               "{count} transaction",
                               "{count} transactions",
                               client.num_transactions).format(count=client.num_transactions))

    admin_transactions_link.short_description = _("Transactions")

    # noinspection PyMethodMayBeStatic
    def admin_duid(self, client: Client) -> str:
        """
        Show the DUID as MAC address if possible

        :param client: The client object
        :return: The MAC address embedded in the DUID, otherwise the DUID itself
        """
        return client.duid_ll or client.duid

    admin_duid.short_description = _('DUID / MAC')
    admin_duid.admin_order_field = 'duid'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin interface for transactions
    """
    date_hierarchy = 'request_ts'
    list_filter = ('server', ResponseFilter, 'request_type', 'response_type')
    list_display = ('admin_duid', 'admin_interface_id', 'admin_remote_id',
                    'server', 'admin_request_ts_ms',
                    'request_ll', 'request_type', 'response_type')
    search_fields = ('client__duid', 'client__interface_id', 'client__remote_id', 'request', 'response')

    readonly_fields = ('client_duid', 'client_duid_ll', 'client_duid_ll_org',
                       'request_ll', 'request_ll_mac', 'request_ll_mac_org',
                       'client_interface_id',
                       'client_remote_id',
                       'request_html', 'admin_request_ts_ms',
                       'response_html', 'admin_response_ts_ms')
    fieldsets = (
        ('Client', {
            'fields': (('client_duid', 'client_duid_ll', 'client_duid_ll_org'),
                       ('request_ll', 'request_ll_mac', 'request_ll_mac_org'),
                       'client_interface_id',
                       'client_remote_id'),
        }),
        ('Request', {
            'fields': ('request_html', 'admin_request_ts_ms'),
        }),
        ('Response', {
            'fields': ('response_html', 'admin_response_ts_ms'),
        }),
    )

    # noinspection PyMethodMayBeStatic
    def admin_request_ts_ms(self, transaction: Transaction) -> str:
        """
        Show the last request timestamp with milliseconds

        :param transaction: The transaction
        :return: The timestamp as a string
        """
        return "{:%Y-%m-%d %H:%M:%S.%f}".format(timezone.localtime(transaction.request_ts))

    admin_request_ts_ms.short_description = _('last request')
    admin_request_ts_ms.admin_order_field = 'request_ts'

    # noinspection PyMethodMayBeStatic
    def admin_response_ts_ms(self, transaction: Transaction) -> str:
        """
        Show the last response timestamp with milliseconds

        :param transaction: The transaction
        :return: The timestamp as a string
        """
        return "{:%Y-%m-%d %H:%M:%S.%f}".format(timezone.localtime(transaction.response_ts))

    admin_response_ts_ms.short_description = _('last request')
    admin_response_ts_ms.admin_order_field = 'response_ts'

    # noinspection PyMethodMayBeStatic
    def admin_duid(self, transaction: Transaction) -> str:
        """
        Show the DUID as MAC address if possible

        :param transaction: The transaction object
        :return: The MAC address embedded in the DUID, otherwise the DUID itself
        """
        return transaction.client.duid_ll or transaction.client.duid

    admin_duid.short_description = _('DUID / MAC')
    admin_duid.admin_order_field = 'client.duid'

    # noinspection PyMethodMayBeStatic
    def admin_interface_id(self, transaction: Transaction) -> str:
        """
        Show the Interface ID of the client

        :param transaction: The transaction object
        :return: The Interface ID
        """
        return transaction.client.interface_id

    admin_interface_id.short_description = _('Interface ID')
    admin_interface_id.admin_order_field = 'client.interface_id'

    # noinspection PyMethodMayBeStatic
    def admin_remote_id(self, transaction: Transaction) -> str:
        """
        Show the Remote ID of the client

        :param transaction: The transaction object
        :return: The Remote ID
        """
        return transaction.client.remote_id

    admin_remote_id.short_description = _('Remote ID')
    admin_remote_id.admin_order_field = 'client.remote_id'
