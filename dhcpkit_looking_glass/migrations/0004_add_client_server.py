# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-18 20:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dhcpkit_looking_glass', '0003_rename_client_to_transaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duid', models.CharField(max_length=258, verbose_name='DUID')),
                ('interface_id', models.CharField(blank=True, max_length=256, verbose_name='Interface-ID')),
                ('remote_id', models.CharField(blank=True, max_length=512, verbose_name='Remote-ID')),
            ],
            options={
                'verbose_name': 'client',
                'verbose_name_plural': 'clients',
                'ordering': ('remote_id', 'interface_id', 'duid'),
            },
        ),
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'verbose_name': 'server',
                'verbose_name_plural': 'servers',
                'ordering': ('name',),
            },
        ),
        migrations.AlterUniqueTogether(
            name='client',
            unique_together={('duid', 'interface_id', 'remote_id')},
        ),
        migrations.AlterModelOptions(
            name='transaction',
            options={'ordering': ('-last_request_ts',),
                     'verbose_name': 'transaction',
                     'verbose_name_plural': 'transactions'},
        ),
        migrations.AddField(
            model_name='transaction',
            name='client',
            field=models.ForeignKey(null=True, on_delete=models.deletion.CASCADE, to='dhcpkit_looking_glass.Client'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='server',
            field=models.ForeignKey(null=True, on_delete=models.deletion.CASCADE, to='dhcpkit_looking_glass.Server'),
        ),
        migrations.AlterUniqueTogether(
            name='transaction',
            unique_together=set([]),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='duid',
            field=models.CharField(max_length=1024, verbose_name='DUID', null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='interface_id',
            field=models.CharField(max_length=1024, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='remote_id',
            field=models.CharField(max_length=1024, blank=True, null=True),
        ),
    ]
