import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runCron(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "list", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") {
		printValue(
			[
				"Usage: kageko cron <action>",
				"  list --session <id> [--json]",
				"  create --session <id> --schedule <cron> --prompt <text> [--once]",
				"  delete <id> --session <id> --yes",
			].join("\n"),
		);
		return;
	}
	if (action === "list") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		printValue(
			await client.listCron(required(parsed.values["--session"], "cron list requires --session")),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "create") {
		const parsed = parseCommandArguments(rest, ["--session", "--schedule", "--prompt"], ["--once"]);
		const result = await client.createCron(required(parsed.values["--session"], "cron create requires --session"), {
			cron: required(parsed.values["--schedule"], "cron create requires --schedule"),
			prompt: required(parsed.values["--prompt"], "cron create requires --prompt"),
			recurring: parsed.values["--once"] !== true,
		});
		printValue(result);
		return;
	}
	if (action === "delete") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--yes"]);
		if (parsed.positionals.length !== 1 || parsed.values["--yes"] !== true)
			throw new Error("Usage: kageko cron delete <id> --session <session-id> --yes");
		await client.deleteCron(
			required(parsed.values["--session"], "cron delete requires --session"),
			parsed.positionals[0]!,
		);
		return;
	}
	throw new Error(`Unknown cron command: ${action}`);
}
function required(value: string | boolean | undefined, message: string): string {
	if (typeof value !== "string") throw new Error(message);
	return value;
}
