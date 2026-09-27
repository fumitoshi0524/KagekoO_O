import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runMemory(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "status", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "status") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		printValue(
			await client.memoryStatus(required(parsed.values["--session"], "memory status requires --session")),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "query") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		const text = parsed.positionals.join(" ");
		if (!text) throw new Error("Usage: kageko memory query --session <session-id> <text>");
		printValue(
			await client.queryMemory(required(parsed.values["--session"], "memory query requires --session"), text),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "remember") {
		const parsed = parseCommandArguments(rest, ["--session", "--scope"], []);
		const fact = parsed.positionals.join(" ");
		if (!fact) throw new Error("Usage: kageko memory remember --session <session-id> [--scope <scope>] <fact>");
		await client.rememberFact(
			required(parsed.values["--session"], "memory remember requires --session"),
			fact,
			typeof parsed.values["--scope"] === "string" ? parsed.values["--scope"] : undefined,
		);
		return;
	}
	if (action === "recall") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		// A query-less recall tokenizes to zero terms and always returns []; require
		// the query text like the TUI does instead of printing an empty result.
		const query = parsed.positionals.join(" ");
		if (!query) throw new Error("Usage: kageko memory recall --session <session-id> <query>");
		printValue(
			await client.recallProfile(required(parsed.values["--session"], "memory recall requires --session"), query),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "index") {
		const parsed = parseCommandArguments(rest, ["--session"]);
		printValue(await client.indexRepository(required(parsed.values["--session"], "memory index requires --session")));
		return;
	}
	if (action === "generate-skill") {
		const parsed = parseCommandArguments(rest, ["--session"]);
		printValue(
			(await client.generateSessionSkill(
				required(parsed.values["--session"], "memory generate-skill requires --session"),
			)) ?? "No skill generated.",
		);
		return;
	}
	throw new Error(`Unknown memory command: ${action}`);
}

function printUsage(): void {
	console.log("Usage: kageko memory <status|query|remember|recall|index|generate-skill> --session <session-id>");
}

function required(value: string | boolean | undefined, message: string): string {
	if (typeof value !== "string") throw new Error(message);
	return value;
}
