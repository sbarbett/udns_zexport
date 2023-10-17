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
./src/zexport.py -u $UDNS_UNAME -p $UDNS_PW
```

#### Debug Mode

By default, this script will request zone files in batches of 250. If there's an issue with a single zone in the whole of the batch request, however, the entire export will fail. To work around this, use the `-d-` or `--debug` switch. Debug mode will, instead, download each zone individually and display warnings for any that fail. Obviously, this takes much longer.

#### Custom Input File

Optionally, you may specify a text file containing a list of zones to export. The file is expected to be in your working directory. Each zone should be separated by line breaks. I included zoneslist.txt as a basic formatting example. The switch is `-z` or `--zones-file`.

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
./src/zexport.py -u $UDNS_UNAME -p $UDNS_PW -j
```

Convert the exported JSON to CSV:

```bash
./utils/csvgen.py zones_data.json
```

### Audit Report

The `audit.py` utility provides an analysis of your DNS.

#### Features:
- **General Information**: Overview of the number of zones, total records, and the timestamp of the report generation.
- **Record Types Distribution**: Breakdown of the distribution of different types of DNS records (e.g., `NS`, `SOA`, `MX`).
- **Domain Analysis**:
  - **Subdomain Count**: Enumerates the number of subdomains per domain.
  - **Deepest Subdomain**: Identifies the subdomain with the highest level of depth.
- **MX Records Analysis**:
  - **MX Distribution**: Provides details on mail exchange servers being used.
  - **Priority Distribution**: Assesses the priority levels set for mail servers.
- **CNAME Records Analysis**:
  - **Longest CNAME Chain**: Reveals the longest `CNAME` redirection chain, which can be useful for debugging potential DNS issues.
- **TXT Records Analysis**: Analysis of `TXT` records including:
  - Breakdown of `SPF`, `DKIM`, and `DMARC` record counts, crucial for mail delivery and security.
- **Security Checks**:
  - **DNSSEC Enabled Zones**: Counts the number of zones with DNSSEC enabled, indicating a secure DNS configuration.
- **Miscellaneous Checks**:
  - **IPv6 Adoption**: Quantifies the number of zones adopting IPv6.

#### Usage:
The input file is the JSON export produced by `zexport.py`. By default, it reads from `zones_data.json`, but this can be customized using the file switch. The report can be outputted either to the terminal or as an HTML file.

Example:
```bash
$ ./utils/audit.py
```

For HTML output:
```bash
$ ./utils/audit.py --html
```

## Prerequisites

This project uses the [ultra_auth](https://github.com/sbarbett/ultra_auth) module.

- Python dependencies: 
    * ultra_auth
    * tqdm
    * requests
    * termcolor

Install the required Python packages with:

```bash
pip install -r requirements.txt
```

## License

This project is licensed under the terms of the [MIT License](LICENSE.md).
