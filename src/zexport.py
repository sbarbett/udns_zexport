#!/usr/bin/env python3

import requests
import argparse
import zipfile
from io import BytesIO
import time
from tqdm import tqdm
from ultra_auth import UltraApi
import json
import os
import datetime

class CustomHelpParser(argparse.ArgumentParser):
    def print_help(self, *args, **kwargs):
        ascii_art = """
__     ______     _______   _______ ___________ _____ 
\\ \\   |___  /    |  ___\\ \\ / | ___ |  _  | ___ |_   _|
 \\ \\     / ______| |__  \\ V /| |_/ | | | | |_/ / | |  
  > >   / |______|  __| /   \\|  __/| | | |    /  | |  
 / /  ./ /___    | |___/ /^\\ | |   \\ \\_/ | |\\ \\  | |  
/_/   \\_____/    \\____/\\/   \\_|    \\___/\\_| \\_| \\_/  
 
"""
        print(ascii_art)
        super().print_help(*args, **kwargs)

def get_zones(client):
    zones = []
    cursor = ""
    while True:
        response = client.get(f"/v3/zones?limit=1000&cursor={cursor}")
        zones.extend(response.get("zones", []))
        cursor = response["cursorInfo"].get("next")
        if not cursor:
            break
    return zones

def get_zone_properties(client, zone_name):
    return client.get(f"/v3/zones/{zone_name}")

def get_zones_from_file(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def initiate_zone_export(client, zone_names):
    payload = {
        "zoneNames": zone_names
    }
    # For PTR records with "/" in them...
    pstring = json.dumps(payload).replace('/', '\\u002F')
    response = client.post("/v3/zones/export", pstring, plain_text=True)
    return response["task_id"]

def poll_task_status(client, task_id, debug=False):
    while True:
        response = client.get(f"/tasks/{task_id}")
        if response["code"] == "COMPLETE":
            break
        if response["code"] == "ERROR":
            if debug:
                print(f"Warning: An error occurred processing this zone: {json.dumps(response)}")
                return None
            else:
                print("Warning: There was an issue with a domain in your batch request. Consider using --debug mode.")
                raise Exception(f"Error message: {json.dumps(response)}")
        time.sleep(10)
    return response

def download_exported_data(client, task_id):
    return client.get(f"/tasks/{task_id}/result")

def save_zone_to_file(zone_name, content):
    """Save the zone content to an individual file in /zones directory."""
    if not os.path.exists('zones'):
        os.makedirs('zones')
    # Sometimes reverse DNS records have a "/" in them and it is a pain
    # Also, eliminate the trailing dot
    formatted_name = zone_name.replace('/', '_').rstrip('.')
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

def get_web_forwards_for_zone(client, zone_name):
    """Fetch all web forwards for the specified zone."""
    all_web_forwards = []
    offset = 0
    limit = 100  # Maximum allowed by the API

    while True:
        try:
            response = client.get(f"/v3/zones/{zone_name}/webforwards?limit={limit}&offset={offset}")
            web_forwards = response.get("webForwards", [])
            all_web_forwards.extend(web_forwards)

            # Get total count and number of returned records to determine if there's another page
            total_count = response["resultInfo"]["totalCount"]
            returned_count = response["resultInfo"]["returnedCount"]
            offset += returned_count

            if offset >= total_count:
                break

        except requests.HTTPError as e:
            if e.response.status_code == 404:  # Handle 404, which means no web forwards found for this domain
                break  # Exit the loop and return an empty list
            else:
                print(f"Error: Unable to fetch web forwards for {zone_name}. HTTP Error: {e.response.status_code}.")
                raise

    return all_web_forwards

def main(username=None, password=None, token=None, refresh_token=None, combined_file=False, json_output=False, debug=False, zones_file=None):
    if token:
        client = UltraApi(token, refresh_token, True)
    else:
        client = UltraApi(username, password)

    zones = get_zones(client)

    if zones_file:
        zone_file_names = get_zones_from_file(zones_file)
        # Ensure zone_names are stripped of trailing dots for comparison
        zone_file_names = [name.rstrip('.') for name in zone_file_names]
        # Iterate in reverse to safely remove items while iterating
        for i in reversed(range(len(zones))):
            zone_name = zones[i]['properties']['name'].rstrip('.')
            if zone_name not in zone_file_names:
                del zones[i]

    if json_output:
        zones_data = []
        web_forward_ips = ["204.74.99.100", "204.74.99.101", "204.74.99.102", "204.74.99.103"]

        for zone in tqdm(zones, desc="Fetching data for zones"):
            zone_name = zone["properties"]["name"]
            zone_type = zone["properties"]["type"]
            if zone_type == "SECONDARY":
                zone_properties = get_zone_properties(client, zone_name)
                primary_ns = zone_properties["primaryNameServers"]
                zone_secondary_data = {
                    "zoneName": zone_name,
                    "type": "SECONDARY",
                    "primaryNameServers": primary_ns
                }
                zones_data.append(zone_secondary_data)
            elif zone_type == "ALIAS":
                zone_alias_data = {
                    "zoneName": zone["properties"]["name"],
                    "type": "ALIAS",
                    "originalZoneName": zone["originalZoneName"]
                }
                zones_data.append(zone_alias_data)
            else:
                rrsets = get_rrsets_for_zone(client, zone_name)

                # Check if any of the system-generated A records are present in the RRsets
                should_fetch_web_forwards = any(
                    record for record in rrsets if (
                            record["rrtype"] == "A (1)" and
                            "rdata" in record and
                            record["rdata"][0] in web_forward_ips
                    )
                )

                # If a system-generated A record is detected, fetch the web forwards
                web_forwards = []
                if should_fetch_web_forwards:
                    web_forwards = get_web_forwards_for_zone(client, zone_name)

                # Exclude system-generated A records for final storage
                rrsets = [record for record in rrsets if not (
                        record["rrtype"] == "A (1)" and
                        "rdata" in record and
                        record["rdata"][0] in web_forward_ips
                )]

                zones_primary_data = {
                    "zoneName": zone_name,
                    "type": "PRIMARY",
                    "rrSets": rrsets
                }
                if web_forwards:
                    zones_primary_data.append({"webForwards": web_forwards})

                zones_data.append(zones_primary_data)

        with open("zones_data.json", "w") as out_file:
            json.dump({
                "username": username,
                "timestamp": int(datetime.datetime.now().timestamp()),
                "zones": zones_data
            }, out_file, indent=4)
        return

    zone_names = [z['properties']['name'] for z in zones]
    # If you want to exclude particular domains from your request, add them here
    # zone_names = [zone for zone in zone_names if zone != "example1.com." and zone != "example2.com."]
    combined_zone_data = []

    if debug or len(zone_names) == 1:
        for zone in tqdm(zone_names, desc="Processing zones individually"):
            task_id = initiate_zone_export(client, [zone])
            status = poll_task_status(client, task_id, debug=True)
            if not status:  # If the task status returned None (meaning there was an error)
                continue
            data = download_exported_data(client, task_id)
            save_zone_to_file(zone, data)
            
    else:
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
    parser = CustomHelpParser(description="UltraDNS Zone Exporter")

    # Group authentication arguments
    auth_group = parser.add_argument_group('authentication')
    auth_group.add_argument("-u", "--username", help="Username for authentication")
    auth_group.add_argument("-p", "--password", help="Password for authentication")
    auth_group.add_argument("-t", "--token", help="Directly pass the Bearer token")
    auth_group.add_argument("-r", "--refresh-token", help="Pass the Refresh token (optional with --token)")
    
    parser.add_argument("-c", "--combined-file", action="store_true", help="Combine all zone data into a single file")
    parser.add_argument("-j", "--json", action="store_true", help="Save RRsets for all zones into a single JSON object")
    parser.add_argument("-d", "--debug", action="store_true", help="Fetch zones individually to identify potential errors.")
    parser.add_argument("-z", "--zones-file", help="Specify a file containing a list of zones to export (one per line). If not specified, all zones will be exported.")

    args = parser.parse_args()

    # Enforce the rules specified
    if args.token:
        if args.username or args.password:
            parser.error("You cannot provide a token along with a username or password.")
    elif args.username and args.password:
        pass
    elif args.username or args.password:  # If one of them is provided but not both
        parser.error("You must provide both a username and password.")
    else:
        parser.error("You must provide either a token, or both a username and password.")

    main(args.username, args.password, args.token, args.refresh_token, args.combined_file, args.json, args.debug, args.zones_file)

