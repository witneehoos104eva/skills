---
name: deploy-mizai
description: Launch, connect, or assign a production URL for a site under mizai.solutions using GitHub, Vercel, and either Vercel DNS or Porkbun DNS. Use whenever Mike asks to deploy a site to a mizai.solutions URL, give an existing Vercel project a mizai.solutions subdomain, create or connect a GitHub repository and Vercel project, or set up a new Miz AI site. Handle both new and already-existing GitHub/Vercel state safely.
---

# Deploy Miz AI

Use this skill for state-aware launches of sites at `slug.mizai.solutions`.

`mizai.solutions` means **Miz AI**: Mizzi plus AI. Preserve the exact spelling in commands, domain records, and user-facing copy.

## Bundled resources

- `references/vercel-commands.md` - the Vercel CLI commands for Mike's Windows host (project inspect, domains add/inspect, production deploy).
- `scripts/porkbun_dns.py` - idempotent Porkbun DNS record management (`ping` / `list` / `create` / `upsert` / `delete`), reading `PORKBUN_API_KEY`/`PORKBUN_SECRET_KEY` from the environment. This is what implements the "retrieve, compare, only touch what's needed" record-aware approach in Step 4's Porkbun DNS mode below - use `list` to inventory before changing anything, `upsert` to write the value Vercel asked for without disturbing unrelated records.
- `scripts/vercel_domain.py` - a Vercel domain REST API wrapper (`add` / `status` / `verify` / `remove`), reading `VERCEL_TOKEN`/`VERCEL_TEAM_ID` from the environment. Prefer the CLI in `references/vercel-commands.md` when working interactively on Mike's machine; fall back to this script when you need a scriptable, non-interactive check (e.g. polling `status` for `misconfigured: false` after a DNS change) or when the CLI isn't available.
- `references/dns-troubleshooting.md` - which record type goes where (apex vs. subdomain), what to check before writing a record (parking-page defaults, MX/SPF safety), and the failure modes that actually come up (CAA blocking cert issuance, Porkbun's per-domain API-access toggle, propagation vs. a record that never saved).

## Scope and safety

The registrar remains Porkbun in both DNS modes. The DNS host differs:

| Mode | Nameservers point to | Who creates web DNS records |
| --- | --- | --- |
| Vercel DNS | Vercel | Vercel |
| Porkbun DNS | Porkbun | Porkbun API or dashboard |

Default to **Vercel DNS** if `mizai.solutions` is primarily used for Vercel sites. It makes future subdomain launches simpler. Use **Porkbun DNS** if existing email, forwarding, or non-Vercel services make a nameserver migration unsuitable.

Never switch nameservers without the user's explicit approval. Before a nameserver move, inventory all current records and explain which must be recreated, especially MX, SPF, DKIM, DMARC, verification TXT, and non-Vercel hosts. Do not delete or overwrite unrelated records.

Never push, deploy to production, create a repository, or reassign a domain without the user's explicit request or confirmation in the current task. A request to inspect, plan, or dry-run authorizes only read-only work.

## Required inputs

Collect or infer only what is needed:

- Desired URL slug, yielding `slug.mizai.solutions`.
- Local project path, if available.
- Existing GitHub repository, if any, in `owner/repo` form.
- Existing Vercel project, if any.
- DNS mode: Vercel DNS or Porkbun DNS.
- Whether the user is authorizing a production deployment now.

If a slug is not given, propose a short lowercase, hyphenated slug based on the project name and ask for approval. Do not silently replace a requested slug.

## Step 1: preflight and inventory

Start with read-only checks. Report concise findings under:

- **What exists**: local Git repository and remote, GitHub repository, Vercel project, current linked repository, production branch, current project domains, DNS mode, and existing DNS records relevant to the requested hostname.
- **Proposed change**: exact repository, Vercel project, URL, required DNS record or configuration, and whether a production deploy would occur.
- **Decision needed**: only if an important item is missing, ambiguous, or conflicts.

Use the current working tree without discarding or absorbing unrelated changes. For a local Git repository, inspect `git status --short`, `git remote -v`, and the current branch before changing anything. If the working tree is dirty, state it. Do not commit unrelated changes.

Check Vercel project linkage and production branch rather than assuming that a project name matches a repository. On this Windows host, use `.cmd` executables and, if Vercel TLS verification fails, set:

```powershell
$env:NODE_OPTIONS = '--use-system-ca'
```

Then use `npx.cmd vercel@latest` or a known working `vercel.cmd` installation. See [Vercel commands](references/vercel-commands.md) for the standard checks.

## Step 2: choose the safe branch

Handle the existing-state matrix explicitly:

| GitHub repository | Vercel project | Action |
| --- | --- | --- |
| Missing | Missing | Create both only after approval, connect them, then assign the URL. |
| Exists | Missing | Reuse the repository, create and connect the Vercel project after approval. |
| Missing | Exists | Inspect the existing Vercel Git link. If unlinked, ask before creating a new repository. Do not replace an existing unknown link. |
| Exists | Exists | Verify the actual link and production branch. Reuse both if they match. |

If GitHub or Vercel shows a conflict, stop before mutation and name the conflicting resource. Never use Vercel's `--force` domain reassignment or overwrite a Git remote unless the user explicitly authorizes that exact move.

## Step 3: connect the source and project

If creating a GitHub repository is authorized, use the requested owner, visibility, and repository name. Initialize and push only the user-approved project files. If the repository already exists, retain its visibility, default branch, and collaborators.

Create or link the Vercel project in the correct team. Keep the intended production branch, normally `main`, unless the existing project is intentionally configured otherwise. Confirm the Git link by inspecting the Vercel project configuration after the change.

If a project is already deployed and only needs a domain, do not create a second Vercel project or redeploy unless requested.

## Step 4: assign and configure the URL

Request or add exactly `slug.mizai.solutions` to the intended Vercel project. Check whether it is already assigned elsewhere first.

### Vercel DNS mode

Add the subdomain to the project through Vercel and confirm its configured status. Because Vercel is authoritative for DNS, do not create a Porkbun record for each new subdomain.

### Porkbun DNS mode

First add the domain in Vercel and retrieve Vercel's exact required record type, host, and value (`vercel domains inspect slug.mizai.solutions`, or `python scripts/vercel_domain.py status --domain slug.mizai.solutions` if you need it non-interactively). Then create or update only that record through Porkbun's API. Use the Porkbun API key only from local secrets or environment variables, never source control or client-side code.

Use an idempotent, record-aware approach - `scripts/porkbun_dns.py` implements exactly this:

1. Retrieve records for `mizai.solutions` and search for the same host and type:
   `python scripts/porkbun_dns.py list --domain mizai.solutions --name slug`
2. If it already has Vercel's requested value, leave it unchanged.
3. If it is absent, create it; if it's present with the wrong value, update it in place:
   `python scripts/porkbun_dns.py upsert --domain mizai.solutions --type <type> --content <value> --name slug`
4. If it conflicts with a non-Vercel record, stop and request explicit approval rather than replacing it.
5. Ask Vercel to verify the project domain after the record is present.

Read `references/dns-troubleshooting.md` before this step if the domain is new or hasn't had a Vercel record on it before - new Porkbun domains often carry default parking-page records at the apex/`www` that will conflict and need clearing first, and it's worth confirming there's no CAA record blocking Let's Encrypt before you're several steps in.

Never assume a universal Vercel CNAME target. Read the current target from Vercel for the specific project and hostname.

## Step 5: deploy and verify

Deploy to production only when the user authorized it. Treat a successful CLI command as an intermediate result, not completion.

For a production deploy:

1. Run the project's relevant build, lint, typecheck, or tests when available.
2. Deploy the intended branch to Vercel production.
3. Inspect the production alias and ensure Vercel reports a healthy deployment.
4. Request `https://slug.mizai.solutions` and verify it reaches the intended site over HTTPS.
5. For a changed site, check one distinctive visible marker or primary workflow, not only a status code.

DNS and certificate issuance can take time. Report the actual status as pending rather than calling it live until the custom URL works. If DNS resolves but HTTPS still fails, or a CAA record is in play, see `references/dns-troubleshooting.md`.

## Completion report

Use this exact concise structure:

### What happened

- GitHub: [created, reused, or not changed] - `owner/repo`.
- Vercel: [created, linked, reused, or not changed] - project name and production branch.
- Domain: [assigned, verified, pending, or unchanged] - `https://slug.mizai.solutions`.

### What changed

- List only intentional mutations, including DNS record changes if Porkbun DNS was used.

### What's next

- State the production URL and verification evidence, or the single remaining action if not yet live.

Include a direct link to the verified production URL. Clearly distinguish configured, deployed, and live.
