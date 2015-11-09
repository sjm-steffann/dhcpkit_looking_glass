"""
Represent the database that the option handler creates
"""
import json
from ipaddress import IPv6Address

import yaml
from dhcpkit.ipv6.duids import DUID
from django.conf import settings
from django.db import models
from django.utils.html import format_html
from netaddr.eui import EUI
from netaddr.strategy.eui48 import mac_unix_expanded

""

# Insert our own router in here
settings.DATABASE_ROUTERS.append('dhcpkit_looking_glass.db_routers.LookingGlassRouter')


class Client(models.Model):
    """
    Representation of the clients table that the dhcpkit option handler creates
    """
    duid = models.CharField("DUID", max_length=1024)
    interface_id = models.CharField(max_length=1024, blank=True)
    remote_id = models.CharField(max_length=1024, blank=True)

    last_request_type = models.CharField(max_length=50, blank=True, null=True)
    last_request = models.TextField(blank=True, null=True)
    last_request_ll = models.GenericIPAddressField("Link-local address", protocol='ipv6', blank=True, null=True)
    last_request_ts = models.DateTimeField("Last request timestamp", blank=True, null=True)

    last_response_type = models.CharField(max_length=50, blank=True, null=True)
    last_response = models.TextField(blank=True, null=True)
    last_response_ts = models.DateTimeField("Last response timestamp", blank=True, null=True)

    class Meta:
        db_table = 'clients'
        unique_together = (('duid', 'interface_id', 'remote_id'),)

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

    duid_ll.short_description = 'MAC from DUID'
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

    duid_ll_org.short_description = 'MAC vendor'
    duid_ll_org = property(duid_ll_org)

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

    last_request_ll_mac.short_description = 'Embedded MAC'
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

        request_yaml = yaml.dump(json.loads(self.last_request), default_flow_style=False)
        return format_html('<pre style="float: left; margin: 0">{}</pre>', request_yaml)

    last_request_html.short_description = 'Last request'
    last_request_html.allow_tags = True
    last_request_html = property(last_request_html)

    def last_response_html(self):
        """
        Return the JSON of the last response in a nice human readable format

        :return: HTML or None
        """
        if not self.last_response:
            return None

        response_yaml = yaml.dump(json.loads(self.last_response), default_flow_style=False)
        return format_html('<pre style="float: left; margin: 0">{}</pre>', response_yaml)

    last_response_html.short_description = 'Last response'
    last_response_html.allow_tags = True
    last_response_html = property(last_response_html)
