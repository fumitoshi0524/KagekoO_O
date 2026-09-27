# Security boundaries (0.x)

Kageko runs on your machine with your user account's operating-system privileges. Its permission profiles decide when a tool call needs approval; they are not an operating-system sandbox. Run it only in workspaces and with extensions you are willing to trust.

## Tool permissions

- The default is `--permission manual --interaction interactive`. Built-in local reads and public web reads can be approved automatically. Other operations generally require approval. Explicit deny rules and hard denials take precedence.
- `workspace` also approves classified writes inside the current workspace and some classified shell operations. `unrestricted` approves remaining operations after hard denials and explicit configured asks. Neither profile confines a shell process to the workspace.
- `unattended` cannot ask for approval; an operation that still needs approval is denied. Do not use `unrestricted` merely to make unattended jobs pass.
- File tools resolve paths against the workspace and check symlink targets. Shell commands are spawned as normal child processes and can use the user account's filesystem and network permissions. Command classification and credential environment scrubbing reduce risk but do not make arbitrary shell code safe.

## Credentials, sessions, and logs

- Provider credentials and MCP tokens are stored locally in `~/.kageko/auth.json` and `~/.kageko/mcp-tokens.json`. They are not encrypted at rest. On Unix, Kageko creates the containing directory with private permissions, rejects an existing directory accessible to other users, and writes private files. If an older directory is too broad, set its permissions to `0700` before using the credential store. On Windows, access depends on the account and filesystem ACLs.
- Kageko removes commonly named credential variables from child process environments by default. A secret with an unusual variable name or stored in a file may still be reachable by a shell command or extension.
- Sessions, tool output, memory and learning artifacts are persisted locally. They can contain source code or other sensitive content. Inspect them before sharing diagnostic bundles.
- Telemetry is disabled by default. When enabled, it is stored locally with size and retention limits and heuristic secret redaction; it is not automatically uploaded. Redaction cannot guarantee removal of every secret.

## Network and extensions

- The built-in URL fetcher permits HTTP(S) public destinations and checks resolved IP addresses and redirects. The web search tool sends the search query to DuckDuckGo Lite. Model providers receive the prompts and tool results needed for the session; review your provider and endpoint configuration.
- Project MCP servers, hooks, plugins, skills and generated capabilities can run code or access external services. Kageko requires trust before loading security-sensitive project configuration, and generated capabilities have a review path. Treat code and instructions from these sources as untrusted until reviewed.
- Permission checks and network filtering are defense in depth. Do not place Kageko in a hostile multi-tenant environment as a substitute for an OS/container sandbox.
