"""
Admin settings for the dhcpkit looking glass
"""
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.filters import SimpleListFilter
from django.db.models.aggregates import Count
from django.db.models.expressions import F, Value
from django.db.models.functions import Concat
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _

from dhcpkit_looking_glass.models import Client, Server, Transaction


class ResponseFilter(SimpleListFilter):
    """
    Filter on response statistics
    """
    title = _('Response statistics')
    parameter_name = 'response_stat'

    def lookups(self, request, model_admin):
        """
        Which filters do we provide?

        :param request: The incoming request
        :param model_admin:
        :return: A list of lookups
        """
        return (('slow', _('Slow responses (>1s)')),
                ('no', _('No response to last request')))

    def queryset(self, request, queryset):
        """
        Adjust the queryset based on the selection

        :param request: The incoming request
        :type request: django.http.request.HttpRequest
        :param queryset: The original queryset
        :type queryset: django.db.models.query.QuerySet
        :return: The modified queryset
        :rtype: django.db.models.query.QuerySet
        """
        val = self.value()
        if val == 'slow':
            return queryset.filter(last_response_ts__gt=F('last_request_ts') + timedelta(seconds=1))
        elif val == 'no':
            return queryset.filter(Q(last_response_ts__lt=F('last_request_ts')) | Q(last_response_ts=None))
        else:
            return queryset


class MultipleDUIDFilter(SimpleListFilter):
    """
    Filter on multiple DUIDs per remote-id/interface-id
    """
    title = _('Multiple DUIDs')
    parameter_name = 'multi_duid'

    def lookups(self, request, model_admin):
        """
        Which filters do we provide?

        :param request: The incoming request
        :param model_admin:
        :return: A list of lookups
        """
        return (('per_interface_id', _('per Interface-ID')),
                ('per_remote_id', _('per Remote-ID')),
                ('per_combi', _('per combination of both')))

    def queryset(self, request, queryset):
        """
        Adjust the queryset based on the selection

        :param request: The incoming request
        :type request: django.http.request.HttpRequest
        :param queryset: The original queryset
        :type queryset: django.db.models.query.QuerySet
        :return: The modified queryset
        :rtype: django.db.models.query.QuerySet
        """
        val = self.value()
        if val == 'per_interface_id':
            return queryset \
                .filter(interface_id__in=Client.objects.values('interface_id')
                        .annotate(duid_count=Count('duid'))
                        .filter(duid_count__gt=1)
                        .values('interface_id'))
        elif val == 'per_remote_id':
            return queryset \
                .filter(remote_id__in=Client.objects.values('remote_id')
                        .annotate(duid_count=Count('duid'))
                        .filter(duid_count__gt=1)
                        .values('remote_id'))
        elif val == 'per_combi':
            return queryset \
                .annotate(concat_id=Concat('remote_id', Value('|'), 'interface_id')) \
                .filter(concat_id__in=Client.objects.values('interface_id', 'remote_id')
                        .annotate(duid_count=Count('duid'))
                        .filter(duid_count__gt=1)
                        .annotate(concat_id=Concat('remote_id', Value('|'), 'interface_id'))
                        .values('concat_id'))
        else:
            return queryset


class DuplicateDUIDFilter(SimpleListFilter):
    """
    Filter on multiple DUIDs per remote-id/interface-id
    """
    title = _('Duplicate DUIDs')
    parameter_name = 'duplicate_duid'

    def lookups(self, request, model_admin):
        """
        Which filters do we provide?

        :param request: The incoming request
        :param model_admin:
        :return: A list of lookups
        """
        return (('yes', _('DUID on different ports')),
                )

    def queryset(self, request, queryset):
        """
        Adjust the queryset based on the selection

        :param request: The incoming request
        :type request: django.http.request.HttpRequest
        :param queryset: The original queryset
        :type queryset: django.db.models.query.QuerySet
        :return: The modified queryset
        :rtype: django.db.models.query.QuerySet
        """
        val = self.value()
        if val == 'yes':
            return queryset \
                .filter(duid__in=Client.objects.values('duid')
                        .annotate(port_count=Count('interface_id', 'remote_id'))
                        .filter(port_count__gt=1)
                        .values('duid'))
        else:
            return queryset


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
    list_display = ('admin_duid', 'interface_id', 'remote_id')
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

    # noinspection PyMethodMayBeStatic
    def admin_duid(self, client):
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
    date_hierarchy = 'last_request_ts'
    list_filter = ('server', ResponseFilter, 'last_request_type', 'last_response_type')
    list_display = ('admin_duid', 'admin_interface_id', 'admin_remote_id',
                    'server',
                    'last_request_ll', 'last_request_type', 'last_request_ts',
                    'last_response_type', 'last_response_ts')
    search_fields = ('last_request', 'last_response')

    readonly_fields = ('client_duid', 'client_duid_ll', 'client_duid_ll_org',
                       'last_request_ll', 'last_request_ll_mac', 'last_request_ll_mac_org',
                       'client_interface_id',
                       'client_remote_id',
                       'last_request_html', 'last_request_ts',
                       'last_response_html', 'last_response_ts')
    fieldsets = (
        ('Client', {
            'fields': (('client_duid', 'client_duid_ll', 'client_duid_ll_org'),
                       ('last_request_ll', 'last_request_ll_mac', 'last_request_ll_mac_org'),
                       'client_interface_id',
                       'client_remote_id'),
        }),
        ('Request', {
            'fields': ('last_request_html', 'last_request_ts'),
        }),
        ('Response', {
            'fields': ('last_response_html', 'last_response_ts'),
        }),
    )

    # noinspection PyMethodMayBeStatic
    def admin_duid(self, transaction):
        """
        Show the DUID as MAC address if possible

        :param transaction: The transaction object
        :return: The MAC address embedded in the DUID, otherwise the DUID itself
        """
        return transaction.client.duid_ll or transaction.client.duid

    admin_duid.short_description = _('DUID / MAC')
    admin_duid.admin_order_field = 'client.duid'

    # noinspection PyMethodMayBeStatic
    def admin_interface_id(self, transaction):
        """
        Show the Interface ID of the client

        :param transaction: The transaction object
        :return: The Interface ID
        """
        return transaction.client.interface_id

    admin_interface_id.short_description = _('Interface ID')
    admin_interface_id.admin_order_field = 'client.interface_id'

    # noinspection PyMethodMayBeStatic
    def admin_remote_id(self, transaction):
        """
        Show the Remote ID of the client

        :param transaction: The transaction object
        :return: The Remote ID
        """
        return transaction.client.remote_id

    admin_remote_id.short_description = _('Remote ID')
    admin_remote_id.admin_order_field = 'client.remote_id'
