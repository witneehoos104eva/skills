---
name: custom-domain-setup
description: Point a custom domain (registered/managed at Porkbun) at a website that is already deployed on Vercel and connected to a GitHub repo. Use this whenever the user wants to add, connect, or fix a custom domain, subdomain, or "custom URL" for a Vercel-deployed site - phrases like "set up my domain", "connect mizai.solutions to my project", "add a custom URL", "point app.mydomain.com at Vercel", or "why isn't my domain working on Vercel" should all trigger this. Covers attaching the domain in Vercel, working out the exact DNS records Vercel needs (A/CNAME/TXT), writing those records via the Porkbun DNS API, and verifying DNS propagation + HTTPS issuance. Do not use for domain purchase/registration, or for DNS providers other than Porkbun (the record-writing steps are Porkbun-specific, though the Vercel side generalizes).
---

# Custom Domain Setup (Porkbun -> Vercel)

Connecting a custom domain to a Vercel deployment is really two independent
systems that have to agree with each other: Vercel needs to know it should
accept traffic for the domain and prove you own it, and Porkbun's DNS zone
needs to actually route that domain's traffic to Vercel. Most failures come
from doing one side without checking what the other side actually asked for
- e.g. writing `A 76.76.21.21` because it's the well-known default, without
checking whether Vercel is asking for a different anycast IP for this
account, or whether the hostname in question needs a CNAME instead because
it's a subdomain, not the apex.

This skill uses two bundled scripts (`scripts/vercel_domain.py` and
`scripts/porkbun_dns.py`) so each side is a single deterministic API call
instead of hand-built curl commands. Run each with `--help` first.

## Prerequisites

Confirm these exist before starting - if any are missing, get them from the
user or point them to where to generate one rather than guessing:

- **The exact hostname** to connect (e.g. `mizai.solutions` for the apex, or
  `app.mizai.solutions` for a subdomain). Ask if it's ambiguous - "my domain"
  could mean the apex, `www`, or a specific subdomain, and that choice
  changes which DNS record type is correct.
- **The Vercel project** the site is already deployed under (name or ID).
  If unsure, `vercel project ls` or the Vercel dashboard will show it.
- **`VERCEL_TOKEN`** in the environment - generate at
  vercel.com/account/tokens if missing. Add `VERCEL_TEAM_ID` too if the
  project lives under a team, not the personal account.
- **`PORKBUN_API_KEY`** and **`PORKBUN_SECRET_KEY`** in the environment -
  generate at porkbun.com > Account > API Access. Porkbun also requires
  toggling "API Access" on for that *specific* domain under Domain
  Management > (domain) > Details - the key pair alone isn't enough.

Never ask the user to paste secrets into chat; have them export the env vars
in their shell, or set them wherever this session's environment is
configured.

## Workflow

1. **Attach the domain to the Vercel project:**
   ```
   python scripts/vercel_domain.py add --project <project> --domain <hostname>
   ```
   This tells you immediately if Vercel needs an ownership TXT challenge
   before it'll route traffic (common when a domain's apex is being added, or
   when it's already attached elsewhere). If it does, note the TXT
   `domain`/`value` pair from the output - you'll write that record in step 3.

2. **Get the exact DNS records Vercel wants:**
   ```
   python scripts/vercel_domain.py status --domain <hostname>
   ```
   Don't assume `A 76.76.21.21` / `CNAME cname.vercel-dns.com` - those are
   the long-standing defaults and still work, but Vercel increasingly hands
   back per-account anycast addresses. Read the actual recommended values
   from this output. See `references/dns-troubleshooting.md` for the
   apex-vs-subdomain rule if you need the reasoning.

3. **Check what's already at that name in Porkbun before changing anything:**
   ```
   python scripts/porkbun_dns.py list --domain <base-domain> --name <subdomain-or-blank>
   ```
   New domains often have default parking-page records here that will
   conflict. Show the user what exists and what you're about to change,
   especially if it means deleting a record type that can't coexist with the
   new one (e.g. switching an apex from `ALIAS` to `A`).

4. **Write the record(s) Vercel asked for:**
   ```
   python scripts/porkbun_dns.py upsert --domain <base-domain> --type A --content <ip> --name <sub-or-blank>
   ```
   `upsert` edits an existing matching record in place or creates one if none
   exists - safe to re-run. If a TXT verification challenge was needed from
   step 1, write that TXT record too, then run:
   ```
   python scripts/vercel_domain.py verify --project <project> --domain <hostname>
   ```

5. **Verify end to end:**
   - `dig <hostname> A +short` (or `CNAME`) to confirm the record resolves
     as expected. If it doesn't after ~15-30 min, re-check with
     `porkbun_dns.py list` that the record actually saved, before assuming
     it's just slow propagation.
   - Re-run `vercel_domain.py status` until `misconfigured` is `false`.
   - `curl -Iv https://<hostname>` once DNS resolves - TLS certificate
     issuance happens automatically but takes a few extra minutes after DNS
     is correct, so a handshake error right after fixing DNS isn't
     necessarily a new problem.

If anything doesn't behave as expected at any step - auth errors, a domain
already attached elsewhere, certificates not issuing, CAA records blocking
issuance - check `references/dns-troubleshooting.md` before improvising; it
covers the failure modes that actually come up in practice.

## Safety notes

- Only ever touch the specific `A`/`CNAME`/`ALIAS`/`TXT` records this
  workflow needs. Never delete or edit MX records or unrelated TXT records
  (SPF/DKIM) while doing this - a domain-pointing task breaking someone's
  email is a much worse outcome than a slightly slower setup.
- `porkbun_dns.py delete` and `vercel_domain.py remove` both require `--yes`
  and should only be run after showing the user what will be removed and why
  it's necessary (e.g. clearing a conflicting default record before creating
  the real one).
- Credentials are read from environment variables only, never accepted as
  command arguments - keep it that way so they don't leak into shell history
  or process listings.
