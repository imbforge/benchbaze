from typing import Any, Dict, List, Optional
import re
import os

from .common import (
    _normalize_snapgene_parsed_sequence,
    _parse_snapgene_feature_sgff,
    _parse_snapgene_primers_sgff,
    _validate_sequence_array,
    _flatten_sequence_array,
    _create_initial_sequence,
)


def _get_sgff_object_from_file(file_obj: Any) -> Any:
    from sgffp import SgffReader

    if isinstance(file_obj, str):
        return SgffReader.from_file(file_obj)

    return SgffReader.from_bytes(_get_array_buffer_from_file(file_obj))


def _get_array_buffer_from_file(file_obj: Any) -> bytes:
    """Best-effort Python equivalent of getArrayBufferFromFile"""

    if isinstance(file_obj, (bytes, bytearray)):
        return bytes(file_obj)
    if isinstance(file_obj, str):
        with open(file_obj, "rb") as f:
            return f.read()
    if hasattr(file_obj, "read"):
        data = file_obj.read()
        return data if isinstance(data, bytes) else bytes(data)
    raise TypeError("file_obj must be bytes, file path, or file-like object")


def _parse_snapgene_notes_sgff(sgff_obj: Any) -> Dict[str, Optional[str]]:
    out = {"name": None, "description": None}
    notes = sgff_obj.notes.data if getattr(sgff_obj, "has_notes", False) else {}

    custom_map_label = notes.get("CustomMapLabel") if isinstance(notes, dict) else None
    if isinstance(custom_map_label, str):
        stripped_name = custom_map_label.strip()
        if stripped_name:
            out["name"] = stripped_name

    description = notes.get("Description") if isinstance(notes, dict) else None
    if isinstance(description, str):
        out["description"] = description.replace("<html><body>", "").replace(
            "</body></html>", ""
        )

    return out


def _extract_file_extension(file_name: Optional[str]) -> Optional[str]:
    """Best-effort Python equivalent of extractFileExtension"""
    if not file_name:
        return None
    ext = os.path.splitext(str(file_name))[1]
    return ext[1:].lower() if ext.startswith(".") else ext.lower()


def snapgene_to_json(
    file_obj: Any, options: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    options = dict(options or {})
    return_val = _create_initial_sequence(options)
    sgff_obj = _get_sgff_object_from_file(file_obj)
    ext = _extract_file_extension(options.get("fileName"))

    is_protein = bool(options.get("isProtein", False))
    if ext and re.match(r"^(prot)$", ext):
        is_protein = True
        options["isProtein"] = True

    sequence = str(sgff_obj.sequence.value or "")
    is_circular = str(sgff_obj.sequence.topology).lower() == "circular"

    data = {
        **return_val["parsedSequence"],
        "isDNA": bool(getattr(sgff_obj.cookie, "type_of_sequence", 0))
        and not is_protein,
        "exportVersion": getattr(sgff_obj.cookie, "export_version", None),
        "importVersion": getattr(sgff_obj.cookie, "import_version", None),
        "features": [
            _parse_snapgene_feature_sgff(f.to_dict(), is_protein)
            for f in sgff_obj.features
        ],
        "circular": is_circular,
        "size": len(sequence) * 3 if is_protein else len(sequence),
        "sequence": sequence,
    }

    # Primers
    if sgff_obj.primers:
        data["primers"] = _parse_snapgene_primers_sgff(
            [primer.to_dict() for primer in sgff_obj.primers],
            sgff_obj.blocks[5][0]
            .get("Primers", {})
            .get("HybridizationParams", {})
            .copy()
            if 5 in sgff_obj.blocks
            else {},
            record_length=sgff_obj.sequence.length,
        )

    if is_protein or ("isProtein" in options):
        data["isProtein"] = is_protein

    notes = _parse_snapgene_notes_sgff(sgff_obj)
    if notes.get("name"):
        data["name"] = notes["name"]
    if notes.get("description") is not None:
        data["description"] = notes["description"]

    return_val["parsedSequence"] = _normalize_snapgene_parsed_sequence(data)
    return _validate_sequence_array(
        _flatten_sequence_array([return_val], options), options
    )
