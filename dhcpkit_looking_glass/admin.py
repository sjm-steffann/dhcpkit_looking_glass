"""
Admin settings for the dhcpkit looking glass
"""
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.filters import SimpleListFilter
from django.db.models.expressions import F
from django.db.models.query_utils import Q

from dhcpkit_looking_glass.models import Client


class ResponseFilter(SimpleListFilter):
    """
    Filter on response statistics
    """
    title = 'Response statistics'
    parameter_name = 'response_stat'

    def lookups(self, request, model_admin):
        """
        Which filters do we provide?

        :param request: The incoming request
        :param model_admin:
        :return: A list of lookups
        """
        return (('slow', 'Slow responses'),
                ('no', 'No response'))

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


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Admin interface for client access
    """
    date_hierarchy = 'last_request_ts'
    list_filter = (ResponseFilter, 'last_request_ts', 'last_response_ts')
    list_display = ('admin_duid', 'interface_id', 'remote_id',
                    'last_request_ll', 'last_request_type', 'last_request_ts',
                    'last_response_type', 'last_response_ts')
    search_fields = ('interface_id', 'remote_id', 'last_request', 'last_response')
    ordering = ('remote_id', 'interface_id', 'duid')

    readonly_fields = ('duid', 'duid_ll', 'duid_ll_org',
                       'last_request_ll', 'last_request_ll_mac', 'last_request_ll_mac_org',
                       'interface_id', 'remote_id',
                       'last_request_html', 'last_request_ts',
                       'last_response_html', 'last_response_ts')
    fieldsets = (
        ('Client', {
            'fields': (('duid', 'duid_ll', 'duid_ll_org'),
                       ('last_request_ll', 'last_request_ll_mac', 'last_request_ll_mac_org'),
                       'interface_id',
                       'remote_id'),
        }),
        ('Request', {
            'fields': ('last_request_html', 'last_request_ts'),
        }),
        ('Response', {
            'fields': ('last_response_html', 'last_response_ts'),
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

    admin_duid.short_description = 'DUID / MAC'
    admin_duid.admin_order_field = 'duid'
