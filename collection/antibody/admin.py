from common.admin import AddDocFileInlineMixin, DocFileInlineMixin

from ..shared.admin import CollectionSimpleAdmin
from .models import AntibodyDoc
from .search import AntibodyQLSchema


class AntibodyDocInline(DocFileInlineMixin):
    """Inline to view existing Antibody documents"""

    model = AntibodyDoc


class AntibodyAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Antibody documents"""

    model = AntibodyDoc


class AntibodyAdmin(CollectionSimpleAdmin):
    djangoql_schema = AntibodyQLSchema
    inlines = [AntibodyDocInline, AntibodyAddDocInline]
