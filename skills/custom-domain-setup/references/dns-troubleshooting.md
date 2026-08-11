# DNS record cheat sheet & troubleshooting

## Which record type goes where

| Hostname you're pointing        | Record type | Typical content                         |
|----------------------------------|-------------|------------------------------------------|
| Apex / root (`example.com`)      | `A`         | Vercel's anycast IP (get exact value from `vercel_domain.py status`, fallback `76.76.21.21`) |
| Subdomain (`www`, `app`, `blog`) | `CNAME`     | `cname.vercel-dns.com` (or the value Vercel's `status` output recommends) |
| Ownership verification           | `TXT`       | Value Vercel returns in the `verification` array when `verified: false` |

Apex domains cannot use a CNAME (DNS spec restriction - a zone's root can't have a
CNAME alongside its other required records like NS/SOA). If the user wants the
apex itself to work (not just `www`), it must be an `A` record. Some registrars,
Porkbun included, offer an `ALIAS`/`ANAME` record as a CNAME-like workaround for
apex domains, but Vercel's own guidance is built around the `A` record + anycast
IP approach, so prefer that unless the user specifically wants ALIAS and
understands it's provider-specific.

A common, solid pattern: `A` record on the apex pointing at Vercel, `CNAME` on
`www` pointing at `cname.vercel-dns.com`, then set one as the canonical domain
and redirect the other in the Vercel project's domain settings (or via the
`redirect` field on the domain object).

## Before writing any record

Run `porkbun_dns.py list --domain <domain>` first. New domains at Porkbun often
ship with default parking-page `A`/`ALIAS`/`CNAME` records at the apex and
`www` - these will conflict with Vercel's records and must be removed or
overwritten, not left in place alongside the new ones. Also watch for:

- **MX / mail records** - never touch these when setting up a web domain. Only
  touch `A`, `CNAME`, `ALIAS`, and the specific `TXT` record Vercel asked for.
- **Existing TXT records at the same name** - e.g. SPF (`v=spf1 ...`) records
  live at the apex as TXT too. `upsert` on TXT only matches records with the
  exact same name; it won't clobber an SPF record because that's a different
  record's content, but if there happen to be *multiple* TXT records at the
  same name, `upsert` will overwrite all of them - `list` first and use
  `create` instead of `upsert` if there's already an unrelated TXT record you
  need to preserve at that exact name.

## After writing the records

1. **Propagation**: `dig <domain> A +short` / `dig <domain> CNAME +short` (or
   `nslookup`) to see what's currently resolving. Porkbun's default TTL is
   short (600s or less if you set it), but recursive resolvers and ISPs can
   cache longer. If it hasn't updated after ~15-30 minutes, double check the
   record was actually saved (`porkbun_dns.py list`) before assuming it's just
   slow propagation.
2. **Vercel-side config check**: `vercel_domain.py status --domain <domain>`
   until `misconfigured` is `false`.
3. **TLS**: Vercel auto-issues a Let's Encrypt certificate once it sees
   correct DNS - this can take a few extra minutes after DNS resolves
   correctly. `curl -Iv https://<domain>` will show a handshake failure or
   wrong cert until issuance finishes; retry rather than assuming it's broken.
4. **CAA records**: if the domain (or a parent zone) has a `CAA` record
   restricting which certificate authorities may issue certs, and it doesn't
   include Let's Encrypt (`letsencrypt.org`), certificate issuance will fail
   silently from the user's perspective. Check with
   `porkbun_dns.py list --domain <domain> --type CAA`; if one exists and
   blocks Let's Encrypt, either delete it or add a permissive entry.

## Common failure modes

- **"invalid API key" from Porkbun despite correct keys**: the per-domain
  "API Access" toggle (Domain Management > domain > Details) is off. This is
  a separate switch from generating the key pair itself.
- **Vercel `verified: true` immediately but dashboard still asks for
  records**: this is a known quirk where `verified` reflects ownership
  verification, not DNS configuration - always confirm with the `status`
  subcommand (which hits the domain config endpoint), not just the `add`
  response.
- **Domain already attached to a different Vercel project**: Vercel will
  refuse to add it to a second project until it's removed from the first
  (`vercel_domain.py remove --project <old-project> --domain <domain> --yes`).
