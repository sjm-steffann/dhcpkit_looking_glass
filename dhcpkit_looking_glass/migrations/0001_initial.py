# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duid', models.CharField(max_length=1024, verbose_name='DUID')),
                ('interface_id', models.CharField(max_length=1024, blank=True)),
                ('remote_id', models.CharField(max_length=1024, blank=True)),
                ('last_request', models.TextField(null=True, blank=True)),
                ('last_request_ll', models.GenericIPAddressField(null=True, protocol='ipv6', blank=True,
                                                                 verbose_name='Link-local address')),
                ('last_request_ts', models.DateTimeField(null=True, blank=True, verbose_name='Last request timestamp')),
                ('last_response', models.TextField(null=True, blank=True)),
                ('last_response_ts',
                 models.DateTimeField(null=True, blank=True, verbose_name='Last response timestamp')),
            ],
            options={
                'db_table': 'clients',
            },
        ),
        migrations.AlterUniqueTogether(
            name='client',
            unique_together={('duid', 'interface_id', 'remote_id')},
        ),
    ]
