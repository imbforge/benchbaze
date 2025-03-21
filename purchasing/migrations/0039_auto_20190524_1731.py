# Generated by Django 2.1.8 on 2019-05-24 15:31

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0038_auto_20190426_1528"),
    ]

    operations = [
        migrations.AlterField(
            model_name="costunit",
            name="status",
            field=models.BooleanField(
                default=False, null=True, verbose_name="Deactivate?"
            ),
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="created_approval_by_pi",
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="created_date_time",
            field=models.DateTimeField(
                blank=True, editable=False, null=True, verbose_name="Created"
            ),
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="delivery_alert",
            field=models.BooleanField(
                default=False, null=True, verbose_name="Delivery notification?"
            ),
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="last_changed_date_time",
            field=models.DateTimeField(
                blank=True, editable=False, null=True, verbose_name="Last Changed"
            ),
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="sent_email",
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name="historicalorder",
            name="urgent",
            field=models.BooleanField(
                default=False, null=True, verbose_name="Is this an urgent order?"
            ),
        ),
        migrations.AlterField(
            model_name="location",
            name="status",
            field=models.BooleanField(
                default=False, null=True, verbose_name="Deactivate?"
            ),
        ),
        migrations.AlterField(
            model_name="msdsform",
            name="created_date_time",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created"
            ),
        ),
        migrations.AlterField(
            model_name="msdsform",
            name="last_changed_date_time",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Last Changed"
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="cost_unit",
            field=models.ForeignKey(
                default=1,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="purchasing.CostUnit",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="created_approval_by_pi",
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="created_date_time",
            field=models.DateTimeField(
                auto_now_add=True, null=True, verbose_name="Created"
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="delivery_alert",
            field=models.BooleanField(
                default=False, null=True, verbose_name="Delivery notification?"
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="last_changed_date_time",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="Last Changed"
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="sent_email",
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="urgent",
            field=models.BooleanField(
                default=False, null=True, verbose_name="Is this an urgent order?"
            ),
        ),
        migrations.AlterField(
            model_name="orderextradoc",
            name="order",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="purchasing.Order",
            ),
        ),
    ]
