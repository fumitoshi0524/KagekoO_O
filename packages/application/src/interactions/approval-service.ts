export type ApprovalDecision = "once" | "session" | "deny";
export interface ApprovalRequest {
	id: string;
	action: string;
	risk?: "low" | "medium" | "high";
	preview?: string;
}
export type ApprovalHandler = (request: ApprovalRequest) => Promise<ApprovalDecision>;
export type PendingChangeFailureReporter = (sessionId: string, error: unknown) => void | Promise<void>;

interface ApprovalResponse {
	readonly decision: ApprovalDecision;
	readonly feedback?: string;
}

export interface PendingApproval {
	readonly kind: "approval";
	readonly sessionId: string;
	readonly request: ApprovalRequest;
	readonly createdAt: number;
}

interface PendingApprovalEntry extends PendingApproval {
	resolve(response: ApprovalResponse): void;
	reject(reason: Error): void;
}

export class ApprovalService {
	private readonly pending = new Map<string, Map<string, PendingApprovalEntry>>();
	private pendingChanged?: (sessionId: string) => void | Promise<void>;
	setPendingChanged(listener: (sessionId: string) => void | Promise<void>): void {
		this.pendingChanged = listener;
	}
	// Listener failures remain observational and never propagate into a request.
	private notifyPendingChanged(sessionId: string): void {
		try {
			void Promise.resolve(this.pendingChanged?.(sessionId)).catch((error: unknown) => {
				void this.reportFailure(sessionId, error);
			});
		} catch (error) {
			void this.reportFailure(sessionId, error);
		}
	}
	constructor(
		private readonly handler?: ApprovalHandler,
		private readonly reportPendingChangeFailure?: PendingChangeFailureReporter,
	) {}
	private async reportFailure(sessionId: string, error: unknown): Promise<void> {
		try {
			await this.reportPendingChangeFailure?.(sessionId, error);
		} catch {
			/* diagnostics must not escape */
		}
	}
	request(request: ApprovalRequest): Promise<ApprovalDecision> {
		if (!this.handler) return Promise.resolve("deny");
		return this.handler(request);
	}
	listPending(sessionId: string): readonly string[] {
		return [...(this.pending.get(sessionId)?.keys() ?? [])];
	}
	listDetails(sessionId?: string): readonly PendingApproval[] {
		const sessions = sessionId === undefined ? this.pending.values() : [this.pending.get(sessionId)];
		const details: PendingApproval[] = [];
		for (const entries of sessions)
			for (const entry of entries?.values() ?? []) {
				details.push({
					kind: entry.kind,
					sessionId: entry.sessionId,
					request: entry.request,
					createdAt: entry.createdAt,
				});
			}
		return details.sort((left, right) => left.createdAt - right.createdAt);
	}
	respond(sessionId: string, requestId: string, decision: ApprovalDecision, feedback?: string): boolean {
		const entry = this.pending.get(sessionId)?.get(requestId);
		if (!entry) return false;
		const normalizedFeedback = normalizeFeedback(feedback);
		entry.resolve(normalizedFeedback ? { decision, feedback: normalizedFeedback } : { decision });
		return true;
	}
	async requestForSession(
		sessionId: string,
		request: ApprovalRequest,
		signal?: AbortSignal,
	): Promise<ApprovalResponse> {
		const entries = this.pending.get(sessionId) ?? new Map<string, PendingApprovalEntry>();
		this.pending.set(sessionId, entries);
		return new Promise<ApprovalResponse>((resolve, reject) => {
			let settled = false;
			const release = () => {
				if (settled) return false;
				settled = true;
				entries.delete(request.id);
				if (!entries.size) this.pending.delete(sessionId);
				this.notifyPendingChanged(sessionId);
				return true;
			};
			const onAbort = () => {
				if (!release()) return;
				reject(abortError(`Approval request aborted: ${request.action}`));
			};
			// Register the pending entry before notifying listeners so status
			// projections observe the awaiting state in the same tick.
			entries.set(request.id, {
				kind: "approval",
				sessionId,
				request,
				createdAt: Date.now(),
				resolve: (response) => {
					signal?.removeEventListener("abort", onAbort);
					if (release()) resolve(response);
				},
				reject: (error) => {
					signal?.removeEventListener("abort", onAbort);
					if (release()) reject(error);
				},
			});
			if (signal?.aborted) {
				onAbort();
				return;
			}
			signal?.addEventListener("abort", onAbort, { once: true });
			this.notifyPendingChanged(sessionId);
			// A presentation adapter is optional. Without one, application retains
			// the pending promise until the public SDK resolves or cancels it.
			const entry = entries.get(request.id)!;
			if (this.handler) void this.handler(request).then((decision) => entry.resolve({ decision }), entry.reject);
		});
	}
	cancelSession(sessionId: string, reason: "closed" | "cancelled" = "closed"): void {
		const entries = this.pending.get(sessionId);
		if (!entries) return;
		this.pending.delete(sessionId);
		for (const entry of entries.values())
			entry.reject(new Error(`Session ${sessionId} ${reason} while awaiting approval`));
		this.notifyPendingChanged(sessionId);
	}
	asPermissionHandler(sessionId: string): import("@kageko/agent-core").ApprovalHandler {
		return async (toolName, args, reason, signal) => {
			const response = await this.requestForSession(
				sessionId,
				{
					id: randomUUID(),
					action: toolName,
					risk: reason ? "medium" : undefined,
					preview: JSON.stringify(args),
				},
				signal,
			);
			return {
				approved: response.decision === "once" || response.decision === "session",
				record: response.decision === "session",
				...(response.feedback ? { feedback: response.feedback } : {}),
			};
		};
	}
}

function normalizeFeedback(feedback: string | undefined): string | undefined {
	const normalized = feedback?.trim();
	if (!normalized) return undefined;
	return [...normalized].slice(0, 2_000).join("");
}

function abortError(message: string): Error {
	const error = new Error(message);
	error.name = "AbortError";
	return error;
}
import { randomUUID } from "node:crypto";
