import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runGoal(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "status", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "status") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		printValue(
			await client.session(required(parsed.values["--session"], "goal status requires --session")).getGoal(),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "create") {
		const parsed = parseCommandArguments(rest, ["--session", "--objective"], ["--json"]);
		const session = client.session(required(parsed.values["--session"], "goal create requires --session"));
		printValue(
			await session.createGoal({
				objective: required(parsed.values["--objective"], "goal create requires --objective"),
			}),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "pause" || action === "resume") {
		const parsed = parseCommandArguments(rest, ["--session"]);
		const session = client.session(required(parsed.values["--session"], `goal ${action} requires --session`));
		const updated = await session.updateGoal({ status: action === "pause" ? "paused" : "active" });
		// updateGoal returns null when there is no active goal; that is a failure,
		// not a result worth printing.
		if (updated === null) throw new Error(action === "pause" ? "No active goal." : "No goal to resume.");
		printValue(updated);
		return;
	}
	if (action === "complete") {
		const parsed = parseCommandArguments(rest, ["--session"]);
		const session = client.session(required(parsed.values["--session"], "goal complete requires --session"));
		const completed = await session.updateGoal({ status: "completed" });
		if (completed === null) throw new Error("No active goal.");
		printValue("Goal completed.");
		return;
	}
	throw new Error(`Unknown goal command: ${action}`);
}

function printUsage(): void {
	console.log("Usage: kageko goal <status|create|pause|resume|complete> --session <session-id>");
}

function required(value: string | boolean | undefined, message: string): string {
	if (typeof value !== "string") throw new Error(message);
	return value;
}
