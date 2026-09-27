import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runMcp(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "list", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "list") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		printValue(
			await client.listCapabilities(required(parsed.values["--session"], "mcp list requires --session"), "mcp"),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "add") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--trust-workspace"]);
		if (parsed.positionals.length !== 2)
			throw new Error(
				"Usage: kageko mcp add <name> <json-config> --session <session-id> --trust-workspace",
			);
		const [name, raw] = [parsed.positionals[0]!, parsed.positionals[1]!];
		let serverConfig: unknown;
		try {
			serverConfig = JSON.parse(raw);
		} catch {
			throw new Error("mcp add config must be valid JSON");
		}
		if (typeof serverConfig !== "object" || serverConfig === null || Array.isArray(serverConfig))
			throw new Error("mcp add config must be a JSON object");
		// Validate everything before mutating: a missing --session must not leave a
		// persisted config change behind without the capability reload.
		const sessionId = required(parsed.values["--session"], "mcp add requires --session");
		if (parsed.values["--trust-workspace"] !== true)
			throw new Error(
				"mcp add requires --trust-workspace so the changed security configuration can be trusted before reload",
			);
		// ConfigService deep-merges patches, so a single-key patch adds the server
		// without copying the merged (user+project) view into project scope.
		await client.updateConfiguration({ mcp: { servers: { [name]: serverConfig } } });
		// Project-scoped capability changes invalidate workspace trust. Restore it
		// only when a non-interactive caller explicitly accepts the changed config.
		await client.grantWorkspaceTrust();
		await client.reloadCapabilities(sessionId);
		return;
	}
	if (action === "remove") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--yes", "--trust-workspace"]);
		if (parsed.positionals.length !== 1)
			throw new Error(
				"Usage: kageko mcp remove <name> --session <session-id> --yes --trust-workspace",
			);
		if (parsed.values["--yes"] !== true) throw new Error("Refusing to remove an MCP server without --yes");
		const sessionId = required(parsed.values["--session"], "mcp remove requires --session");
		if (parsed.values["--trust-workspace"] !== true)
			throw new Error(
				"mcp remove requires --trust-workspace so the changed security configuration can be trusted before reload",
			);
		const name = parsed.positionals[0]!;
		const config = (await client.getConfiguration()) as { mcp?: { servers?: Record<string, unknown> } };
		if (!config.mcp?.servers?.[name]) throw new Error(`Unknown MCP server: ${name}`);
		// ConfigService deep-merges patches and never deletes keys, so removal is
		// a null tombstone; filterMcpServers drops entries that fail validation.
		await client.updateConfiguration({ mcp: { servers: { [name]: null } } });
		await client.grantWorkspaceTrust();
		await client.reloadCapabilities(sessionId);
		return;
	}
	if (action === "auth") {
		const parsed = parseCommandArguments(rest, [], ["--json"]);
		if (parsed.positionals.length !== 1) throw new Error("Usage: kageko mcp auth <name>");
		printValue(
			await client.authenticateMcpServer(parsed.positionals[0]!),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	throw new Error(`Unknown mcp command: ${action}`);
}

function printUsage(): void {
	console.log(
		"Usage: kageko mcp <list|add|remove|auth> [--session <session-id>] (add/remove require --trust-workspace)",
	);
}

function required(value: string | boolean | undefined, message: string): string {
	if (typeof value !== "string") throw new Error(message);
	return value;
}
