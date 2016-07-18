# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-18 20:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dhcpkit_looking_glass', '0006_remove_old_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='request',
            field=models.TextField(blank=True, null=True, verbose_name='request'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='request_ts',
            field=models.DateTimeField(blank=True, null=True, verbose_name='request timestamp'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='request_type',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='request type'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='response',
            field=models.TextField(blank=True, null=True, verbose_name='response'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='response_ts',
            field=models.DateTimeField(blank=True, null=True, verbose_name='response timestamp'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='response_type',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='response type'),
        ),
    ]
