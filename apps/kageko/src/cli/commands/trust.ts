import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { printValue } from "../output.js";

export async function runTrust(argv: readonly string[], client: KagekoClient): Promise<void> {
	const [action = "status", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "status") {
		const parsed = parseCommandArguments(rest, [], ["--json"]);
		if (parsed.positionals.length) throw new Error("trust status does not take positional arguments");
		printValue(await client.inspectWorkspaceTrust(), parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	if (action === "grant") {
		const parsed = parseCommandArguments(rest, [], ["--json"]);
		if (parsed.positionals.length) throw new Error("trust grant does not take positional arguments");
		printValue(await client.grantWorkspaceTrust(), parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	if (action === "revoke") {
		const parsed = parseCommandArguments(rest, [], ["--yes"]);
		if (parsed.positionals.length) throw new Error("trust revoke does not take positional arguments");
		if (parsed.values["--yes"] !== true) throw new Error("Refusing to revoke workspace trust without --yes");
		await client.revokeWorkspaceTrust();
		return;
	}
	throw new Error(`Unknown trust command: ${action}`);
}

function printUsage(): void {
	console.log("Usage: kageko trust <status|grant|revoke>");
}
