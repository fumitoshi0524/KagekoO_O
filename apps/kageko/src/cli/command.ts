export const BUILTIN_COMMANDS = new Set([
	"prompt",
	"session",
	"config",
	"auth",
	"plugin",
	"task",
	"cron",
	"capability",
	"memory",
	"learning",
	"goal",
	"skill",
	"mcp",
	"trust",
	"setup",
	"help",
]);

export type BuiltinCommand =
	| "prompt"
	| "session"
	| "config"
	| "auth"
	| "plugin"
	| "task"
	| "cron"
	| "capability"
	| "memory"
	| "learning"
	| "goal"
	| "skill"
	| "mcp"
	| "trust"
	| "setup"
	| "help";

export interface ParsedCommandArguments {
	readonly values: Readonly<Record<string, string | boolean>>;
	readonly positionals: readonly string[];
}

/**
 * Shared strict parser for subcommands.  It deliberately does not guess at
 * unknown flags: a misspelled destructive session command must fail before
 * application startup, as in Kimi and Hermes' top-level command parsers.
 */
export function parseCommandArguments(
	argv: readonly string[],
	valueFlags: readonly string[] = [],
	booleanFlags: readonly string[] = [],
): ParsedCommandArguments {
	const allowedValues = new Set(valueFlags);
	const allowedBooleans = new Set(booleanFlags);
	const values: Record<string, string | boolean> = {};
	const positionals: string[] = [];
	let positionalOnly = false;
	for (let index = 0; index < argv.length; index += 1) {
		const token = argv[index]!;
		if (positionalOnly) {
			positionals.push(token);
			continue;
		}
		if (token === "--") {
			positionalOnly = true;
			continue;
		}
		const [flag = "", inlineValue] = token.split("=", 2);
		if (allowedBooleans.has(flag)) {
			if (inlineValue !== undefined) throw new Error(`${flag} does not take a value`);
			values[flag] = true;
			continue;
		}
		if (allowedValues.has(flag)) {
			const value = inlineValue ?? argv[++index];
			if (value === undefined || value.length === 0 || value.startsWith("-"))
				throw new Error(`${flag} requires a value`);
			values[flag] = value;
			continue;
		}
		if (token.startsWith("-")) throw new Error(`Unknown flag: ${token}`);
		positionals.push(token);
	}
	return { values, positionals };
}
