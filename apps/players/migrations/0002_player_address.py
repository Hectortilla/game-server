# Generated by Django 2.2.2 on 2020-01-19 19:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('players', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='address',
            field=models.GenericIPAddressField(db_index=True, unique=True),
            preserve_default=False,
        ),
    ]
