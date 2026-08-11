#!/usr/bin/env python3
"""Thin CLI wrapper around the Porkbun DNS API (https://porkbun.com/api/json/v3/documentation).

Credentials come from the environment, never from arguments, so they don't end up
in shell history or process listings:
  PORKBUN_API_KEY        - starts with "pk1_"
  PORKBUN_SECRET_KEY      - starts with "sk1_"

Porkbun requires "API Access" to be toggled ON for the specific domain in
Domain Management > (domain) > Details, in addition to a valid key pair.
A ping/list call will fail with an auth-looking error if that toggle is off
even though the keys themselves are correct - check that first if auth fails.

Subcommands:
  ping                                    verify credentials work
  list --domain D [--name SUB] [--type T] list records, optionally filtered
  create --domain D --type T --content C [--name SUB] [--ttl N] [--prio N]
  upsert --domain D --type T --content C [--name SUB] [--ttl N]
                                           idempotent: edits matching records
                                           in place, or creates if none exist
  delete --domain D --type T [--name SUB] [--id ID] --yes
                                           requires --yes to actually delete

--name is the subdomain label only (e.g. "www" or "_vercel"), never
including the base domain. Omit --name (or pass "") for the root/apex.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = "https://api.porkbun.com/api/json/v3"


def _creds():
    key = os.environ.get("PORKBUN_API_KEY")
    secret = os.environ.get("PORKBUN_SECRET_KEY")
    if not key or not secret:
        sys.exit(
            "Missing credentials. Set PORKBUN_API_KEY and PORKBUN_SECRET_KEY "
            "(generate at porkbun.com > Account > API Access), and make sure "
            "'API Access' is toggled on for this domain in Domain Management."
        )
    return key, secret


def _call(path, payload=None):
    key, secret = _creds()
    body = dict(payload or {})
    body["apikey"] = key
    body["secretapikey"] = secret
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode())
    if data.get("status") != "SUCCESS":
        sys.exit(f"Porkbun API error on {path}: {data.get('message', data)}")
    return data


def cmd_ping(args):
    data = _call("/ping")
    print(f"OK - credentials valid, outbound IP seen by Porkbun: {data.get('yourIp')}")


def cmd_list(args):
    data = _call(f"/dns/retrieve/{args.domain}")
    records = data.get("records", [])
    if args.type:
        records = [r for r in records if r["type"].upper() == args.type.upper()]
    if args.name is not None:
        full_name = f"{args.name}.{args.domain}" if args.name else args.domain
        records = [r for r in records if r["name"] == full_name]
    for r in records:
        prio = f" prio={r['prio']}" if r.get("prio") else ""
        print(f"[{r['id']}] {r['name']:<40} {r['type']:<6} ttl={r['ttl']:<6} {r['content']}{prio}")
    if not records:
        print("(no matching records)")


def cmd_create(args):
    payload = {"type": args.type.upper(), "content": args.content, "name": args.name or ""}
    if args.ttl:
        payload["ttl"] = str(args.ttl)
    if args.prio is not None:
        payload["prio"] = str(args.prio)
    data = _call(f"/dns/create/{args.domain}", payload)
    print(f"Created record id {data.get('id')}")


def _matching_records(domain, name, rtype):
    data = _call(f"/dns/retrieve/{domain}")
    full_name = f"{name}.{domain}" if name else domain
    return [r for r in data.get("records", []) if r["name"] == full_name and r["type"].upper() == rtype.upper()]


def cmd_upsert(args):
    existing = _matching_records(args.domain, args.name or "", args.type)
    if not existing:
        return cmd_create(args)
    if len(existing) > 1:
        print(
            f"Warning: {len(existing)} existing {args.type} records at this name - "
            "editing all of them to the new content. Review with 'list' first if unsure."
        )
    for r in existing:
        payload = {"type": args.type.upper(), "content": args.content}
        if args.ttl:
            payload["ttl"] = str(args.ttl)
        _call(f"/dns/edit/{args.domain}/{r['id']}", payload)
        print(f"Updated record id {r['id']} -> {args.content}")


def cmd_delete(args):
    if not args.yes:
        sys.exit("Refusing to delete without --yes. Run 'list' first to confirm what you're removing.")
    if args.id:
        _call(f"/dns/delete/{args.domain}/{args.id}")
        print(f"Deleted record id {args.id}")
        return
    if not args.type:
        sys.exit("Need either --id or --type (with optional --name) to know what to delete.")
    sub = args.name or ""
    path = f"/dns/deleteByNameType/{args.domain}/{args.type.upper()}/{sub}" if sub else f"/dns/deleteByNameType/{args.domain}/{args.type.upper()}"
    _call(path)
    print(f"Deleted all {args.type.upper()} records at {'@' if not sub else sub}.{args.domain}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping").set_defaults(func=cmd_ping)

    sp = sub.add_parser("list")
    sp.add_argument("--domain", required=True)
    sp.add_argument("--name", default=None, help="subdomain label, omit for all, '' for apex only")
    sp.add_argument("--type")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("create")
    sp.add_argument("--domain", required=True)
    sp.add_argument("--type", required=True)
    sp.add_argument("--content", required=True)
    sp.add_argument("--name", default="")
    sp.add_argument("--ttl", type=int, default=600)
    sp.add_argument("--prio", type=int)
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("upsert")
    sp.add_argument("--domain", required=True)
    sp.add_argument("--type", required=True)
    sp.add_argument("--content", required=True)
    sp.add_argument("--name", default="")
    sp.add_argument("--ttl", type=int, default=600)
    sp.set_defaults(func=cmd_upsert)

    sp = sub.add_parser("delete")
    sp.add_argument("--domain", required=True)
    sp.add_argument("--type")
    sp.add_argument("--name", default="")
    sp.add_argument("--id")
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=cmd_delete)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
