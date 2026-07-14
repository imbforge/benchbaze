import re
from io import StringIO
from typing import Any, Dict, List, Optional

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

from .common import (
    UNTITLED_SEQUENCE_NAME,
    _create_initial_sequence,
    _flatten_sequence_array,
    _normalize_genbank_qualifier_value,
    _normalize_snapgene_parsed_sequence,
    _parse_snapgene_feature_sgff,
    _parse_snapgene_primers_sgff,
    _validate_sequence_array,
)

GenBankInput = str | SeqRecord

GB_DIVISIONS = {
    "PRI": True,
    "ROD": True,
    "MAM": True,
    "VRT": True,
    "INV": True,
    "PLN": True,
    "BCT": True,
    "VRL": True,
    "PHG": True,
    "SYN": True,
    "UNA": True,
    "EST": True,
    "PAT": True,
    "SOVE": True,
    "GSS": True,
    "HTG": True,
    "HTC": True,
    "ENV": True,
    "CON": True,
}


def _split_string_into_lines(text: str) -> List[str]:
    """Best-effort Python equivalent of splitStringIntoLines"""

    if text == "":
        return []
    lines = re.split(r"\r?\n", text)
    if len(lines) == 1:
        lines = text.split("\\n")
    return lines


def _genbank_feature_name_from_qualifiers(qualifiers: Dict[str, Any]) -> str:
    """Get a feature name from GenBank qualifiers, trying various common keys
    in order of precedence.
    Check postProcessGenbankFeature in original OVE for rationale on key order"""

    for key in (
        "label",
        "gene",
        "ApEinfo_label",
        "name",
        "product",
        "region_name",
        "organism",
        "locus_tag",
    ):
        vals = qualifiers.get(key)
        if not vals:
            continue
        vals_list = vals if isinstance(vals, list) else [vals]
        name = vals_list[0]
        if name == 0:
            return "0"
        if name:
            return str(name)

    # Fall back to using the first 100 characters of the "note" qualifier if no better
    # name keys are found
    note_vals = qualifiers.get("note")
    if isinstance(note_vals, list) and note_vals:
        return str(note_vals[0])[:100]

    return "Untitled Feature"


def _genbank_arrowhead_type_from_qualifiers(
    qualifiers: Dict[str, Any],
) -> Optional[str]:
    """Determine arrowhead type from GenBank qualifiers, using the "direction" qualifier if it has a valid value"""

    direction_vals = qualifiers.get("direction")
    if not isinstance(direction_vals, list) or not direction_vals:
        return None

    direction = str(direction_vals[0]).upper()
    if direction in {"BOTH", "NONE"}:
        return direction
    return None


def _construct_bounds(
    locations: List[Dict[str, int]],
    start: Optional[int],
    end: Optional[int],
    *,
    include_locations: bool,
) -> Dict[str, Any]:
    """Helper function to construct a dictionary representing the location of a feature"""
    return {
        "start": start,
        "end": end,
        "locations": locations if include_locations and len(locations) > 1 else None,
    }


def _location_has_int_bounds(location: Dict[str, Any]) -> bool:
    """Defensive check to make sure a location has integer start and end bounds"""

    return isinstance(location.get("start"), int) and isinstance(
        location.get("end"), int
    )


def _all_locations_have_int_bounds(locations: List[Dict[str, Any]]) -> bool:
    """Check if all locations in a list have integer start and end bounds"""

    return all(_location_has_int_bounds(location) for location in locations)


def _select_feature_bounds(
    merged_locations: List[Dict[str, int]],
    *,
    is_circular: bool,
    has_wraparound_segment: bool,
    forward_wrap_merge_needs_location_collapse: bool,
    preserve_point_order: bool,
    preserve_ove_circular_source_order: bool,
    reverse_parts_need_ove_order_recovery: bool,
    has_overlapping_chain: bool,
    has_trailing_contained_segments: bool,
) -> Dict[str, Any]:
    """Select the appropriate start and end bounds for a feature"""
    starts = [
        loc.get("start")
        for loc in merged_locations
        if isinstance(loc.get("start"), int)
    ]
    ends = [
        loc.get("end") for loc in merged_locations if isinstance(loc.get("end"), int)
    ]

    # If there are no valid integer bounds, return None for start and end and include all locations
    # if there are multiple locations
    if not starts or not ends:
        return _construct_bounds(
            merged_locations,
            None,
            None,
            include_locations=True,
        )

    first_start = merged_locations[0].get("start")
    last_end = merged_locations[-1].get("end")
    preserves_ordered_bounds = (
        preserve_point_order
        or preserve_ove_circular_source_order
        or reverse_parts_need_ove_order_recovery
    )

    # If there is a wraparound segment and the original order appears to be in source order
    # with the head before the tail, preserve the original first start and last end as the
    # feature bounds, and include locations unless the forward wrap merge needs location collapse
    if (
        is_circular
        and isinstance(first_start, int)
        and isinstance(last_end, int)
        and has_wraparound_segment
    ):
        return _construct_bounds(
            merged_locations,
            first_start,
            last_end,
            include_locations=not forward_wrap_merge_needs_location_collapse,
        )

    # If the original order appears to be in source order with the head before the tail,
    # preserve the original first start and last end as the feature bounds, and include locations
    if (
        preserves_ordered_bounds
        and isinstance(first_start, int)
        and isinstance(last_end, int)
    ):
        return _construct_bounds(
            merged_locations,
            first_start,
            last_end,
            include_locations=True,
        )

    # If there is an overlapping chain and the original order appears to be in reverse order,
    # preserve the original first start and last end as the feature bounds, and exclude locations
    if (
        has_overlapping_chain
        and isinstance(first_start, int)
        and isinstance(last_end, int)
    ):
        return _construct_bounds(
            merged_locations,
            first_start,
            last_end,
            include_locations=False,
        )

    # If there are trailing contained segments and the original order appears to be in reverse order,
    # preserve the original first start and last end as the feature bounds, and exclude locations
    if (
        has_trailing_contained_segments
        and isinstance(first_start, int)
        and isinstance(last_end, int)
    ):
        return _construct_bounds(
            merged_locations,
            first_start,
            last_end,
            include_locations=False,
        )

    # Otherwise, return the min start and max end as the feature bounds
    return _construct_bounds(
        merged_locations,
        min(starts),
        max(ends),
        include_locations=True,
    )


def _sorted_int_locations(
    locations: List[Dict[str, Any]],
) -> Optional[List[Dict[str, int]]]:
    """Return a new list of locations sorted by start and end bounds,
    or None if any location is missing integer bounds"""

    if not _all_locations_have_int_bounds(locations):
        return None
    return sorted(locations, key=lambda loc: (loc["start"], loc["end"]))


def _sort_locations_by_bounds(
    locations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Sort locations by start and end bounds, treating non-integer
    bounds as coming after integer bounds"""

    return sorted(
        locations,
        key=lambda loc: (
            not isinstance(loc.get("start"), int),
            loc.get("start") if isinstance(loc.get("start"), int) else 0,
            not isinstance(loc.get("end"), int),
            loc.get("end") if isinstance(loc.get("end"), int) else 0,
        ),
    )


def _is_wraparound_location(location: Dict[str, Any]) -> bool:
    """Determine if a location represents a wraparound segment that crosses the
    origin of a circular sequence"""

    return _location_has_int_bounds(location) and location["start"] > location["end"]


def _find_wraparound_segment_index(
    locations: List[Dict[str, Any]],
) -> Optional[int]:
    """Find the index of the first location that represents a wraparound segment,
    or None if there is no such location"""

    return next(
        (
            idx
            for idx, location in enumerate(locations)
            if _is_wraparound_location(location)
        ),
        None,
    )


def _locations_form_overlapping_chain(locations: List[Dict[str, Any]]) -> bool:
    """Check if locations form an overlapping chain where each location overlaps with the previous one"""

    sorted_locations = _sorted_int_locations(locations)
    if sorted_locations is None or len(sorted_locations) <= 1:
        return False
    return all(
        sorted_locations[idx]["start"] <= sorted_locations[idx - 1]["end"]
        for idx in range(1, len(sorted_locations))
    )


def _locations_have_trailing_contained_segments(
    locations: List[Dict[str, Any]],
) -> bool:
    """Check if there are any locations that have all subsequent locations fully contained within their bounds"""

    sorted_locations = _sorted_int_locations(locations)
    if sorted_locations is None or len(sorted_locations) <= 2:
        return False

    for idx, location in enumerate(sorted_locations[:-1]):
        trailing_locations = sorted_locations[idx + 1 :]
        if trailing_locations and all(
            trailing_location["start"] >= location["start"]
            and trailing_location["end"] <= location["end"]
            for trailing_location in trailing_locations
        ):
            return True

    return False


def _locations_are_all_points(locations: List[Dict[str, Any]]) -> bool:
    """Check if all locations represent points where start and end are the same integer"""

    return all(
        _location_has_int_bounds(location) and location["start"] == location["end"]
        for location in locations
    )


def _locations_form_contiguous_chain(locations: List[Dict[str, Any]]) -> bool:
    """Check if locations form a contiguous chain where each location starts exactly one
    base after the previous location ends"""

    sorted_locations = _sorted_int_locations(locations)
    if sorted_locations is None or len(sorted_locations) <= 1:
        return False
    return all(
        sorted_locations[idx]["start"] == sorted_locations[idx - 1]["end"] + 1
        for idx in range(1, len(sorted_locations))
    )


def _merge_circular_origin_segments(
    locations: List[Dict[str, int]],
    sequence_length: int,
    strand_num: int,
) -> tuple[List[Dict[str, int]], Optional[Dict[str, int]]]:
    """Merge adjacent tail/head pairs of locations that cross the origin of a circular sequence,
    according to the behavior of OVE's wrapOriginSpanningFeatures function"""

    merged_locations = [dict(loc) for loc in locations]
    wraparound_merge_context: Optional[Dict[str, int]] = None

    if not merged_locations:
        return merged_locations, wraparound_merge_context

    # Recover OVE wrapOriginSpanningFeatures behaviour by only merging an
    # adjacent tail/head pair that crosses the origin.
    i = 0
    while i < len(merged_locations) - 1:
        first_segment = merged_locations[i]
        second_segment = merged_locations[i + 1]
        first_start = first_segment.get("start")
        first_end = first_segment.get("end")
        second_start = second_segment.get("start")
        second_end = second_segment.get("end")

        first_is_tail = isinstance(first_end, int) and first_end == sequence_length - 1
        second_is_head = isinstance(second_start, int) and second_start == 0
        first_is_head = isinstance(first_start, int) and first_start == 0
        second_is_tail = (
            isinstance(second_end, int) and second_end == sequence_length - 1
        )

        if strand_num != -1 and first_is_tail and second_is_head:
            wraparound_merge_context = {
                "tail_start": first_start,
                "tail_end": first_end,
                "head_start": second_start,
                "head_end": second_end,
                "merge_index": i,
            }
            merged_locations[i] = {
                "start": first_start,
                "end": second_end,
            }
            merged_locations.pop(i + 1)
            continue

        if strand_num == -1 and first_is_head and second_is_tail:
            merged_locations[i] = {
                "start": second_start,
                "end": first_end,
            }
            merged_locations.pop(i + 1)
            continue

        i += 1

    return merged_locations, wraparound_merge_context


def _should_collapse_forward_wrap_merge_locations(
    locations: List[Dict[str, int]],
    wraparound_segment_index: Optional[int],
    wraparound_merge_context: Optional[Dict[str, int]],
    is_circular: bool,
    strand_num: int,
) -> bool:
    """Determine if a forward-strand wraparound merge should collapse its merged tail/head pair
    of locations into a single location, based on whether there are any trailing locations after
    the merge that would be fully contained within the merged location or that would extend the
    head by only a small gap"""

    if not (
        is_circular
        and strand_num != -1
        and wraparound_merge_context is not None
        and wraparound_segment_index == wraparound_merge_context.get("merge_index")
    ):
        return False

    trailing_locations = locations[wraparound_segment_index + 1 :]
    tail_start = wraparound_merge_context.get("tail_start")
    tail_end = wraparound_merge_context.get("tail_end")
    head_end = wraparound_merge_context.get("head_end")
    tail_length = (
        tail_end - tail_start + 1
        if isinstance(tail_start, int) and isinstance(tail_end, int)
        else None
    )

    trailing_are_contained_in_tail = bool(trailing_locations) and all(
        _location_has_int_bounds(loc)
        and isinstance(tail_start, int)
        and isinstance(tail_end, int)
        and loc["start"] >= tail_start
        and loc["end"] <= tail_end
        for loc in trailing_locations
    )

    # Only merge the head with a trailing location if the gap between the head and
    # the previous location is at most 2 bases, to account for small gaps that may be
    # introduced by parsing. Probably not necessary
    trailing_extend_head_with_small_gaps = False
    if (
        trailing_locations
        and isinstance(head_end, int)
        and tail_length == 1
        and _all_locations_have_int_bounds(trailing_locations)
    ):
        previous_end = head_end
        trailing_extend_head_with_small_gaps = True
        for loc in trailing_locations:
            if loc["start"] - previous_end > 2:
                trailing_extend_head_with_small_gaps = False
                break
            previous_end = loc["end"]

    # SeqIO occasionally leaves malformed extra segments after the same wrap
    # merge OVE would collapse to a single outer span.
    return trailing_are_contained_in_tail or trailing_extend_head_with_small_gaps


def _normalize_location_order(
    locations: List[Dict[str, int]],
    *,
    is_circular: bool,
    strand_num: int,
    original_first_start: Optional[int],
    original_last_end: Optional[int],
    has_wraparound_segment: bool,
    has_overlapping_chain: bool,
) -> tuple[List[Dict[str, int]], Dict[str, bool]]:
    """Normalize the order of locations. Locations will be sorted by their start and end
    bounds unless any specific conditions are met.
    """

    merged_locations = locations

    # Preserve original order if it appears to be a list of points in reverse order
    # A point is a location where start and end are the same integer
    preserve_point_order = (
        len(merged_locations) > 1
        and isinstance(original_first_start, int)
        and isinstance(original_last_end, int)
        and original_first_start > original_last_end
        and _locations_are_all_points(merged_locations)
    )

    # Preserve original order for circular sequences if the original order appears to be
    # in source order with the head before the tail
    preserve_ove_circular_source_order = (
        is_circular
        and strand_num != -1
        and len(merged_locations) > 1
        and isinstance(original_first_start, int)
        and isinstance(original_last_end, int)
        and original_first_start > original_last_end
        and not has_wraparound_segment
        and not has_overlapping_chain
    )

    # Recover the OVE-style reverse order only for reverse-strand contiguous chains when SeqIO
    # returns them in forward genomic order. This preserves the correct original order for that
    # specific GenBank case, while still sorting normally for genuinely reversed or non-GenBank
    # segments
    reverse_parts_need_ove_order_recovery = False
    if (
        len(merged_locations) > 1
        and strand_num == -1
        and isinstance(original_first_start, int)
        and isinstance(original_last_end, int)
        and original_first_start < original_last_end
    ):
        sorted_locations = _sorted_int_locations(merged_locations)
        if sorted_locations is not None:
            if not has_wraparound_segment:
                # OVE parses GenBank location strings in source order. SeqIO can hand us
                # a reverse-strand contiguous chain in forward genomic order instead,
                # so recover the OVE-style reverse order only for that specific shape.
                reverse_parts_need_ove_order_recovery = (
                    _locations_form_contiguous_chain(merged_locations)
                )
                if reverse_parts_need_ove_order_recovery:
                    merged_locations = list(reversed(sorted_locations))
            else:
                # For reverse-strand circular wraparound features, SeqIO may return the
                # wraparound segment after other parts rather than preserving the original
                # GenBank source order. In that case, move the wraparound location to the
                # head of the list so the feature bounds and locations mirror OVE.
                wraparound_index = _find_wraparound_segment_index(merged_locations)
                if (
                    wraparound_index is not None
                    and wraparound_index == len(merged_locations) - 1
                    and not _is_wraparound_location(merged_locations[0])
                ):
                    merged_locations = [merged_locations[-1]] + merged_locations[:-1]
                    reverse_parts_need_ove_order_recovery = True

    # Sort by bounds if there are multiple locations. Don't sort if 1) there is a wraparound
    # segment since those can only be correctly ordered in their original order, or 2) there is
    # an overlapping chain
    should_sort_locations = (
        len(merged_locations) > 1
        and not has_wraparound_segment
        and not preserve_point_order
        and not preserve_ove_circular_source_order
        and not reverse_parts_need_ove_order_recovery
    )
    if should_sort_locations:
        merged_locations = _sort_locations_by_bounds(merged_locations)

    return merged_locations, {
        "preserve_point_order": preserve_point_order,
        "preserve_ove_circular_source_order": preserve_ove_circular_source_order,
        "reverse_parts_need_ove_order_recovery": reverse_parts_need_ove_order_recovery,
    }


def _normalize_feature_bounds_from_locations(
    locations: List[Dict[str, int]],
    sequence_length: int,
    is_circular: bool,
    strand_num: int,
) -> Dict[str, Any]:
    """Normalize the bounds of a feature based on its locations. Handle various edge
    cases related to circular sequences and location ordering.
    The logic is complex to handle a few edge cases that I suspect come from "malformed"
    Genbank files. I will try to simplify this in the future."""

    merged_locations = [dict(loc) for loc in locations]

    # Get the original first start and last end before any merging or sorting, to determine
    # whether the original order appears to be in source order or reverse order
    original_first_start = (
        merged_locations[0].get("start") if merged_locations else None
    )
    original_last_end = merged_locations[-1].get("end") if merged_locations else None

    # Merge circular-origin-crossing segments
    if is_circular:
        merged_locations, wraparound_merge_context = _merge_circular_origin_segments(
            merged_locations,
            sequence_length,
            strand_num,
        )
    else:
        wraparound_merge_context = None

    # Check for the presence of a wraparound segment and find the index of the wraparound segment
    has_wraparound_segment = any(
        _is_wraparound_location(location) for location in merged_locations
    )
    wraparound_segment_index = _find_wraparound_segment_index(merged_locations)

    # Check for various edge cases related to the presence of a wraparound (origin-spanning)
    # segment and the original order of locations, to determine whether the original order
    # needs to be preserved and/or the merged wraparound segment needs to be collapsed into
    # a single location

    # If there are trailing locations after a forward-strand wraparound merge, check if the
    # merged tail/head pair need to be collapsed into a single location to preserve the
    # original bounds
    forward_wrap_merge_needs_location_collapse = (
        _should_collapse_forward_wrap_merge_locations(
            merged_locations,
            wraparound_segment_index,
            wraparound_merge_context,
            is_circular,
            strand_num,
        )
    )

    # Check if there is an overlapping chain of locations that do not form a clear contiguous
    # chain, even after merging any wraparound segments
    has_overlapping_chain = (
        len(merged_locations) > 1
        and not has_wraparound_segment
        and _locations_form_overlapping_chain(merged_locations)
    )

    # Check if there are trailing contained segments that would be fully contained within the
    # bounds of a previous segment
    has_trailing_contained_segments = (
        len(merged_locations) > 2
        and not has_wraparound_segment
        and _locations_have_trailing_contained_segments(merged_locations)
    )

    # Normalize the order of locations
    merged_locations, ordering_flags = _normalize_location_order(
        merged_locations,
        is_circular=is_circular,
        strand_num=strand_num,
        original_first_start=original_first_start,
        original_last_end=original_last_end,
        has_wraparound_segment=has_wraparound_segment,
        has_overlapping_chain=has_overlapping_chain,
    )

    preserve_point_order = ordering_flags["preserve_point_order"]
    preserve_ove_circular_source_order = ordering_flags[
        "preserve_ove_circular_source_order"
    ]
    reverse_parts_need_ove_order_recovery = ordering_flags[
        "reverse_parts_need_ove_order_recovery"
    ]

    return _select_feature_bounds(
        merged_locations,
        is_circular=is_circular,
        has_wraparound_segment=has_wraparound_segment,
        forward_wrap_merge_needs_location_collapse=forward_wrap_merge_needs_location_collapse,
        preserve_point_order=preserve_point_order,
        preserve_ove_circular_source_order=preserve_ove_circular_source_order,
        reverse_parts_need_ove_order_recovery=reverse_parts_need_ove_order_recovery,
        has_overlapping_chain=has_overlapping_chain,
        has_trailing_contained_segments=has_trailing_contained_segments,
    )


def _extract_genbank_raw_metadata(map_dna: str) -> Dict[str, Any]:
    """Directly extract raw metadata from GenBank text by parsing its lines and looking
    for specific keywords and patterns. Necessary because SeqIO doesn't yield all the
    raw metadata that OVE's GenBank parser gives"""

    metadata: Dict[str, Any] = {
        "comments": [],
        "extraLines": [],
    }

    line_type: Optional[str] = None
    has_found_locus = False

    for line in _split_string_into_lines(map_dna):
        if line is None:
            break

        stripped = line.strip()
        if stripped == "" or stripped == ";":
            continue

        # Get the key of a line by looking for the first word before any
        # whitespace or equals sign:
        # If the line starts with a whitespace, use the first word as the key
        # Otherwise use the first word before an equals sign if present
        # If not, the first word before whitespace
        should_use_space_as_delimiter = not stripped.startswith("/")
        key = _get_genbank_line_key(line, should_use_space_as_delimiter)
        key_runon = _is_genbank_keyword_runon(line)
        key_line = _is_genbank_keyword(line)

        # Determine the line type based on the key and whether it's a run-on line:
        # If it's a run-on line, it continues the previous line type
        # If it's a key line, check if the key is one of the main GenBank keywords to set the line type
        # Otherwise use the key as the line type
        if not key_runon:
            if key in {
                "LOCUS",
                "REFERENCE",
                "FEATURES",
                "ORIGIN",
                "//",
                "DEFINITION",
                "ACCESSION",
                "VERSION",
            }:
                line_type = key
            elif key_line:
                line_type = key

        # LOCUS
        if not has_found_locus:
            if line_type != "LOCUS":
                break
            has_found_locus = True

        if line_type == "LOCUS":
            _parse_genbank_locus_metadata(line, metadata)
            continue

        # COMMENT
        if line_type == "COMMENT":
            line2 = re.sub(r"COMMENT", "", line).strip()
            if "teselagen_unique_id:" in line2:
                metadata["teselagen_unique_id"] = line2.replace(" ", "").replace(
                    "teselagen_unique_id:", ""
                )
            elif "library:" in line2:
                metadata["library"] = line2.replace(" ", "").replace("library:", "")
            elif line2:
                metadata["comments"].append(line2)
            continue

        # FEATURES, ORIGIN and //
        if line_type in {
            "FEATURES",
            "ORIGIN",
            "//",
            "DEFINITION",
            "ACCESSION",
            "VERSION",
        }:
            continue

        metadata["extraLines"].append(line)

    return metadata


def _parse_genbank_locus_metadata(line: str, metadata: Dict[str, Any]) -> None:
    """Parse the LOCUS line of a GenBank file to extract metadata such as locus name,
    circularity, division, and date"""

    line_arr = re.split(r"[\s]+", line)
    locus_name = line_arr[1] if len(line_arr) > 1 else UNTITLED_SEQUENCE_NAME
    circular: Optional[bool] = None
    gb_division = None
    date = None

    locus_meta: Dict[str, Any] = {}

    # Circularity
    for item in line_arr[1:]:
        if re.search(r"circular", item, flags=re.I):
            circular = True
        elif re.search(r"linear", item, flags=re.I):
            circular = False

    # Date, sequence type, and GenBank division indicators
    for j, item in enumerate(line_arr[1:], start=1):
        if re.search(r"-[A-Z]{3}-", item):
            date = item
        if j == 3 and re.search(r"aa", item, flags=re.I):
            locus_meta["sequenceTypeFromLocus"] = item
            locus_meta["isProtein"] = True
        if j == 4 and re.search(r"ds-dna|ss-dna|dna|rna", item, flags=re.I):
            if locus_meta.get("isProtein") is None:
                locus_meta["isProtein"] = False
            locus_meta["sequenceTypeFromLocus"] = item
            if re.search(r"ss-dna", item, flags=re.I):
                locus_meta["isDNA"] = True
                locus_meta["isSingleStrandedDNA"] = True
            elif re.search(r"rna", item, flags=re.I):
                locus_meta["isRna"] = True
            elif re.search(r"ds-dna|dna", item, flags=re.I):
                locus_meta["isDNA"] = True
                locus_meta["isDoubleStrandedDNA"] = True
            if re.search(r"rna", item, flags=re.I) and not re.search(
                r"ss-rna", item, flags=re.I
            ):
                locus_meta["isDoubleStrandedRNA"] = True

        if isinstance(item, str) and item.upper() in GB_DIVISIONS:
            gb_division = item.upper()

    # Only set the name from the LOCUS line if it's not "Exported"
    if locus_name.lower() != "exported":
        metadata["name"] = locus_name
    metadata["gbDivision"] = gb_division
    metadata["date"] = date
    metadata["circular"] = circular
    metadata.update(locus_meta)


def _get_genbank_line_key(line: str, should_use_space_as_delimiter: bool) -> str:
    """Extract the key from a GenBank line, which is the first word before any
    whitespace or equals sign"""

    line2 = re.sub(r"^[\s]*", "", line)
    if "=" not in line2 or should_use_space_as_delimiter:
        arr = re.split(r"[\s]+", line2)
    else:
        arr = line2.split("=")
    return arr[0] if arr else ""


def _is_genbank_keyword(line: str) -> bool:
    """Check if the line starts with a GenBank keyword, which is indicated by having
    a non-whitespace character in the first 10 characters"""

    return bool(re.match(r"^[\S]+", line[:10]))


def _is_genbank_keyword_runon(line: str) -> bool:
    """Check if the line is a run-on line that continues from the previous line,
    which is indicated by having whitespace in the first 10 characters"""

    return bool(re.match(r"[\s]{10}", line[:10]))


def _genbank_to_json_via_seqio(
    map_dna: GenBankInput, options: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Parse GenBank input using Biopython's SeqIO parser, and extract metadata and
    features to construct a JSON representation of the sequence that should be as
    close as possible to the output of OVE's GenBank parser"""

    options = dict(options or {})
    initial_sequence = _create_initial_sequence(options)
    parsed_sequence = initial_sequence["parsedSequence"]

    # Get input map
    if isinstance(map_dna, str):
        raw_meta = _extract_genbank_raw_metadata(map_dna)
        record = SeqIO.read(StringIO(map_dna), "genbank")
    elif isinstance(map_dna, SeqRecord):
        raw_meta = {}
        record = map_dna
    else:
        raise TypeError("map_dna must be a GenBank string or SeqRecord")

    # Get relevant metadata from the SeqRecord and its annotations, and use
    # it to populate the parsed sequence object
    sequence = str(record.seq).lower()
    annotations = getattr(record, "annotations", {}) or {}

    topology = str(annotations.get("topology", "")).lower()
    molecule_type = str(annotations.get("molecule_type", "")).lower()

    # Name
    record_name = record.name or ""
    if record_name and record_name.lower() != "exported":
        name = record_name
    elif raw_meta.get("name"):
        name = raw_meta.get("name")
    else:
        name = parsed_sequence.get("name") or UNTITLED_SEQUENCE_NAME

    # Accession
    accession = (
        annotations.get("accessions", [None])[0]
        if isinstance(annotations.get("accessions"), list)
        else annotations.get("accession")
    )
    if accession is None:
        accession = raw_meta.get("accession")

    # Version
    version = annotations.get("sequence_version") or annotations.get("version")
    version = version if version is not None else raw_meta.get("version", ".")

    # Sequence type
    is_dna = "dna" in molecule_type or molecule_type == ""
    is_rna = None
    if ("rna" in molecule_type) or (raw_meta.get("isRna") is not None):
        is_rna = True if "rna" in molecule_type else raw_meta.get("isRna")

    # Populate the parsed sequence object with the extracted metadata and sequence information
    parsed_sequence.update(
        {
            "name": name,
            "sequence": sequence,
            "size": len(sequence),
            "type": "DNA",
            "isProtein": False,
            "circular": True
            if topology == "circular"
            else raw_meta.get("circular", False),
            "gbDivision": annotations.get("data_file_division", "").strip()
            or raw_meta.get("gbDivision", "").strip()
            or "SYN",
            "date": annotations.get("date") or raw_meta.get("date"),
            "definition": raw_meta.get("definition") or record.description or "",
            "description": raw_meta.get("description") or record.description or "",
            "accession": accession,
            "version": version,
            "sequenceTypeFromLocus": raw_meta.get("sequenceTypeFromLocus"),
            "isDNA": is_dna,
            "isDoubleStrandedDNA": True if is_dna else None,
            "comments": raw_meta.get("comments", []),
            "extraLines": raw_meta.get("extraLines", []),
        }
    )

    if raw_meta.get("isSingleStrandedDNA") is not None:
        parsed_sequence["isSingleStrandedDNA"] = raw_meta.get("isSingleStrandedDNA")
    if is_rna is not None:
        parsed_sequence["isRna"] = is_rna
    if raw_meta.get("isDoubleStrandedRNA") is not None:
        parsed_sequence["isDoubleStrandedRNA"] = raw_meta.get("isDoubleStrandedRNA")
    if raw_meta.get("teselagen_unique_id"):
        parsed_sequence["teselagen_unique_id"] = raw_meta["teselagen_unique_id"]
    if raw_meta.get("library"):
        parsed_sequence["library"] = raw_meta["library"]

    # Features
    features: List[Dict[str, Any]] = []
    for feature in record.features:
        feat_obj: Dict[str, Any] = {}

        # Notes
        # We get notes from the SeqRecord qualifiers, no matter whether the file originally
        # comes from GenBank or SnapGene, to ensure that any notes added, for example,
        # during common feature detection, are preserved
        notes: Dict[str, List[Any]] = {}
        for k, vals in (feature.qualifiers or {}).items():
            if k in {"label", "direction"}:
                continue
            normalized_vals = vals if isinstance(vals, list) else [vals]
            notes[k] = [
                _normalize_genbank_qualifier_value(k, v) for v in normalized_vals
            ]

        # If SeqRecord comes from a SnapGene file via Sgff
        if hasattr(record, "converted_from_sgff") and hasattr(feature, "sgff_feature"):
            feat_obj = _parse_snapgene_feature_sgff(
                feature.sgff_feature,
                False,
            )

        # All others
        else:
            # Strand
            strand = getattr(feature.location, "strand", None)
            strand_num = -1 if strand == -1 else 1

            # Parts
            parts = getattr(feature.location, "parts", None)
            loc_parts = parts if parts else [feature.location]
            locs: List[Dict[str, int]] = []
            for part in loc_parts:
                start = int(part.start)
                end = int(part.end) - 1
                locs.append({"start": start, "end": end})

            if not locs:
                continue

            # Normalized feature bounds
            bounds = _normalize_feature_bounds_from_locations(
                locs,
                parsed_sequence["size"],
                bool(parsed_sequence.get("circular")),
                strand_num,
            )

            # Create feature object
            feat_obj = {
                "name": _genbank_feature_name_from_qualifiers(feature.qualifiers or {}),
                "type": feature.type,
                "strand": strand_num,
                "forward": strand_num == 1,
                "start": bounds["start"],
                "end": bounds["end"],
                "notes": notes,
            }
            arrowhead_type = _genbank_arrowhead_type_from_qualifiers(
                feature.qualifiers or {}
            )
            if arrowhead_type:
                feat_obj["arrowheadType"] = arrowhead_type
            if bounds["locations"]:
                feat_obj["locations"] = bounds["locations"]

        feat_obj["notes"] = notes
        features.append(feat_obj)

    # Process features
    for feat in features:
        if feat.get("type") == "primer":
            feat["type"] = "primer_bind"

    if options.get("primersAsFeatures"):
        parsed_sequence["features"] = features

    # If a SeqRecord was converted from a SnapGene file and has SGFF primer metadata,
    # use that to populate the primers field
    if hasattr(record, "sgff_primer_hybridization_params") and hasattr(
        record, "sgff_primers"
    ):
        parsed_sequence["primers"] = _parse_snapgene_primers_sgff(
            record.sgff_primers,
            record.sgff_primer_hybridization_params,
            len(record.seq),
        )
        parsed_sequence["features"] = features
    else:
        parsed_sequence["primers"] = [
            f for f in features if f.get("type") == "primer_bind"
        ]
        parsed_sequence["features"] = [
            f for f in features if f.get("type") != "primer_bind"
        ]

    # Normalize the parsed sequence object from SnapGene if applicable
    if hasattr(record, "converted_from_sgff"):
        initial_sequence["parsedSequence"] = _normalize_snapgene_parsed_sequence(
            parsed_sequence
        )

    return _validate_sequence_array(
        _flatten_sequence_array([initial_sequence], options), options
    )


def genbank_to_json(
    map_dna: str, options: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    try:
        return _genbank_to_json_via_seqio(map_dna, options)
    except Exception as e:
        return [
            {
                "success": False,
                "error": f"Import Error: {str(e)}",
            }
        ]
