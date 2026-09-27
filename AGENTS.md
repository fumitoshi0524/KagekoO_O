# AGENTS.md — Guide for AI agents working in this repository

Kageko is an AI coding agent implemented as an npm-workspaces TypeScript (ESM)
monorepo. Node >= 24 is required. Preserve the package boundaries and
dependency direction below when extending cross-package capabilities.

## Layout

- `packages/protocol` — cross-package contracts; the single source of event
  types (`DurableEvent`/`LiveEvent`/`RuntimeEvent`, schema version, validators).
- `packages/kaos` — controlled filesystem and environment operations.
- `packages/kosong` — model/provider (LLM) abstraction; credentials arrive via
  injected ports.
- `packages/oauth` — credentials and OAuth flows (provider keys, MCP tokens).
- `packages/telemetry` — observability.
- `packages/session-store` — session repository and journal read/write.
- `packages/process-supervisor` — background task/process supervision.
- `packages/agent-core` — agent core: turn runner (`TurnFlow`), tools,
  permissions, memory, learning (resident learner agent gated by deterministic
  triggers). Depends on `protocol` + ports only.
- `packages/application` — composition root (`composeApplication`), session
  services, `AgentRuntime`, `ApplicationHarness` (in-process method handler).
- `packages/node-sdk` — the public SDK (`KagekoHarness`, `SessionClient`,
  `InProcessTransport`); the only entry point for frontends.
- `apps/kageko` — the CLI/TUI; depends only on `@kageko/node-sdk` for application capabilities and `@kageko/tui-kit` for terminal presentation.
- `packages/tui-kit/native/` — win32 prebuilt helper (`win32-console-mode.node`,
  ported from kimi-code's pi-tui) enabling `ENABLE_VIRTUAL_TERMINAL_INPUT`;
  `apps/kageko/scripts/copy-native-assets.mjs` copies it next to the bundled
  CLI at build time (the app-level `native/` output is gitignored).
- `test/helpers` — shared test helpers (fake LLM, temp dirs, hermetic env
  setup). Package tests import them via the `#test-helpers/*` alias
  (vitest alias + tsconfig paths); avoid relative imports that escape a
  package and import workspace dependencies through package entry points.

## Dependency direction (iron rules)

```text
CLI/TUI/Gateway -> node-sdk -> application -> agent-core
                                         -> session-store
                                         -> kaos/oauth/kosong/process-supervisor
agent-core -> protocol only
protocol   -> no runtime package
```

- The CLI may only depend on `@kageko/node-sdk` and the business-logic-free
  `@kageko/tui-kit` (enforced by package.json whitelist and structure tests).
- `agent-core` never reads or writes `.kageko`; paths are injected by the
  application composition root.
- Event types are defined only in `packages/protocol/src/events.ts`; internal
  packages use the protocol names (no `JournalEvent`/`TurnEvent` aliases).
- Only the `session-store` repository writes `.kageko/sessions/<id>`; cron,
  learning, and process recovery must go through the repository.
- No cross-package deep imports (`@kageko/*/src/*` or relative paths escaping
  the package); import from package entry points only.

## Commands

- `npm run build` — build all workspaces (tsdown).
- `npm test` — full vitest suite.
- `npm run lint` — eslint.
- `npx tsc --noEmit` — typecheck (must stay green).
- `npm run test:e2e` — end-to-end script against a real harness.

## Working agreements

- Keep workspace package manifests aligned with the dependency direction above
  when adding cross-package dependencies.
- Behavior changes land with (or after) their tests; the repo expects
  `tsc`/`test`/`lint` all green on `main`.
- Commits: English conventional commits, atomic.
