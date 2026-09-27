#!/usr/bin/env node
import path from "node:path";
import { fileURLToPath } from "node:url";
import { realpath, stat } from "node:fs/promises";
import { realpathSync } from "node:fs";
import { createCliApplication } from "./application.js";
import { BUILTIN_COMMANDS } from "./cli/command.js";
import { parsePromptCommandOptions } from "./cli/commands/prompt.js";
import { dispatchOperationalCommand, isOperationalCommand } from "./cli/command-dispatch.js";
import { CliUsageError } from "./cli/errors.js";
import { parseCliOptions, type CLIOptions } from "./cli/options.js";
import { formatStartupError } from "./cli/startup-error.js";
import { flushProcessOutput } from "./cli/output-drain.js";
import { printHelp } from "./cli/help.js";
import { installShutdown } from "./lifecycle/shutdown.js";
import { KagekoTui } from "./tui/kageko-tui.js";

// Keep the executable's identity available without requiring the package
// manifest at runtime: the distributable is a single bundled entrypoint.
const CLI_VERSION = "0.1.0";

export async function runCli(argv: readonly string[]): Promise<void> {
	const command = argv[0];
	if (command === "--version" || command === "-v") {
		process.stdout.write(`kageko ${CLI_VERSION}\n`);
		return;
	}
	if (command === "help" || command === "--help" || command === "-h") {
		printHelp();
		return;
	}
	let flags: CLIOptions;
	try {
		flags =
			command === "prompt"
				? parsePromptCommandOptions(argv.slice(1))
				: command !== undefined && BUILTIN_COMMANDS.has(command)
					? {}
					: parseCliOptions([...argv]);
	} catch (error) {
		throw new CliUsageError(formatStartupError(error));
	}
	if (flags.help) {
		printHelp();
		return;
	}

	let application: Awaited<ReturnType<typeof createCliApplication>> | undefined;
	const getApplication = async () => (application ??= await createCliApplication(flags));
	let tui: KagekoTui | undefined;
	const shutdown = installShutdown(async () => {
		await tui?.close();
		await application?.close();
	});
	try {
		if (command === "setup") {
			if (["help", "--help", "-h"].includes(argv[1] ?? "")) {
				process.stdout.write("Usage: kageko setup\nRun the interactive provider and model setup wizard.\n");
				return;
			}
			if (!process.stdin.isTTY || !process.stdout.isTTY) {
				process.stderr.write(
					'Setup requires an interactive terminal. Set KAGEKO_API_KEY / KAGEKO_MODEL_PROVIDER / KAGEKO_MODEL_NAME, or use `kageko auth set <provider> <key>` and `kageko config set model.provider "<id>" --scope user`.\n',
				);
				// A printed setup error must be observable by scripts and CI. Returning
				// with the default status (0) makes a failed provisioning step look
				// successful to the caller.
				process.exitCode = 1;
				return;
			}
			const cwd = await canonicalWorkspacePath(flags.cwd ?? process.cwd());
			const app = await getApplication();
			tui = new KagekoTui({ client: app.client, cwd, setup: true, subscribeDiagnostics: app.subscribeDiagnostics });
			await tui.start();
			await tui.wait();
		} else if (
			isOperationalCommand(command) &&
			(await dispatchOperationalCommand(command, { client: (await getApplication()).client, args: argv.slice(1) }))
		) {
			/* handled */
		} else if (flags.prompt) {
			const app = await getApplication();
			await app.prompt(flags.prompt);
		} else if (command !== undefined && BUILTIN_COMMANDS.has(command)) printHelp();
		else {
			if (!process.stdin.isTTY || !process.stdout.isTTY) {
				throw new CliUsageError("Interactive mode requires a TTY; use --prompt for headless execution.");
			}
			const cwd = await canonicalWorkspacePath(flags.cwd ?? process.cwd());
			let continued: string | undefined;
			if (flags.continue) {
				for (const session of await (await getApplication()).client.listSessions()) {
					if (!session.archived && (await canonicalWorkspacePath(session.cwd)) === cwd) {
						continued = session.sessionId;
						break;
					}
				}
			}
			const app = await getApplication();
			tui = new KagekoTui({
				client: app.client,
				cwd,
				sessionId: flags.sessionId ?? continued,
				resumePicker: flags.resumePicker,
				model: flags.model,
				subscribeDiagnostics: app.subscribeDiagnostics,
			});
			await tui.start();
			await tui.wait();
		}
	} finally {
		await tui?.close();
		shutdown.dispose();
		await shutdown.cleanup();
		await flushProcessOutput().catch(() => {});
	}
}

/** Stable workspace identity: real paths for extant directories, lexical fallback otherwise. */
export async function canonicalWorkspacePath(value: string): Promise<string> {
	const resolved = path.resolve(value);
	const info = await stat(resolved).catch(() => undefined);
	const canonical = info?.isDirectory() ? await realpath(resolved).catch(() => resolved) : resolved;
	return process.platform === "win32" ? canonical.toLocaleLowerCase() : canonical;
}

async function main(): Promise<void> {
	try {
		await runCli(process.argv.slice(2));
	} catch (error) {
		process.stderr.write(`${error instanceof CliUsageError ? error.message : formatStartupError(error)}\n`);
		if (error instanceof CliUsageError) printHelp();
		process.exitCode = error instanceof CliUsageError ? 2 : 1;
	}
}

/**
 * Node exposes `import.meta.main` for executable modules. Keep a real-path
 * fallback for older runtimes and transpilers that do not provide it; npm's
 * Windows shims can invoke a package through a junction/symlink, so a plain
 * lexical path comparison is not sufficient there.
 */
function isMainModule(): boolean {
	const importMetaMain = (import.meta as ImportMeta & { main?: boolean }).main;
	if (typeof importMetaMain === "boolean") return importMetaMain;
	const entry = process.argv[1];
	if (!entry) return false;
	const modulePath = fileURLToPath(import.meta.url);
	try {
		return realpathSync.native(entry) === realpathSync.native(modulePath);
	} catch {
		return path.resolve(entry) === path.resolve(modulePath);
	}
}

if (isMainModule()) void main();
