import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printSessionList, printValue } from "../output.js";

export async function runSession(argv: readonly string[], application: KagekoClient): Promise<void> {
	const [action = "list", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "list") {
		const parsed = parseCommandArguments(rest, [], ["--all", "--json"]);
		if (parsed.positionals.length) throw new Error("session list does not take positional arguments");
		const includeArchived = parsed.values["--all"] === true;
		// Archived sessions are excluded at the repository boundary by default.
		// Filtering an already-default list cannot bring them back, so --all must
		// be part of the public request rather than a local post-filter.
		const sessions = await application.listSessions({ includeArchived });
		if (parsed.values["--json"] === true) printValue(sessions, "json");
		else printSessionList(sessions);
		return;
	}
	if (action === "create") {
		const parsed = parseCommandArguments(rest, ["--id", "--title", "--cwd"], ["--json"]);
		if (parsed.positionals.length) throw new Error("session create does not take positional arguments");
		const session = await application.createSession({
			sessionId: asString(parsed.values["--id"]),
			title: asString(parsed.values["--title"]),
			cwd: asString(parsed.values["--cwd"]) ?? process.cwd(),
		});
		printValue(await session.snapshot(), parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	if (action === "resume") {
		const parsed = parseCommandArguments(rest, [], ["--json"]);
		const sessionId = exactlyOne(parsed.positionals, "Usage: kageko session resume <session-id>");
		const session = await application.resumeSession(sessionId);
		printValue(session, parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	if (action === "fork") {
		const parsed = parseCommandArguments(rest, ["--id"], ["--json"]);
		const sessionId = exactlyOne(parsed.positionals, "Usage: kageko session fork <session-id> [--id <new-id>]");
		const session = await application.forkSession(sessionId, asString(parsed.values["--id"]));
		printValue(await session.snapshot(), parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	if (action === "rename") {
		const parsed = parseCommandArguments(rest);
		if (parsed.positionals.length !== 2) throw new Error("Usage: kageko session rename <session-id> <title>");
		await application.renameSession(parsed.positionals[0]!, parsed.positionals[1]!);
		return;
	}
	if (action === "archive" || action === "unarchive") {
		const parsed = parseCommandArguments(rest);
		const sessionId = exactlyOne(parsed.positionals, `Usage: kageko session ${action} <session-id>`);
		await application.archiveSession(sessionId, action === "archive");
		return;
	}
	if (action === "delete") {
		const parsed = parseCommandArguments(rest, [], ["--yes"]);
		const sessionId = exactlyOne(parsed.positionals, "Usage: kageko session delete <session-id> --yes");
		if (parsed.values["--yes"] !== true) throw new Error("Refusing to delete a session without --yes");
		await application.deleteSession(sessionId);
		return;
	}
	if (action === "compact") {
		const parsed = parseCommandArguments(rest, [], ["--json"]);
		const [sessionId, ...instructionParts] = parsed.positionals;
		if (!sessionId) throw new Error("Usage: kageko session compact <session-id> [instruction]");
		// Print the CompactResult as-is: skipped/failed outcomes must stay visible.
		printValue(
			await application.session(sessionId).compact(instructionParts.join(" ") || undefined),
			parsed.values["--json"] === true ? "json" : "text",
		);
		return;
	}
	throw new Error(`Unknown session command: ${action}`);
}

function asString(value: string | boolean | undefined): string | undefined {
	return typeof value === "string" ? value : undefined;
}

function exactlyOne(values: readonly string[], usage: string): string {
	if (values.length !== 1) throw new Error(usage);
	return values[0]!;
}

function printUsage(): void {
	console.log("Usage: kageko session <list|create|resume|fork|rename|archive|unarchive|delete|compact>");
}
