"""Parity tester for GenBank parsing: @teselagen/bio-parsers vs BenchBaze.

Usage examples:
  python collection/shared/map_dna/viewer/test_parity_genbank.py \
    --input-dir ./gbk_files \
    --output-dir ./gbk_files \
    --output-prefix comparison_genbank

Outputs:
  - <prefix>_full_report.json
  - <prefix>_biological_mismatches_with_ts_values.json
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_python_parser(module_path: Path):
    package_parts = []
    package_paths = []
    current = module_path.parent
    while (current / "__init__.py").exists():
        package_parts.append(current.name)
        package_paths.append(current)
        current = current.parent

    package_parts.reverse()
    package_paths.reverse()

    module_name = module_path.stem
    package_name = ""
    if package_parts:
        package_name = ".".join(package_parts)
        module_name = f"{package_name}.{module_name}"

    for part, path in zip(package_parts, package_paths):
        if package_name == part:
            full_name = part
        else:
            prefix = package_parts[: package_parts.index(part)]
            full_name = ".".join(prefix + [part]) if prefix else part

        if full_name not in sys.modules:
            pkg = types.ModuleType(full_name)
            pkg.__path__ = [str(path)]
            pkg.__package__ = full_name
            sys.modules[full_name] = pkg

    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load parser module: {module_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_ts_genbank(module_url: str, file_path: Path) -> Any:
    js = r"""
import fs from 'fs';
import path from 'path';

const moduleUrl = process.argv[1];
const filePath = process.argv[2];
const m = await import(moduleUrl);
const out = m.genbankToJson(
  fs.readFileSync(filePath, 'utf8'),
  { fileName: path.basename(filePath) }
);
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js, module_url, str(file_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"node exited {proc.returncode}")
    return json.loads(proc.stdout)


def _stable(value: Any) -> Any:
    if isinstance(value, list):
        return [_stable(v) for v in value]
    if isinstance(value, dict):
        return {k: _stable(value[k]) for k in sorted(value.keys())}
    return value


def _collect_diffs(
    a: Any, b: Any, path: str = "$", out: Optional[List[Dict[str, Any]]] = None
):
    if out is None:
        out = []

    if type(a) is not type(b):
        out.append(
            {
                "path": path,
                "aType": type(a).__name__,
                "bType": type(b).__name__,
                "a": a,
                "b": b,
            }
        )
        return out

    if a is None or b is None:
        if a != b:
            out.append({"path": path, "a": a, "b": b})
        return out

    if isinstance(a, list):
        if len(a) != len(b):
            out.append({"path": f"{path}.length", "a": len(a), "b": len(b)})
        for i in range(min(len(a), len(b))):
            _collect_diffs(a[i], b[i], f"{path}[{i}]", out)
        return out

    if isinstance(a, dict):
        a_keys = set(a.keys())
        b_keys = set(b.keys())
        for k in sorted(a_keys - b_keys):
            out.append({"path": f"{path}.{k}", "a": a[k], "b": None, "missingIn": "b"})
        for k in sorted(b_keys - a_keys):
            out.append({"path": f"{path}.{k}", "a": None, "b": b[k], "missingIn": "a"})
        for k in sorted(a_keys & b_keys):
            _collect_diffs(a[k], b[k], f"{path}.{k}", out)
        return out

    if a != b:
        out.append({"path": path, "a": a, "b": b})
    return out


def _is_subsequence(needle: str, haystack: str) -> bool:
    idx = 0
    for ch in haystack:
        if idx < len(needle) and needle[idx] == ch:
            idx += 1
    return idx == len(needle)


def _normalize_fragment_note(value: str) -> Optional[tuple[str, str]]:
    normalized = re.sub(r'^note="?', "", value).strip()
    normalized = normalized.replace('"', "")
    match = re.search(
        r"(?P<name>.+?)\s*(?P<digest>\[\d+\s+nt\]\s*:\s*\([^)]+\))$",
        normalized,
    )
    if not match:
        return None
    return match.group("name").strip(), match.group("digest").strip()


def _is_fragment_note_shortening(ts_value: str, py_value: str) -> bool:
    if "Fragment extracted from" not in py_value:
        return False

    ts_parts = _normalize_fragment_note(ts_value)
    py_parts = _normalize_fragment_note(py_value)
    if not ts_parts or not py_parts:
        return False

    ts_name, ts_digest = ts_parts
    py_name, py_digest = py_parts
    return ts_digest == py_digest and ts_name in py_name


def _normalize_translation_note(value: str) -> str:
    normalized = value.replace('"', "")
    normalized = normalized.replace("direct strand ", "")
    normalized = normalized.replace("translation:", "")
    normalized = normalized.replace("translation=", "")
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _normalize_vntifkey_note(value: str) -> str:
    normalized = re.sub(
        r'vntifkey="[^"]+"\s*-\s*label=.*?\s*-;',
        "vntifkey=-;",
        value,
    )
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _matches_except_trailing_dot(a: str, b: str) -> bool:
    return a.rstrip(".") == b.rstrip(".")


def _is_representation_only(diff: Dict[str, Any]) -> bool:
    p = diff.get("path", "")

    if p == "$[0].parsedSequence.isProtein":
        return True
    if p == "$[0].messages.length":
        return True
    if p.startswith("$[0].messages["):
        return True

    a = diff.get("a")
    b = diff.get("b")
    if isinstance(a, str) and isinstance(b, str):
        # Account for systematic differences between the OVE and the Python parser that
        # are in fact more "correctly" reported by the Python parser

        # The OVE parser sometimes joins wrapped GenBank text without reinserting
        # spaces. Treat pure whitespace-only drift as non-meaningful.
        if re.sub(r"\s+", "", a) == re.sub(r"\s+", "", b):
            return True

        # Treat quote-only corruption as representation drift when the payload is
        # otherwise identical.
        if a.replace('"', "") == b.replace('"', ""):
            return True

        # OVE sometimes truncates note text at an embedded quote while the Python
        # parser preserves the full quoted phrase from the source file.
        if b.startswith(a) and '"' in b:
            return True

        # OVE sometimes flattens backslash-delimited tokens into spaces while the
        # Python parser preserves the literal backslash from the source text.
        a_backslash_normalized = re.sub(r"\s+", " ", a.replace("\\", " ")).strip()
        b_backslash_normalized = re.sub(r"\s+", " ", b.replace("\\", " ")).strip()
        if a_backslash_normalized == b_backslash_normalized:
            return True

        if _normalize_vntifkey_note(a) == _normalize_vntifkey_note(b):
            return True

        # definition/description may differ by a trailing period. The Biopython parser
        # strip this tariling dot while the OVE parser preserves it from the source file
        if p in {"$[0].parsedSequence.definition", "$[0].parsedSequence.description"}:
            if _matches_except_trailing_dot(a, b):
                return True

        # OVE often shortens "Fragment extracted from ..." notes down to the tail
        # file label plus digest coordinates.
        if _is_fragment_note_shortening(a, b):
            return True

        # OVE sometimes truncates long /translation= note payloads while the
        # Python parser keeps the full amino-acid sequence.
        if a.startswith("/translation=") and b.startswith("/translation="):
            a_compact = re.sub(r"\s+", "", a)
            b_compact = re.sub(r"\s+", "", b)
            if len(a_compact) < len(b_compact) and _is_subsequence(
                a_compact, b_compact
            ):
                return True

        # OVE sometimes flattens note-carried translation annotations and drops
        # the descriptive prefix while the Python parser preserves the source.
        if "translation" in a or "translation" in b:
            a_compact = _normalize_translation_note(a)
            b_compact = _normalize_translation_note(b)
            if a_compact == b_compact or _is_subsequence(a_compact, b_compact):
                return True

    return False


def _extract_feature_index(path_text: str) -> Optional[int]:
    prefix = "$[0].parsedSequence.features["
    if prefix not in path_text:
        return None
    rest = path_text.split(prefix, 1)[1]
    idx_text = rest.split("]", 1)[0]
    return int(idx_text) if idx_text.isdigit() else None


def _is_failed_parse(payload: Any) -> bool:
    if not isinstance(payload, list) or not payload:
        return True
    first = payload[0]
    return bool(isinstance(first, dict) and first.get("success") is False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare OVE and Python GenBank parser outputs."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing .gbk/.gb/.genbank files",
    )
    parser.add_argument(
        "--output-dir", required=True, help="Directory for report JSON files"
    )
    parser.add_argument(
        "--output-prefix", default="comparison_genbank", help="Report prefix"
    )
    parser.add_argument(
        "--python-parser", default=None, help="Path to the Python parser file"
    )
    parser.add_argument(
        "--ts-module", default=None, help="Path to @teselagen/bio-parsers/index.js"
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    parser_path = (
        Path(args.python_parser) if args.python_parser else script_dir / "parsers.py"
    )
    ts_path = (
        Path(args.ts_module)
        if args.ts_module
        else script_dir / "node_modules" / "@teselagen" / "bio-parsers" / "index.js"
    )

    if not parser_path.exists():
        raise FileNotFoundError(f"Python parser not found: {parser_path}")
    if not ts_path.exists():
        raise FileNotFoundError(f"OVE parser module not found: {ts_path}")

    ts_module_url = ts_path.resolve().as_uri()
    py_mod = _load_python_parser(parser_path)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    genbank_files = sorted(
        [
            p
            for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".gbk", ".gb", ".genbank", ".gbff"}
        ]
    )

    full_report = {
        "inputDir": str(input_dir),
        "totalFiles": len(genbank_files),
        "processedFiles": 0,
        "matched": [],
        "mismatches": [],
        "skippedCorrupted": [],
        "errors": [],
    }

    biological_report = {
        "sourceMismatchFileCount": 0,
        "biologicallyMeaningfulMismatchFileCount": 0,
        "topMeaningfulDiffPaths": [],
        "mismatches": [],
    }

    path_counts: Dict[str, int] = {}

    for fp in genbank_files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
            ts_out = _run_ts_genbank(ts_module_url, fp)
            py_out = py_mod.genbank_to_json(text, {"fileName": fp.name})

            if _is_failed_parse(ts_out) or _is_failed_parse(py_out):
                full_report["skippedCorrupted"].append(str(fp))
                continue

            full_report["processedFiles"] += 1

            diffs = _collect_diffs(_stable(ts_out), _stable(py_out))
            if not diffs:
                full_report["matched"].append(str(fp))
                continue

            full_report["mismatches"].append(
                {
                    "file": str(fp),
                    "diffCount": len(diffs),
                    "diffPaths": [d["path"] for d in diffs],
                }
            )

            meaningful = [d for d in diffs if not _is_representation_only(d)]
            if not meaningful:
                continue

            ts_features = (
                ts_out[0].get("parsedSequence", {}).get("features", [])
                if isinstance(ts_out, list) and ts_out
                else []
            )

            enriched = []
            for d in meaningful:
                p = d.get("path", "")
                idx = _extract_feature_index(p)
                feature_name = None
                if idx is not None and idx < len(ts_features):
                    feature_name = ts_features[idx].get("name")
                enriched.append(
                    {
                        "path": p,
                        "featureIndex": idx,
                        "featureName": feature_name,
                        "tsValue": d.get("a"),
                        "pyValue": d.get("b"),
                        "tsType": d.get("aType"),
                        "pyType": d.get("bType"),
                        "missingIn": d.get("missingIn"),
                    }
                )
                path_counts[p] = path_counts.get(p, 0) + 1

            biological_report["mismatches"].append(
                {
                    "file": str(fp),
                    "meaningfulDiffCount": len(enriched),
                    "meaningfulDiffs": enriched,
                }
            )

        except Exception as exc:  # noqa: BLE001
            full_report["errors"].append({"file": str(fp), "error": str(exc)})

    biological_report["sourceMismatchFileCount"] = len(full_report["mismatches"])
    biological_report["biologicallyMeaningfulMismatchFileCount"] = len(
        biological_report["mismatches"]
    )
    biological_report["topMeaningfulDiffPaths"] = sorted(
        path_counts.items(), key=lambda kv: kv[1], reverse=True
    )[:30]

    full_path = output_dir / f"{args.output_prefix}_full_report.json"
    bio_path = (
        output_dir / f"{args.output_prefix}_biological_mismatches_with_ts_values.json"
    )

    full_path.write_text(json.dumps(full_report, indent=2), encoding="utf-8")
    bio_path.write_text(json.dumps(biological_report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "fullReport": str(full_path),
                "biologicalReport": str(bio_path),
                "totalFiles": full_report["totalFiles"],
                "processedFiles": full_report["processedFiles"],
                "matchedCount": len(full_report["matched"]),
                "mismatchCount": len(full_report["mismatches"]),
                "skippedCorruptedCount": len(full_report["skippedCorrupted"]),
                "errorCount": len(full_report["errors"]),
                "biologicallyMeaningfulMismatchFileCount": biological_report[
                    "biologicallyMeaningfulMismatchFileCount"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
