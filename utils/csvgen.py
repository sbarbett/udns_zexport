#!/usr/bin/env python3

import json
import csv

# Load the JSON data
with open('zones_data.json', 'r') as f:
    data = json.load(f)

# Prepare the CSV data
csv_data = []
header = ['Zone Name', 'Zone Type', 'Owner Name', 'TTL', 'Class', 'Record Type', 'Record Data']
csv_data.append(header)  # Adding header row

for zone in data['zones']:
    zone_name = zone['zoneName']
    zone_type = zone['type']  # Get the zone type
    # Check if 'rrSets' exists before processing
    if 'rrSets' in zone:
        for rrset in zone['rrSets']:
            owner_name = rrset.get('ownerName', '')
            rrtype = rrset.get('rrtype', '').split(' ')[0]  # Get just the type e.g., A from "A (1)"
            ttl = rrset.get('ttl', '')
            
            # For each rdata value, we'll create a new CSV row
            for rdata_value in rrset.get('rdata', []):
                csv_row = [zone_name, zone_type, owner_name, ttl, 'IN', rrtype, rdata_value]
                csv_data.append(csv_row)
    else:
        # Handle zones without 'rrSets' by adding a row with limited data
        csv_row = [zone_name, zone_type, 'N/A', 'N/A', 'IN', 'N/A', 'N/A']
        csv_data.append(csv_row)

# Write the CSV data to a file
with open('zones_data.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for row in csv_data:
        csvwriter.writerow(row)

print("CSV conversion complete!")