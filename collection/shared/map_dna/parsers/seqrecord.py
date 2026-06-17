from .genbank import _genbank_to_json_via_seqio
from typing import Any, Dict, List, Optional
from Bio.SeqRecord import SeqRecord


def seqrecord_to_json(
    map_dna: SeqRecord, options: Optional[Dict[str, Any]] = None
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
