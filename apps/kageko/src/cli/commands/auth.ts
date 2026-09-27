import { createInterface, type Interface } from "node:readline";
import type { KagekoClient, OAuthLoginEvent, OAuthPrompt } from "@kageko/node-sdk";
import { parseCommandArguments } from "../command.js";
import { SETUP_PROVIDERS } from "../../tui/controllers/setup-controller.js";

/** Injectable stdio for `auth login` prompts; defaults to the process streams. */
export interface AuthLoginIo {
	readonly input?: NodeJS.ReadableStream;
	readonly output?: NodeJS.WritableStream;
}

export async function runAuth(argv: readonly string[], application: KagekoClient, io: AuthLoginIo = {}): Promise<void> {
	const [action = "status", ...rest] = argv;
	if (action === "help" || action === "--help" || action === "-h") return printUsage();
	if (action === "status") {
		const parsed = parseCommandArguments(rest);
		const provider = exactlyOne(parsed.positionals, "Usage: kageko auth status <provider>");
		printLine(
			(await application.hasCredential(provider))
				? `Credential configured for ${provider}.`
				: `No credential configured for ${provider}.`,
		);
		return;
	}
	if (action === "set") {
		const parsed = parseCommandArguments(rest, ["--api-key"]);
		const provider = exactlyOne(parsed.positionals, "Usage: kageko auth set <provider> [--api-key <key>]");
		const key =
			typeof parsed.values["--api-key"] === "string" ? parsed.values["--api-key"] : process.env["KAGEKO_API_KEY"];
		if (!key)
			throw new Error(
				"Provide KAGEKO_API_KEY or --api-key. KAGEKO_API_KEY avoids exposing the secret in shell history.",
			);
		if (parsed.values["--api-key"])
			process.stderr.write(
				"warning: --api-key can be visible in shell history and process listings; prefer KAGEKO_API_KEY.\n",
			);
		await application.setApiKey(provider, key);
		printLine(`Credential saved for ${provider}.`);
		return;
	}
	if (action === "remove") {
		const parsed = parseCommandArguments(rest, [], ["--yes"]);
		const provider = exactlyOne(parsed.positionals, "Usage: kageko auth remove <provider> --yes");
		if (parsed.values["--yes"] !== true) throw new Error("Refusing to remove a credential without --yes");
		await application.removeCredential(provider);
		printLine(`Credential removed for ${provider}.`);
		return;
	}
	if (action === "login") {
		const parsed = parseCommandArguments(rest);
		const provider = exactlyOne(parsed.positionals, "Usage: kageko auth login <provider>");
		if (
			SETUP_PROVIDERS.some((entry) => entry.id === provider) &&
			!SETUP_PROVIDERS.some((entry) => entry.id === provider && entry.authMode === "oauth")
		) {
			throw new Error(`${provider} does not support OAuth login. Set an API key instead: kageko auth set ${provider}`);
		}
		const print = (line: string) => (io.output ?? process.stdout).write(`${line}\n`);
		const rl = createInterface({ input: io.input ?? process.stdin, output: io.output ?? process.stdout });
		// A pending rl.question never settles when stdin ends (e.g. </dev/null on a
		// headless box); track close so prompts resolve undefined instead of hanging.
		let inputClosed = false;
		rl.on("close", () => {
			inputClosed = true;
		});
		try {
			await application.loginOAuth(provider, undefined, {
				notify: (event) => printLoginEvent(print, event),
				prompt: (definition) => askLoginPrompt(rl, print, () => inputClosed, definition),
			});
		} finally {
			rl.close();
		}
		print(`OAuth login complete for ${provider}.`);
		return;
	}
	throw new Error(`Unknown auth command: ${action}`);
}

function printLine(value: string): void {
	process.stdout.write(`${value}\n`);
}

function printLoginEvent(print: (line: string) => void, event: OAuthLoginEvent): void {
	if (event.type === "device_code") {
		print(`Open ${event.verificationUri} and enter code: ${event.userCode}`);
		if (event.expiresInSeconds !== undefined) print(`The code expires in ${event.expiresInSeconds} seconds.`);
		return;
	}
	if (event.type === "auth_url") {
		print(`Open this URL to authenticate: ${event.url}`);
		if (event.instructions !== undefined) print(event.instructions);
		return;
	}
	process.stderr.write(`${event.message}\n`);
}

function askLoginPrompt(
	rl: Interface,
	print: (line: string) => void,
	isInputClosed: () => boolean,
	definition: OAuthPrompt,
): Promise<string | undefined> {
	if (isInputClosed()) return Promise.resolve(undefined);
	const options = definition.options;
	if (options !== undefined && options.length > 0) {
		print(definition.message);
		options.forEach((option, index) => {
			print(`  ${index + 1}) ${option.label}${option.description !== undefined ? ` — ${option.description}` : ""}`);
		});
		return askQuestion(rl, isInputClosed, "Enter a number or id: ", (answer) => {
			const trimmed = answer.trim();
			const byId = options.find((option) => option.id === trimmed);
			if (byId !== undefined) return byId.id;
			const index = Number.parseInt(trimmed, 10);
			if (Number.isInteger(index) && index >= 1 && index <= options.length) return options[index - 1]!.id;
			return trimmed === "" ? undefined : trimmed;
		});
	}
	return askQuestion(
		rl,
		isInputClosed,
		`${definition.message}${definition.placeholder !== undefined ? ` (${definition.placeholder})` : ""}: `,
		(answer) => (answer.trim() === "" ? undefined : answer.trim()),
	);
}

/** Resolves undefined when stdin closes mid-question so piped/EOF input aborts the login instead of hanging. */
function askQuestion(
	rl: Interface,
	isInputClosed: () => boolean,
	query: string,
	interpret: (answer: string) => string | undefined,
): Promise<string | undefined> {
	if (isInputClosed()) return Promise.resolve(undefined);
	return new Promise((resolve) => {
		const onClose = () => resolve(undefined);
		rl.once("close", onClose);
		rl.question(query, (answer) => {
			rl.removeListener("close", onClose);
			resolve(interpret(answer));
		});
	});
}

function exactlyOne(values: readonly string[], usage: string): string {
	if (values.length !== 1) throw new Error(usage);
	return values[0]!;
}

function printUsage(): void {
	printLine("Usage: kageko auth <status|set|remove|login> <provider>");
}
