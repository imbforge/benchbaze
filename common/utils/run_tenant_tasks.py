import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Setup Django environment, up 3 levels from common/utils/ to project root
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.core.management import call_command
from django_tenants.utils import get_tenant_model, schema_context

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def get_active_tenants():
    """Retrieve all active tenant schemas, excluding the public schema."""

    TenantModel = get_tenant_model()
    public_schema_name = getattr(settings, "PUBLIC_SCHEMA_NAME", "public")
    return list(
        TenantModel.objects.exclude(schema_name=public_schema_name)
        .order_by("schema_name")
        .values_list("schema_name", flat=True)
    )


def run_command_across_tenants(command_name, delay_minutes):
    """Run a Django management command across all active tenants with optional delay."""

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
            logging.error(f"Failed for schema {schema}: {str(e)}")

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
