# Generated by Django 3.1.2 on 2020-12-21 03:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_catenauser_public_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catenauser',
            name='public_key',
            field=models.CharField(max_length=34, verbose_name='public key'),
        ),
    ]
