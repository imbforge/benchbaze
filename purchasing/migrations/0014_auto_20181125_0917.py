# Generated by Django 1.11 on 2018-11-25 08:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0013_auto_20181125_0906"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalorder",
            name="delivered_date",
            field=models.DateField(blank=True, null=True, verbose_name="Delivered"),
        ),
        migrations.AlterField(
            model_name="order",
            name="delivered_date",
            field=models.DateField(blank=True, null=True, verbose_name="Delivered"),
        ),
    ]
