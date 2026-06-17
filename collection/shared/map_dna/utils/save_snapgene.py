import json
from Bio.SeqUtils import MeltingTemp as mt
from seguid import cdseguid, ldseguid
from sgffp import SgffFeature, SgffPrimer, SgffReader, SgffSegment, SgffWriter
from .colour_maps import SNAPGENE_FEATURE_COLOUR_MAP
from .common import _read_uploaded_file_content
from Bio.Seq import Seq


def changed_sequence(seq_a, seq_b, seq_a_topology, seq_b_topology):
    """Check if two sequences are identical by comparing their topology and SEGUID
    checksums and return whether the sequence and the topology have changed
    """

    if seq_a_topology != seq_b_topology:
        return True, True

    seq_a = Seq(str(seq_a).upper())
    seq_b = Seq(str(seq_b).upper())
    checksum_function = cdseguid if seq_a_topology == "circular" else ldseguid
    checksum_a = checksum_function(
        str(seq_a), str(seq_a.reverse_complement()), alphabet="{DNA}"
    )
    checksum_b = checksum_function(
        str(seq_b), str(seq_b.reverse_complement()), alphabet="{DNA}"
    )

    return checksum_a != checksum_b, False


def _normalize_ove_colour(colour, feature_type):
    """Normalize the colour value from OVE, handling cases where it may be a list or missing,
    and falling back to a default based on feature type"""
    if isinstance(colour, list):
        colour = colour[0] if colour else None

    if colour is None:
        colour = SNAPGENE_FEATURE_COLOUR_MAP.get(
            feature_type, SNAPGENE_FEATURE_COLOUR_MAP["_default"]
        )

    return str(colour) if colour is not None else None


def _build_ove_segments(feature_ove, colour):
    """Build a list of SgffSegment objects for the feature based on the OVE feature data"""
    locations = feature_ove.get("locations") or [feature_ove]
    return [
        SgffSegment(
            start=segment["start"],
            end=segment["end"] + 1,
            color=colour,
        )
        for segment in locations
    ]


def create_new_sgff_feature_segments(feature_ove, colour, plasmid_changed):
    """Create a new list of SgffSegment objects for the feature based on the
    OVE feature data"""

    feature_sgff = feature_ove.get("sgff_feature", {})
    ranges_sgff = {seg["range"]: seg for seg in feature_sgff.get("segments", [])}

    new_ranges = []
    identical_ranges = True
    locations = feature_ove.get("locations") or [feature_ove]
    for segment in locations:
        coordinate_range = f"{segment['start'] + 1}-{segment['end'] + 1}"

        # If the plasmid has not changed and the coordinate range from OVE matches
        # an existing segment in the original feature, keep the original segment to
        # preserve any existing properties that are not present in the OVE data
        if not plasmid_changed and coordinate_range in ranges_sgff:
            new_ranges.append(ranges_sgff[coordinate_range])
            continue

        identical_ranges = False
        new_range = {
            "range": coordinate_range,
            "color": colour,
            "type": "standard",
        }
        if "translation" in feature_ove.get("notes", {}):
            new_range["translated"] = True
        new_ranges.append(new_range)

    return new_ranges, identical_ranges


def convert_ove_to_sgff_features(feature_ove, recent_id, plasmid_changed):
    """Create a new SgffFeature for the map_dna file with the given properties"""

    notes = feature_ove.get("notes", {}) or {}
    colour = _normalize_ove_colour(feature_ove.get("color"), feature_ove["type"])
    feature = feature_ove.get("sgff_feature", {})
    if "extras" in feature:
        if isinstance(feature["extras"], dict):
            feature["extras"]["recentID"] = recent_id
        else:
            feature["extras"] = {"recentID": recent_id}

    # If an original feature is found, update its properties based on the OVE data.
    # We just update the properties that are editable in OVE
    if feature:
        feature["name"] = feature_ove["name"]
        feature["type"] = feature_ove["type"]
        new_strand = "+" if feature_ove["strand"] == 1 else "-"
        original_strand = str(feature.get("strand"))
        feature["strand"] = new_strand
        feature["qualifiers"] = notes
        feature["raw_qualifiers"] = None
        feature["segments"], identical_ranges = create_new_sgff_feature_segments(
            feature_ove, colour, plasmid_changed
        )
        # If the feature ranges or strand have changed, reset extras
        if identical_ranges or (new_strand != original_strand):
            feature["extras"] = {"recentID": recent_id}
        feature_sgff = SgffFeature.from_dict(feature)

    # If no original feature is found, create a new one from the OVE data
    else:
        feature_sgff = SgffFeature(
            name=feature_ove["name"],
            type=feature_ove["type"],
            strand="+" if feature_ove["strand"] == 1 else "-",
            segments=_build_ove_segments(feature_ove, colour),
            qualifiers=notes,
            color=colour,
        )

    return feature_sgff


def _prepare_sgff_primers(sgff_map, primers):
    """Prepare the SGFF primer collection and return deduplicated primers."""

    # Migrate HybridizationParams from an existing SGFF primer wrapper, otherwise
    # set default values
    if sgff_map.primers:
        _ = list(sgff_map.primers)
        wrapper_extras = getattr(sgff_map.primers, "_wrapper_extras", {}) or {}
    else:
        wrapper_extras = {
            "HybridizationParams": {
                "minContinuousMatchLen": "10",
                "allowMismatch": "1",
                "minMeltingTemperature": "40",
                "showAdditionalFivePrimeMatches": "1",
                "minimumFivePrimeAnnealing": "15",
            },
        }

    # If a primer originates from SnapGene, it has a sgff_primer field with a unique recentID
    # For these primers, only keep the first occurrence of a recentID
    unique_primers = []
    seen_recent_ids = set()
    for primer in primers:
        sgff_primer = primer.get("sgff_primer")
        if not sgff_primer:
            unique_primers.append(primer)
            continue

        recent_id = sgff_primer.get("recentID")
        if not recent_id or recent_id in seen_recent_ids:
            continue

        seen_recent_ids.add(recent_id)
        unique_primers.append(primer)

    sgff_map.primers.clear()
    wrapper_extras["nextValidID"] = str(len(unique_primers))
    sgff_map.blocks[5] = [{"Primers": dict(wrapper_extras)}]
    sgff_map.primers._wrapper_extras = dict(wrapper_extras)
    sgff_map.primers._sync()

    return unique_primers


def _build_ove_primer_binding_site(primer_range, primer_sequence, strand):
    """Return a binding site dict for OVE primer conversion."""

    return {
        "Component": {
            "hybridizedRange": primer_range,
            "bases": primer_sequence,
        },
        "location": primer_range,
        "boundStrand": "0" if strand == 1 else "1",
        "annealedBases": primer_sequence,
        # N.B.: The value produced by mt.Tm_NN is more often than not ± 5° C from the one
        # reported by SnapGene, but so it is good enough
        "meltingTemperature": round(
            mt.Tm_NN(primer_sequence, Na=100),
            0,
        ),
    }


def convert_ove_to_sgff_primer(
    primer_ove, primer_sequence_fwd, recent_id, plasmid_changed
):
    """Create a new SgffPrimer for the map_dna file with the given properties."""

    primer_ove_range = f"{primer_ove['start']}-{primer_ove['end']}"
    primer_sgff = primer_ove.get("sgff_primer")
    primer = dict(primer_sgff) if isinstance(primer_sgff, dict) else {}
    strand = primer_ove["strand"]
    primer_sequence = (
        primer_sequence_fwd
        if strand == 1
        else str(Seq(primer_sequence_fwd).reverse_complement())
    )

    keep_primer_sgff = (
        primer
        and not plasmid_changed
        and primer_ove.get("sgff_range") == primer_ove_range
        and primer_ove.get("sgff_strand") == strand
    )

    # If neither the plasmid nor the primer binding sites/strand have  changed,
    # keep the original sgff primer to preserve any existing properties not
    # supplied by OVE
    if keep_primer_sgff:
        primer["name"] = primer_ove["name"]
    else:
        annealed_bases = primer_ove.get("sgff_annealed_bases") or ""

        # If the annealed bases have not changed, it is probably the same primer as
        # sgff_primer just at a different location, likely due to a change in the
        # plasmid sequence
        if primer and annealed_bases.upper() == primer_sequence.upper():
            primer["name"] = primer_ove["name"]
            primer["BindingSite"] = _build_ove_primer_binding_site(
                primer_ove_range, primer_sequence, strand
            )
        # These are primers that are added directly in OVE or completely changed from
        # the original sgff_primer, so create a primer anew
        else:
            primer = {
                "name": primer_ove["name"],
                "sequence": primer_sequence,
                "BindingSite": _build_ove_primer_binding_site(
                    primer_ove_range, primer_sequence, strand
                ),
            }

    # Set the primer color, but only if the primer comes from a sgff_primer
    # (i.e. it is not a completely new primer added in OVE)
    if "color" in primer_ove and primer_sgff:
        primer["color"] = primer_ove["color"]

    if notes := primer_ove.get("notes", {}):
        if "description" in notes:
            description = (
                notes["description"]
                if isinstance(notes["description"], list)
                else [notes["description"]]
            )
            primer["description"] = (
                f"<html><body>{'<br/>'.join(description)}</body></html>"
            )
        # Update key notes if key not one the keys below
        for key, note in notes.items():
            if key not in {
                "description",
                "name",
                "sequence",
                "bindingSite",
                "strand",
                "BindingSite",
                "recentID",
                "color",
                "phosphorylated",
                "dateAdded",
            }:
                primer[key] = note

    primer["recentID"] = recent_id

    return SgffPrimer.from_dict(primer)


def update_snapgene_map_file(map_file_original_sg, map_file_edited_json):
    """Build an updated SnapGene map file from the original file and edited JSON payload."""

    original_content = _read_uploaded_file_content(map_file_original_sg)
    if not isinstance(original_content, (bytes, bytearray)):
        raise TypeError("map_file_original_sg must be bytes or file-like")

    sgff_record = SgffReader.from_bytes(original_content)

    if isinstance(map_file_edited_json, str):
        map_file_edited_json = json.loads(map_file_edited_json)

    required_keys = {"sequence", "features", "primers"}
    if not required_keys.issubset(map_file_edited_json):
        raise ValueError("Edited JSON is missing required fields")

    # Take an "original" SnapGene map and the OVE JSON of the edited/final
    # map and update the SnapGene map to reflect the edits. Update: sequence,
    # features, and primers. Anything else?

    # Check if sequence or topology have changed, if so update them
    topology_ove = (
        "circular" if map_file_edited_json.get("circular", False) else "linear"
    )
    sequence_changed, topology_changed = changed_sequence(
        sgff_record.sequence.value,
        map_file_edited_json["sequence"],
        sgff_record.sequence.topology,
        topology_ove,
    )
    if sequence_changed:
        sgff_record.set_sequence(
            str(map_file_edited_json["sequence"]), record_history=True
        )
    if topology_changed:
        sgff_record.sequence.topology = topology_ove
        sgff_record.ops.change_topology()

    plasmid_changed = sequence_changed or topology_changed

    # Add features
    sgff_record.features.clear()
    if features := map_file_edited_json["features"].values():
        for recent_id, feature in enumerate(features):
            sgff_record.features.add(
                convert_ove_to_sgff_features(feature, recent_id, plasmid_changed)
            )

    # If primers are present, persist any existing primer extras that are not supplied by OVE to avoid
    if primers := map_file_edited_json["primers"].values():
        unique_primers = _prepare_sgff_primers(sgff_record, primers)
        for recent_id, primer in enumerate(unique_primers):
            sgff_record.primers.add(
                convert_ove_to_sgff_primer(
                    primer,
                    map_file_edited_json.get("sequence", "")[
                        primer["start"] : primer["end"] + 1
                    ],
                    recent_id,
                    plasmid_changed,
                )
            )
    else:
        sgff_record.primers.clear()

    return SgffWriter.to_bytes(sgff_record)
