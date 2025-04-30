#!/usr/bin/env python3
import sys
import os
import socket
import requests
import time

# GeoIP service configuration
GEOIP_URL = 'http://ip-api.com/json/{ip}'
RATE_LIMIT_PAUSE = 1.5  # seconds between requests

def usage():
    print(f"Usage: {sys.argv[0]} <input_domains.txt> <output_directory>")
    print("  <input_domains.txt>   File with one domain per line")
    print("  <output_directory>    Directory where per-country files will be written")
    sys.exit(1)

def resolve_domain(domain):
    """Resolve a domain to its first A-record IP."""
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror as e:
        print(f"[!] Could not resolve {domain}: {e}")
        return None

def query_geoip(ip):
    """Query the GeoIP service for (city, country)."""
    try:
        resp = requests.get(GEOIP_URL.format(ip=ip), timeout=5)
        data = resp.json()
        if data.get('status') != 'success':
            print(f"[!] GeoIP lookup failed for {ip}: {data.get('message')}")
            return None, None
        return data.get('city', '').strip(), data.get('country', '').strip()
    except Exception as e:
        print(f"[!] Exception during GeoIP request for {ip}: {e}")
        return None, None

def sanitize_filename(name):
    """Make a safe filename (e.g. 'United States' → 'United_States')."""
    return "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in name).replace(' ', '_')

def main():
    if len(sys.argv) != 3:
        usage()

    input_file = sys.argv[1]
    out_dir = sys.argv[2]

    # Read domains
    try:
        with open(input_file, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]
    except IOError as e:
        print(f"[!] Unable to read input file '{input_file}': {e}")
        sys.exit(1)

    # Ensure output directory exists
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as e:
        print(f"[!] Could not create output directory '{out_dir}': {e}")
        sys.exit(1)

    # Cache open file handles per country
    files = {}

    try:
        for domain in domains:
            ip = resolve_domain(domain)
            if not ip:
                continue

            time.sleep(RATE_LIMIT_PAUSE)  # respect rate limit

            city, country = query_geoip(ip)
            if not country:
                country = "Unknown"
            loc_str = f"{city}, {country}" if city else country
            line = f"{domain} → {ip} @ {loc_str}\n"

            # Determine filename for this country
            fname = f"servers_{sanitize_filename(country)}.txt"
            path = os.path.join(out_dir, fname)

            # Open file handle if not already
            if country not in files:
                try:
                    files[country] = open(path, 'a')
                except IOError as e:
                    print(f"[!] Could not open '{path}' for writing: {e}")
                    continue

            # Write and print
            files[country].write(line)
            print(f"[+] {line.strip()}")

    finally:
        # Close all open files
        for fh in files.values():
            fh.close()

    print(f"\nDone! Per-country files written under '{out_dir}'")

if __name__ == '__main__':
    main() 
