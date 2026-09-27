import type { SessionRepository } from "@kageko/session-store";
import { RuntimeSession } from "./runtime-session.js";
import { PromptService } from "../prompts/prompt-service.js";

export type PromptJournalAppender = (
	sessionId: string,
	input: import("../prompts/prompt-parts.js").PromptInput,
) => Promise<void>;

export class SessionFactory {
	constructor(
		readonly repository: SessionRepository,
		private readonly appendPrompt?: PromptJournalAppender,
	) {}
	async resume(sessionId: string): Promise<RuntimeSession> {
		const summary = await this.repository.get(sessionId);
		if (!summary) throw new Error(`Unknown session: ${sessionId}`);
		const appendPrompt = this.appendPrompt;
		if (!appendPrompt) throw new Error("SessionFactory requires the composition-root prompt journal appender");
		return new RuntimeSession(
			summary,
			new PromptService(async (input) => {
				await appendPrompt(summary.sessionId, input);
			}),
		);
	}
}
