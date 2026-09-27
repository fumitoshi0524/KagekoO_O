/**
 * Sleep for `ms` milliseconds, rejecting immediately if `signal` is aborted.
 */
export function abortableSleep(ms: number, signal?: AbortSignal): Promise<void> {
	return new Promise((resolve, reject) => {
		if (signal?.aborted) {
			reject(signal.reason ?? new Error("Aborted"));
			return;
		}
		if (!signal) {
			setTimeout(resolve, ms);
			return;
		}
		let timer: NodeJS.Timeout;
		const onAbort = (): void => {
			clearTimeout(timer);
			reject(signal.reason ?? new Error("Aborted"));
		};
		timer = setTimeout(() => {
			signal.removeEventListener("abort", onAbort);
			resolve();
		}, ms);
		signal.addEventListener("abort", onAbort, { once: true });
	});
}

/**
 * Throw if `signal` is already aborted.
 */
export function throwIfAborted(signal?: AbortSignal): void {
	if (signal?.aborted) {
		throw signal.reason ?? new Error("Aborted");
	}
}
