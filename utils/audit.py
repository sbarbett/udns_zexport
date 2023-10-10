#!/usr/bin/env python3

import json
import collections
import datetime
import sys
import argparse
import random
from termcolor import colored

# Define a list of colors supported by termcolor
COLORS = ["grey", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]

def print_section(title, content):
    random_color = random.choice(COLORS)
    print(colored(f"\n{title}\n{'-' * len(title)}", random_color))
    
    for key, value in content.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                print(f"{sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")

def record_type_distribution(zones):
    types = [rrset['rrtype'].split(" ")[0] for zone in zones for rrset in zone['rrSets']]
    return dict(collections.Counter(types))

def subdomain_count(zones):
    domain_sub_count = {}
    for zone in zones:
        domain = zone['zoneName']
        subdomains = set(rrset['ownerName'] for rrset in zone['rrSets'])
        domain_sub_count[domain] = len(subdomains) - 1  # Subtract 1 to exclude the main domain
    return domain_sub_count

def deepest_subdomain(zones):
    all_domains = [rrset['ownerName'] for zone in zones for rrset in zone['rrSets']]
    return max(all_domains, key=lambda domain: domain.count("."))

def mx_distribution(zones):
    mx_records = [rrset for zone in zones for rrset in zone['rrSets'] if rrset['rrtype'].startswith("MX")]
    mx_servers = [rdata.split()[-1] for mx in mx_records for rdata in mx['rdata']]
    return dict(collections.Counter(mx_servers))

def mx_priority_distribution(zones):
    mx_records = [rrset for zone in zones for rrset in zone['rrSets'] if rrset['rrtype'].startswith("MX")]
    priorities = [rdata.split()[0] for mx in mx_records for rdata in mx['rdata']]
    return dict(collections.Counter(priorities))

def cname_chains(zones):
    cnames = {rrset['ownerName']: rrset['rdata'][0] for zone in zones for rrset in zone['rrSets'] if rrset['rrtype'].startswith("CNAME")}
    chains = {}
    for cname, target in cnames.items():
        chain = [cname]
        while target in cnames and target not in chain:  # Avoid infinite loops
            chain.append(target)
            target = cnames[target]
        chains[cname] = chain
    return chains

def longest_cname_chain(zones):
    chains = cname_chains(zones)
    longest_chain_domain = max(chains, key=lambda k: len(chains[k]))
    return {longest_chain_domain: chains[longest_chain_domain]}

def txt_records_analysis(zones):
    txt_records = [rrset for zone in zones for rrset in zone['rrSets'] if rrset['rrtype'].startswith("TXT")]
    
    spf_count = sum(1 for record in txt_records if any("v=spf1" in rdata for rdata in record['rdata']))
    dkim_count = sum(1 for record in txt_records if any("v=DKIM1" in rdata for rdata in record['rdata']))
    dmarc_count = sum(1 for record in txt_records if any("v=DMARC1" in rdata for rdata in record['rdata']))

    return {
        "SPF_Count": spf_count,
        "DKIM_Count": dkim_count,
        "DMARC_Count": dmarc_count
    }

def dnssec_enabled_zones(zones):
    return sum(1 for zone in zones for rrset in zone['rrSets'] if rrset['rrtype'].startswith("DNSKEY"))

def ipv6_adoption(zones):
    return sum(1 for zone in zones for rrset in zone['rrSets'] if rrset['rrtype'].startswith("AAAA"))

def generate_audit_report(zones):
    report = {
        "General Information": {
            "Total Zones": len(zones),
            "Total Records": sum(len(zone['rrSets']) for zone in zones),
            "Date of Report": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "Record Types Distribution": record_type_distribution(zones),
        "Domain Analysis": {
            "Subdomain Count": subdomain_count(zones),
            "Deepest Subdomain": deepest_subdomain(zones)
        },
        "MX Records Analysis": {
            "MX Distribution": mx_distribution(zones),
            "Priority Distribution": mx_priority_distribution(zones)
        },
        "CNAME Records Analysis": {
            "Longest CNAME Chain": longest_cname_chain(zones)
        },
        "TXT Records Analysis": txt_records_analysis(zones),
        "Security Checks": {
            "DNSSEC Enabled Zones": dnssec_enabled_zones(zones)
        },
        "Miscellaneous Checks": {
            "IPv6 Adoption": ipv6_adoption(zones)
        }
    }
    return report

def generate_html_report(report):
    html_content = """
    <html>
    <head>
        <title>DNS Report</title>
        <style>
            body { font-family: Arial, sans-serif; }
            h2 { color: blue; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid black; padding: 8px 12px; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
    """

    for section, content in report.items():
        html_content += f"<h2>{section}</h2>"
        html_content += "<table>"

        for key, value in content.items():
            if isinstance(value, dict):  # To handle Subdomain Count, MX Distribution, Priority Distribution and Longest CNAME Chain
                html_content += f"<tr><th colspan='2'>{key}</th></tr>"
                for sub_key, sub_value in value.items():
                    html_content += f"<tr><td>{sub_key}</td><td>{sub_value}</td></tr>"
            else:
                html_content += f"<tr><th>{key}</th><td>{value}</td></tr>"

        html_content += "</table>"

    html_content += "</body></html>"
    return html_content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''
    Generate DNS Audit Report. This script provides insights into DNS zones data including:
    1. General Information about the zones and records.
    2. Record type distribution among zones.
    3. Subdomain count and the deepest subdomain information.
    4. MX records distribution and priority.
    5. Analysis of CNAME records.
    6. Analysis of TXT records, including SPF, DKIM, and DMARC.
    7. Security checks to identify DNSSEC enabled zones.
    8. Miscellaneous checks, e.g., IPv6 adoption.
    ''')
    
    parser.add_argument('--file', default='zones_data.json', 
                        help='Path to the JSON file containing DNS zones data. Defaults to "zones_data.json".')
    
    parser.add_argument('--html', action='store_true', 
                        help='If set, outputs the report as an HTML file instead of printing to terminal.')

    args = parser.parse_args()

    with open(args.file, 'r') as file:
        data = json.load(file)

    report = generate_audit_report(data['zones'])

    if args.html:
        html_content = generate_html_report(report)
        with open("dns_report.html", "w") as html_file:
            html_file.write(html_content)
        print("Report saved to dns_report.html")
    else:
        for section, content in report.items():
            print_section(section, content)