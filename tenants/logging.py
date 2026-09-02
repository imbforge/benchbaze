# common/logging.py
import logging

from django.conf import settings
from django_tenants.utils import get_current_tenant

PUBLIC_SCHEMA_NAME = getattr(settings, "PUBLIC_SCHEMA_NAME", "main")


class TenantLogFilter(logging.Filter):
    """
    Injects the active tenant's schema_name into log records.
    """

    def filter(self, record):
        tenant = get_current_tenant()
        record.tenant_schema = tenant.schema_name if tenant else PUBLIC_SCHEMA_NAME
        return True
