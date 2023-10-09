#!/usr/bin/env python3

import argparse
import os

def generate_named_conf(directory, output_path):
    zone_stanzas = []

    # Loop through each file in the directory
    for filename in os.listdir(directory):
        if filename.endswith('.conf'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as infile:
                lines = infile.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("$ORIGIN"):
                        domain_name = line.split()[1].rstrip('.')
                        stanza = f"""
zone "{domain_name}" {{
    type master;
    file "/etc/bind/{filename}";
}};
"""
                        zone_stanzas.append(stanza)

    with open(output_path, 'w') as outfile:
        outfile.write('\n'.join(zone_stanzas))

    print(f"named.conf file written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate named.conf from a directory of .conf files")
    parser.add_argument("directory", default="zones", help="Directory containing .conf zone files")
    parser.add_argument("--output", default="named.conf", help="Path to the output named.conf file")
    
    args = parser.parse_args()
    
    generate_named_conf(args.directory, args.output)


if __name__ == "__main__":
    main()
