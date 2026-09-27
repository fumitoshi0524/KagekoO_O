import { parsePromptOptions, type CLIOptions } from "../options.js";

/** Parse the explicit `kageko prompt` command without accepting loose input. */
export function parsePromptCommandOptions(argv: readonly string[]): CLIOptions {
	const { options: flags, positionals } = parsePromptOptions(argv);
	if (flags.prompt && positionals.length)
		throw new Error("Prompt may be supplied either positionally or with --prompt, not both");
	const prompt = flags.prompt ?? positionals.join(" ");
	if (!prompt.trim()) throw new Error("prompt requires non-empty text");
	return { ...flags, prompt };
}
