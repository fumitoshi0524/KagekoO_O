# Product acceptance suite

This product suite treats `apps/kageko/dist/main.mjs` as an
installed product: no workspace source imports, aliases, virtual terminals, or
internal harnesses are allowed.

Each scenario gets an independent home and workspace. Contracts are written in
user language before test drivers, and assertions concern observable artifacts,
terminal states, durable state, and recovery after a second process starts.

The suite is deliberately organized by user journeys, not packages:

- `cli-contract.test.ts`: every documented non-TUI operation, including bad
  arguments and independent-process persistence.
- `tui-routes.pty.test.ts`: cross-platform route-entry smoke only. It proves
  canonical slash commands can open their first surface; it is never counted
  as interaction coverage.
- `tui-interactions.pty.test.ts`: stateful Windows PTY journeys execute menu
  actions, nested panels, empty and valid forms, destructive confirmation and
  cancellation, composer recovery, process restart, and durable-state checks.
- `agent-mission.e2e.test.ts`: a local OpenAI-compatible model fixture drives
  the bundled executable through streaming, function calling, learner proposal,
  approval, trust, generated tool/MCP artifact validation, and fresh-session
  skill/MCP reuse. It never needs a real API key.
- `user-workflows.contract.test.ts`: independent-process lifecycle, goal,
  memory, scheduling, trust, credentials, malformed input, and destructive
  confirmation journeys.

Coverage is complete only when every public command or slash route has a PTY or
subprocess scenario. Generated skills, tools, and MCP servers additionally need
artifact-schema, single-capability-boundary, reload, and fresh-process checks;
mere file creation is not coverage.

## Evaluation boundary

This acceptance suite is deterministic product conformance. Its scripted model
responses score observable contracts: state transitions, tool routing and
validation, permission boundaries, persistence, recovery, PTY interaction, and
generated-capability loading and execution. It does not establish real-world
task success rates or the learner's effect on downstream work.
