# TypeScript CLI Engineering Reference

Use this reference after inspecting the repository. Existing project conventions win unless the task explicitly requests migration.

## Architecture

Recommended shape for a multi-provider operational CLI:

```text
src/
├── index.ts                 executable boundary
├── cli.ts                   parser and root registration
├── core/                    output, errors, config, pagination, JSON input
├── commands/                provider-neutral commands
└── providers/
    └── provider-name/
        ├── register.ts
        ├── commands/
        ├── services/
        └── types/
```

Keep tests beside the code they validate. Use a local parser instance instead of a global singleton so command trees can be tested repeatedly. Keep command handlers responsible for parsing and orchestration only. Put SDK translation, retries, pagination, and provider-specific validation in services.

For greenfield bin-only packages, prefer one bundled executable and an explicit `files` allowlist. Preserve CommonJS in existing projects unless ESM migration is requested. For greenfield ESM, use `"type": "module"` and a bundler-aware TypeScript resolution mode when the bundler owns emission.

## Package contract

`package.json` should define:

- Lowercase package name and semantic version.
- `bin` map from every installed command to the built executable.
- Explicit `files` allowlist.
- Runtime `engines.node` floor.
- Public repository, issue tracker, homepage, license, and publish access.
- `prepublishOnly` as a final build guard, not the primary release test.

The first line of each packed executable must be `#!/usr/bin/env node`. Omit `main`, `exports`, and type declarations for a bin-only package unless an importable JavaScript API is intentionally supported.

## Output and errors

Recommended failure envelope:

```json
{
  "ok": false,
  "error": {
    "code": "RATE_LIMIT",
    "message": "The provider rate limit was reached.",
    "retryable": true,
    "next_steps": ["Wait for the retry window, then repeat the same read command."],
    "retry_after_ms": 1000
  }
}
```

Keep codes stable and uppercase snake case. Allow optional safe `details` only when agents can act on them. Centralize parser failures, validation errors, provider errors, and unexpected errors through the same reporter. Do not mix prose with JSON on machine paths.

Use 0 for success and 1 for ordinary failures. Let Node handle signals for short-lived commands. Add signal handlers only when a long-running command owns cleanup, and ensure the handler actually terminates. Set `process.exitCode` and let streams flush.

## Configuration and inputs

Document one precedence order, such as explicit flag, environment variable, project config, user config, default. Never load arbitrary `.env` files implicitly without a documented contract. Restrict saved secret files to user read/write permissions.

Accept complex objects as inline JSON plus `@path` only when both forms are tested and documented. Validate files before remote calls. Redact secrets in errors. For destructive or externally visible operations, support dry-run when the provider permits it and require explicit caller authorization regardless.

## Verification

Minimum repository gate:

```bash
npm ci
npm run format:check
npm run typecheck
npm test
npm run build
npm pack --dry-run
npm run test:package
git diff --check
```

Adapt command names to the repository. A package smoke should:

1. Create the tarball once.
2. Inspect the allowlisted contents and executable mode/shebang.
3. Install the tarball into a temporary prefix.
4. Run each binary's help and version.
5. Run a valid local command and an invalid command.
6. Assert stdout, stderr, JSON shape, and exit codes.

Run the supported Node matrix. Add macOS and Windows artifact smokes only when cross-platform support is claimed.

## CI and release

Split responsibilities:

- CI: pull requests and main branch run install, format, typecheck, tests, build, and package smoke.
- Docs: build on docs changes and deploy only from the protected branch.
- Release: trusted tag or release commit verifies version, repeats the gate, publishes, verifies npm, and creates a GitHub Release.

For npm trusted publishing, re-check the official requirements before each workflow change. As verified 2026-07-27, npm requires a supported hosted CI provider, npm 11.5.1 or newer, Node 22.14.0 or newer, the exact trusted workflow filename and repository, and `id-token: write`. Public packages from public GitHub repositories receive provenance automatically. Do not cache release dependencies when npm guidance forbids it.

Semantic versioning policy:

- Before 1.0: patch for compatible fixes; minor for features and breaking contracts, with breakage stated clearly.
- After 1.0: patch for fixes, minor for compatible additions/deprecations, major for breaking contracts.
- Never republish or rewrite an existing version.

Use Conventional Commits with Release Please only when the repository already uses that workflow or explicitly adopts it. Do not bolt two release authorities onto one project.

## Documentation and agent readiness

Keep README limited to identity, install, one quick start, and links. Put tutorials, task guides, exact references, architecture, provider compatibility, troubleshooting, deployment, and release details under `docs/`. Keep generated help authoritative for command flags.

Ship a repository-local skill when agents are expected to operate the CLI. Root `AGENTS.md` should define development and delivery rules. `CLAUDE.md` may reference or symlink to `AGENTS.md` when the host supports it.

## Primary sources

- [Node.js packages](https://nodejs.org/api/packages.html)
- [Node.js process and exit behavior](https://nodejs.org/api/process.html)
- [TypeScript module resolution](https://www.typescriptlang.org/tsconfig/moduleResolution.html)
- [npm package.json, files, and bin](https://docs.npmjs.com/cli/v11/configuring-npm/package-json/)
- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/)
- [npm semantic versioning](https://docs.npmjs.com/about-semantic-versioning/)
- [GitHub Node package publishing](https://docs.github.com/en/actions/tutorials/publish-packages/publish-nodejs-packages)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [Commander](https://github.com/tj/commander.js)
- [esbuild Node bundling](https://esbuild.github.io/getting-started/#bundling-for-node)
- [Vitest](https://vitest.dev/guide/)
- [Diataxis documentation framework](https://diataxis.fr/start-here/)
