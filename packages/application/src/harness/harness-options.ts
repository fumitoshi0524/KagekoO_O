import type { RuntimeSessionRepository } from "@kageko/session-store";
import type { ApprovalHandler } from "../interactions/approval-service.js";
import type { QuestionHandler } from "../interactions/question-service.js";

export interface ApplicationDiagnostic {
	readonly code:
		| "event.delivery_failed"
		| "interaction.status_failed"
		| "cron.restore_skipped"
		| "event.forward_failed"
		| "learning"
		| "core.diagnostic";
	readonly message: string;
	readonly error?: unknown;
	readonly sessionId?: string;
	readonly eventType?: string;
}

export type ApplicationDiagnosticSink = (diagnostic: ApplicationDiagnostic) => void | Promise<void>;

export interface HarnessOptions {
	readonly sessionRepository: RuntimeSessionRepository;
	readonly cwd?: string;
	/** Injectable live-provider transport for deterministic host and integration tests. */
	readonly modelCatalogRequest?: typeof fetch;
	/** Presentation adapters supplied by a first-party host such as the CLI. */
	readonly approvalHandler?: ApprovalHandler;
	readonly questionHandler?: QuestionHandler;
	/** Host-owned diagnostics. Application never writes to stdout or stderr. */
	readonly onDiagnostic?: ApplicationDiagnosticSink;
}
