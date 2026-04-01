# Convert DNA maps to SVG files for BenchBaze

Server-side renders a DNA map to an SVG file using the CircularView component from [Teselagen's Open Vector Editor (OVE)](https://github.com/TeselaGen/tg-oss/tree/master/packages/ove).

An Express server renders the `CircularView` React component to an HTML string via `ReactDOMServer.renderToString`, extracts the `<svg>` element, and serves it as a downloadable file.

## Setup

1. `cd` into this directory
2. Run `yarn install`
3. Run `yarn build`
4. Run `yarn start`

The server listens on port `3000` by default (override with the `PORT` environment variable).

## Usage

Send a GET request with the following query parameters:

| Parameter | Required | Description |
|---|---|---|
| `mapDnaPath` | Yes | Path to the DNA map file to render (`.gbk`, `.gb`, or `.dna`) |
| `mapDnaTitle` | No | Name used for the plasmid and the downloaded filename (defaults to `plasmid`) |

**Supported file formats:** GenBank (`.gb`, `.gbk`) and SnapGene (`.dna`).

**Example**

```bash
curl http://localhost:3000/?mapDnaPath=src/pHU6066.gbk&mapDnaTitle=pHU6066
```

The response is an SVG file downloaded as `<mapDnaTitle>.html`.

### Error responses

| Status | Cause |
|---|---|
| 400 | `mapDnaPath` parameter missing or file extension not supported |
| 404 | File not found at the given path |
| 500 | Parse failure or render error (response body contains the specific error message) |

## Running as a service

The server can be run as a systemd service directly or via PM2 (which may offer some advantages)

**Directly**

```bash
node ${BENCHBAZE_HOME}/collection/shared/map_dna/svg_converter/build/server.js
```

**systemd unit file**

```ini
[Unit]
Description=DNA-Map-to-SVG converter for BenchBaze
After=syslog.target network-online.target

[Service]
ExecStart=${NODE_BIN}/node ${BENCHBAZE_HOME}/collection/shared/map_dna/svg_converter/build/server.js
Type=exec
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

**PM2**

```bash
npx pm2 start ${BENCHBAZE_HOME}/collection/shared/map_dna/svg_converter/build/server.js --name "map-dna-svg-converter"
```

To make PM2 restore the process automatically after a server reboot:

```bash
pm2 save       # snapshot the current process list
pm2 startup    # install a systemd unit to restore the snapshot on boot
```

`pm2 startup` prints a `sudo` command — copy and run it to complete the setup. If you later change which processes should autostart, run `pm2 save` again.

## Notes

- Features whose names match `synthetic dna construct`, `recombinant plasmid`, or `source` and that span the full plasmid length are automatically excluded from the map.
- The rendered view shows features, parts, and axis numbers; translations, ORFs, cut sites, primers, and the sequence itself are hidden.