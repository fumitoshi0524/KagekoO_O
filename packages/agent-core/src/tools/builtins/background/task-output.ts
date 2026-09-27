import type { Tool, ToolContext } from "../../types.js";

interface TaskOutputArgs {
	task_id: string;
	block?: boolean;
	timeout?: number;
	offset?: number;
	limit?: number;
}

const MAX_OUTPUT_BYTES = 65_536;

export const taskOutputTool: Tool<TaskOutputArgs> = {
	name: "task_output",
	description: "Read output from a background task.",
	parameters: {
		type: "object",
		properties: {
			task_id: { type: "string", description: "Task id" },
			block: { type: "boolean", description: "Wait for the task to finish before returning (default false)" },
			timeout: { type: "number", description: "Seconds to wait when block=true (default 30)" },
			offset: { type: "number", description: "Byte offset for paged output (default: tail preview)" },
			limit: { type: "number", description: "Maximum bytes to read from offset (max 65536)" },
		},
		required: ["task_id"],
	},
	async execute({ task_id, block = false, timeout = 30, offset, limit }: TaskOutputArgs, { session }: ToolContext) {
		if (!session?.tracker) {
			return { output: "Process tracker is not available.", isError: true };
		}
		const info = session.tracker.getTask(task_id);
		if (!info) {
			return { output: `Task not found: ${task_id}`, isError: true };
		}

		if (block) {
			const timeoutSec = Number.isFinite(timeout) && timeout > 0 ? Math.min(timeout, 86400) : 30;
			await session.tracker.wait(task_id, timeoutSec * 1000);
		}
		const current = session.tracker.getTask(task_id);
		if (!current) {
			return { output: `Task not found after wait: ${task_id}`, isError: true };
		}

		const snapshot = await session.tracker.getOutputSnapshot(task_id);
		if (!snapshot) {
			return { output: `No output available for task ${task_id}.`, isError: true };
		}

		const lines = [
			`task_id: ${current.taskId}`,
			`status: ${current.status}`,
			`pid: ${current.pid ?? "?"}`,
			`exitCode: ${current.exitCode ?? "?"}`,
			`command: ${current.command}`,
			`outputSizeBytes: ${snapshot.outputSizeBytes}`,
			`outputTruncated: ${snapshot.truncated}`,
			`outputPath: ${snapshot.outputPath ?? "in-memory"}`,
		];
		if (offset !== undefined || limit !== undefined) {
			const requestedLimit = Number.isFinite(limit)
				? Math.max(0, Math.min(MAX_OUTPUT_BYTES, Math.trunc(limit!)))
				: MAX_OUTPUT_BYTES;
			const chunk = await session.tracker.readOutput(task_id, offset, requestedLimit);
			if (!chunk) return { output: `No output available for task ${task_id}.`, isError: true };
			lines.push(`offset: ${chunk.offset}`, `nextOffset: ${chunk.nextOffset}`, `eof: ${chunk.eof}`);
			lines.push("[output]", capUtf8(chunk.content, MAX_OUTPUT_BYTES) || "[no output available]");
		} else {
			if (snapshot.truncated) lines.push("[Truncated tail preview; use offset and limit to page the private log]");
			lines.push("[output]", capUtf8(snapshot.preview, MAX_OUTPUT_BYTES) || "[no output available]");
		}
		return { output: capUtf8(lines.join("\n"), MAX_OUTPUT_BYTES) };
	},
};

function capUtf8(value: string, maxBytes: number): string {
	const bytes = Buffer.from(value);
	if (bytes.length <= maxBytes) return value;
	const suffix = `\n[output capped at ${maxBytes} bytes]`;
	let prefix = bytes.subarray(0, Math.max(0, maxBytes - Buffer.byteLength(suffix))).toString("utf8");
	while (Buffer.byteLength(prefix + suffix) > maxBytes) prefix = prefix.slice(0, -1);
	return prefix + suffix;
}
