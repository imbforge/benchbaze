from pathlib import Path

from django.core.management.base import BaseCommand

from config.settings import MEDIA_ROOT
from config.settings import BASE_DIR
from django import apps


class Command(BaseCommand):
    help = "Creates relevant project folders, e.g. .logs and uploads"

    def handle(self, *args, **options):
        paths = set()

        # Add the .logs folder to the set of paths to create
        paths.add(Path(BASE_DIR / ".logs"))

        # Get all paths for the uploads folder
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if upload_to := getattr(field, "upload_to", None):
                    paths.add(Path(MEDIA_ROOT / upload_to))
            if (
                (_mixin_props := getattr(model, "_mixin_props", None))
                and isinstance(_mixin_props, dict)
                and (destination_dir := _mixin_props.get("destination_dir"))
            ):
                paths.add(Path(MEDIA_ROOT / destination_dir))

        for folder in paths:
            folder.mkdir(parents=True, exist_ok=True)
            # NB: The user running the web app, e.g. www-data,
            # must have access to these folders
            folder.chmod(0o770)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created folder: {folder}")
            )

        self.stdout.write(self.style.SUCCESS("Done"))
