# Generated by Django 1.11 on 2018-11-16 14:11

import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("purchasing", "0002_auto_20180517_1309"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalMsdsForm",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("name", models.TextField(max_length=100, verbose_name="File name")),
                (
                    "created_date_time",
                    models.DateTimeField(
                        blank=True, editable=False, verbose_name="Created"
                    ),
                ),
                (
                    "last_changed_date_time",
                    models.DateTimeField(
                        blank=True, editable=False, verbose_name="Last Changed"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_date", models.DateTimeField()),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical MSDS form",
                "get_latest_by": "history_date",
                "ordering": ("-history_date", "-history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalOrder",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("supplier", models.CharField(max_length=255, verbose_name="Supplier")),
                (
                    "supplier_part_no",
                    models.CharField(max_length=255, verbose_name="Supplier Part-No"),
                ),
                (
                    "part_description",
                    models.CharField(max_length=255, verbose_name="Part Description"),
                ),
                ("quantity", models.CharField(max_length=255, verbose_name="Quantity")),
                (
                    "price",
                    models.CharField(blank=True, max_length=255, verbose_name="Price"),
                ),
                (
                    "urgent",
                    models.BooleanField(verbose_name="Is this an urgent order?"),
                ),
                (
                    "delivery_alert",
                    models.BooleanField(
                        verbose_name="Would you like to receive a delivery alert for this order?"
                    ),
                ),
                ("sent_email", models.BooleanField(default=False)),
                ("comment", models.TextField(blank=True, verbose_name="Comments")),
                (
                    "url",
                    models.URLField(blank=True, max_length=400, verbose_name="URL"),
                ),
                (
                    "cas_number",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="CAS number"
                    ),
                ),
                (
                    "ghs_pictogram",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="GHS pictogram"
                    ),
                ),
                (
                    "created_date_time",
                    models.DateTimeField(
                        blank=True, editable=False, verbose_name="Created"
                    ),
                ),
                (
                    "last_changed_date_time",
                    models.DateTimeField(
                        blank=True, editable=False, verbose_name="Last Changed"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_date", models.DateTimeField()),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "cost_unit",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="purchasing.CostUnit",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="purchasing.Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Order",
                "get_latest_by": "history_date",
                "ordering": ("-history_date", "-history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalOrderExtraDoc",
            fields=[
                (
                    "id",
                    models.IntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("name", models.TextField(max_length=100, verbose_name="File name")),
                (
                    "created_date_time",
                    models.DateTimeField(
                        blank=True, editable=False, verbose_name="Created"
                    ),
                ),
                (
                    "last_changed_date_time",
                    models.DateTimeField(
                        blank=True, editable=False, verbose_name="Last Changed"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_date", models.DateTimeField()),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical order extra document",
                "get_latest_by": "history_date",
                "ordering": ("-history_date", "-history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="MsdsForm",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.FileField(upload_to="temp/", verbose_name="File name")),
                (
                    "created_date_time",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "last_changed_date_time",
                    models.DateTimeField(auto_now=True, verbose_name="Last Changed"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "MSDS form",
            },
        ),
        migrations.CreateModel(
            name="OrderExtraDoc",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.FileField(upload_to="temp/", verbose_name="File name")),
                (
                    "created_date_time",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "last_changed_date_time",
                    models.DateTimeField(auto_now=True, verbose_name="Last Changed"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "order extra document",
            },
        ),
        migrations.AlterModelOptions(
            name="order",
            options={"verbose_name": "Order"},
        ),
        migrations.AddField(
            model_name="order",
            name="cas_number",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="CAS number"
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="ghs_pictogram",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="GHS pictogram"
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="last_changed_date_time",
            field=models.DateTimeField(auto_now=True, verbose_name="Last Changed"),
        ),
        migrations.AddField(
            model_name="order",
            name="sent_email",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="orderextradoc",
            name="order",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="purchasing.Order"
            ),
        ),
        migrations.AddField(
            model_name="msdsform",
            name="order",
            field=models.ManyToManyField(to="purchasing.Order"),
        ),
        migrations.AddField(
            model_name="historicalorderextradoc",
            name="order",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="purchasing.Order",
            ),
        ),
    ]
