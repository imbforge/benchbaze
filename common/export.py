from django.http import HttpResponse
from django.utils import timezone


def export_objects_file(queryset, export_data, file_format):
    now = timezone.localtime(timezone.now())
    file_name = f"{queryset.model.__name__}_{now.strftime('%Y%m%d_%H%M%S')}"

    if file_format == "xlsx":
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response.write(export_data.xlsx)
    elif file_format == "tsv":
        response = HttpResponse(content_type="text/tab-separated-values")
        response.write(export_data.tsv)
    else:
        raise ValueError(f"Unsupported export format: {file_format}")

    response["Content-Disposition"] = (
        f'attachment; filename="{file_name}.{file_format}"'
    )

    return response


def export_objects_xlsx(queryset, export_data):
    return export_objects_file(queryset, export_data, "xlsx")


def export_objects_tsv(queryset, export_data):
    return export_objects_file(queryset, export_data, "tsv")
