import os

from django.conf import settings
from django.http import HttpResponse, JsonResponse

from .parsers.genbank import genbank_to_json
from .parsers.seqrecord import seqrecord_to_json
from .parsers.snapgene import snapgene_to_json
from .utils.common import (
    get_map_file_format,
    process_genbank_map_file,
)
from .utils.detect_features import detect_map_dna_features
from .utils.save_snapgene import update_snapgene_map_file

BASE_DIR = getattr(settings, "BASE_DIR", "")


def _method_not_allowed():
    return JsonResponse(
        {"success": False, "error": "Invalid request method"}, status=405
    )


def _bad_request(message):
    return JsonResponse({"success": False, "error": message}, status=400)


def _resolve_map_file_path(file_path):
    """Resolve the map file path, ensuring it is within the allowed directory"""

    if not file_path:
        raise ValueError(
            "Missing required file or parameter: map_file_path or map_file_content"
        )

    # Prevent directory traversal by normalizing the path and ensuring it is within BASE_DIR
    if os.path.isabs(file_path):
        file_path = file_path.lstrip(os.sep)
    file_path = file_path.lstrip("/\\")

    normalized_path = os.path.normpath(os.path.join(BASE_DIR, file_path))
    base_dir_norm = os.path.normpath(BASE_DIR)
    if os.path.commonpath([base_dir_norm, normalized_path]) != base_dir_norm:
        raise ValueError("Invalid map_file_path")
    if not os.path.isfile(normalized_path):
        raise ValueError("Map file not found")

    return normalized_path


def convert_any_to_ove_json(request):
    """Accept uploaded map file as content or file path, convert it to OVE JSON
    for the viewer, and return the JSON content.
    Optionally detects features during conversion if detect_features flag is set
    in the request."""

    if request.method != "POST":
        return _method_not_allowed()

    # Determine file name and format from request data or uploaded file
    file_name = (
        request.POST.get("map_file_path", "")
        or request.POST.get("map_file_name", "")
        or getattr(request.FILES.get("map_file_content"), "name", "")
    )

    if not file_name:
        return _bad_request("Could not find file name in request")

    file_format = get_map_file_format(
        file_name,
        request.POST.get("file_format", request.POST.get("map_file_format", "")),
    )
    if not file_format:
        return _bad_request("Could not determine file format from request")

    # Check if detect_features flag is set in the request (default to false)
    detect_features = request.POST.get("detect_features", "false").lower() == "true"

    # Convert the map file content to OVE JSON for the viewer, optionally detecting features
    try:
        # Check if file content is provided directly in the request
        if "map_file_content" in request.FILES:
            map_file = request.FILES["map_file_content"].read()

        # Otherwise read it from the provided file path
        else:
            map_file_path = request.POST.get("map_file_path", "")
            normalized_path = _resolve_map_file_path(map_file_path)
            with open(normalized_path, "rb") as content_file:
                map_file = content_file.read()

        # If detect_features flag is set, process the map file to detect features before converting to JSON
        if detect_features:
            map_file = detect_map_dna_features(map_file, file_format)
            file_format = (
                ".seqrecord"  # Detected features are returned as SeqRecord format
            )
    except ValueError as exc:
        return _bad_request(str(exc))
    except Exception as exc:
        return _bad_request(f"Error processing map file: {exc}")

    # Convert the map file content to JSON format for the viewer
    if file_format == ".dna":
        processed_content = snapgene_to_json(map_file)
    elif file_format in (".gbk", ".gb"):
        if isinstance(map_file, bytes):
            map_file = map_file.decode("utf-8")
        processed_content = genbank_to_json(map_file)
    elif file_format == ".seqrecord":
        processed_content = seqrecord_to_json(map_file)
    else:
        return _bad_request("Unsupported file format")

    return JsonResponse(
        processed_content,
        safe=False,
        json_dumps_params={"ensure_ascii": False},
    )


def create_map_file(request):
    """Accept uploaded map information and return processed map content for the viewer, which
    is then saved back to the form"""

    if request.method != "POST":
        return _method_not_allowed()

    # Check that required fields are present
    if "map_file_name" not in request.POST or "map_file_format" not in request.POST:
        error_message = "Missing required files or parameters: "
        if "map_file_name" not in request.POST:
            error_message += "map_file_name "
        if "map_file_format" not in request.POST:
            error_message += "map_file_format"
        return _bad_request(error_message)

    map_file_name = request.POST.get("map_file_name", "")
    map_file_format = get_map_file_format(
        map_file_name, request.POST.get("map_file_format", "")
    )

    # GenBank
    # Convert the uploaded GenBank content back to GenBank format using Biopython
    # to ensure proper formatting
    if map_file_format in (".gbk", ".gb"):
        if "map_file_edited_gb" not in request.FILES:
            return _bad_request("Missing edited map file")

        processed_content = process_genbank_map_file(
            request.FILES["map_file_edited_gb"]
        )
        content_type = "text/plain; charset=utf-8"

    # SnapGene
    # Create a new .dna file on the server using the original .dna file as base but
    # update its features, primers and sequence based on the edited sequence data
    # sent as JSON from the viewer
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
            return _bad_request(error_message)

        processed_content = update_snapgene_map_file(
            request.FILES["map_file_original_sg"],
            request.POST.get("map_file_edited_json", "{}"),
        )
        content_type = "application/octet-stream"

    else:
        return _bad_request("Unsupported file format")

    file_name_root = os.path.splitext(map_file_name)[0]
    processed_file_name = f"{file_name_root}_detected_features{map_file_format}"

    response = HttpResponse(
        processed_content,
        content_type=content_type,
    )
    response["Content-Disposition"] = f'inline; filename="{processed_file_name}"'
    response["X-BB-Viewer-File-Name"] = processed_file_name

    return response
