import type { SubagentResult } from "../../subagents/subagent-host.js";
import type { Tool, ToolContext } from "../types.js";

interface AgentSwarmArgs {
	tasks: string[];
	system_prompt?: string;
	max_concurrency?: number;
	rate_limit?: number;
	rateLimit?: number;
	abort_on_error?: boolean;
}

export const agentSwarmTool: Tool<AgentSwarmArgs> = {
	name: "agent_swarm",
	description:
		"Spawn multiple child agents in parallel, each with its own isolated memory, and aggregate their results.",
	parameters: {
		type: "object",
		properties: {
			tasks: {
				type: "array",
				items: { type: "string" },
				description: "Array of task prompts, one per subagent",
			},
			system_prompt: {
				type: "string",
				description: "Optional system prompt shared by all subagents",
			},
			max_concurrency: {
				type: "number",
				description: "Deprecated: use rate_limit.",
			},
			rate_limit: {
				type: "number",
				description: "Maximum number of subagents to run in parallel (default Infinity)",
			},
			rateLimit: {
				type: "number",
				description: "Maximum number of subagents to run in parallel (default Infinity)",
			},
			abort_on_error: {
				type: "boolean",
				description:
					"Fail-fast: abort queued and in-flight tasks when any task fails (default: false — task failures are collected per task and siblings keep running)",
			},
		},
		required: ["tasks"],
	},
	async execute(
		{ tasks, system_prompt, max_concurrency, rate_limit, rateLimit, abort_on_error }: AgentSwarmArgs,
		{ session, signal }: ToolContext,
	) {
		if (!session) {
			return { output: "Session is not available.", isError: true };
		}
		if (!Array.isArray(tasks) || tasks.length === 0) {
			return { output: "tasks must be a non-empty array.", isError: true };
		}

		const limit = rate_limit ?? rateLimit ?? max_concurrency ?? Infinity;
		const host = session.subagentHost;
		if (!host) {
			return { output: "Subagent runtime is not available in this session.", isError: true };
		}
		const hostLimit = host.maxConcurrent;
		const effectiveRateLimit = Number.isFinite(limit) ? limit : hostLimit;
		const concurrency = Math.max(1, Math.min(effectiveRateLimit, hostLimit, tasks.length));

		const abortController = new AbortController();
		let abortListener: (() => void) | undefined;
		if (signal) {
			abortListener = () => abortController.abort(signal.reason);
			signal.addEventListener("abort", abortListener, { once: true });
		}

		try {
			const results = await mapConcurrent(
				tasks,
				concurrency,
				(prompt: string) =>
					host.run({
						prompt,
						systemPrompt: system_prompt,
						signal: abortController.signal,
					}),
				{ abortController, abortOnError: abort_on_error ?? false },
			);

			let hasError = false;
			const output = results
				.map((result: unknown, index: number) => {
					const resolved = result as SubagentResult | { error: unknown };
					if ("error" in resolved) {
						hasError = true;
						return `Task ${index + 1} (error):\n${String((resolved.error as Error).message ?? resolved.error)}`;
					}
					return `Task ${index + 1}:\n${resolved.content ?? ""}`;
				})
				.join("\n\n");

			return { output, isError: hasError };
		} finally {
			if (signal && abortListener) {
				signal.removeEventListener("abort", abortListener);
			}
		}
	},
};

async function mapConcurrent<T, R>(
	items: T[],
	concurrency: number,
	fn: (item: T, index: number) => Promise<R>,
	{ abortController, abortOnError = false }: { abortController?: AbortController; abortOnError?: boolean } = {},
): Promise<(R | { error: unknown })[]> {
	// Pre-fill every slot so a task that never started (aborted before a worker
	// picked it up) is distinguishable from one that ran and returned empty
	// output. Each completion overwrites its own slot.
	const results: (R | { error: unknown })[] = items.map(() => ({
		error: new Error("not started (aborted)"),
	}));
	let index = 0;

	async function worker(): Promise<void> {
		while (index < items.length) {
			if (abortController?.signal.aborted) {
				break;
			}
			const i = index++;
			try {
				results[i] = await fn(items[i]!, i);
			} catch (err) {
				results[i] = { error: err };
				if (abortOnError && abortController && !abortController.signal.aborted) {
					abortController.abort();
				}
			}
		}
	}

	await Promise.all(Array.from({ length: concurrency }, worker));
	return results;
}
