"""
Represent the database that the option handler creates
"""
from collections import OrderedDict
from ipaddress import IPv6Address

import yaml
from dhcpkit.ipv6.duids import DUID
from django.db import models
from django.utils.translation import ugettext_lazy as _
from netaddr.eui import EUI
from netaddr.strategy.eui48 import mac_unix_expanded

from dhcpkit_looking_glass.utils import json_message_to_html


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
    """
    Log a transaction between a client and a server
    """
    server = models.ForeignKey(Server)
    client = models.ForeignKey(Client)

    request_type = models.CharField(_('request type'), max_length=50, blank=True, null=True)
    request = models.TextField(_('request'), blank=True, null=True)
    request_ll = models.GenericIPAddressField(_('Link-local address'), protocol='ipv6', blank=True, null=True)
    request_ts = models.DateTimeField(_('request timestamp'), blank=True, null=True)

    response_type = models.CharField(_('response type'), max_length=50, blank=True, null=True)
    response = models.TextField(_('response'), blank=True, null=True)
    response_ts = models.DateTimeField(_('response timestamp'), blank=True, null=True)

    class Meta:
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')
        unique_together = (('client', 'server', 'request_ts'),)
        ordering = ('-request_ts',)

    def __str__(self):
        return "{client} -> {server} @ {ts:%Y-%m-%d %H:%H:%S.%f}".format(client=self.client,
                                                                         server=self.server,
                                                                         ts=self.request_ts)

    def request_ll_mac(self):
        """
        Try to get the MAC address based on the link-local address, if possible

        :return: MAC address or None
        """

        if not self.request_ll:
            return None

        # noinspection PyBroadException
        try:
            addr = IPv6Address(self.request_ll)
            int_id = bytearray(addr.packed[8:])
            if int_id[3:5] == b'\xff\xfe':
                # Extract bytes and flip the right bit
                mac_bytes = int_id[0:3] + int_id[5:8]
                mac_bytes[0] ^= 2

                return EUI(int.from_bytes(mac_bytes, byteorder='big'), dialect=mac_unix_expanded)
        except:
            pass

        return None

    request_ll_mac.short_description = _('Embedded MAC')
    request_ll_mac = property(request_ll_mac)

    def request_ll_mac_org(self):
        """
        Get the vendor from the link-layer address in the DUID, if available

        :return: Vendor name or None
        """
        request_ll_mac = self.request_ll_mac
        if request_ll_mac:
            reg = request_ll_mac.oui.registration()
            if reg:
                return reg['org']

        return None

    request_ll_mac_org.short_description = 'MAC vendor'
    request_ll_mac_org = property(request_ll_mac_org)

    def request_html(self):
        """
        Return the JSON of the request in a nice human readable format

        :return: HTML or None
        """
        return json_message_to_html(self.request)

    request_html.short_description = _('request')
    request_html.allow_tags = True
    request_html = property(request_html)

    def response_html(self):
        """
        Return the JSON of the response in a nice human readable format

        :return: HTML or None
        """
        return json_message_to_html(self.response)

    response_html.short_description = _('response')
    response_html.allow_tags = True
    response_html = property(response_html)

    def client_duid(self):
        """
        The DUID of the client
        """
        return self.client.duid

    client_duid.short_description = _('DUID')
    client_duid = property(client_duid)

    def client_duid_ll(self):
        """
        The DUID Link Local address of the client
        """
        return self.client.duid_ll

    client_duid_ll.short_description = _('MAC from DUID')
    client_duid_ll = property(client_duid_ll)

    def client_duid_ll_org(self):
        """
        The DUID Link Local address organisation of the client
        """
        return self.client.duid_ll_org

    client_duid_ll_org.short_description = _('MAC vendor')
    client_duid_ll_org = property(client_duid_ll_org)

    def client_interface_id(self):
        """
        The interface-id of the client
        """
        return self.client.interface_id

    client_interface_id.short_description = _('Interface ID')
    client_interface_id = property(client_interface_id)

    def client_remote_id(self):
        """
        The remote-id of the client
        """
        return self.client.remote_id

    client_remote_id.short_description = _('Remote ID')
    client_remote_id = property(client_remote_id)


# Proper representation of OrderedDict
yaml.add_representer(OrderedDict,
                     lambda self, data: self.represent_mapping('tag:yaml.org,2002:map', data.items()))
