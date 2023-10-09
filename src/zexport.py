#!/usr/bin/env python3

import requests
import argparse
import zipfile
from io import BytesIO
import time
from tqdm import tqdm
from udns import UltraApi
import json
import os
import datetime

def get_zones(client):
    zones = []
    cursor = ""
    while True:
        response = client.get(f"/v2/zones?limit=1000&cursor={cursor}")
        zones.extend(response.get("zones", []))
        cursor = response["cursorInfo"].get("next")
        if not cursor:
            break
    return zones

def initiate_zone_export(client, zone_names):
    payload = {
        "zoneNames": zone_names
    }
    # For PTR records with "/" in them...
    pstring = json.dumps(payload).replace('/', '\\u002F')
    response = client.post("/v2/zones/export", pstring)
    return response["task_id"]

def poll_task_status(client, task_id):
    while True:
        response = client.get(f"/tasks/{task_id}")
        if response["code"] == "COMPLETE":
            break
        if response["code"] == "ERROR":
            raise Exception(f"There was an error exporting the zones: {json.dumps(response)}")
        time.sleep(10)
    return response

def download_exported_data(client, task_id):
    return client.get(f"/tasks/{task_id}/result", content_type="text/plain")

def save_zone_to_file(zone_name, content):
    """Save the zone content to an individual file in /zones directory."""
    if not os.path.exists('zones'):
        os.makedirs('zones')
    # Sometimes reverse DNS records have a "/" in them and it is a pain
    formatted_name = zone_name.replace('/', '_')
    with open(f"zones/{formatted_name}.conf", "w") as f:
        f.write(content)

def get_rrsets_for_zone(client, zone_name):
    """Fetch all RRsets for the specified zone."""
    all_rrsets = []
    offset = 0
    limit = 1000  # Maximum allowed by the API

    while True:
        try:
            response = client.get(f"/zones/{zone_name}/rrsets?limit={limit}&offset={offset}")
            rrsets = response.get("rrSets", [])
            all_rrsets.extend(rrsets)

            # Get total count and number of returned records to determine if there's another page
            total_count = response["resultInfo"]["totalCount"]
            returned_count = response["resultInfo"]["returnedCount"]
            offset += returned_count

            if offset >= total_count:
                break

        except requests.HTTPError as e:
            if e.response.status_code in [404, 500]:
                print(f"Warning: Unable to fetch RRsets for {zone_name}. HTTP Error: {e.response.status_code}. Skipping...")
                return []  # Return an empty list since there's an error fetching this zone
            else:
                print(f"Error: Unable to fetch RRsets for {zone_name}. HTTP Error: {e.response.status_code}.")
                raise

    return all_rrsets


def main(username=None, password=None, token=None, combined_file=False, json_output=False):
    client = UltraApi(username, password, token)
    
    zones = get_zones(client)
    zone_names = [z['properties']['name'] for z in zones]
    # You can use this to exclude certain zones from the script
    zone_names = [zone for zone in zone_names if zone != "00000zkchawxh1.com." and zone != "hyperdns.ninja."]
    combined_zone_data = []

    if json_output:
        zones_data = []

        for zone in tqdm(zone_names, desc="Fetching RRsets for zones"):
            rrsets = get_rrsets_for_zone(client, zone)
            zones_data.append({"zoneName": zone, "rrSets": rrsets})

        with open("zones_data.json", "w") as out_file:
            json.dump({
                "username": username,
                "timestamp": int(datetime.datetime.now().timestamp()),
                "zones": zones_data
            }, out_file, indent=4)
        return

    for i in tqdm(range(0, len(zone_names), 250), desc="Processing zones"):
        chunk = zone_names[i:i+249]
        task_id = initiate_zone_export(client, chunk)
        poll_task_status(client, task_id)
        zip_data = download_exported_data(client, task_id)

        with zipfile.ZipFile(BytesIO(zip_data), 'r') as zip_ref:
            for file in zip_ref.namelist():
                domain_name = file.replace(".txt", "")
                with zip_ref.open(file, 'r') as textf:
                    content = textf.read().decode('utf-8')
                    if combined_file:
                        combined_zone_data.append(content)
                    else:
                        save_zone_to_file(domain_name, content)

    if combined_file:
        with open("combined_zone_file.conf", "w") as out_file:
            out_file.write("\n".join(combined_zone_data))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UltraDNS Zone Exporter")

    # Group authentication arguments
    auth_group = parser.add_argument_group('authentication')
    auth_group.add_argument("--username", help="Username for authentication")
    auth_group.add_argument("--password", help="Password for authentication")
    token_arg = parser.add_argument("--token", help="Directly pass the Bearer token")
    parser.add_argument("--combined-file", action="store_true", help="Combine all zone data into a single file")
    parser.add_argument("--json", action="store_true", help="Save RRsets for all zones into a single JSON object")

    args = parser.parse_args()

    # Enforce the rules specified
    if args.token:
        if args.username or args.password:
            parser.error("You cannot provide a token along with a username or password.")
    elif args.username and args.password:
        pass
    else:
        parser.error("You must provide either a token, or both a username and password.")

    main(args.username, args.password, args.token, args.combined_file, args.json)
