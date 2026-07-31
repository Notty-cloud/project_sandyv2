"""
Tenant scoping.

Every model in this project carries a ``tenant_id``. The authenticated
account's tenant is the only one it may read or write; a ``tenant_id`` that
arrives in the query string or request body is untrusted input and is ignored.

Scoping deliberately fails closed — if the caller's tenant cannot be
determined the queryset is emptied rather than left unfiltered, so a future
authentication change cannot silently expose every school's records.
"""


def request_tenant_id(request):
    """Return the caller's own tenant id, or None when unauthenticated."""
    return getattr(getattr(request, 'user', None), 'tenant_id', None)


def scope_to_tenant(queryset, request, field='tenant_id'):
    """Restrict ``queryset`` to the caller's tenant."""
    tenant_id = request_tenant_id(request)
    if tenant_id is None:
        return queryset.none()
    return queryset.filter(**{field: tenant_id})


class TenantScopedMixin:
    """
    Scope a ModelViewSet to the caller's tenant.

    Reads are narrowed by :func:`scope_to_tenant`, which also governs
    ``get_object`` — so detail, update and delete routes return 404 for another
    tenant's record instead of acting on it. Writes have ``tenant_id`` forced to
    the caller's tenant, so a payload cannot plant a row in someone else's.
    """

    tenant_field = 'tenant_id'

    def get_queryset(self):
        return scope_to_tenant(super().get_queryset(), self.request, self.tenant_field)

    def perform_create(self, serializer):
        serializer.save(**{self.tenant_field: request_tenant_id(self.request)})
