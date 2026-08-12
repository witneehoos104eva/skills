#!/usr/bin/env python3
"""Thin CLI wrapper around the Vercel REST API for attaching a custom domain
to a project (https://vercel.com/docs/rest-api/endpoints/domains).

Credentials come from the environment:
  VERCEL_TOKEN     - required, create at vercel.com/account/tokens
  VERCEL_TEAM_ID   - optional, only needed if the project lives under a team

Subcommands:
  add --project P --domain D          attach D to project P, prints the DNS
                                       records / TXT verification challenge
                                       Vercel needs (if any)
  status --domain D                   check current DNS configuration state
                                       for D and print Vercel's recommended
                                       A / CNAME values for it
  verify --project P --domain D       re-check an ownership TXT challenge
                                       after you've added the TXT record
  remove --project P --domain D --yes detach D from the project

Always run 'status' after adding the domain and before writing DNS records -
Vercel increasingly hands back per-account anycast addresses instead of the
old fixed 76.76.21.21, so treat that IP as a fallback, not a given.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = "https://api.vercel.com"


def _token():
    token = os.environ.get("VERCEL_TOKEN")
    if not token:
        sys.exit("Missing VERCEL_TOKEN. Create one at vercel.com/account/tokens.")
    return token


def _call(method, path, payload=None):
    team_id = os.environ.get("VERCEL_TEAM_ID")
    if team_id:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}teamId={team_id}"
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"error": {"message": raw}}
        sys.exit(f"Vercel API error ({e.code}) on {method} {path}: {data.get('error', data)}")


def cmd_add(args):
    data = _call("POST", f"/v10/projects/{args.project}/domains", {"name": args.domain})
    print(f"Domain {data.get('name')} attached to project {args.project}.")
    if data.get("verified"):
        print("verified: true - no ownership challenge needed.")
    else:
        print("verified: false - ownership challenge required before DNS will route traffic:")
        for v in data.get("verification", []):
            print(f"  add a {v['type']} record at {v['domain']} with value: {v['value']}")
        print("After adding that record, run this script's 'verify' subcommand.")
    print("\nNow run 'status --domain {}' to get the exact A/CNAME values to set.".format(args.domain))


def cmd_status(args):
    data = _call("GET", f"/v6/domains/{args.domain}/config")
    print(json.dumps(data, indent=2))
    if data.get("misconfigured") is False:
        print("\nDNS looks correctly configured according to Vercel.")
    elif "misconfigured" in data:
        print(
            "\nDNS is NOT yet correctly configured. Compare the fields above "
            "(aValues / cnames / recommended*) against what's currently set at your "
            "DNS provider, or check the domain in the Vercel dashboard for the exact "
            "records it wants."
        )


def cmd_verify(args):
    data = _call("POST", f"/v10/projects/{args.project}/domains/{args.domain}/verify")
    if data.get("verified"):
        print("Verified.")
    else:
        print("Still not verified:")
        print(json.dumps(data, indent=2))


def cmd_remove(args):
    if not args.yes:
        sys.exit("Refusing to remove without --yes.")
    _call("DELETE", f"/v9/projects/{args.project}/domains/{args.domain}")
    print(f"Removed {args.domain} from project {args.project}.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("add")
    sp.add_argument("--project", required=True, help="Vercel project name or ID")
    sp.add_argument("--domain", required=True)
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("status")
    sp.add_argument("--domain", required=True)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("verify")
    sp.add_argument("--project", required=True)
    sp.add_argument("--domain", required=True)
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("remove")
    sp.add_argument("--project", required=True)
    sp.add_argument("--domain", required=True)
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=cmd_remove)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
