import { formatStartupError } from "../cli/startup-error.js";

/**
 * Bound on a single application close before the CLI gives up waiting.
 *
 * A normal close drains the resident learning graph. Capability code generation
 * is bounded at 120 seconds, after which the remaining stores and process
 * resources still need a small grace period to commit. A
 * shorter outer timeout can kill valid learning work after it has already
 * produced side effects but before the durable queue is acknowledged.
 */
export const SHUTDOWN_TIMEOUT_MS = 150_000;
/** Grace period after cleanup before the unref'd backstop force-exits. */
export const FORCE_EXIT_GRACE_MS = 5_000;

/** Minimal process surface the shutdown lifecycle needs (injectable for tests). */
export interface ShutdownProcess {
	exitCode: number | string | null | undefined;
	readonly platform: string;
	on(signal: NodeJS.Signals, listener: (signal: NodeJS.Signals) => void): unknown;
	off(signal: NodeJS.Signals, listener: (signal: NodeJS.Signals) => void): unknown;
	exit(code: number): void;
	stderr: { write(chunk: string): unknown };
}

export interface ShutdownController {
	/** Idempotent bounded cleanup; an optional signal maps to its exit code. */
	cleanup(signal?: NodeJS.Signals): Promise<void>;
	/** Removes the signal handlers (normal exit path). */
	dispose(): void;
}

/**
 * Installs the CLI shutdown lifecycle around `close`:
 *  - the close is raced against a timeout so a wedged shutdown step cannot
 *    keep a finished run alive forever; the overrun is reported and the exit
 *    path continues (the close keeps running in the background),
 *  - an unref'd force-exit backstop is armed once cleanup settles, so only a
 *    genuinely wedged event loop is killed and the timer itself never keeps
 *    the process alive,
 *  - a second SIGINT means the user is done waiting and exits immediately
 *    with code 130.
 */
export function installShutdown(close: () => Promise<void>, proc: ShutdownProcess = process): ShutdownController {
	let closing: Promise<void> | undefined;
	let forceExit: NodeJS.Timeout | undefined;
	let sigintReceived = false;

	const armForceExit = (): void => {
		if (forceExit) return;
		// The exit code is read lazily at fire time so callers may still set
		// process.exitCode after cleanup finished.
		forceExit = setTimeout(() => {
			proc.exit(typeof proc.exitCode === "number" ? proc.exitCode : 0);
		}, FORCE_EXIT_GRACE_MS);
		forceExit.unref?.();
	};

	const cleanup = async (signal?: NodeJS.Signals): Promise<void> => {
		closing ??= (async () => {
			let timer: NodeJS.Timeout | undefined;
			try {
				await Promise.race([
					close(),
					new Promise<never>((_, reject) => {
						timer = setTimeout(
							() => reject(new Error(`Application shutdown timed out after ${String(SHUTDOWN_TIMEOUT_MS)}ms`)),
							SHUTDOWN_TIMEOUT_MS,
						);
						timer.unref?.();
					}),
				]);
			} catch (error) {
				// A failed or timed-out close must not hang the exit: report it and
				// leave the force-exit backstop to cover any straggling work.
				proc.stderr.write(`${formatStartupError(error)}\n`);
				proc.exitCode ??= 1;
			} finally {
				if (timer) clearTimeout(timer);
			}
		})();
		try {
			await closing;
		} finally {
			if (signal) proc.exitCode ??= signal === "SIGINT" ? 130 : 143;
			armForceExit();
		}
	};

	const onSignal = (signal: NodeJS.Signals): void => {
		if (signal === "SIGINT") {
			if (sigintReceived) {
				proc.exit(130);
				return;
			}
			sigintReceived = true;
		}
		void cleanup(signal);
	};

	proc.on("SIGINT", onSignal);
	proc.on("SIGTERM", onSignal);
	if (proc.platform === "win32") proc.on("SIGBREAK", onSignal);

	return {
		cleanup,
		dispose() {
			proc.off("SIGINT", onSignal);
			proc.off("SIGTERM", onSignal);
			if (proc.platform === "win32") proc.off("SIGBREAK", onSignal);
			if (forceExit) {
				clearTimeout(forceExit);
				forceExit = undefined;
			}
		},
	};
}
