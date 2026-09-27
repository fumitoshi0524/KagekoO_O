import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runLearning(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "pending", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "pending") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--json"]);
		printValue(
			await client.listLearningPending(required(parsed.values["--session"], "learning pending requires --session")),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	if (action === "approve" || action === "reject") {
		const parsed = parseCommandArguments(rest, ["--session"], ["--yes"]);
		if (parsed.positionals.length !== 1)
			throw new Error(
				`Usage: kageko learning ${action} <event-id> --session <session-id>${action === "reject" ? " --yes" : ""}`,
			);
		if (action === "reject" && parsed.values["--yes"] !== true)
			throw new Error("Refusing to reject a learning entry without --yes");
		const result = (await client.resolveLearning(
			required(parsed.values["--session"], `learning ${action} requires --session`),
			parsed.positionals[0]!,
			action,
		)) as { readonly resolved?: boolean; readonly reason?: string } | undefined;
		// A resolved:false result is a failure, not a success: surface the reason.
		if (result?.resolved === false)
			throw new Error(`Could not ${action} learning entry: ${result.reason ?? "unknown reason"}`);
		printValue(result ?? { resolved: true });
		return;
	}
	throw new Error(`Unknown learning command: ${action}`);
}

function printUsage(): void {
	console.log("Usage: kageko learning <pending|approve|reject> --session <session-id>");
}

function required(value: string | boolean | undefined, message: string): string {
	if (typeof value !== "string") throw new Error(message);
	return value;
}
