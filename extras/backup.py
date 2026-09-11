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
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context

from common.actions import create_export_resource

BASE_DIR = getattr(settings, "BASE_DIR", None)
DB_CONFIG = getattr(settings, "DATABASES", {}).get("default", {})
DB_NAME = DB_CONFIG.get("NAME", "")
DB_USER = DB_CONFIG.get("USER", "")
DB_PASSWORD = DB_CONFIG.get("PASSWORD", "")
DB_HOST = DB_CONFIG.get("HOST")
DB_PORT = str(DB_CONFIG.get("PORT", ""))
PG_DUMP_BIN = shutil.which("pg_dump") or "/usr/bin/pg_dump"
RSYNC_BIN = shutil.which("rsync")
BACKUP_DIR = BASE_DIR / ".backup"

# Suppress silly warning "UserWarning: Using a coordinate with ws.cell is deprecated..."
warnings.simplefilter("ignore")


def export_db_table(model, export_resource, backup_dir=BACKUP_DIR):
    """Export a database table to both XLSX and TSV formats"""

    file_name_base = backup_dir / f"excel_tables/{model.__name__}"

    if model.objects.exists():
        dataset = export_resource().export(model.objects.all().order_by("-id"))

        with open(file_name_base.with_suffix(".xlsx"), "wb") as out_handle:
            out_handle.write(dataset.xlsx)

        with open(
            file_name_base.with_suffix(".tsv"), "w", encoding="utf-8"
        ) as out_handle:
            out_handle.write(dataset.tsv)


def ensure_backup_directories(backup_dir=BACKUP_DIR):
    """Ensure that the required backup directories exist"""
    required_dirs = [
        backup_dir / "db_dumps",
        backup_dir / "excel_tables",
        backup_dir / "uploads",
    ]
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)


def remove_old_dumps(days=7, backup_dir=BACKUP_DIR):
    """Remove database dump files older than the specified number of days
    while ensuring at least one recent dump is retained"""
    dumps_dir = backup_dir / "db_dumps"
    cutoff = datetime.now().timestamp() - days * 24 * 60 * 60
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


def create_db_dump(backup_dir=BACKUP_DIR, tenant_schema=None):
    """Create a compressed database dump using pg_dump and gzip"""
    dumps_dir = backup_dir / "db_dumps"
    output_path = dumps_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}.sql.gz"
    env = os.environ.copy()
    if DB_PASSWORD:
        env["PGPASSWORD"] = DB_PASSWORD

    pg_dump_cmd = [
        PG_DUMP_BIN,
        DB_NAME,
        "-U",
        DB_USER,
        "-h",
        DB_HOST,
        "-p",
        DB_PORT,
        "--no-password",
    ]

    if tenant_schema:
        pg_dump_cmd.extend(
            [
                "--schema",
                tenant_schema,
                "--exclude-schema",
                "public",
            ]
        )

    with (
        open(output_path, "wb") as output_file,
        gzip.GzipFile(fileobj=output_file, mode="wb") as gz_file,
    ):
        try:
            run(pg_dump_cmd, check=True, stdout=gz_file, env=env)
        except Exception:
            if "PGPASSWORD" in env:
                env.pop("PGPASSWORD", None)
                run(pg_dump_cmd, check=True, stdout=gz_file, env=env)
            else:
                raise


def export_tables(backup_dir=BACKUP_DIR):
    """Export all models that have _backup = True and _export_field_names defined
    to XLSX and TSV formats"""

    # Export tables only for models that have _backup = True and _export_field_names defined
    [
        export_db_table(m, create_export_resource(m), backup_dir)
        for m in apps.get_models()
        if getattr(m, "_backup", False) and getattr(m, "_export_field_names", False)
    ]


def sync_uploads(src_dir, dst_dir):
    """Sync the uploads directory to the backup location using
    rsync if available, otherwise fall back to shutil.copytree"""

    # Use rsync if available for efficient syncing, otherwise fall back to copying
    if RSYNC_BIN:
        run([RSYNC_BIN, "-a", f"{src_dir}/", str(dst_dir)], check=True)
        return

    # If rsync is not available, use shutil to copy files (inefficient for large uploads)
    if not src_dir.exists():
        return

    for src_path in src_dir.rglob("*"):
        rel_path = src_path.relative_to(src_dir)
        dst_path = dst_dir / rel_path
        if src_path.is_dir():
            dst_path.mkdir(parents=True, exist_ok=True)
        else:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)


tenant_schema = connection.schema_name
tenant = get_tenant_model().objects.get(schema_name=tenant_schema)

with schema_context(tenant.schema_name):
    backup_dir_tenant = BACKUP_DIR / tenant.schema_name
    ensure_backup_directories(backup_dir_tenant)
    create_db_dump(backup_dir_tenant, tenant.schema_name)
    export_tables(backup_dir_tenant)
    sync_uploads(Path(default_storage.location), backup_dir_tenant / "uploads")
    remove_old_dumps(7, backup_dir_tenant)
