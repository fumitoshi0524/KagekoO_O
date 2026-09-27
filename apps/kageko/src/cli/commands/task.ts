import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runTask(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "list", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "list") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--all", "--json"]);
		if (parsed.positionals.length) throw new Error("task list does not take positional arguments");
		const activities = await client.listActivities({
			sessionId: stringValue(parsed.values["--session"]),
			activeOnly: parsed.values["--all"] !== true,
		});
		printValue(activities, parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	if (action === "output") {
		const parsed = parseCommandArguments(rest, ["--session", "--offset", "--limit"], ["--json"]);
		if (parsed.positionals.length !== 1) throw new Error("Usage: kageko task output <task-id> --session <session-id>");
		const sessionId = required(parsed.values["--session"], "task output requires --session");
		const session = client.session(sessionId);
		printValue(
			await session.readActivityOutput(
				parsed.positionals[0]!,
				numberValue(parsed.values["--offset"]),
				numberValue(parsed.values["--limit"]),
			),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "stop") {
		const parsed = parseCommandArguments(rest, ["--session"]);
		if (parsed.positionals.length !== 1) throw new Error("Usage: kageko task stop <task-id> --session <session-id>");
		await client
			.session(required(parsed.values["--session"], "task stop requires --session"))
			.stopActivity(parsed.positionals[0]!);
		return;
	}
	throw new Error(`Unknown task command: ${action}`);
}

function printUsage(): void {
	console.log("Usage: kageko task <list|output|stop>");
}

function stringValue(value: string | boolean | undefined): string | undefined {
	return typeof value === "string" ? value : undefined;
}
function required(value: string | boolean | undefined, message: string): string {
	if (typeof value !== "string") throw new Error(message);
	return value;
}
function numberValue(value: string | boolean | undefined): number | undefined {
	return typeof value === "string" && /^\d+$/.test(value) ? Number(value) : undefined;
}
