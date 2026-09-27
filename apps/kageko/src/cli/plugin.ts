import type { KagekoClient } from "@kageko/node-sdk";
import { parsePluginCommand } from "./commands/plugin.js";

function printUsage(): void {
	console.log("Usage: kageko plugin install <source>");
	console.log("       kageko plugin uninstall <plugin-id> --yes");
	console.log("");
	console.log("Sources:");
	console.log("  owner/repo            GitHub repository");
	console.log("  github:owner/repo     GitHub repository (explicit)");
	console.log("  https://...           Direct zip or tarball URL");
}

export async function runPlugin(argv: readonly string[], client: KagekoClient): Promise<void> {
	const command = parsePluginCommand(argv);
	if (command === "help") {
		printUsage();
		return;
	}
	if (command.kind === "install") {
		const pluginId = await client.installPlugin(command.source);
		console.log(`Installed plugin: ${pluginId}`);
		return;
	}
	await client.uninstallPlugin(command.pluginId);
	console.log(`Uninstalled plugin: ${command.pluginId}`);
}
