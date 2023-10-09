#!/usr/bin/env python3

import json
import csv

# Load the JSON data
with open('zones_data.json', 'r') as f:
    data = json.load(f)

# Prepare the CSV data
csv_data = []

for zone in data['zones']:
    zone_name = zone['zoneName']
    for rrset in zone['rrSets']:
        owner_name = rrset.get('ownerName', '')
        rrtype = rrset.get('rrtype', '').split(' ')[0]  # Get just the type e.g., A from "A (1)"
        ttl = rrset.get('ttl', '')
        
        # For each rdata value, we'll create a new CSV row
        for rdata_value in rrset.get('rdata', []):
            csv_row = [zone_name, owner_name, ttl, 'IN', rrtype, rdata_value]
            csv_data.append(csv_row)

# Write the CSV data to a file
with open('zones_data.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for row in csv_data:
        csvwriter.writerow(row)

print("CSV conversion complete!")
