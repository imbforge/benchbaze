# Convert DNA maps to SVG files for BenchBaze

Server-side renders a DNA map to an SVG file using the CircularView component from [Teselagen's Open Vector Editor (OVE)](https://github.com/TeselaGen/tg-oss/tree/master/packages/ove).

An Express server renders the `CircularView` React component to an HTML string via `ReactDOMServer.renderToString`, extracts the `<svg>` element, and serves it as a downloadable file.

## Setup

1. `cd` into this directory
2. Run `npm install`
3. Run `npm run build`
4. Run `npm start`

The server listens on port `3000` by default (override with the `PORT` environment variable).

## Usage

Send a GET request with the following query parameters:

| Parameter | Description |
|---|---|
| `plasmidFilePath` | Path to the GenBank (`.gbk`) file to render |
| `plasmidTitle` | Name used for the plasmid and the downloaded filename |

**Example:**

```
http://localhost:3000/?plasmidFilePath=src/pHU6066.gbk&plasmidTitle=pHU6066
```

The response is an SVG file downloaded as `<plasmidTitle>.html`.

## Running as a service

The server can be run as a systemd service directly or via PM2 (which may offer some advantages)

**Directly**

```bash
node ${BENCHBAZE_HOME}/collection/shared/map_dna/svg_converter/build/server.js
```

**PM2**

```bash
npx pm2 start ${BENCHBAZE_HOME}/collection/shared/map_dna/svg_converter/build/server.js
```

**systemd unit file**

```ini
[Unit]
Description=DNA-Map-to-SVG converter for BenchBaze
After=syslog.target network-online.target

[Service]
ExecStart=${NODE_BIN}/node ${BENCHBAZE_HOME}/collection/shared/map_dna/svg_converter/build/server.js
#ExecStart=${NODE_BIN}/npx pm2 start ${BENCHBAZE_HOME}/collection/shared/map_dna/svg_converter/build/server.js
Type=exec
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

## Notes

- Features whose names match `synthetic dna construct`, `recombinant plasmid`, or `source` and that span the full plasmid length are automatically excluded from the map.
- The rendered view shows features, parts, and axis numbers; translations, ORFs, cut sites, primers, and the sequence itself are hidden.