from django.contrib import admin

from common.export import export_objects

from .export import VirusMammalianExportResource, VirusInsectExportResource


@admin.action(description="Export selected viruses")
def export_virus_mammalian(modeladmin, request, queryset):
    """Export Virus Mammalian"""

    export_data = VirusMammalianExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


@admin.action(description="Export selected viruses")
def export_virus_insect(modeladmin, request, queryset):
    """Export Virus Insect"""

    export_data = VirusInsectExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
