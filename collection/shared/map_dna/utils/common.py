import os
from io import StringIO

import requests
from Bio import SeqIO


def get_feature_label(feature):
    """Prefer label-like qualifiers when available, then fall back to feature type."""

    # Check common label-like qualifiers in order of preference, returning the first one found
    for key in ("label", "gene", "locus_tag", "note"):
        value = feature.qualifiers.get(key)
        if isinstance(value, list) and value:
            return str(value[0]).strip()
        elif isinstance(value, str) and value.strip():
            return str(value).strip()

    return feature.type


def get_map_file_format(map_file_name, file_format=""):
    """Normalize map file format from explicit field or filename extension."""

    file_format = (file_format or "").strip().lower()
    if file_format:
        return file_format

    file_name = (map_file_name or "").strip()
    extension = os.path.splitext(file_name)[1].lower()
    return extension if extension else None


def _read_uploaded_file_content(uploaded_file):
    """Read the contents of an uploaded file object or raw bytes."""

    if hasattr(uploaded_file, "read"):
        return uploaded_file.read()
    return uploaded_file


def seqrecord_to_genbank_text(seq_record):
    """Write a SeqRecord to GenBank format and return the resulting text."""
    processed_handle = StringIO()
    SeqIO.write(seq_record, processed_handle, "genbank")
    return processed_handle.getvalue()


def process_genbank_map_file(map_file_edited):
    """Read and normalize an edited GenBank map file, returning clean GenBank text."""

    content = _read_uploaded_file_content(map_file_edited)
    if isinstance(content, bytes):
        content = content.decode()

    seq_record = SeqIO.read(StringIO(content), "genbank")
    return seqrecord_to_genbank_text(seq_record)


def get_map_dna_seqrecord(path):
    """Returns a SeqRecord object for the map_dna file, or None if not available or invalid"""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Map DNA file not found at path: {path}")

    try:
        name = os.path.basename(path).lower()
        if name.endswith(".dna"):
            return SeqIO.read(path, "snapgene")
        elif name.endswith((".gbk", ".gb")):
            return SeqIO.read(path, "genbank")
    except Exception:
        return None


def extract_location_bounds(location):
    """Return (start, end, strand_symbol) for a location, merging parts if needed."""

    if location is None:
        return None

    # If the location has multiple parts (e.g. from a join), take the min start and max
    # end across all parts
    parts = getattr(location, "parts", None)
    if parts and len(parts) > 1:
        start = min(int(part.start) for part in parts)
        end = max(int(part.end) for part in parts)
        strand = location.strand
        if strand is None:
            for part in parts:
                if part.strand is not None:
                    strand = part.strand
                    break
    # If the location has no parts, just take its start and end
    else:
        start = int(location.start)
        end = int(location.end)
        strand = location.strand
    # Convert strand to symbol to be descriptive
    strand_symbol = {1: "+", -1: "-"}.get(strand, "?")
    return (start, end, strand_symbol)


def is_ignored_feature(feature):
    label = get_feature_label(feature).strip().lower()
    ftype = feature.type.strip().lower()
    return label == "source" or ftype == "source" or ftype == "primer_bind"


def get_map_dna_features_simple(seq_record):
    """Returns a list of features in the map_dna file, with each feature represented
    as a tuple of

    (label, type, (start, end, strand_symbol))

    The start and end positions are merged across all parts of the feature if it has
    multiple parts (e.g. from a join). Strand is represented as '+' for forward, '-'
    for reverse, and '?' for unknown or mixed."""

    if not isinstance(seq_record, SeqIO.SeqRecord):
        raise ValueError("Input must be a SeqRecord object")

    return [
        (get_feature_label(f), f.type, extract_location_bounds(f.location))
        for f in seq_record.features
        if not is_ignored_feature(f)
    ]


def get_map_dna_feature_names(seq_record):
    """Return the names of the features in the map_dna file"""

    if not isinstance(seq_record, SeqIO.SeqRecord):
        raise ValueError("Input must be a SeqRecord object")

    features = get_map_dna_features_simple(seq_record)
    feature_names = [feature[0].strip() for feature in features]

    return feature_names


def convert_map_dna_to_svg(path, title):
    """Convert the map_dna file to svg format for display in the frontend"""

    if not os.path.exists(path):
        raise FileNotFoundError(f"Map DNA file not found at path: {path}")

    # Get the map_dna file as an SVG string from the conversion service
    response = requests.get(
        "http://localhost:3000",
        params={
            "path": path,
            "title": title,
        },
    )

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to convert the map to SVG. Response: {response.text}")
