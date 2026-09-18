import inspect
import itertools
import os
from datetime import timedelta
from pathlib import Path

from background_task.models import CompletedTask
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import get_tenant_model, schema_context

from approval.models import Approval

User = get_user_model()


class Command(BaseCommand):
    help = "Runs weekly maintenance: sends approval notifications, cleans temp files, purges background tasks, and deduplicates history records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            type=str,
            help="Target schema name. Defaults to current active connection.",
        )
        parser.add_argument(
            "--temp-days",
            type=int,
            default=8,
            help="Retention threshold in days for temp files (default: 8).",
        )
        parser.add_argument(
            "--history-days",
            type=int,
            default=8,
            help="Retention threshold in days for history deduplication (default: 8).",
        )

    def handle(self, *args, **options):
        target_schema = options.get("schema") or connection.schema_name

        TenantModel = get_tenant_model()
        try:
            tenant = TenantModel.objects.get(schema_name=target_schema)
        except TenantModel.DoesNotExist:
            raise CommandError(f"Tenant schema '{target_schema}' does not exist.")

        self.stdout.write(
            self.style.NOTICE(f"Starting weekly tasks for tenant: {tenant.schema_name}")
        )

        with schema_context(tenant.schema_name):
            # Email Notifications for Approvals
            self.check_and_notify_approval_records(tenant)

            # Cleanup Temp Files
            media_root = getattr(settings, "MEDIA_ROOT", None)
            if media_root:
                temp_dir = os.path.join(media_root, "temp")
                self.cleanup_temp_files(temp_dir, days=options["temp_days"])
                self.stdout.write(self.style.SUCCESS(" Cleared temporary files."))

            # Clear Completed Background Tasks
            deleted_tasks_count, _ = CompletedTask.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f" Deleted {deleted_tasks_count} completed tasks.")
            )

            # Deduplicate Model History Records
            cutoff_date = timezone.now() - timedelta(days=options["history_days"])
            self.deduplicate_history_records(cutoff_date)

    def check_and_notify_approval_records(self, tenant):
        """Find pending approval records and send notification emails to project leaders."""

        # Fetch all approval records that are pending approval
        records_to_be_approved = Approval.objects.all()

        # Check if there are any records to be approved
        if not records_to_be_approved.exists():
            self.stdout.write(" No approval records found to notify.")
            return

        # Get project leader emails for the pending approval records
        project_leader_emails = self.get_formz_project_leader_emails(
            records_to_be_approved
        )
        if not project_leader_emails:
            self.stdout.write(" No project leader emails found for notifications.")
            return

        # Get the primary domain for the tenant
        # If the tenant has a primary domain, create a link to the approval list
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

        # Get the site title and server email from the tenant and settings
        site_title = getattr(tenant, "site_title", "BenchBaze")
        server_email = getattr(settings, "SERVER_EMAIL_ADDRESS", "noreply@example.com")

        # Compose the email message
        email_message_txt = inspect.cleandoc(
            f"""Hello there,

            There are records that need your approval.

            {visit_message}

            Best wishes,
            {site_title}
            """
        )

        # Send the email notification to project leaders
        send_mail(
            "There are records that need your approval",
            email_message_txt,
            server_email,
            project_leader_emails,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f" Sent approval notification to {len(project_leader_emails)} email(s)."
            )
        )

    def get_formz_project_leader_emails(self, qs):
        """Returns project leader emails for given approval queryset."""

        # Exclude certain content types from the queryset
        qs = qs.exclude(content_type__model__in=["order", "oligo"])
        ids = []

        # Collect project leader IDs from the approval records
        for approval_obj in qs:
            project_leader_ids = list(
                approval_obj.content_object.formz_projects.all().values_list(
                    "project_leader", flat=True
                )
            )
            ids.extend(project_leader_ids)

        # Add the PI user if they are not already in the list
        # If the PI user is not already in the list, add them
        pi_user = User.objects.filter(is_pi=True).first()
        if pi_user and pi_user.id not in ids:
            ids.append(pi_user.id)

        return list(
            User.objects.filter(id__in=ids)
            .exclude(email="")
            .values_list("email", flat=True)
            .distinct()
        )

    def cleanup_temp_files(self, temp_dir, days):
        """Delete files older than threshold in temp directory."""

        # Calculate the cutoff datetime for file deletion
        cutoff = timezone.now() - timedelta(days=days)
        temp_dir_path = Path(temp_dir)

        # Check if the temp directory exists
        if temp_dir_path.is_dir():
            # Iterate through files in the temp directory and delete those older than the cutoff
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

    def deduplicate_history_records(self, cutoff_date):
        """Deduplicates history items differing only by last_changed_date_time."""

        # Get all models with history and last_changed_date_time fields
        total_deleted = 0
        history_models = [
            m
            for m in apps.get_models()
            if getattr(m, "history", False)
            and getattr(m, "last_changed_date_time", False)
        ]

        # Iterate through each model and delete duplicate history records
        for model in history_models:
            ids_to_delete = self.delete_dup_hist_rec_ids(model, cutoff_date)
            if ids_to_delete:
                deleted_count, _ = model.history.filter(
                    history_id__in=ids_to_delete
                ).delete()
                total_deleted += deleted_count

        self.stdout.write(
            self.style.SUCCESS(f" Deduplicated {total_deleted} history record(s).")
        )

    def delete_dup_hist_rec_ids(self, model, time_delta):
        """Identify duplicate history IDs."""

        def pairwise(iterable):
            """Create pairs of consecutive items from iterable"""
            a, b = itertools.tee(iterable)
            next(b, None)
            return zip(a, b)

        # Get all items of the model that have a last_changed_date_time greater than or equal to the time delta
        items_to_check = model.objects.filter(last_changed_date_time__gte=time_delta)
        hist_item_ids_delete = []

        # Iterate through each item and check for duplicate history records
        for item in items_to_check:
            history_records = item.history.all()
            if history_records.count() > 1:
                history_pairs = pairwise(history_records)
                for history_element in history_pairs:
                    newer_record = history_element[0]
                    older_record = history_element[1]
                    delta = newer_record.diff_against(older_record)
                    changed_fields = delta.changed_fields
                    # If the only changed field is last_changed_date_time, then it's a duplicate
                    if (
                        "last_changed_date_time" in changed_fields
                        and len(changed_fields) == 1
                    ):
                        hist_item_ids_delete.append(delta.new_record.history_id)

        return hist_item_ids_delete
