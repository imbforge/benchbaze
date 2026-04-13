# BenchBaze - DNA Annotation Module

This DNA map annotation tool based on [pLannotate](https://github.com/mmcguffi/pLannotate), adapted for, and integrated in, [BenchBaze](https://github.com/imbforge/benchbaze).

It provides functions to annotate DNA sequences and export the results in BenchBaze.

## Setup

1. Create and activate an environment.

```bash
conda env create -f environment.yml
conda activate plannotate
```

2. Install the package.

```bash
python setup.py install
```

3. Download the annotation databases (required).

```bash
python -c "from plannotate import resources; resources.download_databases()"
```

## Usage

Use the module directly from Python:

```python
from plannotate.annotate import annotate
from plannotate import resources

seq = "ATGCGT..."  # input DNA sequence

# Detailed annotation dataframe
hits = annotate(seq, is_detailed=True, linear=False)

# Export GenBank text
gbk_text = resources.get_gbk(hits, seq)

# Export Biopython SeqRecord
seq_record = resources.get_seq_record(hits, seq)

# Export cleaned report dataframe
csv_df = resources.get_clean_csv_df(hits)
```

## BenchBaze Integration

- accept uploaded sequence/plasmid data in BenchBaze
- call `annotate(...)` in your service layer
- store or return `get_clean_csv_df(...)` output for UI/reporting
- optionally generate GenBank output with `get_gbk(...)`

## Notes

- External binaries must be available on `PATH`: `blastn`, `diamond`, `cmscan`, `rg`.

## Credits

pLannotate was originally developed by Matthew J McGuffie in the Barrick Lab at The University of Texas at Austin, <https://doi.org/10.1093/nar/gkab374>.
