# udns_zexport

This tool provides a programmatic way to export _all_ zone files from your UltraDNS account, either in BIND text format or JSON. For those who wish to locally test DNS resolutions, it offers a Docker build to spin up a BIND server with your zone files.

## Features

1. Export zones in BIND text format.
2. Export zones in JSON format.
3. Convert JSON formatted zones into CSV.
4. Docker integration to spin up a local BIND server using the exported zone files.

## Quick Start

### Zone Export

To export your zone files:

```bash
./src/zexport.py --username \$UDNS_UNAME --password \$UDNS_PW
```

### Docker BIND Server

To quickly start a BIND server with the exported zone files:

```bash
cp -R zones docker
cd docker
./build.sh
```

You can then query your local BIND server:

```bash
dig @localhost testingsomethingout.biz
```

### JSON and CSV Conversion

To export zones in JSON format:

```bash
./src/zexport.py --username \$UDNS_UNAME --password \$UDNS_PW --json
```

Convert the exported JSON to CSV:

```bash
./utils/csvgen.py zones_data.json
```

## Prerequisites

- Python dependencies: 
    * tqdm
    * requests

Install the required Python packages with:

```bash
pip install -r requirements.txt
```

## License

This project is licensed under the terms of the [MIT License](LICENSE.md).
