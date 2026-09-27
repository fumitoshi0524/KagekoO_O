import { Command, Option } from "commander";

export interface CLIOptions {
	provider?: string;
	model?: string;
	permission?: "manual" | "workspace" | "unrestricted";
	interaction?: "interactive" | "unattended";
	prompt?: string;
	sessionId?: string;
	resumePicker?: boolean;
	continue?: boolean;
	cwd?: string;
	output?: "text" | "json" | "stream-json";
	resumeOnCheckpoint?: boolean;
	help?: boolean;
}

/** Strict Commander parser used by both the bare command and `kageko prompt`. */
export function parseCliOptions(argv: readonly string[]): CLIOptions {
	const { values, positionals } = parseWithCommander(argv, false);
	if (positionals.length) throw new Error(`Unexpected argument: ${positionals[0]}`);
	return validateOptions(toOptions(values));
}

export function parsePromptOptions(argv: readonly string[]): {
	readonly options: CLIOptions;
	readonly positionals: readonly string[];
} {
	const { values, positionals } = parseWithCommander(argv, true);
	return { options: validateOptions(toOptions(values), true), positionals };
}

function parseWithCommander(
	argv: readonly string[],
	allowPositionals: boolean,
): { readonly values: Record<string, unknown>; readonly positionals: readonly string[] } {
	const program = new Command("kageko")
		.exitOverride()
		.allowUnknownOption(false)
		.allowExcessArguments(allowPositionals)
		.configureOutput({ writeOut: () => {}, writeErr: () => {} })
		.addOption(new Option("-p, --prompt <text>", "Run one prompt non-interactively"))
		.addOption(new Option("-r, --resume [id]", "Resume a session; without id open the session picker"))
		.option("-c, --continue", "Continue the latest workspace session")
		.option("--session <id>", "Compatibility alias for --resume <id>")
		.option("--provider <id>")
		.option("--model <id>")
		.addOption(new Option("--permission <profile>").choices(["manual", "workspace", "unrestricted"]))
		.addOption(new Option("--interaction <mode>").choices(["interactive", "unattended"]))
		.option("--cwd <path>")
		.addOption(new Option("--output <format>").choices(["text", "json", "stream-json"]))
		.option("--resume-on-checkpoint", "Automatically resume only a checkpointed execution slice")
		.option("-h, --help", "Show help");
	if (allowPositionals) program.argument("[text...]");
	try {
		program.parse([...argv], { from: "user" });
	} catch (error) {
		throw new Error(normalizeCommanderError(error, argv));
	}
	return { values: program.opts<Record<string, unknown>>(), positionals: [...program.args] };
}

function toOptions(values: Record<string, unknown>): CLIOptions {
	const resume = values["resume"];
	const alias = values["session"];
	const prompt = nonEmptyString(values["prompt"], "--prompt");
	const provider = nonEmptyString(values["provider"], "--provider");
	const model = nonEmptyString(values["model"], "--model");
	const cwd = nonEmptyString(values["cwd"], "--cwd");
	const resumeId = typeof resume === "string" ? nonEmptyString(resume, "--resume") : undefined;
	const sessionId = typeof alias === "string" ? nonEmptyString(alias, "--session") : undefined;
	if (resumeId !== undefined && sessionId !== undefined && resumeId !== sessionId)
		throw new Error("--resume and --session must identify the same session");
	if (resume === true && sessionId !== undefined)
		throw new Error("--resume without an id cannot be combined with --session");
	if (values["continue"] === true && (resumeId !== undefined || sessionId !== undefined))
		throw new Error("--continue cannot be combined with --resume");
	return {
		...(prompt !== undefined ? { prompt } : {}),
		...(provider !== undefined ? { provider } : {}),
		...(model !== undefined ? { model } : {}),
		...(values["permission"] ? { permission: values["permission"] as CLIOptions["permission"] } : {}),
		...(values["interaction"] ? { interaction: values["interaction"] as CLIOptions["interaction"] } : {}),
		...((resumeId ?? sessionId) ? { sessionId: resumeId ?? sessionId } : {}),
		...(resume === true ? { resumePicker: true } : {}),
		...(values["continue"] === true ? { continue: true } : {}),
		...(cwd !== undefined ? { cwd } : {}),
		...(values["output"] ? { output: values["output"] as CLIOptions["output"] } : {}),
		...(values["resumeOnCheckpoint"] === true ? { resumeOnCheckpoint: true } : {}),
		...(values["help"] === true ? { help: true } : {}),
	};
}

function validateOptions(options: CLIOptions, explicitPromptCommand = false): CLIOptions {
	const promptMode = explicitPromptCommand || options.prompt !== undefined;
	if (!promptMode && options.output !== undefined) throw new Error("--output is only supported in prompt mode");
	if (promptMode && options.resumePicker) throw new Error("--resume requires a session id in prompt mode");
	if (promptMode && options.continue) throw new Error("--continue is only supported in interactive mode");
	return options;
}

function normalizeCommanderError(error: unknown, argv: readonly string[]): string {
	const message = error instanceof Error ? error.message : String(error);
	const missing = argv.findLast((value) => value.startsWith("-"));
	if (message.includes("argument missing") && missing) return `${missing} requires a value`;
	const unknown = /unknown option '([^']+)'/.exec(message)?.[1];
	if (unknown) return `Unknown flag: ${unknown}`;
	if (message.includes("too many arguments")) {
		const positional = argv.find((value) => !value.startsWith("-"));
		if (positional) return `Unexpected argument: ${positional}`;
	}
	return message.replace(/^error:\s*/, "");
}

function nonEmptyString(value: unknown, flag: string): string | undefined {
	if (value === undefined) return undefined;
	if (typeof value !== "string" || value.trim().length === 0) throw new Error(`${flag} requires a non-empty value`);
	return value;
}
