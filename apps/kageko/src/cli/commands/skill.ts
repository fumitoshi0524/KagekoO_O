import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runSkill(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "list", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "list") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		printValue(
			await client.listCapabilities(required(parsed.values["--session"], "skill list requires --session"), "skill"),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "reload") {
		const parsed = parseCommandArguments(rest, ["--session"]);
		if (parsed.positionals.length) throw new Error("skill reload does not take positional arguments");
		await client.reloadCapabilities(required(parsed.values["--session"], "skill reload requires --session"));
		return;
	}
	if (action === "remove") {
		// Skill removal is global by name; the SDK takes no session here.
		const parsed = parseCommandArguments(rest, [], ["--yes"]);
		if (parsed.positionals.length !== 1) throw new Error("Usage: kageko skill remove <name> --yes");
		if (parsed.values["--yes"] !== true) throw new Error("Refusing to remove a skill without --yes");
		await client.removeSkill(parsed.positionals[0]!);
		return;
	}
	throw new Error(`Unknown skill command: ${action}`);
}

function printUsage(): void {
	console.log("Usage: kageko skill <list|reload|remove> [--session <session-id>]");
}

function required(value: string | boolean | undefined, message: string): string {
	if (typeof value !== "string") throw new Error(message);
	return value;
}
