"""
Represent the database that the option handler creates
"""
import json
from collections import OrderedDict
from ipaddress import IPv6Address

import yaml
from dhcpkit.ipv6.duids import DUID
from django.db import models
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from netaddr.eui import EUI
from netaddr.strategy.eui48 import mac_unix_expanded


class Server(models.Model):
    """
    Keep track of which servers are writing to this database
    """
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = _('server')
        verbose_name_plural = _('servers')
        ordering = ('name',)

    def __str__(self):
        return self.name


class Client(models.Model):
    """
    Representation of the clients table that the dhcpkit option handler creates
    """
    duid = models.CharField(_('DUID'), max_length=258)  # max. 128 octets = 256 hex chars, + '0x'
    interface_id = models.CharField(_('Interface-ID'), max_length=256, blank=True)
    remote_id = models.CharField(_('Remote-ID'), max_length=512, blank=True)

    class Meta:
        verbose_name = _('client')
        verbose_name_plural = _('clients')
        unique_together = (('duid', 'interface_id', 'remote_id'),)
        ordering = ('remote_id', 'interface_id', 'duid')

    def __str__(self):
        if self.remote_id and self.interface_id:
            return '{} - {} - {}'.format(self.remote_id, self.interface_id, self.duid)
        elif self.remote_id:
            return '{} - {}'.format(self.remote_id, self.duid)
        elif self.interface_id:
            return '{} - {}'.format(self.interface_id, self.duid)
        else:
            return self.duid

    def duid_ll(self):
        """
        Get the link-layer address stored in the DUID, if any

        :return: Link-layer address or None
        """

        # noinspection PyBroadException
        try:
            duid_str = self.duid
            if duid_str.startswith('0x'):
                duid_str = duid_str[2:]
            duid_bytes = bytes.fromhex(duid_str)
            length, duid = DUID.parse(duid_bytes, length=len(duid_bytes))

            if getattr(duid, 'hardware_type') == 1 and hasattr(duid, 'link_layer_address'):
                return EUI(int.from_bytes(duid.link_layer_address, byteorder='big'), dialect=mac_unix_expanded)
        except:
            pass

        return None

    duid_ll.short_description = _('MAC from DUID')
    duid_ll = property(duid_ll)

    def duid_ll_org(self):
        """
        Get the vendor from the link-layer address in the DUID, if available

        :return: Vendor name or None
        """
        duid_ll = self.duid_ll
        if duid_ll:
            reg = duid_ll.oui.registration()
            if reg:
                return reg['org']

        return None

    duid_ll_org.short_description = _('MAC vendor')
    duid_ll_org = property(duid_ll_org)


class Transaction(models.Model):
    server = models.ForeignKey(Server)
    client = models.ForeignKey(Client)

    last_request_type = models.CharField(_('last request type'), max_length=50, blank=True, null=True)
    last_request = models.TextField(_('last request'), blank=True, null=True)
    last_request_ll = models.GenericIPAddressField(_('Link-local address'), protocol='ipv6', blank=True, null=True)
    last_request_ts = models.DateTimeField(_('last request timestamp'), blank=True, null=True)

    last_response_type = models.CharField(_('last response type'), max_length=50, blank=True, null=True)
    last_response = models.TextField(_('last response'), blank=True, null=True)
    last_response_ts = models.DateTimeField(_('last response timestamp'), blank=True, null=True)

    class Meta:
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')
        unique_together = (('client', 'server'),)
        ordering = ('client', 'server')

    def last_request_ll_mac(self):
        """
        Try to get the MAC address based on the link-local address, if possible

        :return: MAC address or None
        """

        if not self.last_request_ll:
            return None

        # noinspection PyBroadException
        try:
            addr = IPv6Address(self.last_request_ll)
            int_id = bytearray(addr.packed[8:])
            if int_id[3:5] == b'\xff\xfe':
                # Extract bytes and flip the right bit
                mac_bytes = int_id[0:3] + int_id[5:8]
                mac_bytes[0] ^= 2

                return EUI(int.from_bytes(mac_bytes, byteorder='big'), dialect=mac_unix_expanded)
        except:
            pass

        return None

    last_request_ll_mac.short_description = _('Embedded MAC')
    last_request_ll_mac = property(last_request_ll_mac)

    def last_request_ll_mac_org(self):
        """
        Get the vendor from the link-layer address in the DUID, if available

        :return: Vendor name or None
        """
        last_request_ll_mac = self.last_request_ll_mac
        if last_request_ll_mac:
            reg = last_request_ll_mac.oui.registration()
            if reg:
                return reg['org']

        return None

    last_request_ll_mac_org.short_description = 'MAC vendor'
    last_request_ll_mac_org = property(last_request_ll_mac_org)

    def last_request_html(self):
        """
        Return the JSON of the last request in a nice human readable format

        :return: HTML or None
        """
        if not self.last_request:
            return None

        request_yaml = yaml.dump(json.loads(self.last_request, object_pairs_hook=OrderedDict),
                                 default_flow_style=False)
        return format_html('<pre style="float: left; margin: 0">{}</pre>', request_yaml)

    last_request_html.short_description = _('last request')
    last_request_html.allow_tags = True
    last_request_html = property(last_request_html)

    def last_response_html(self):
        """
        Return the JSON of the last response in a nice human readable format

        :return: HTML or None
        """
        if not self.last_response:
            return None

        response_yaml = yaml.dump(json.loads(self.last_response, object_pairs_hook=OrderedDict),
                                  default_flow_style=False)
        return format_html('<pre style="float: left; margin: 0">{}</pre>', response_yaml)

    last_response_html.short_description = _('last response')
    last_response_html.allow_tags = True
    last_response_html = property(last_response_html)

    def client_duid(self):
        return self.client.duid

    client_duid.short_description = _('DUID')
    client_duid = property(client_duid)

    def client_duid_ll(self):
        return self.client.duid_ll

    client_duid_ll.short_description = _('MAC from DUID')
    client_duid_ll = property(client_duid_ll)

    def client_duid_ll_org(self):
        return self.client.duid_ll_org

    client_duid_ll_org.short_description = _('MAC vendor')
    client_duid_ll_org = property(client_duid_ll_org)

    def client_interface_id(self):
        return self.client.interface_id

    client_interface_id.short_description = _('Interface ID')
    client_interface_id = property(client_interface_id)

    def client_remote_id(self):
        return self.client.remote_id

    client_remote_id.short_description = _('Remote ID')
    client_remote_id = property(client_remote_id)


# Proper representation of OrderedDict
yaml.add_representer(OrderedDict,
                     lambda self, data: self.represent_mapping('tag:yaml.org,2002:map', data.items()))
