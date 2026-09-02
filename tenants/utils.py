from rest_framework.test import APIClient


class TenantAPIClient(APIClient):
    """
    DRF APIClient configured to direct requests to a specific django-tenants tenant domain.
    """

    def __init__(self, tenant, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        # Get the tenant's primary domain
        domain = tenant.domains.first().domain

        # Set the host header so django-tenants middleware routes to this tenant
        self.defaults["HTTP_HOST"] = domain
