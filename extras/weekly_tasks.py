import inspect
import os
from datetime import timedelta
from pathlib import Path

from background_task.models import CompletedTask
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import get_tenant_model, schema_context

from approval.models import Approval

User = get_user_model()
SERVER_EMAIL_ADDRESS = getattr(settings, "SERVER_EMAIL_ADDRESS", "noreply@example.com")
NOW_MINUS_8DAYS = timezone.now() - timedelta(days=8)


def get_formz_project_leader_emails(qs):
    """Returns the user ids of the project leaders for a queryset of
    relevant approval objects"""

    qs = qs.exclude(content_type__model__in=["order", "oligo"])

    ids = []

    for approval_obj in qs:
        project_leader_ids = list(
            approval_obj.content_object.formz_projects.all().values_list(
                "project_leader", flat=True
            )
        )
        ids.extend(project_leader_ids)

    pi_user_id = User.objects.get(is_pi=True).id

    if pi_user_id not in ids:
        ids.append(pi_user_id)

    project_leader_emails = User.objects.filter(id__in=ids).values_list(
        "email", flat=True
    )

    return list(project_leader_emails)


def delete_dup_hist_rec_ids(model, time_delta):
    """Delete history items that differ just by last_changed_date_time"""

    def pairwise(iterable):
        """Create pairs of consecutive items from
        iterable"""

        import itertools

        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    items_to_check = model.objects.filter(last_changed_date_time__gte=time_delta)

    hist_item_ids_delete = []

    for item in items_to_check:
        history_records = item.history.all()
        if history_records.count() > 1:
            history_pairs = pairwise(history_records)
            for history_element in history_pairs:
                newer_record = history_element[0]
                older_record = history_element[1]
                delta = newer_record.diff_against(older_record)
                changed_fields = delta.changed_fields
                if (
                    "last_changed_date_time" in changed_fields
                    and len(changed_fields) == 1
                ):
                    hist_item_ids_delete.append(delta.new_record.history_id)

    return hist_item_ids_delete


def cleanup_temp_files(temp_dir, days=8):
    """Delete all files in the temp directory that are older than days"""

    cutoff = timezone.now() - timedelta(days=days)
    temp_dir_path = Path(temp_dir)

    if temp_dir_path.is_dir():
        for file_path in temp_dir_path.iterdir():
            if file_path.is_file():
                file_mtime = timezone.datetime.fromtimestamp(
                    file_path.stat().st_mtime, tz=timezone.utc
                )
                if file_mtime < cutoff:
                    try:
                        file_path.unlink()
                    except OSError:
                        pass


def check_and_notify_approval_records(tenant):
    """Check for approval records that need to be approved and notify project leaders via email"""

    records_to_be_approved = Approval.objects.all()

    if (
        records_to_be_approved.exists()
    ):  # Check if there are records to be be approved at all
        project_leader_emails = get_formz_project_leader_emails(records_to_be_approved)

        primary_domain = tenant.get_primary_domain()
        approval_url = (
            f"https://{primary_domain.domain}{reverse('admin:approval_approval_changelist')}"
            if primary_domain
            else None
        )
        visit_message = (
            f"You can visit {approval_url} to check for new or modified records that need to be approved."
            if approval_url
            else ""
        )

        email_message_txt = inspect.cleandoc(
            f"""Hello there,

        There are records that need your approval.

        {visit_message}

        Best wishes,
        {tenant.site_title}
        """
        )

        send_mail(
            f"{tenant.site_title} weekly notification",
            email_message_txt,
            SERVER_EMAIL_ADDRESS,
            project_leader_emails,
        )


tenant_schema = connection.schema_name
tenant = get_tenant_model().objects.get(schema_name=tenant_schema)

with schema_context(tenant.schema_name):
    check_and_notify_approval_records(tenant)
    cleanup_temp_files(os.path.join(settings.MEDIA_ROOT, "temp"))
    # Delete all completed tasks
    CompletedTask.objects.all().delete()

    # Delete history records that differ only by last_changed_date_time
    for model in [
        m
        for m in apps.get_models()
        if getattr(m, "history", False) and getattr(m, "last_changed_date_time", False)
    ]:
        ids_to_delete = delete_dup_hist_rec_ids(model, NOW_MINUS_8DAYS)
        if ids_to_delete:
            history_records = model.history.filter(history_id__in=ids_to_delete)
            history_records.delete()
