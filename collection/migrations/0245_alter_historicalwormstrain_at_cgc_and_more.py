# Generated by Django 4.2.17 on 2025-01-17 10:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("collection", "0244_alter_historicalwormstrain_phenotype_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalwormstrain",
            name="at_cgc",
            field=models.BooleanField(
                blank=True,
                default=False,
                help_text="Caenorhabditis Genetics Center",
                verbose_name="at CGC?",
            ),
        ),
        migrations.AlterField(
            model_name="wormstrain",
            name="at_cgc",
            field=models.BooleanField(
                blank=True,
                default=False,
                help_text="Caenorhabditis Genetics Center",
                verbose_name="at CGC?",
            ),
        ),
    ]
