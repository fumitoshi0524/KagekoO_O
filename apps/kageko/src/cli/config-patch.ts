/**
 * Builds a nested config patch from a dotted key, rejecting segments that are
 * not safe identifiers (guards against `__proto__`/`constructor`/`prototype`
 * pollution and malformed keys like `a..b`). Shared by the CLI and TUI
 * `/config set` paths.
 */
export function buildConfigPatch(key: string, value: unknown): Record<string, unknown> {
	const segments = key.split(".");
	if (
		!segments.length ||
		segments.some(
			(segment) =>
				!/^[A-Za-z][A-Za-z0-9]*$/.test(segment) || ["__proto__", "constructor", "prototype"].includes(segment),
		)
	) {
		throw new Error("config key must be a safe dotted identifier");
	}
	const root: Record<string, unknown> = {};
	let target = root;
	for (const segment of segments.slice(0, -1)) {
		const child: Record<string, unknown> = {};
		target[segment] = child;
		target = child;
	}
	target[segments.at(-1)!] = value;
	return root;
}
