import { rename } from "node:fs/promises";

const DEFAULT_ATTEMPTS = 20;
const MAX_DELAY_MS = 250;
const TRANSIENT_REPLACE_ERRORS = new Set(["EACCES", "EBUSY", "EPERM"]);

export interface TransientFileRetryOptions {
	readonly attempts?: number;
	readonly sleep?: (delayMs: number) => Promise<void>;
}

export interface AtomicReplaceOptions extends TransientFileRetryOptions {
	readonly renameFile?: (source: string, destination: string) => Promise<void>;
}

/** Retry a bounded transient filesystem operation, primarily for Windows sharing races. */
export async function retryTransientFileOperation<T>(
	operation: () => Promise<T>,
	options: TransientFileRetryOptions = {},
): Promise<T> {
	const attempts = options.attempts ?? DEFAULT_ATTEMPTS;
	if (!Number.isSafeInteger(attempts) || attempts < 1) throw new RangeError("File retry attempts must be positive");
	const sleep = options.sleep ?? ((delayMs: number) => new Promise<void>((resolve) => setTimeout(resolve, delayMs)));
	for (let attempt = 0; attempt < attempts; attempt += 1) {
		try {
			return await operation();
		} catch (error) {
			const code = (error as NodeJS.ErrnoException).code;
			if (!TRANSIENT_REPLACE_ERRORS.has(code ?? "") || attempt === attempts - 1) throw error;
			await sleep(Math.min(25 * (attempt + 1), MAX_DELAY_MS));
		}
	}
	throw new Error("Unreachable transient file retry state");
}

/** Retry only transient Windows sharing errors while preserving atomic rename publication. */
export async function replaceAtomically(
	temporary: string,
	destination: string,
	options: AtomicReplaceOptions = {},
): Promise<void> {
	const renameFile = options.renameFile ?? rename;
	await retryTransientFileOperation(() => renameFile(temporary, destination), options);
}
