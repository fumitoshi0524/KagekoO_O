// safe-regex has no bundled declaration; its runtime API is a boolean predicate.
// @ts-expect-error The dependency intentionally ships JavaScript only.
import isSafeRegex from "safe-regex";

const MAX_PATTERN_LENGTH = 500;

/**
 * Test a regex source against a value, but only if the source is statically
 * determined to be ReDoS-safe by `safe-regex`. Unsafe patterns are treated as
 * non-matching and a warning is logged.
 */
export function safeRegexTest(source: string, value: string, { flags = "" }: { flags?: string } = {}): boolean {
	if (!isSafeRegexSource(source)) {
		return false;
	}
	try {
		return new RegExp(source, flags).test(value);
	} catch {
		return false;
	}
}

/**
 * Return a RegExp for a safe source, or undefined if the source is unsafe or
 * invalid. Unlike `safeRegexTest`, this returns the regex object for callers
 * that need to reuse it (e.g. per-line matching in a loop).
 */
export function compileSafeRegex(source: string, flags = ""): RegExp | undefined {
	if (!isSafeRegexSource(source)) {
		return undefined;
	}
	try {
		return new RegExp(source, flags);
	} catch {
		return undefined;
	}
}

export function isSafeRegexSource(source: string): boolean {
	if (typeof source !== "string" || source.length === 0) return false;
	if (source.length > MAX_PATTERN_LENGTH) return false;
	return isSafeRegex(source);
}

/**
 * Compile a regex produced by {@link globToRegex}. Glob-generated patterns are
 * structurally safe (no nested quantifiers over overlapping character classes),
 * so this bypasses safe-regex which would otherwise conservatively reject
 * globstar patterns like a double-star glob.
 */
export function compileGlobRegex(source: string, flags = ""): RegExp | undefined {
	if (typeof source !== "string" || source.length === 0 || source.length > MAX_PATTERN_LENGTH) {
		return undefined;
	}
	try {
		return new RegExp(source, flags);
	} catch {
		return undefined;
	}
}

/**
 * Test whether a value matches a glob pattern. Globstar patterns are supported.
 */
export function safeGlobTest(pattern: string, value: string): boolean {
	const regex = compileGlobRegex(`^${globToRegex(pattern)}$`);
	if (!regex) return false;
	return regex.test(value);
}

/**
 * Convert a glob pattern to a regex source string. The result is NOT checked
 * for ReDoS safety — callers must pass it through `safeRegex` or
 * `safeRegexTest` before compiling it.
 *
 * Supports star, question, and globstar wildcards with standard glob semantics.
 */
export function globToRegex(pattern: string): string {
	if (typeof pattern !== "string") return "";
	const parts = pattern.split("/");
	const segments = parts.map((part) => ({
		globstar: part === "**",
		source:
			part === "**"
				? ""
				: part
						.replace(/[.+^${}()|[\]\\]/g, "\\$&")
						.replace(/\*/g, "[^\\/]*")
						.replace(/\?/g, "[^\\/]"),
	}));

	// Collapse consecutive globstars.
	const collapsed: { globstar: boolean; source: string }[] = [];
	for (const seg of segments) {
		if (seg.globstar && collapsed.length > 0 && collapsed[collapsed.length - 1]?.globstar) continue;
		collapsed.push(seg);
	}

	if (collapsed.length === 1 && collapsed[0]?.globstar) {
		return ".*";
	}

	const out: string[] = [];
	for (let i = 0; i < collapsed.length; i++) {
		const seg = collapsed[i];
		if (!seg) continue;
		if (seg.globstar) {
			const isFirst = i === 0;
			const isLast = i === collapsed.length - 1;
			if (isFirst) {
				out.push("(?:[^\\/]+\\/)*");
			} else if (isLast) {
				out.push("(?:\\/[^\\/]+)*");
			} else {
				out.push("(?:\\/[^\\/]+)*\\/");
			}
		} else {
			if (i > 0 && !collapsed[i - 1]?.globstar) {
				out.push("/");
			}
			out.push(seg.source);
		}
	}
	return out.join("");
}
