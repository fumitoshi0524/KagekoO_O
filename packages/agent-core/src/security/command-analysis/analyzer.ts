import * as path from "node:path";
import * as os from "node:os";
import type { ToolAccess } from "../../tools/types.js";
import { parseBash } from "./bash.js";
import { detectHardline } from "./hardline.js";
import { parsePowerShell } from "./powershell.js";
import type {
	CommandAnalysis,
	CommandAnalysisOptions,
	CommandEffects,
	CommandRisk,
	ExecutionEnvironment,
	ParsedCommand,
} from "./types.js";

const SAFE_READ = new Set([
	"pwd",
	"ls",
	"dir",
	"cat",
	"head",
	"tail",
	"echo",
	"printf",
	"wc",
	"stat",
	"file",
	"which",
	"where",
	"where.exe",
	"grep",
	"rg",
	"findstr",
	"get-location",
	"get-childitem",
	"get-content",
	"select-string",
	"test-path",
]);
const FILE_WRITES = new Set([
	"mkdir",
	"touch",
	"cp",
	"mv",
	"rm",
	"install",
	"new-item",
	"copy-item",
	"move-item",
	"remove-item",
	"set-content",
	"add-content",
	"out-file",
]);
const NETWORK = new Set(["curl", "wget", "invoke-webrequest", "iwr", "invoke-restmethod", "irm"]);
const PACKAGE_MANAGERS = new Set([
	"npm",
	"npx",
	"pnpm",
	"yarn",
	"bun",
	"pip",
	"pip3",
	"uv",
	"cargo",
	"gem",
	"dotnet",
	"nuget",
	"corepack",
]);
const PRIVILEGE = new Set(["sudo", "su", "doas", "runas", "start-process"]);
const PROCESS_CONTROL = new Set([
	"kill",
	"pkill",
	"killall",
	"taskkill",
	"stop-process",
	"stop-service",
	"systemctl",
	"service",
	"sc.exe",
	"sc",
]);

export function analyzeCommand(source: string, options: CommandAnalysisOptions): CommandAnalysis {
	const environment = effectiveEnvironment(options.environment);
	const preflightHardline = detectHardline(source, environment);
	if (preflightHardline && options.dialect === "powershell") {
		return {
			dialect: options.dialect,
			confidence: "partial",
			commands: [],
			accesses: [{ kind: "all" }],
			effects: { ...emptyEffects(), filesystem: "destructive", processes: "system-control" },
			risk: "hardline",
			reasons: [preflightHardline.description],
			hardlineRule: preflightHardline.id,
		};
	}
	const parsed = parseDialect(source, options);
	const hardline = preflightHardline ?? detectHardline(source, environment, parsed.commands);
	const effects = emptyEffects();
	const reasons: string[] = [];
	const accesses: ToolAccess[] = [];
	let unknown = parsed.hasErrors || parsed.unavailable !== undefined || parsed.commands.length === 0;

	if (hardline) {
		return {
			dialect: options.dialect,
			confidence: parsed.unavailable ? "opaque" : parsed.hasErrors ? "partial" : "parsed",
			commands: parsed.commands,
			accesses: [{ kind: "all" }],
			effects: { ...effects, filesystem: "destructive", processes: "system-control" },
			risk: "hardline",
			reasons: [hardline.description],
			hardlineRule: hardline.id,
		};
	}

	for (const command of parsed.commands) {
		const name = normalizeName(command.name);
		if (!name || command.dynamic) unknown = true;
		if (!name) continue;
		accesses.push({ kind: "process", operation: "execute", target: name });
		if (SAFE_READ.has(name)) {
			classifyReadCommand(command, name, options.cwd, effects, accesses, reasons);
			continue;
		}
		if (name === "git") {
			if (!classifyGit(command, effects, reasons)) unknown = true;
			continue;
		}
		if (name === "find") {
			if (!classifyFind(command, options.cwd, effects, accesses, reasons)) unknown = true;
			continue;
		}
		if (FILE_WRITES.has(name)) {
			classifyFileWrite(command, options.cwd, effects, accesses, reasons);
			continue;
		}
		if (NETWORK.has(name)) {
			classifyNetwork(command, source, options.cwd, effects, accesses, reasons);
			continue;
		}
		if (PACKAGE_MANAGERS.has(name)) {
			if (!classifyPackage(command, effects, reasons)) unknown = true;
			continue;
		}
		if (PRIVILEGE.has(name)) {
			effects.privilege = "elevated";
			reasons.push(`${name} requests elevated execution`);
			continue;
		}
		if (PROCESS_CONTROL.has(name)) {
			effects.processes = "system-control";
			reasons.push(`${name} controls host processes or services`);
			continue;
		}
		unknown = true;
	}

	if (/(?:^|[^&])&\s*$|\b(?:Start-Job|Start-Process|nohup|setsid)\b/i.test(source)) {
		effects.processes = "background";
		reasons.push("command starts or detaches a background process");
	}
	if (containsCredentialReference(source)) {
		effects.credentials = containsNetworkTransfer(parsed.commands) ? "export" : "read";
		reasons.push(
			effects.credentials === "export"
				? "command may send credential material externally"
				: "command references credential material",
		);
	}
	classifyShellDataFlow(source, options.cwd, effects, accesses, reasons);
	if (parsed.unavailable) reasons.push(parsed.unavailable);
	if (parsed.hasErrors) reasons.push("shell parser reported syntax errors");
	if (parsed.commands.some((command) => command.dynamic))
		reasons.push("command contains dynamic expansion or invocation");

	const risk = determineRisk(effects, unknown);
	return {
		dialect: options.dialect,
		confidence: parsed.unavailable
			? "opaque"
			: parsed.hasErrors || parsed.commands.some((c) => c.dynamic)
				? "partial"
				: "parsed",
		commands: parsed.commands,
		accesses: risk === "opaque" ? [{ kind: "all" }] : deduplicateAccesses(accesses),
		effects,
		risk,
		reasons: reasons.length
			? [...new Set(reasons)]
			: [risk === "safe" ? "recognized read-only command" : "classified command effects"],
	};
}

function parseDialect(
	source: string,
	options: CommandAnalysisOptions,
): {
	commands: ParsedCommand[];
	hasErrors: boolean;
	unavailable?: string;
} {
	if (options.dialect === "bash") return parseBash(source);
	if (options.dialect === "powershell") return parsePowerShell(source, options.shellExecutable);
	return {
		commands: [],
		hasErrors: false,
		unavailable: "cmd syntax does not have a supported complete parser; authorization fails closed",
	};
}

function classifyGit(command: ParsedCommand, effects: CommandEffects, reasons: string[]): boolean {
	const subcommand = unquote(command.arguments[0] ?? "").toLowerCase();
	if (["status", "diff", "log", "show", "branch", "tag", "remote", "rev-parse", "ls-files"].includes(subcommand)) {
		effects.vcs = "read";
		return true;
	}
	if (["add", "commit", "restore", "checkout", "switch", "merge", "rebase", "stash", "clean"].includes(subcommand)) {
		effects.vcs = ["clean", "rebase"].includes(subcommand) ? "history-rewrite" : "local-write";
		reasons.push(`git ${subcommand} changes local repository state`);
		return true;
	}
	if (subcommand === "reset") {
		effects.vcs = command.text.includes("--hard") ? "history-rewrite" : "local-write";
		reasons.push(`git reset changes local repository state`);
		return true;
	}
	if (["push", "fetch", "pull", "clone"].includes(subcommand)) {
		effects.network = subcommand === "push" ? "write" : "read";
		effects.vcs =
			subcommand === "push"
				? /-f\b|--force(?:-with-lease)?\b/.test(command.text)
					? "history-rewrite"
					: "remote-write"
				: "read";
		reasons.push(`git ${subcommand} accesses a remote repository`);
		return true;
	}
	return false;
}

function classifyFind(
	command: ParsedCommand,
	cwd: string,
	effects: CommandEffects,
	accesses: ToolAccess[],
	reasons: string[],
): boolean {
	const destructive = command.arguments.some((arg) =>
		["-delete", "-exec", "-execdir"].includes(unquote(arg).toLowerCase()),
	);
	if (!destructive) {
		effects.filesystem = maxFileEffect(effects.filesystem, "read");
		return true;
	}
	const root = command.arguments.map(unquote).find(isPlausiblePath);
	if (!root) return false;
	const external = !isInside(cwd, root);
	effects.filesystem = external ? "external-write" : "workspace-write";
	accesses.push({ kind: "file", operation: "write", path: path.resolve(cwd, root), recursive: true });
	reasons.push(`find performs a recursive destructive action ${external ? "outside" : "inside"} the workspace`);
	return true;
}

function classifyReadCommand(
	command: ParsedCommand,
	name: string,
	cwd: string,
	effects: CommandEffects,
	accesses: ToolAccess[],
	reasons: string[],
): void {
	const pathless = new Set(["pwd", "echo", "printf", "which", "where", "where.exe", "get-location"]);
	if (pathless.has(name)) {
		effects.filesystem = maxFileEffect(effects.filesystem, "read");
		return;
	}
	let candidates = command.arguments.map(unquote).filter(isPlausiblePath);
	if (["grep", "rg", "findstr", "select-string"].includes(name)) {
		candidates = candidates.length > 1 ? candidates.slice(1) : [];
	}
	if (candidates.length === 0) {
		effects.filesystem = maxFileEffect(effects.filesystem, "read");
		return;
	}
	let external = false;
	for (const candidate of candidates) {
		const resolved = resolveShellPath(cwd, candidate);
		if (!isResolvedInside(cwd, resolved)) external = true;
		accesses.push({ kind: "file", operation: "read", path: resolved });
	}
	effects.filesystem = maxFileEffect(effects.filesystem, external ? "external-read" : "read");
	if (external) reasons.push("command reads outside the workspace");
}

function classifyFileWrite(
	command: ParsedCommand,
	cwd: string,
	effects: CommandEffects,
	accesses: ToolAccess[],
	reasons: string[],
): void {
	const paths = command.arguments.map(unquote).filter(isPlausiblePath);
	const external = paths.some((candidate) => !isInside(cwd, candidate));
	effects.filesystem = external ? "external-write" : "workspace-write";
	for (const candidate of paths) {
		accesses.push({
			kind: "file",
			operation: "write",
			path: path.resolve(cwd, candidate),
			recursive: /\b(?:rm|remove-item)\b/i.test(command.name ?? ""),
		});
	}
	reasons.push(external ? "command writes outside the workspace" : "command writes inside the workspace");
}

function classifyNetwork(
	command: ParsedCommand,
	source: string,
	cwd: string,
	effects: CommandEffects,
	accesses: ToolAccess[],
	reasons: string[],
): void {
	const remoteExec =
		/(?:curl|wget|iwr|irm|invoke-webrequest|invoke-restmethod)[\s\S]*(?:\|\s*(?:bash|sh|zsh|pwsh|powershell)|\b(?:iex|invoke-expression)\b)/i.test(
			source,
		);
	effects.network = remoteExec
		? "remote-exec"
		: /(?:--data|-d\b|--upload-file|-T\b|-Method\s+(?:POST|PUT|PATCH|DELETE))/i.test(command.text)
			? "write"
			: "read";
	const target = command.arguments.map(unquote).find((arg) => /^https?:\/\//i.test(arg)) ?? "unknown";
	accesses.push({
		kind: "network",
		operation: effects.network === "read" ? "fetch" : "send",
		target,
		method: effects.network === "read" ? "GET" : "UNKNOWN",
		credentialed: containsCredentialReference(source),
		sendsContent: effects.network !== "read",
	});
	classifyNetworkOutput(command, normalizeName(command.name) ?? "", cwd, effects, accesses, reasons);
	reasons.push(remoteExec ? "downloads and directly executes remote content" : `network ${effects.network}`);
}

function classifyNetworkOutput(
	command: ParsedCommand,
	name: string,
	cwd: string,
	effects: CommandEffects,
	accesses: ToolAccess[],
	reasons: string[],
): void {
	const args = command.arguments.map(unquote);
	let output: string | undefined;
	for (let index = 0; index < args.length; index++) {
		const arg = args[index] ?? "";
		if (/^(?:--output|--output-document|--outfile|--out-file|--out-file=)$/i.test(arg)) output = args[index + 1];
		else if (/^(?:--output|--output-document|--outfile|--out-file)=/i.test(arg))
			output = arg.slice(arg.indexOf("=") + 1);
		else if (name === "curl" && arg === "-o") output = args[index + 1];
		else if (name === "wget" && arg === "-O") output = args[index + 1];
		else if (name === "curl" && arg === "-O") {
			const url = args.find((candidate) => /^https?:\/\//i.test(candidate));
			if (url) output = url.slice(url.lastIndexOf("/") + 1) || "downloaded-file";
		}
	}
	if (!output || !isPlausiblePath(output)) return;
	const resolved = resolveShellPath(cwd, output);
	const external = !isResolvedInside(cwd, resolved);
	effects.filesystem = maxFileEffect(effects.filesystem, external ? "external-write" : "workspace-write");
	accesses.push({ kind: "file", operation: "write", path: resolved });
	reasons.push(`network command writes downloaded content ${external ? "outside" : "inside"} the workspace`);
}

function classifyPackage(command: ParsedCommand, effects: CommandEffects, reasons: string[]): boolean {
	const args = command.arguments.map((arg) => unquote(arg).toLowerCase());
	const executable = normalizeName(command.name) ?? "package-command";
	if (executable === "npx" || args.some((arg) => ["exec", "x", "dlx", "runx"].includes(arg))) {
		effects.network = "remote-exec";
		reasons.push("package command downloads or executes package code");
		return true;
	}
	if (args.some((arg) => ["publish", "deploy", "push"].includes(arg))) {
		effects.packages = "publish";
		effects.network = "write";
		reasons.push("package command publishes or deploys externally");
		return true;
	}
	if (args.some((arg) => ["install", "add", "update", "upgrade", "sync"].includes(arg))) {
		effects.packages = "install";
		effects.network = "read";
		reasons.push("package installation downloads code and may run lifecycle scripts");
		return true;
	}
	if (
		args.some((arg) => ["--version", "-v", "list", "ls", "view", "info", "search", "outdated", "audit"].includes(arg))
	) {
		if (args.some((arg) => ["view", "info", "search", "outdated", "audit"].includes(arg))) effects.network = "read";
		return true;
	}
	return false;
}

function classifyShellDataFlow(
	source: string,
	cwd: string,
	effects: CommandEffects,
	accesses: ToolAccess[],
	reasons: string[],
): void {
	const unquoted = maskQuoted(source);
	if (/\|\s*(?:curl|wget|invoke-webrequest|invoke-restmethod|iwr|irm)\b/i.test(unquoted)) {
		effects.network = "write";
		reasons.push("pipeline sends command output to a network client");
		for (const access of accesses) {
			if (access.kind === "network") {
				access.operation = "send";
				access.method = "UNKNOWN";
				access.sendsContent = true;
			}
		}
	}
	const targets = scanRedirectionTargets(source);
	for (const target of targets.filter(isPlausiblePath)) {
		const external = !isInside(cwd, target);
		effects.filesystem = maxFileEffect(effects.filesystem, external ? "external-write" : "workspace-write");
		accesses.push({ kind: "file", operation: "write", path: path.resolve(cwd, target) });
		reasons.push(`shell redirection writes ${external ? "outside" : "inside"} the workspace`);
	}
}

function maskQuoted(source: string): string {
	let quote: '"' | "'" | undefined;
	let escaped = false;
	return [...source]
		.map((character) => {
			if (escaped) {
				escaped = false;
				return quote ? " " : character;
			}
			if (quote && character === "\\" && quote === '"') {
				escaped = true;
				return " ";
			}
			if (quote) {
				if (character === quote) quote = undefined;
				return " ";
			}
			if (character === '"' || character === "'") {
				quote = character;
				return " ";
			}
			return character;
		})
		.join("");
}

function scanRedirectionTargets(source: string): string[] {
	const masked = maskQuoted(source);
	const targets: string[] = [];
	for (let index = 0; index < masked.length; index++) {
		if (masked[index] !== ">" || masked[index - 1] === ">") continue;
		let cursor = index + 1;
		if (masked[cursor] === ">") cursor++;
		while (/\s/.test(source[cursor] ?? "")) cursor++;
		if (source[cursor] === "&") continue;
		while (/\s/.test(source[cursor] ?? "")) cursor++;
		const quote = source[cursor] === '"' || source[cursor] === "'" ? source[cursor] : undefined;
		if (quote) {
			const end = source.indexOf(quote, cursor + 1);
			if (end > cursor) targets.push(unquote(source.slice(cursor, end + 1)));
			index = end > cursor ? end : index;
			continue;
		}
		const start = cursor;
		while (cursor < source.length && !/[\s;&|]/.test(source[cursor] ?? "")) cursor++;
		if (cursor > start) targets.push(unquote(source.slice(start, cursor)));
		index = cursor - 1;
	}
	return targets;
}

function determineRisk(effects: CommandEffects, unknown: boolean): CommandRisk {
	if (
		effects.credentials === "export" ||
		effects.network === "remote-exec" ||
		effects.processes === "system-control" ||
		effects.packages === "publish" ||
		effects.vcs === "history-rewrite" ||
		effects.privilege === "elevated"
	)
		return "dangerous";
	if (unknown) return "opaque";
	if (
		effects.filesystem === "external-read" ||
		effects.filesystem === "external-write" ||
		effects.network === "write" ||
		effects.vcs === "remote-write" ||
		effects.packages === "install"
	)
		return "external";
	if (effects.filesystem === "workspace-write" || effects.vcs === "local-write" || effects.processes === "background")
		return "workspace";
	return "safe";
}

function emptyEffects(): CommandEffects {
	return {
		filesystem: "none",
		network: "none",
		credentials: "none",
		processes: "spawn",
		packages: "none",
		vcs: "none",
		privilege: "normal",
	};
}

function effectiveEnvironment(input: CommandAnalysisOptions["environment"]): ExecutionEnvironment {
	return {
		kind: input?.kind ?? "local",
		hostReachable: input?.hostReachable ?? true,
		privileged: input?.privileged ?? false,
		hasHostMounts: input?.hasHostMounts ?? false,
		hasCredentials: input?.hasCredentials ?? true,
	};
}

function normalizeName(name: string | undefined): string | undefined {
	if (!name) return undefined;
	const unquoted = unquote(name).replaceAll("\\", "/");
	return path.posix
		.basename(unquoted)
		.replace(/\.exe$/i, "")
		.toLowerCase();
}

function unquote(value: string): string {
	return value.replace(/^["']|["']$/g, "");
}

function isPlausiblePath(value: string): boolean {
	return value.length > 0 && !value.startsWith("-") && !/^[a-z][a-z0-9+.-]*:\/\//i.test(value);
}

function isInside(cwd: string, candidate: string): boolean {
	return isResolvedInside(cwd, resolveShellPath(cwd, candidate));
}

function isResolvedInside(cwd: string, resolved: string): boolean {
	const relative = path.relative(path.resolve(cwd), resolved);
	return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function resolveShellPath(cwd: string, candidate: string): string {
	if (candidate === "~") return os.homedir();
	if (candidate.startsWith("~/") || candidate.startsWith("~\\")) return path.resolve(os.homedir(), candidate.slice(2));
	return path.resolve(cwd, candidate);
}

function containsCredentialReference(source: string): boolean {
	return /(?:\.env(?:\.|\b)|\.ssh[\\/]|\.aws[\\/]|\.kube[\\/]|\.npmrc\b|\.netrc\b|api[_-]?key|access[_-]?token|authorization\s*:|\$env:[A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)|\$(?:[A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)))/i.test(
		source,
	);
}

function containsNetworkTransfer(commands: readonly ParsedCommand[]): boolean {
	const transferCommands = new Set([
		"curl",
		"wget",
		"invoke-webrequest",
		"invoke-restmethod",
		"iwr",
		"irm",
		"scp",
		"sftp",
		"ssh",
	]);
	return commands.some((command) => {
		const name = normalizeName(command.name);
		return name !== undefined && transferCommands.has(name);
	});
}

function maxFileEffect(a: CommandEffects["filesystem"], b: CommandEffects["filesystem"]): CommandEffects["filesystem"] {
	const rank = {
		none: 0,
		read: 1,
		"external-read": 2,
		"workspace-write": 3,
		"external-write": 4,
		destructive: 5,
	} as const;
	return rank[a] >= rank[b] ? a : b;
}

function deduplicateAccesses(accesses: ToolAccess[]): ToolAccess[] {
	const seen = new Set<string>();
	return accesses.filter((access) => {
		const key = JSON.stringify(access);
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}
