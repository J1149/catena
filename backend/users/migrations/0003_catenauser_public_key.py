# Generated by Django 3.1.2 on 2020-12-21 03:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_catenauser_access_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='catenauser',
            name='public_key',
            field=models.CharField(blank=True, max_length=31, verbose_name='public key'),
        ),
    ]