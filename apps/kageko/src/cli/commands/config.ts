import type { KagekoClient } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { buildConfigPatch } from "../config-patch.js";
import { printValue } from "../output.js";

export async function runConfig(argv: readonly string[], application: KagekoClient): Promise<void> {
	const [action = "get", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "get") {
		const parsed = parseCommandArguments(rest, [], ["--json"]);
		if (parsed.positionals.length) throw new Error("config get does not take positional arguments");
		printValue(await application.getConfiguration(), parsed.values["--json"] === true ? "json" : "text");
		return;
	}
	if (action === "path") {
		const parsed = parseCommandArguments(rest);
		const scope = parsed.positionals[0] ?? "project";
		if (parsed.positionals.length > 1 || (scope !== "project" && scope !== "user"))
			throw new Error("Usage: kageko config path [project|user]");
		console.log(await application.configurationPath(scope));
		return;
	}
	if (action === "set") {
		const parsed = parseCommandArguments(rest, ["--scope"]);
		if (parsed.positionals.length !== 2)
			throw new Error("Usage: kageko config set <dotted-key> <json-value> [--scope project|user]");
		const scope = parsed.values["--scope"] ?? "project";
		if (scope !== "project" && scope !== "user") throw new Error("--scope must be project or user");
		let value: unknown;
		try {
			value = JSON.parse(parsed.positionals[1]!);
		} catch {
			throw new Error("config set value must be valid JSON");
		}
		const config = await application.updateConfiguration(buildConfigPatch(parsed.positionals[0]!, value), scope);
		printValue(config);
		return;
	}
	throw new Error(`Unknown config command: ${action}`);
}

function printUsage(): void {
	console.log("Usage: kageko config <get|path|set>");
}
