const SENSITIVE_ENV_KEY =
	/(?:^|_)(?:API[_-]?KEY|ACCESS[_-]?KEY|KEY|JWT|SESSION|AUTH(?:ORIZATION)?|TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE[_-]?KEY|CLIENT[_-]?SECRET|COOKIE|CREDENTIALS?|DATABASE[_-]?URL|DB[_-]?URL|CONNECTION[_-]?STRING)(?:$|_)/i;

const SAFE_INHERITED_KEYS = new Set([
	"ALL_PROXY",
	"APPDATA",
	"COMSPEC",
	"HOMEDRIVE",
	"HOMEPATH",
	"HOME",
	"LANG",
	"LOCALAPPDATA",
	"LOGNAME",
	"NO_PROXY",
	"PATH",
	"PATHEXT",
	"PROCESSOR_ARCHITECTURE",
	"PROGRAMFILES",
	"SHELL",
	"SYSTEMDRIVE",
	"SYSTEMROOT",
	"TEMP",
	"TMP",
	"USER",
	"USERNAME",
	"USERPROFILE",
	"WINDIR",
	"HTTP_PROXY",
	"HTTPS_PROXY",
]);

export interface EnvironmentScrubOptions {
	allowSensitive?: boolean;
}

/** Return whether an environment variable name commonly carries a secret. */
export function isSensitiveEnvironmentKey(name: string): boolean {
	return name === "NODE_OPTIONS" || name === "NODE_PATH" || SENSITIVE_ENV_KEY.test(name);
}

/** Remove ambient credentials and Node injection variables from a child environment. */
export function scrubEnvironment(
	environment: Record<string, string | undefined>,
	{ allowSensitive = false }: EnvironmentScrubOptions = {},
): Record<string, string> {
	const result: Record<string, string> = {};
	for (const [name, value] of Object.entries(environment)) {
		if (value === undefined || name.includes("\0") || value.includes("\0") || value.startsWith("()")) continue;
		if (!allowSensitive && isSensitiveEnvironmentKey(name)) continue;
		result[name] = value;
	}
	return result;
}

/** Build a minimal inherited environment for supervisor-owned children. */
export function safeInheritedEnvironment(
	environment: Record<string, string | undefined>,
	options: EnvironmentScrubOptions = {},
): Record<string, string> {
	const scrubbed = scrubEnvironment(environment, options);
	return Object.fromEntries(
		Object.entries(scrubbed).filter(([name]) => {
			const upper = name.toUpperCase();
			return SAFE_INHERITED_KEYS.has(upper) || upper.startsWith("LC_") || upper.startsWith("KAGEKO_");
		}),
	);
}
