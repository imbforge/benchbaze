
# BenchBaze - DNA Map Viewer

This is a DNA map viewer based on [Teselagen's Open Vector Editor (OVE)](https://github.com/TeselaGen/tg-oss/tree/master/packages/ove), adapted for, and integrated in, [BenchBaze](https://github.com/imbforge/benchbaze).

It loads a DNA map file from a URL supplied by BenchBaze, parses it and renders it.

## Setup

1. Install dependencies:

```bash
yarn install
```

2. Build the app

```bash
yarn build
```

3. Optionally, start the development server for testing:

```bash
yarn start
```

The server listens on port `5173` by default.

## Usage

Send a GET request with the following query parameters:

| Parameter     | Required | Description                                                    |
|---------------|----------|----------------------------------------------------------------|
| `file_name`   | Yes      | URL/path to the sequence file to fetch                         |
| `file_format` | Yes      | Parser hint used in the app (`gbk` or `dna`)                   |
| `title`       | No       | Display name shown in the editor and used for export filenames |
| `show_oligos` | No       | If present, primers are shown and translations are hidden      |

Example:

```text
http://localhost:5173/?file_name=https://example.org/plasmids/pABC123.gbk&file_format=gbk&title=pABC123
```

## Notes

- At the moment, the viewer is read-only (`readOnly: true` in editor config).
- The toolbar includes tools for cut sites, features, oligos, ORFs, visibility, and find.
- Full-length generic annotations with these names are filtered out before rendering: `synthetic dna construct`, `recombinant plasmid`, `source`.
