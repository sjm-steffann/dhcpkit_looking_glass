# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('dhcpkit_looking_glass', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='last_request_type',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='last_response_type',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
