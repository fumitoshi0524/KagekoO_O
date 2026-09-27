import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runCapability(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "list", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action !== "list") throw new Error(`Unknown capability command: ${action}`);
	const parsed = parseCommandArguments(rest, ["--session", "--kind"], ["--json"]);
	const kind = parsed.values["--kind"];
	if (kind !== undefined && kind !== "plugin" && kind !== "skill" && kind !== "mcp" && kind !== "tool")
		throw new Error("--kind must be plugin, skill, mcp, or tool");
	const sessionId = parsed.values["--session"];
	if (typeof sessionId !== "string") throw new Error("capability list requires --session");
	if (kind === "tool") {
		printValue(await client.listTools(sessionId), parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	printValue(await client.listCapabilities(sessionId, kind), parsed.values["--json"] === true ? "json" : "text");
}

function printUsage(): void {
	console.log("Usage: kageko capability list --session <session-id> [--kind plugin|skill|mcp|tool] [--json]");
}
