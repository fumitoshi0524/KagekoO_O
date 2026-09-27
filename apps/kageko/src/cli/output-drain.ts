/** Minimal writable shape so the process-exit drain can be tested without a TTY. */
export interface OutputWritable {
	write(chunk: string, callback: (error?: Error | null) => void): boolean;
}

/**
 * Waits until an already-accepted empty write has reached the writable's
 * callback. This is deliberately not a `process.exit()` replacement: Node may
 * still drain naturally, while the CLI can prove that buffered stdout/stderr
 * were given a chance to flush before its shutdown fallback is armed.
 */
export function flushWritable(stream: OutputWritable): Promise<void> {
	return new Promise((resolve, reject) => {
		stream.write("", (error) => (error ? reject(error) : resolve()));
	});
}

export async function flushProcessOutput(
	streams: readonly OutputWritable[] = [process.stdout, process.stderr],
): Promise<void> {
	await Promise.all(streams.map((stream) => flushWritable(stream)));
}
