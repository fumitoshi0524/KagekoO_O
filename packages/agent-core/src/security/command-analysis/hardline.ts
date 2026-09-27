import type { ExecutionEnvironment, ParsedCommand } from "./types.js";

interface HardlineRule {
	id: string;
	description: string;
	patterns: readonly RegExp[];
	/** Executable names that must be present before command-text patterns are considered. */
	commandNames?: readonly string[];
	/** Syntax-only patterns, such as fork bombs or raw-device redirection. */
	unscopedPatterns?: readonly RegExp[];
}

const RULES: readonly HardlineRule[] = [
	{
		id: "filesystem.root-destruction",
		description: "recursive destruction of a filesystem root, system directory, or entire home directory",
		patterns: [
			/\brm\s+(?:-[^\s]*\s+)*(?:\/|\/\*|\/home(?:\/\*)?|\/root(?:\/\*)?|\/etc(?:\/\*)?|\/usr(?:\/\*)?|\/var(?:\/\*)?|\/bin(?:\/\*)?|\/sbin(?:\/\*)?|\/boot(?:\/\*)?|~|\$HOME)(?:\s|$)/i,
			/\b(?:Remove-Item|del|erase|rd|rmdir)\b[^\r\n]*(?:[A-Za-z]:\\(?:\*\s*)?$|\$HOME(?:\\\*)?\s*$|\$env:(?:USERPROFILE|SystemRoot)(?:\\\*)?\s*$)/i,
			/\bfind\s+(?:\/|\/home|\/root|\/etc|\/usr|\/var)(?:\s|$)[^\r\n]*(?:-delete|-exec\s+(?:rm|shred)\b)/i,
			/(?:[A-Za-z]:\\(?:\*)?|\$env:(?:SystemDrive|SystemRoot|USERPROFILE))[^\r\n|]*\|\s*(?:Remove-Item|ri|rm)\b[^\r\n]*(?:-Recurse|-r\b)/i,
		],
		commandNames: ["rm", "remove-item", "del", "erase", "rd", "rmdir", "find", "ri"],
	},
	{
		id: "storage.format-or-raw-write",
		description: "filesystem formatting, partition-table modification, or raw device overwrite",
		patterns: [
			/\b(?:mkfs(?:\.[a-z0-9]+)?|fdisk|parted)\b/i,
			/\bdd\b[^\r\n]*\bof=\/dev\/(?:sd|nvme|hd|mmcblk|vd|xvd)/i,
			/\bformat(?:\.com)?\s+[A-Za-z]:/i,
			/\b(?:Clear-Disk|Initialize-Disk|Remove-Partition|Format-Volume)\b/i,
			/\\\.\\PhysicalDrive\d+/i,
		],
		commandNames: [
			"mkfs",
			"fdisk",
			"parted",
			"dd",
			"format",
			"format.com",
			"clear-disk",
			"initialize-disk",
			"remove-partition",
			"format-volume",
		],
		unscopedPatterns: [/>\s*\/dev\/(?:sd|nvme|hd|mmcblk|vd|xvd)/i],
	},
	{
		id: "host.shutdown",
		description: "shutdown, reboot, halt, or boot-configuration destruction",
		patterns: [
			/(?:^|[;&|\n`] |\$\()\s*(?:(?:sudo|env|exec|nohup|setsid|time)\s+)*(?:shutdown|reboot|halt|poweroff)\b/i,
			/(?:^|[;&|\n])\s*(?:systemctl\s+(?:poweroff|reboot|halt|kexec)|init\s+[06]|telinit\s+[06])\b/i,
			/\bshutdown(?:\.exe)?\s+\/(?:s|r)\b/i,
			/\b(?:Stop-Computer|Restart-Computer)\b/i,
			/\bbcdedit\b[^\r\n]*\/(?:delete|deletevalue|set)\b/i,
		],
		commandNames: [
			"sudo",
			"shutdown",
			"shutdown.exe",
			"reboot",
			"halt",
			"poweroff",
			"systemctl",
			"init",
			"telinit",
			"stop-computer",
			"restart-computer",
			"bcdedit",
		],
	},
	{
		id: "host.denial-of-service",
		description: "fork bomb or command that targets every host process",
		patterns: [/\bkill\s+(?:-[^\s]+\s+)*-1\b/i, /\b(?:Stop-Process|taskkill)\b[^\r\n]*(?:-Name\s+\*|\/IM\s+\*)/i],
		commandNames: ["kill", "pkill", "killall", "taskkill", "stop-process"],
		unscopedPatterns: [/\:\(\)\s*\{\s*\:\s*\|\s*\:\s*&\s*\}\s*;\s*:/],
	},
	{
		id: "privilege.password-guessing",
		description: "password injection or guessing through a privilege-escalation command",
		patterns: [/(?:^|[;&|`\n]|\$\()\s*sudo\s+-S\b/i],
		commandNames: ["sudo"],
	},
	{
		id: "kageko.self-destruction",
		description: "destruction of Kageko supervisor, authorization state, or audit records",
		patterns: [
			/\b(?:pkill|killall|taskkill|Stop-Process)\b[^\r\n]*\b(?:kageko|kageko-supervisor)\b/i,
			/\b(?:rm|Remove-Item|del|erase)\b[^\r\n]*(?:\.kageko[\\/](?:trust|audit|runtime)|workspace-trust\.json)/i,
		],
		commandNames: ["pkill", "killall", "taskkill", "stop-process", "rm", "remove-item", "del", "erase"],
	},
];

export function detectHardline(
	command: string,
	environment: ExecutionEnvironment,
	parsedCommands: readonly ParsedCommand[] = [],
): HardlineRule | undefined {
	if (!canAffectHost(environment)) return undefined;
	const normalized = unquoteArguments(command.normalize("NFKC").replace(/\\\r?\n/g, " "));
	const commandNames = new Set(
		parsedCommands
			.map((parsed) => parsed.name?.replace(/^['"]|['"]$/g, "").toLowerCase())
			.filter((name): name is string => Boolean(name)),
	);
	if (commandNames.size === 0) {
		for (const match of normalized
			.replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, "")
			.matchAll(/(?:^|[;&|])\s*([^\s;&|]+)/g)) {
			const token = match[1]?.replace(/^['"]|['"]$/g, "").toLowerCase();
			if (token) commandNames.add(token);
		}
	}
	return RULES.find((rule) => {
		if (rule.unscopedPatterns?.some((pattern) => pattern.test(normalized))) return true;
		if (
			rule.commandNames &&
			!rule.commandNames.some((name) =>
				[...commandNames].some((commandName) => commandName === name || commandName.startsWith(`${name}.`)),
			)
		)
			return false;
		return rule.patterns.some((pattern) => pattern.test(normalized));
	});
}

/**
 * Hardline patterns describe argument values, not shell quoting syntax. Keep
 * quoted content while removing only its delimiters so `rm -rf "/"` is
 * treated exactly like `rm -rf /`. Command-name discovery below still masks
 * quoted arguments, preventing text passed to `echo` from becoming a command.
 */
function unquoteArguments(source: string): string {
	let result = "";
	let quote: '"' | "'" | undefined;
	let escaped = false;
	for (const character of source) {
		if (escaped) {
			result += character;
			escaped = false;
			continue;
		}
		if (quote === '"' && character === "\\") {
			escaped = true;
			continue;
		}
		if (quote) {
			if (character === quote) quote = undefined;
			else result += character;
			continue;
		}
		if (character === '"' || character === "'") {
			quote = character;
			continue;
		}
		result += character;
	}
	return result;
}

function canAffectHost(environment: ExecutionEnvironment): boolean {
	return (
		environment.kind === "local" ||
		environment.kind === "ssh" ||
		environment.hostReachable ||
		environment.privileged ||
		environment.hasHostMounts
	);
}
