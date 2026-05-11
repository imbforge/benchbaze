import os

from django.http import HttpResponse, JsonResponse

from .utils import (
    convert_snapgene_bytes_to_genbank,
    detect_map_dna_features,
    get_map_file_format,
    process_genbank_map_file,
    process_snapgene_map_file,
    seqrecord_to_genbank_text,
)


def convert_snapgene_to_genbank(request, *args, **kwargs):
    """Convert SnapGene file content to GenBank format using Biopython and pass it back to the viewer.
    We do this because Biopython's SnapGene parser is more robust than OVE's one.
    """

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    # Check if required fields are present
    if "map_file_snapgene" not in request.FILES:
        return JsonResponse(
            {"success": False, "error": "No SnapGene file uploaded"}, status=400
        )

    map_file_snapgene = request.FILES["map_file_snapgene"]
    file_name = getattr(map_file_snapgene, "name", None)
    if not file_name:
        return JsonResponse(
            {"success": False, "error": "Could not find file name"},
            status=400,
        )

    # Read uploaded SnapGene file content and convert to GenBank format using Biopython
    try:
        map_file_content = map_file_snapgene.read()
        processed_content = convert_snapgene_bytes_to_genbank(map_file_content)
    except Exception as exc:
        return JsonResponse(
            {"success": False, "error": f"Error converting SnapGene file: {str(exc)}"},
            status=400,
        )

    output_file_name = f"{os.path.splitext(file_name)[0]}.gbk"
    response = HttpResponse(
        processed_content,
        content_type="text/plain; charset=utf-8",
    )
    response["Content-Disposition"] = f'inline; filename="{output_file_name}"'

    return response


def map_dna_detect_features(request, *args, **kwargs):
    """Accept uploaded map file and return processed map content for the viewer"""

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    # Check if file was uploaded
    if "map_dna_file" not in request.FILES:
        return JsonResponse({"success": False, "error": "No file uploaded"}, status=400)

    # Read uploaded file content
    uploaded_file = request.FILES["map_dna_file"]
    file_content = uploaded_file.read()

    # Determine file format and name
    file_name = getattr(uploaded_file, "name", None)
    if not file_name:
        return JsonResponse(
            {"success": False, "error": "Could not find file name"},
            status=400,
        )
    file_format = os.path.splitext(file_name)[1].lower()
    if not file_format:
        return JsonResponse(
            {"success": False, "error": "Could not determine file format"},
            status=400,
        )

    # Get annotations
    try:
        annotated = seqrecord_to_genbank_text(
            detect_map_dna_features(file_content, file_format)
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error processing file: {str(e)}"},
            status=500,
        )

    # Response
    file_name_root = os.path.splitext(file_name)[0]
    processed_file_name = f"{file_name_root}_detected_features.gbk"

    response = HttpResponse(
        annotated,
        content_type="text/plain; charset=utf-8",
    )
    response["Content-Disposition"] = f'inline; filename="{processed_file_name}"'
    response["X-BB-Viewer-File-Name"] = processed_file_name

    return response


def create_map_file(request):
    """Accept uploaded map information and return processed map content for the viewer, which
    is then saved back to the form"""

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    # Check that required fields are present
    if "map_file_name" not in request.POST or "map_file_format" not in request.POST:
        error_message = "Missing required files or parameters: "
        if "map_file_name" not in request.POST:
            error_message += "map_file_name "
        if "map_file_format" not in request.POST:
            error_message += "map_file_format"
        return JsonResponse({"success": False, "error": error_message}, status=400)

    map_file_name = request.POST.get("map_file_name", "")
    map_file_format = get_map_file_format(
        map_file_name, request.POST.get("fileFormat", "")
    )

    if map_file_format in (".gbk", ".gb"):
        if "map_file_edited_gb" not in request.FILES:
            return JsonResponse(
                {"success": False, "error": "Missing edited map file"}, status=400
            )

        processed_content = process_genbank_map_file(
            request.FILES["map_file_edited_gb"]
        )
        content_type = "text/plain; charset=utf-8"

    elif map_file_format == ".dna":
        if (
            "map_file_original_sg" not in request.FILES
            or "map_file_edited_json" not in request.POST
        ):
            error_message = "Missing required files: "
            if "map_file_original_sg" not in request.FILES:
                error_message += "map_file_original_sg "
            if "map_file_edited_json" not in request.POST:
                error_message += "map_file_edited_json "
            return JsonResponse({"success": False, "error": error_message}, status=400)

        processed_content = process_snapgene_map_file(
            request.FILES["map_file_original_sg"],
            request.POST.get("map_file_edited_json", "{}"),
        )
        content_type = "application/octet-stream"

    else:
        return JsonResponse(
            {"success": False, "error": "Unsupported file format"},
            status=400,
        )

    file_name_root = os.path.splitext(map_file_name)[0]
    processed_file_name = f"{file_name_root}_detected_features{map_file_format}"

    response = HttpResponse(
        processed_content,
        content_type=content_type,
    )
    response["Content-Disposition"] = f'inline; filename="{processed_file_name}"'
    response["X-BB-Viewer-File-Name"] = processed_file_name

    return response
