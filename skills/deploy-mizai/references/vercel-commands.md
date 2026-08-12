# Vercel commands on Mike's Windows host

Use these as a starting point, adjusting the team scope and project names to current state. Do not expose tokens in command output or commit them to files.

```powershell
$env:NODE_OPTIONS = '--use-system-ca'

# Inspect the linked project from a project directory.
npx.cmd vercel@latest project inspect

# List team domains before assigning a hostname.
npx.cmd vercel@latest domains ls --limit 100

# Assign a hostname after verifying it is not used by another project.
npx.cmd vercel@latest domains add slug.mizai.solutions project-name

# Inspect the custom-domain configuration and verification status.
npx.cmd vercel@latest domains inspect slug.mizai.solutions

# Run a production deploy only when explicitly requested.
npx.cmd vercel@latest deploy --prod --yes
```

When CLI output is incomplete, inspect the Vercel project API configuration. Verify `link.type`, `link.org`, `link.repo`, and `link.productionBranch` rather than inferring them from a folder or project name.

After a domain configuration change, use Vercel's domain verification capability. After production deployment, inspect the production alias and request the custom URL directly.
