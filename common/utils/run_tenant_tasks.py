import argparse
import logging
import os
import sys
import time
import traceback
from pathlib import Path

# Setup Django environment (going up 3 levels from common/utils/ to project root)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "benchbaze.settings")

import django

django.setup()

from django.conf import settings
from django.core.mail import mail_admins, send_mail
from django.core.management import call_command
from django_tenants.utils import get_tenant_model, schema_context

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def notify_failure(command_name, schema, error_msg, stack_trace):
    """Send an email alert when a tenant task fails."""
    subject = f"[TASK ERROR] Task '{command_name}' failed for tenant '{schema}'"
    body = (
        f"An error occurred while executing management command '{command_name}' "
        f"for schema '{schema}'.\n\n"
        f"Error Details:\n{error_msg}\n\n"
        f"Traceback:\n{stack_trace}"
    )

    # First attempt to email configured Django ADMINS
    if getattr(settings, "ADMINS", None):
        try:
            mail_admins(subject, body, fail_silently=False)
            logging.info(f"Sent failure alert to ADMINS for schema: {schema}")
            return
        except Exception as mail_err:
            logging.error(f"Failed to send email to ADMINS: {str(mail_err)}")

    # Fallback to SERVER_EMAIL_ADDRESS if ADMINS isn't set or fails
    server_email = getattr(settings, "SERVER_EMAIL_ADDRESS", "noreply@example.com")
    recipient_list = [server_email]

    try:
        send_mail(
            subject,
            body,
            server_email,
            recipient_list,
            fail_silently=True,
        )
        logging.info(f"Sent failure alert email to {recipient_list}")
    except Exception as mail_err:
        logging.error(f"Failed to send fallback alert email: {str(mail_err)}")


def get_active_tenants():
    TenantModel = get_tenant_model()
    public_schema_name = getattr(settings, "PUBLIC_SCHEMA_NAME", "public")
    return list(
        TenantModel.objects.exclude(schema_name=public_schema_name)
        .order_by("schema_name")
        .values_list("schema_name", flat=True)
    )


def run_command_across_tenants(command_name, delay_minutes):
    tenants = get_active_tenants()
    logging.info(
        f"Starting execution of management command '{command_name}' across {len(tenants)} tenants."
    )

    for idx, schema in enumerate(tenants):
        logging.info(f"[{idx + 1}/{len(tenants)}] Executing for schema: {schema}")
        try:
            with schema_context(schema):
                call_command(command_name, schema=schema)
            logging.info(f"Finished successfully for schema: {schema}")
        except Exception as e:
            error_msg = str(e)
            stack_trace = traceback.format_exc()

            logging.error(f"Failed for schema {schema}: {error_msg}")

            # Send immediate email alert
            notify_failure(command_name, schema, error_msg, stack_trace)

        if idx < len(tenants) - 1 and delay_minutes > 0:
            logging.info(f"Sleeping for {delay_minutes} minutes before next tenant...")
            time.sleep(delay_minutes * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Django management command across all tenants."
    )
    parser.add_argument(
        "--command", required=True, help="Management command name (e.g. backup_db)"
    )
    parser.add_argument(
        "--delay", type=int, default=15, help="Delay in minutes between tenants"
    )

    args = parser.parse_args()
    run_command_across_tenants(args.command, args.delay)
