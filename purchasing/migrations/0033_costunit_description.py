# Generated by Django 1.11 on 2019-01-13 07:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0032_remove_costunit_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="costunit",
            name="description",
            field=models.CharField(
                default="0", max_length=255, verbose_name="Description"
            ),
            preserve_default=False,
        ),
    ]
