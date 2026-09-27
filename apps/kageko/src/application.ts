import { KagekoHarness } from "@kageko/node-sdk";
import type { CLIOptions } from "./cli/options.js";
import { printTurnEvent } from "./cli/output.js";
import { parseGoalPrefix } from "./cli/goal-prefix.js";
import { resolveCheckpointAction, type CheckpointSummary } from "./cli/checkpoint-resume.js";
import { processCliIO, type CliIO } from "./cli/io.js";

export async function createCliApplication(flags: CLIOptions = {}, io: CliIO = processCliIO) {
	const diagnosticListeners = new Set<
		(diagnostic: { readonly code: string; readonly message: string; readonly error?: unknown }) => void
	>();
	const reportDiagnostic = (diagnostic: {
		readonly code: string;
		readonly message: string;
		readonly error?: unknown;
	}): void => {
		const detail = diagnostic.error instanceof Error ? `: ${diagnostic.error.message}` : "";
		io.stderr(`kageko diagnostic [${diagnostic.code}] ${diagnostic.message}${detail}\n`);
		for (const listener of diagnosticListeners) listener(diagnostic);
	};
	const harness = KagekoHarness.local({
		cwd: flags.cwd ?? process.cwd(),
		permission: flags.permission,
		interaction: flags.interaction,
		provider: flags.provider,
		model: flags.model,
		// Interaction requests remain retained by the public client until a host
		// responds or cancels them.  Do not silently deny or throw merely because
		// this invocation is headless: that loses the SDK's interaction contract.
		onDiagnostic: reportDiagnostic,
	});
	let activeSession: ReturnType<typeof harness.resume> | undefined;
	return {
		client: harness.client,
		subscribeDiagnostics(
			listener: (diagnostic: { readonly code: string; readonly message: string; readonly error?: unknown }) => void,
		) {
			diagnosticListeners.add(listener);
			return () => diagnosticListeners.delete(listener);
		},
		async prompt(text: string) {
			if (flags.sessionId && !activeSession) {
				await harness.client.resumeSession(flags.sessionId);
				activeSession = harness.resume(flags.sessionId);
			}
			activeSession ??= await harness.client.createSession({ cwd: flags.cwd ?? process.cwd() });
			const goalRequest = parseGoalPrefix(text);
			if (goalRequest) {
				if (goalRequest.replace) await activeSession.updateGoal({ status: "completed" });
				await activeSession.createGoal({ objective: goalRequest.objective });
			}
			let nextPrompt = text;
			let result: { readonly turnId: string } | undefined;
			for (;;) {
				let checkpoint: CheckpointSummary | undefined;
				result = await activeSession.promptAndWait({ parts: [{ type: "text", text: nextPrompt }] }, (event) => {
					if (event.type === "turn.checkpointed") {
						checkpoint = {
							reason: event.data.reason,
							tokensUsed: event.data.tokensUsed,
							costUsd: event.data.costUsd,
						};
					}
					printTurnEvent(event, flags.output, io.stdout);
				});
				const action = resolveCheckpointAction(checkpoint, flags.resumeOnCheckpoint === true, activeSession.id);
				if (action.kind === "resume") {
					nextPrompt = action.prompt;
					continue;
				}
				if (action.kind === "escalate") {
					// The checkpoint and session journal persist under KAGEKO_HOME;
					// only a human may spend beyond the configured budget.
					io.stderr(action.message);
					process.exitCode = 3;
				}
				break;
			}
			return result!;
		},
		async close() {
			await harness.close();
		},
	};
}
