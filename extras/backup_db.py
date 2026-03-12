import gzip
import os
import pathlib
import shutil
import warnings
from datetime import datetime
from os.path import dirname, join
from subprocess import run

from django.apps import apps
from django.conf import settings

from common.actions import create_export_resource

BASE_DIR = settings.BASE_DIR
DB_CONFIG = settings.DATABASES.get("default", {})
DB_NAME = DB_CONFIG.get("NAME", "")
DB_USER = DB_CONFIG.get("USER", "")
DB_PASSWORD = DB_CONFIG.get("PASSWORD", "")
DB_HOST = DB_CONFIG.get("HOST")
DB_PORT = str(DB_CONFIG.get("PORT", ""))
PG_DUMP_BIN = shutil.which("pg_dump") or "/usr/bin/pg_dump"
RSYNC_BIN = shutil.which("rsync")

# Suppress silly warning "UserWarning: Using a coordinate with ws.cell is deprecated..."
warnings.simplefilter("ignore")


def export_db_table(model, export_resource):
    """Export a database table to both XLSX and TSV formats"""
    file_name_base = join(BASE_DIR, f"db_backup/excel_tables/{model.__name__}")

    if model.objects.exists():
        dataset = export_resource().export(model.objects.all().order_by("-id"))

        with open(f"{file_name_base}.xlsx", "wb") as out_handle:
            out_handle.write(dataset.xlsx)

        with open(f"{file_name_base}.tsv", "w", encoding="utf-8") as out_handle:
            out_handle.write(dataset.tsv)


def ensure_backup_directories():
    """Ensure that the required backup directories exist"""
    required_dirs = [
        join(BACKUP_DIR, "db_dumps"),
        join(BACKUP_DIR, "excel_tables"),
        join(BACKUP_DIR, "uploads"),
    ]
    for directory in required_dirs:
        pathlib.Path(directory).mkdir(parents=True, exist_ok=True)


def remove_old_dumps(days=7):
    """Remove database dump files older than the specified number of days
    while ensuring at least one recent dump is retained"""
    dumps_dir = pathlib.Path(BACKUP_DIR, "db_dumps")
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


def create_db_dump(current_date_time):
    """Create a compressed database dump using pg_dump and gzip"""
    output_path = join(BACKUP_DIR, "db_dumps", f"{current_date_time}.sql.gz")
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

    with open(output_path, "wb") as output_file:
        # Use gzip to compress the output of pg_dump directly to the file
        with gzip.GzipFile(fileobj=output_file, mode="wb") as gz_file:
            # Try running pg_dump with the provided environment variables,
            # and if it fails due to authentication issues, try again without PGPASSWORD
            try:
                run(pg_dump_cmd, check=True, stdout=gz_file, env=env)
            except Exception:
                if "PGPASSWORD" in env:
                    env.pop("PGPASSWORD", None)
                    run(pg_dump_cmd, check=True, stdout=gz_file, env=env)
                else:
                    raise


def export_tables():
    """Export all models that have _backup = True and _export_field_names defined
    to XLSX and TSV formats"""

    # Export tables only for models that have _backup = True and _export_field_names defined
    [
        export_db_table(m, create_export_resource(m))
        for m in apps.get_models()
        if getattr(m, "_backup", False) and getattr(m, "_export_field_names", False)
    ]


def sync_uploads():
    """Sync the uploads directory to the backup location using
    rsync if available, otherwise fall back to shutil.copytree"""

    src_dir = pathlib.Path(BASE_DIR, "uploads")
    dst_dir = pathlib.Path(BACKUP_DIR, "uploads")

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


ENV_DIR = dirname(BASE_DIR)
BACKUP_DIR = join(BASE_DIR, "db_backup")

CURRENT_DATE_TIME = datetime.now().strftime("%Y%m%d_%H%M")
ensure_backup_directories()
remove_old_dumps(days=7)
create_db_dump(CURRENT_DATE_TIME)
export_tables()
sync_uploads()
