import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django_tenants.utils import get_current_tenant

PUBLIC_SCHEMA_NAME = getattr(settings, "PUBLIC_SCHEMA_NAME", "public")
MEDIA_ROOT = settings.MEDIA_ROOT
MEDIA_URL = settings.MEDIA_URL


class TenantFileSystemStorage(FileSystemStorage):
    """
    FileSystemStorage that dynamically sets location based on the active
    tenant schema, but keeps public URLs clean (schema-agnostic).
    """

    @property
    def location(self):
        # Return tenant-specific MEDIA_ROOT (e.g., "/path/to/uploads/tenant1/")
        tenant = get_current_tenant()
        schema = tenant.schema_name if tenant else PUBLIC_SCHEMA_NAME
        return os.path.join(MEDIA_ROOT, schema)

    @property
    def base_url(self):
        # Return standard MEDIA_URL (e.g., "/uploads/") without appending the schema name
        base_url = MEDIA_URL
        if not base_url.endswith("/"):
            base_url += "/"
        return base_url
