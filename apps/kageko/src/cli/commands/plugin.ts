import { parseCommandArguments } from "../command.js";

export interface PluginInstallCommand {
	readonly kind: "install";
	readonly source: string;
}

export interface PluginUninstallCommand {
	readonly kind: "uninstall";
	readonly pluginId: string;
}

export type PluginCommand = PluginInstallCommand | PluginUninstallCommand;

/** Strict command parser; installation itself stays in the CLI execution layer. */
export function parsePluginCommand(argv: readonly string[]): PluginCommand | "help" {
	const [subcommand, ...rest] = argv;
	if (!subcommand || subcommand === "--help" || subcommand === "-h") return "help";
	if (subcommand === "install") {
		const parsed = parseCommandArguments(rest);
		if (parsed.positionals.length !== 1) throw new Error("Usage: kageko plugin install <source>");
		return { kind: "install", source: parsed.positionals[0]! };
	}
	if (subcommand === "uninstall") {
		const parsed = parseCommandArguments(rest, [], ["--yes"]);
		if (parsed.positionals.length !== 1) throw new Error("Usage: kageko plugin uninstall <plugin-id> --yes");
		if (parsed.values["--yes"] !== true) throw new Error("Refusing to uninstall a plugin without --yes");
		return { kind: "uninstall", pluginId: parsed.positionals[0]! };
	}
	throw new Error(`Unknown plugin command: ${subcommand}`);
}
