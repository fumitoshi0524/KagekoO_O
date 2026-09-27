import { spawnSync } from "node:child_process";
import type { ParsedCommand } from "./types.js";

const PARSER_SCRIPT = String.raw`
$source = [Console]::In.ReadToEnd()
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput($source, [ref]$tokens, [ref]$errors)
$commands = @($ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.CommandAst] }, $true) | ForEach-Object {
  $name = $_.GetCommandName()
  [pscustomobject]@{
    name = $name
    text = $_.Extent.Text
    arguments = @($_.CommandElements | Select-Object -Skip 1 | ForEach-Object { $_.Extent.Text })
    dynamic = ($null -eq $name) -or ($_.InvocationOperator -ne [System.Management.Automation.Language.TokenKind]::Unknown)
  }
})
[pscustomobject]@{ commands = $commands; errors = @($errors | ForEach-Object { $_.Message }) } | ConvertTo-Json -Compress -Depth 6
`;

type ParseResult = { commands: ParsedCommand[]; hasErrors: boolean; unavailable?: string };
const MAX_CACHE_ENTRIES = 128;
const MAX_EXTERNAL_PARSE_MS = 250;
const parseCache = new Map<string, ParseResult>();

export function parsePowerShell(source: string, executable = "pwsh"): ParseResult {
	const cacheKey = `${executable}\0${source}`;
	const cached = parseCache.get(cacheKey);
	if (cached) {
		parseCache.delete(cacheKey);
		parseCache.set(cacheKey, cached);
		return cloneResult(cached);
	}
	const simple = parseSimpleCommand(source);
	if (simple) return remember(cacheKey, simple);
	const result = spawnSync(executable, ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", PARSER_SCRIPT], {
		input: source,
		encoding: "utf8",
		windowsHide: true,
		// Permission evaluation is latency-sensitive and synchronous today. Keep
		// the external parser strictly bounded; a timeout becomes opaque and is
		// denied/asked by policy rather than blocking the event loop for seconds.
		timeout: MAX_EXTERNAL_PARSE_MS,
		maxBuffer: 1024 * 1024,
	});
	if (result.error || result.status !== 0) {
		return remember(cacheKey, {
			commands: [],
			hasErrors: true,
			unavailable: result.error?.message ?? result.stderr.trim(),
		});
	}
	try {
		const parsed = JSON.parse(result.stdout) as { commands?: ParsedCommand | ParsedCommand[]; errors?: string[] };
		const commands = parsed.commands ? (Array.isArray(parsed.commands) ? parsed.commands : [parsed.commands]) : [];
		return remember(cacheKey, { commands, hasErrors: Boolean(parsed.errors?.length) });
	} catch (error) {
		return remember(cacheKey, {
			commands: [],
			hasErrors: true,
			unavailable: `PowerShell parser returned invalid JSON: ${(error as Error).message}`,
		});
	}
}

/**
 * Avoid starting a full PowerShell process for the overwhelmingly common
 * single-command form. Compound syntax still goes through Microsoft's AST
 * parser below; dynamic tokens remain marked so the analyzer fails closed.
 */
function parseSimpleCommand(source: string): ParseResult | undefined {
	const tokens: string[] = [];
	let token = "";
	let quote: '"' | "'" | undefined;
	let escaped = false;
	for (const character of source.trim()) {
		if (escaped) {
			token += character;
			escaped = false;
			continue;
		}
		if (quote === '"' && character === "`") {
			token += character;
			escaped = true;
			continue;
		}
		if (quote) {
			token += character;
			if (character === quote) quote = undefined;
			continue;
		}
		if (character === '"' || character === "'") {
			quote = character;
			token += character;
			continue;
		}
		if (/[|;&(){}<>]/.test(character)) return undefined;
		if (/\s/.test(character)) {
			if (token) {
				tokens.push(token);
				token = "";
			}
			continue;
		}
		token += character;
	}
	if (quote || escaped) return undefined;
	if (token) tokens.push(token);
	if (tokens.length === 0) return undefined;
	return {
		commands: [
			{
				name: tokens[0],
				text: source.trim(),
				arguments: tokens.slice(1),
				dynamic: tokens.some((value) => /[$`]/.test(value)),
			},
		],
		hasErrors: false,
	};
}

function remember(key: string, result: ParseResult): ParseResult {
	parseCache.set(key, result);
	while (parseCache.size > MAX_CACHE_ENTRIES) {
		const oldest = parseCache.keys().next().value as string | undefined;
		if (oldest === undefined) break;
		parseCache.delete(oldest);
	}
	return cloneResult(result);
}

function cloneResult(result: ParseResult): ParseResult {
	return {
		...result,
		commands: result.commands.map((command) => ({ ...command, arguments: [...command.arguments] })),
	};
}
