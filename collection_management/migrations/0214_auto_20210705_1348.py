# Generated by Django 3.1.6 on 2021-07-05 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection_management', '0213_auto_20210327_0840'),
    ]

    operations = [
        migrations.AddField(
            model_name='antibody',
            name='availability',
            field=models.BooleanField(default=True, verbose_name='available?'),
        ),
        migrations.AddField(
            model_name='historicalantibody',
            name='availability',
            field=models.BooleanField(default=True, verbose_name='available?'),
        ),
    ]
