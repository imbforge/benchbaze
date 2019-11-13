# Generated by Django 2.1.13 on 2019-11-13 11:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formz', '0076_auto_20191113_1145'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formzbaseelement',
            name='name',
            field=models.CharField(help_text="This is only the name displayed in the rendered FormZ form. It is NOT used for auto-detection of features in a plasmid map, only aliases (below) are used for that. Duplicates are allowed, therefore, instead of, for example, using 'Hs EXO1', use 'EXO1'", max_length=255, verbose_name='name'),
        ),
    ]
