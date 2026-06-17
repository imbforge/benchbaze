import argparse
import json
import re
import sys
import warnings
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sgffp import SgffReader

from collection.shared.map_dna.utils.save_snapgene import update_snapgene_map_file

TEST_DATA_DIR = Path(__file__).resolve().parent / "files_for_testing"
ORIGINAL_SG_PATH = TEST_DATA_DIR / "original.dna"


def _load_json(path: Path) -> Any:
    """Load JSON data from the given file path"""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_data(value: Any) -> Any:
    """Recursively convert data to a normalized form for comparison"""

    if isinstance(value, dict):
        return {key: _normalize_data(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize_data(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return list(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _strip_feature_comparison_fields(feature: dict[str, Any]) -> dict[str, Any]:
    """Remove fields from feature dict that are not relevant for semantic comparison"""

    feature = dict(feature)
    feature.pop("raw_qualifiers", None)
    feature.pop("extras", None)
    return feature


def _warn_on_ignored_feature_fields(
    actual: dict[str, Any], expected: dict[str, Any], case_name: str, index: int
) -> None:
    """Print warnings if raw feature fields differ, since these are ignored in semantic comparison"""

    for key in ("raw_qualifiers", "extras"):
        actual_value = actual.get(key)
        expected_value = expected.get(key)
        if actual_value != expected_value:
            warnings.warn(
                f"Case {case_name}: feature[{index}].{key} differs but is ignored in semantic comparison. "
                f"expected={expected_value!r} actual={actual_value!r}",
                UserWarning,
                stacklevel=3,
            )


def _parse_sgff_properties(data: bytes) -> Dict[str, Any]:
    """Parse relevant properties from SGFF data for semantic comparison"""

    sgff = SgffReader.from_bytes(data)
    return {
        "sequence": str(sgff.sequence.value),
        "topology": str(sgff.sequence.topology).lower(),
        "features": [
            _normalize_data(_strip_feature_comparison_fields(feature.to_dict()))
            for feature in sgff.features
        ],
        "primers": [_normalize_data(primer.to_dict()) for primer in sgff.primers]
        if sgff.primers
        else [],
    }


def _parse_sgff_raw_feature_fields(data: bytes) -> list[dict[str, Any]]:
    """Extract raw feature fields from SGFF data for warning purposes"""

    sgff = SgffReader.from_bytes(data)
    return [_normalize_data(feature.to_dict()) for feature in sgff.features]


def _iter_test_cases() -> tuple[str, Path, Path]:
    """Yield tuples of (case_name, json_path, expected_sg_path) for each test case"""

    for json_path in sorted(TEST_DATA_DIR.glob("*.json")):
        if json_path.stem == "unchanged":
            expected_sg_path = ORIGINAL_SG_PATH
        else:
            expected_sg_path = TEST_DATA_DIR / f"{json_path.stem}.dna"

        if not expected_sg_path.exists():
            raise FileNotFoundError(
                f"Missing expected reference SnapGene file for {json_path.name}: {expected_sg_path}"
            )
        yield json_path.stem, json_path, expected_sg_path


def _to_number_if_possible(value: Any) -> Any:
    """Convert a string to int or float if it looks like a number, otherwise return original value"""

    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        try:
            if "." in value or "e" in value.lower():
                return float(value)
        except ValueError:
            pass
    return value


def _is_semantically_equal(a: Any, b: Any) -> bool:
    """Determine if two values are semantically equal, treating numeric strings and numbers as equal"""

    if a == b:
        return True
    a_conv = _to_number_if_possible(a)
    b_conv = _to_number_if_possible(b)
    return a_conv == b_conv


def _get_owner_name_for_path(path: str, data: Dict[str, Any]) -> str | None:
    """Extract the name of the feature or primer that owns the field at the given path, if applicable"""

    feature_match = re.match(r"^\$\.features\[(\d+)\]", path)
    if feature_match:
        index = int(feature_match.group(1))
        features = data.get("features", [])
        if isinstance(features, list) and 0 <= index < len(features):
            return features[index].get("name")

    primer_match = re.match(r"^\$\.primers\[(\d+)\]", path)
    if primer_match:
        index = int(primer_match.group(1))
        primers = data.get("primers", [])
        if isinstance(primers, list) and 0 <= index < len(primers):
            return primers[index].get("name")

    return None


def _warn_on_ignored_strand_fields(
    actual: dict[str, Any], expected: dict[str, Any], case_name: str, index: int
) -> None:
    """Print warnings if strand fields differ in a way that should be ignored"""

    actual_strand = actual.get("strand")
    expected_strand = expected.get("strand")
    if expected_strand == "." and actual_strand in {"+", "-"}:
        warnings.warn(
            f"Case {case_name}: feature[{index}].strand differs because OVE does not support '.' strand values. "
            f"expected={expected_strand!r} actual={actual_strand!r}",
            UserWarning,
            stacklevel=3,
        )


def _is_ignored_strand_difference(path: str, a: Any, b: Any) -> bool:
    """Determine if a difference in strand values should be ignored because OVE does not support '.' strand values"""

    if not path.endswith(".strand"):
        return False
    if {a, b} == {".", "+"}:
        return True
    if {a, b} == {".", "-"}:
        return True
    return False


def _collect_diffs(
    a: Any, b: Any, path: str = "$", out: list[dict] | None = None
) -> list[dict]:
    """Recursively collect differences between two data structures, ignoring certain known non-semantic differences"""

    if out is None:
        out = []

    if type(a) is not type(b):
        if _is_semantically_equal(a, b) or _is_ignored_strand_difference(path, a, b):
            return out
        out.append({"path": path, "a": a, "b": b})
        return out

    if isinstance(a, dict):
        a_keys = set(a.keys())
        b_keys = set(b.keys())
        for key in sorted(a_keys - b_keys):
            out.append({"path": f"{path}.{key}", "a": a[key], "b": None})
        for key in sorted(b_keys - a_keys):
            out.append({"path": f"{path}.{key}", "a": None, "b": b[key]})
        for key in sorted(a_keys & b_keys):
            _collect_diffs(a[key], b[key], f"{path}.{key}", out)
        return out

    if isinstance(a, list):
        if len(a) != len(b):
            out.append({"path": f"{path}.length", "a": len(a), "b": len(b)})
        for index in range(min(len(a), len(b))):
            _collect_diffs(a[index], b[index], f"{path}[{index}]", out)
        return out

    if not _is_semantically_equal(a, b) and not _is_ignored_strand_difference(
        path, a, b
    ):
        out.append({"path": path, "a": a, "b": b})
    return out


def test_update_snapgene_map_file_matches_expected(
    case_name: str,
    json_path: Path,
    expected_sg_path: Path,
    warn_ignored: bool = True,
) -> None:
    """Test that the output of update_snapgene_map_file matches the expected SnapGene file for the given test case,
    ignoring known non-semantic differences"""

    # Load original SnapGene file and edited JSON data
    original_bytes = ORIGINAL_SG_PATH.read_bytes()
    edited_json = _load_json(json_path)

    # Generate new SnapGene file bytes from the original and edited JSON
    output_bytes = update_snapgene_map_file(original_bytes, edited_json)
    expected_bytes = expected_sg_path.read_bytes()

    # Parse relevant properties from both SGFF files for comparison
    output_data = _parse_sgff_properties(output_bytes)
    expected_data = _parse_sgff_properties(expected_bytes)

    # Reorder features and primers in output_data to match expected_data if they have the same names in reverse order.
    # Also keep the raw feature field order aligned for warning comparisons.
    if [f["name"] for f in output_data["features"]] == [
        f["name"] for f in expected_data["features"]
    ][::-1]:
        output_data["features"] = list(reversed(output_data["features"]))
        output_raw = _parse_sgff_raw_feature_fields(output_bytes)
        output_raw = list(reversed(output_raw))
    else:
        output_raw = _parse_sgff_raw_feature_fields(output_bytes)

    if [f["name"] for f in output_data["primers"]] == [
        f["name"] for f in expected_data["primers"]
    ][::-1]:
        output_data["primers"] = list(reversed(output_data["primers"]))

    expected_raw = _parse_sgff_raw_feature_fields(expected_bytes)

    # Check that the number of features is the same before comparing individual features
    if len(output_raw) != len(expected_raw):
        raise AssertionError(
            f"Generated SnapGene file for {case_name} has differing feature count: "
            f"expected={len(expected_raw)} actual={len(output_raw)}"
        )

    # Print warnings for any differences in raw feature fields
    for index, (actual_feature, expected_feature) in enumerate(
        zip(output_raw, expected_raw)
    ):
        if warn_ignored:
            _warn_on_ignored_feature_fields(
                actual_feature, expected_feature, case_name, index
            )
            _warn_on_ignored_strand_fields(
                actual_feature, expected_feature, case_name, index
            )

    # Collect semantic differences between the two parsed data structures, ignoring known non-semantic differences
    diffs = _collect_diffs(output_data, expected_data)
    if diffs:
        diff_lines = []
        for diff in diffs:
            # Get the name of the feature or primer that owns the field at this path
            owner_name = _get_owner_name_for_path(
                diff["path"], output_data
            ) or _get_owner_name_for_path(diff["path"], expected_data)
            name_info = f" ({owner_name})" if owner_name else ""
            diff_lines.append(
                f"{diff['path']}{name_info}: expected={diff['b']!r} actual={diff['a']!r}"
            )
        diff_text = "\n".join(diff_lines)
        raise AssertionError(
            f"Generated SnapGene file for {case_name} does not match expected semantic output."  # noqa: E501
            f"\n{diff_text}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare update_snapgene_map_file output against reference SnapGene files."
    )
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Print warnings for ignored raw feature fields (raw_qualifiers/extras).",
    )
    parser.add_argument(
        "--hide-warnings",
        action="store_true",
        help="Suppress warnings for ignored raw feature fields.",
    )
    args = parser.parse_args()

    if args.show_warnings and args.hide_warnings:
        parser.error("--show-warnings and --hide-warnings cannot be used together")

    if args.hide_warnings:
        warnings.filterwarnings("ignore", category=UserWarning)
    elif args.show_warnings:
        warnings.filterwarnings("default", category=UserWarning)

    warn_ignored = not args.hide_warnings

    failures = []

    for case_name, json_path, expected_sg_path in _iter_test_cases():
        try:
            test_update_snapgene_map_file_matches_expected(
                case_name, json_path, expected_sg_path, warn_ignored=warn_ignored
            )
            print(f"PASS: {case_name}")
        except AssertionError as exc:
            print(f"FAIL: {case_name}: {exc}", file=sys.stderr)
            failures.append(case_name)

    if failures:
        print(f"\n{len(failures)} test case(s) failed.", file=sys.stderr)
        return 1

    print("All test cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
