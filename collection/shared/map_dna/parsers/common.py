import re
from typing import Any, Dict, List, Optional

from Bio.SeqFeature import SimpleLocation

UNTITLED_SEQUENCE_NAME = "Untitled Sequence"


def _encode_newlines_like_ts(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return value
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", "&#10;")


def _normalize_snapgene_parsed_sequence(data: Dict[str, Any]) -> Dict[str, Any]:
    # OVE pipeline runs validateSequenceArray, which injects defaults and
    # normalizes feature bounds from segmented locations.
    data.setdefault("comments", [])
    data.setdefault("extraLines", [])
    data.setdefault("type", "PROTEIN" if data.get("isProtein") else "DNA")

    features = data.get("features") or []
    is_circular = bool(data.get("circular"))
    for feat in features:
        feat.setdefault("notes", {})
        locations = feat.get("locations") or []
        if not locations:
            continue

        starts = [
            loc.get("start") for loc in locations if isinstance(loc.get("start"), int)
        ]
        ends = [loc.get("end") for loc in locations if isinstance(loc.get("end"), int)]
        if not starts or not ends:
            continue

        first_start = locations[0].get("start")
        last_end = locations[-1].get("end")
        has_internal_start_reset = any(
            isinstance(locations[i - 1].get("start"), int)
            and isinstance(locations[i].get("start"), int)
            and locations[i].get("start") < locations[i - 1].get("start")
            for i in range(1, len(locations))
        )

        if (
            is_circular
            and has_internal_start_reset
            and isinstance(first_start, int)
            and isinstance(last_end, int)
            and first_start <= last_end
        ):
            # Match OVE handling for circular segmented features that contain
            # an internal origin-reset chunk: collapse to outer span and
            # omit explicit locations.
            feat["start"] = first_start
            feat["end"] = last_end
            feat.pop("locations", None)
            continue

        if (
            isinstance(first_start, int)
            and isinstance(last_end, int)
            and first_start > last_end
        ):
            if is_circular:
                # Origin-spanning segmented feature on circular sequence.
                feat["start"] = first_start
                feat["end"] = last_end
            else:
                # Match OVE behavior for wrap-like segmented locations in
                # linear records: clamp to origin for feature start.
                feat["start"] = 0
                feat["end"] = last_end
        else:
            feat["start"] = min(starts)
            feat["end"] = max(ends)
    return data


def _parse_primer_location(rangespec, strand, record_length, is_primer=False):
    """Stolen from Bio.SeqIO.SnapGeneIO._parse_location with some modifications to adapt it for OVE"""

    start, end = (int(x) for x in rangespec.split("-"))
    # Account for SnapGene's 1-based coordinates
    start = start - 1
    if is_primer:
        # Primers' coordinates in SnapGene files are shifted by -1
        # for some reasons
        start += 1
    if start > end:
        # Range wrapping the end of the sequence
        l1 = SimpleLocation(start, record_length, strand=strand)
        l2 = SimpleLocation(0, end, strand=strand)
        location = l1 + l2
    else:
        location = SimpleLocation(start, end, strand=strand)
    return location


def _parse_snapgene_primers_sgff(primers, hybridization_params, record_length):
    """Stolen from Bio.SeqIO.SnapGeneIO._parse_primers_packet with some modifications to adapt it for OVE
    and include additional information
    """

    # Get hybridization parameters and filter binding sites based on them
    min_match_length = int(hybridization_params.get("minContinuousMatchLen", 0))
    min_melting_temp = int(hybridization_params.get("minMeltingTemperature", 0))

    # Process each primer and its binding sites to construct OVE-compatible primer
    # objects with locations and notes
    primers_ove = []
    for recent_id, primer in enumerate(primers):
        locations = []
        primer["recentID"] = str(recent_id)

        # Normalize binding sites to a list of dicts, handling cases where it's a single dict or None
        binding_sites = primer.get("BindingSite", primer.get("bindingSite", []))
        if isinstance(binding_sites, dict):
            binding_sites = [binding_sites]
        elif binding_sites is None:
            binding_sites = []
        elif not isinstance(binding_sites, list):
            binding_sites = [binding_sites]

        for site in binding_sites:
            if not isinstance(site, dict):
                continue
            if "location" not in site:
                raise ValueError("Missing binding site location")
            rng = site.get("location")

            strand = int(site.get("boundStrand", "0"))
            if strand == 1:
                strand = -1
            else:
                strand = +1

            location = _parse_primer_location(
                rng, strand, record_length, is_primer=True
            )
            simplified = int(site.get("simplified", "0")) == 1
            if simplified and location in locations:
                # Duplicate "simplified" binding site, ignore
                continue
            annealed = site.get("annealedBases")
            if annealed is not None and len(annealed) < min_match_length:
                continue
            melting_temp = site.get("meltingTemperature")
            if melting_temp is not None and int(melting_temp) < min_melting_temp:
                continue
            locations.append(location)

            quals = {
                "name": primer.get("name", ""),
                "start": int(location.start),
                "end": int(location.end),
                "strand": strand,
                "sgff_primer": primer,  # Not included by the OVE parser
                "sgff_annealed_bases": annealed,
                "sgff_range": f"{location.start}-{location.end}",
                "sgff_strand": strand,
            }
            if colour := primer.get("color"):
                quals["color"] = colour

            if (
                description := primer.get("description", "")
                .replace("<html><body>", "")
                .replace("</body></html>", "")
                .strip()
            ):
                quals["notes"] = {"description": [description]}

            primers_ove.append(quals)

    return primers_ove


def _sgff_strand_to_ts(strand: str) -> Dict[str, Any]:
    if strand == "+":
        return {"strand": 1, "arrowheadType": "TOP"}
    if strand == "-":
        return {"strand": -1, "arrowheadType": "BOTTOM"}
    if strand == "=":
        return {"strand": 1, "arrowheadType": "BOTH"}
    return {"strand": 1, "arrowheadType": "NONE"}


def normalize_sgff_segment_range(segment):
    start_str, end_str = segment["range"].split("-", 1)
    return int(start_str.strip()) - 1, int(end_str.strip()) - 1


def _encode_newlines_like_ts(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return value
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", "&#10;")


def _parse_sgff_feature_segments(
    segments: Dict[str, Any],
    is_protein: bool,
    initial_color: Optional[str] = None,
) -> tuple[List[Dict[str, int]], int, int, Optional[str]]:
    """Parse SGFF segments into locations with bounds and color."""
    locations: List[Dict[str, int]] = []
    color = initial_color

    for seg in segments:
        start, end = normalize_sgff_segment_range(seg)
        if isinstance(seg.get("color"), str) and seg.get("color"):
            color = seg["color"]
        if start < 0:
            start = 0
        if end < 0:
            end = 0
        if is_protein:
            start = start * 3
            end = end * 3 + 2
        locations.append({"start": start, "end": end})

    start_val = 0
    end_val = 0
    if locations:
        start_val = max(loc["start"] for loc in locations)
        end_val = max(loc["end"] for loc in locations)

    return locations, start_val, end_val, color


def _normalize_genbank_qualifier_value(key: str, value: Any) -> Any:
    """Normalize GenBank qualifier values, converting to strings or integers as
    appropriate for certain keys"""

    if value is None:
        return value
    if key in {"note", "locus_tag"}:
        return value if isinstance(value, str) else str(value)
    if isinstance(value, str) and re.fullmatch(r"\d+", value):
        return int(value)
    return value


def _parse_snapgene_feature_sgff(
    sgff_feature: Dict[str, Any], is_protein: bool
) -> List[Dict[str, Any]]:
    name = sgff_feature.get("name")
    if isinstance(name, str):
        # Keep OVE newline entities but normalize away space-only suffixes.
        name = _encode_newlines_like_ts(name.strip(" \t"))

    feature_type = sgff_feature.get("type")
    if isinstance(feature_type, str):
        feature_type = feature_type.strip()
    if not feature_type:
        feature_type = "misc_feature"

    locations, start_val, end_val, color = _parse_sgff_feature_segments(
        sgff_feature.get("segments"),
        is_protein,
        sgff_feature.get("color")
        if isinstance(sgff_feature.get("color"), str) and sgff_feature.get("color")
        else None,
    )

    # Notes
    notes: Dict[str, List[Any]] = {}
    for k, vals in (sgff_feature.get("qualifiers") or {}).items():
        normalized_vals = vals if isinstance(vals, list) else [vals]
        notes[k] = [_normalize_genbank_qualifier_value(k, v) for v in normalized_vals]

    strand_info = _sgff_strand_to_ts(sgff_feature.get("strand", "."))
    sgff_feature["raw_qualifiers"] = None
    feature_obj: Dict[str, Any] = {
        "name": name,
        "type": feature_type,
        "strand": strand_info["strand"],
        "arrowheadType": strand_info["arrowheadType"],
        "start": start_val,
        "end": end_val,
        "color": color,
        "notes": notes,
        "sgff_feature": sgff_feature,  # Not included by the OVE parser
    }
    if len(locations) > 1:
        feature_obj["locations"] = locations

    return feature_obj


def _validate_sequence_array(
    results: List[Dict[str, Any]], _options: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Best-effort Python equivalent of validateSequenceArray"""

    return results


def _flatten_sequence_array(
    results: Any, _opts: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Best-effort Python equivalent of flattenSequenceArray"""

    if results is None:
        return []
    if isinstance(results, list):
        return results
    return [results]


def _create_initial_sequence(
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    options = options or {}
    file_name = options.get("fileName")
    if file_name:
        base = re.sub(r"\.[^/.]+$", "", str(file_name))
    else:
        base = UNTITLED_SEQUENCE_NAME
    return {
        "messages": [],
        "success": True,
        "parsedSequence": {
            "features": [],
            "name": base,
            "sequence": "",
        },
    }
