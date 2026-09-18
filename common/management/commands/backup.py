import gzip
import os
import shutil
import warnings
from datetime import datetime
from pathlib import Path
from subprocess import run

from django.apps import apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context

from common.actions import create_export_resource

# Suppress openpyxl deprecation warnings
warnings.simplefilter("ignore")


class Command(BaseCommand):
    help = "Creates database dumps, table exports, and uploads sync for tenant schemas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            type=str,
            help="Target schema name. If omitted, uses current active schema connection.",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=7,
            help="Number of days to keep database dumps (default: 7).",
        )

    def handle(self, *args, **options):
        """Main command handler for the backup command."""

        # Ensure BASE_DIR is defined in settings
        base_dir = getattr(settings, "BASE_DIR", None)
        if not base_dir:
            raise CommandError("BASE_DIR setting is missing.")

        # Define backup root directory
        backup_root = Path(base_dir) / ".backup"
        retention_days = options["retention_days"]

        # Determine target schema
        target_schema = options.get("schema") or connection.schema_name

        TenantModel = get_tenant_model()
        try:
            tenant = TenantModel.objects.get(schema_name=target_schema)
        except TenantModel.DoesNotExist:
            raise CommandError(f"Tenant schema '{target_schema}' does not exist.")

        self.stdout.write(
            self.style.NOTICE(
                f"Starting backup for tenant schema: {tenant.schema_name}"
            )
        )

        # Perform backup operations within the tenant's schema context
        with schema_context(tenant.schema_name):
            backup_dir_tenant = backup_root / tenant.schema_name
            self.ensure_backup_directories(backup_dir_tenant)

            # PostgreSQL Dump
            self.create_db_dump(backup_dir_tenant, tenant.schema_name)
            self.stdout.write(self.style.SUCCESS(" Database dump created."))

            # Export Excel/TSV Tables
            self.export_tables(backup_dir_tenant)
            self.stdout.write(self.style.SUCCESS(" Table exports completed."))

            # Sync Uploads
            storage_loc = getattr(default_storage, "location", None)
            if storage_loc:
                self.sync_uploads(Path(storage_loc), backup_dir_tenant / "uploads")
                self.stdout.write(self.style.SUCCESS(" Uploads directory synced."))

            # Prune Old Dumps
            self.remove_old_dumps(retention_days, backup_dir_tenant)
            self.stdout.write(
                self.style.SUCCESS(f" Pruned dumps older than {retention_days} days.")
            )

    def ensure_backup_directories(self, backup_dir):
        """Ensure the existence of backup directories."""

        for sub_dir in ["db_dumps", "excel_tables", "uploads"]:
            (backup_dir / sub_dir).mkdir(parents=True, exist_ok=True)

    def export_db_table(self, model, export_resource, backup_dir):
        """Export a single model's data to XLSX and TSV formats."""

        file_name_base = backup_dir / f"excel_tables/{model.__name__}"
        if model.objects.exists():
            dataset = export_resource().export(model.objects.all().order_by("-id"))

            with open(file_name_base.with_suffix(".xlsx"), "wb") as out_handle:
                out_handle.write(dataset.xlsx)

            with open(
                file_name_base.with_suffix(".tsv"), "w", encoding="utf-8"
            ) as out_handle:
                out_handle.write(dataset.tsv)

    def export_tables(self, backup_dir):
        """Export all models marked for backup to both XLSX and TSV formats."""

        for m in apps.get_models():
            if getattr(m, "_backup", False) and getattr(
                m, "_export_field_names", False
            ):
                self.export_db_table(m, create_export_resource(m), backup_dir)

    def create_db_dump(self, backup_dir, tenant_schema):
        """Create a PostgreSQL dump for the specified tenant schema and save it as a gzipped file."""

        # Define the output path for the dump file
        dumps_dir = backup_dir / "db_dumps"
        output_path = dumps_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}.sql.gz"

        # Retrieve database configuration from Django settings
        db_config = getattr(settings, "DATABASES", {}).get("default", {})
        db_name = db_config.get("NAME", "")
        db_user = db_config.get("USER", "")
        db_password = db_config.get("PASSWORD", "")
        db_host = db_config.get("HOST")
        db_port = str(db_config.get("PORT", ""))

        # Find the pg_dump binary
        pg_dump_bin = shutil.which("pg_dump") or "/usr/bin/pg_dump"

        # Set up the environment for the pg_dump command
        env = os.environ.copy()
        if db_password:
            env["PGPASSWORD"] = db_password

        # Construct the pg_dump command with necessary parameters
        pg_dump_cmd = [
            pg_dump_bin,
            db_name,
            "-U",
            db_user,
            "-h",
            db_host,
            "-p",
            db_port,
            "--no-password",
            "--schema",
            tenant_schema,
            "--exclude-schema",
            "public",
        ]

        # Execute the pg_dump command and write the output to a gzipped file
        with (
            open(output_path, "wb") as output_file,
            gzip.GzipFile(fileobj=output_file, mode="wb") as gz_file,
        ):
            run(pg_dump_cmd, check=True, stdout=gz_file, env=env)

    def sync_uploads(self, src_dir, dst_dir):
        """Synchronize the uploads directory from the source to the destination using rsync if available, otherwise fallback to shutil."""

        # Check if rsync is available
        rsync_bin = shutil.which("rsync")
        if rsync_bin:
            run([rsync_bin, "-a", f"{src_dir}/", str(dst_dir)], check=True)
            return

        if not src_dir.exists():
            return

        # Fallback to shutil if rsync is not available
        for src_path in src_dir.rglob("*"):
            rel_path = src_path.relative_to(src_dir)
            dst_path = dst_dir / rel_path
            if src_path.is_dir():
                dst_path.mkdir(parents=True, exist_ok=True)
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)

    def remove_old_dumps(self, days, backup_dir):
        """Remove database dump files older than the specified number of days, keeping at least one recent dump."""

        # Define the directory containing database dumps and calculate the cutoff timestamp
        dumps_dir = backup_dir / "db_dumps"
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        # Get all dump files sorted by modification time
        dump_files = sorted(
            [path for path in dumps_dir.glob("*.gz") if path.is_file()],
            key=lambda path: path.stat().st_mtime,
        )

        # Filter out old files
        old_dump_files = [path for path in dump_files if path.stat().st_mtime < cutoff]
        remaining_files = len(dump_files)

        # Delete old dump files while keeping at least one recent dump
        for dump_file in old_dump_files:
            if remaining_files <= 1:
                break
            dump_file.unlink(missing_ok=True)
            remaining_files -= 1
