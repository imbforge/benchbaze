# Generated by Django 3.2.15 on 2022-12-17 18:04

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0053_msdsform_label"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="historicalorder",
            name="ghs_symbols_autocomplete",
        ),
        migrations.RemoveField(
            model_name="historicalorder",
            name="signal_words_autocomplete",
        ),
        migrations.RemoveField(
            model_name="order",
            name="ghs_symbols_autocomplete",
        ),
        migrations.RemoveField(
            model_name="order",
            name="signal_words_autocomplete",
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="history_ghs_symbols",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveIntegerField(),
                blank=True,
                size=None,
                verbose_name="GHS symbols",
            ),
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="history_signal_words",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveIntegerField(),
                blank=True,
                size=None,
                verbose_name="signal words",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="history_ghs_symbols",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveIntegerField(),
                blank=True,
                size=None,
                verbose_name="GHS symbols",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="history_signal_words",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.PositiveIntegerField(),
                blank=True,
                size=None,
                verbose_name="signal words",
            ),
        ),
    ]
