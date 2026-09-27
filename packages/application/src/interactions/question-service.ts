export interface QuestionRequest {
	id: string;
	prompt: string;
	options?: readonly string[];
}
export type QuestionAnswer = string | readonly string[];
export type QuestionHandler = (request: QuestionRequest) => Promise<QuestionAnswer>;
export type PendingQuestionChangeFailureReporter = (sessionId: string, error: unknown) => void | Promise<void>;

export interface PendingQuestion {
	readonly kind: "question";
	readonly sessionId: string;
	readonly request: QuestionRequest;
	readonly createdAt: number;
}

interface PendingQuestionEntry extends PendingQuestion {
	resolve(answer: QuestionAnswer): void;
	reject(reason: Error): void;
}

export class QuestionService {
	private readonly pending = new Map<string, Map<string, PendingQuestionEntry>>();
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
		private readonly handler?: QuestionHandler,
		private readonly reportPendingChangeFailure?: PendingQuestionChangeFailureReporter,
	) {}
	private async reportFailure(sessionId: string, error: unknown): Promise<void> {
		try {
			await this.reportPendingChangeFailure?.(sessionId, error);
		} catch {
			/* diagnostics must not escape */
		}
	}
	request(request: QuestionRequest): Promise<QuestionAnswer> {
		return this.handler ? this.handler(request) : Promise.reject(new Error("Question handler is not configured"));
	}
	listPending(sessionId: string): readonly string[] {
		return [...(this.pending.get(sessionId)?.keys() ?? [])];
	}
	listDetails(sessionId?: string): readonly PendingQuestion[] {
		const sessions = sessionId === undefined ? this.pending.values() : [this.pending.get(sessionId)];
		const details: PendingQuestion[] = [];
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
	respond(sessionId: string, requestId: string, answer: QuestionAnswer): boolean {
		const entry = this.pending.get(sessionId)?.get(requestId);
		if (!entry) return false;
		entry.resolve(answer);
		return true;
	}
	async requestForSession(sessionId: string, request: QuestionRequest, signal?: AbortSignal): Promise<QuestionAnswer> {
		const entries = this.pending.get(sessionId) ?? new Map<string, PendingQuestionEntry>();
		this.pending.set(sessionId, entries);
		return new Promise<QuestionAnswer>((resolve, reject) => {
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
				reject(abortError(`Question request aborted: ${request.prompt}`));
			};
			// Register the pending entry before notifying listeners so status
			// projections observe the awaiting state in the same tick.
			entries.set(request.id, {
				kind: "question",
				sessionId,
				request,
				createdAt: Date.now(),
				resolve: (answer) => {
					signal?.removeEventListener("abort", onAbort);
					if (release()) resolve(answer);
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
			const entry = entries.get(request.id)!;
			if (this.handler) void this.handler(request).then(entry.resolve, entry.reject);
		});
	}
	cancelSession(sessionId: string, reason: "closed" | "cancelled" = "closed"): void {
		const entries = this.pending.get(sessionId);
		if (!entries) return;
		this.pending.delete(sessionId);
		for (const entry of entries.values())
			entry.reject(new Error(`Session ${sessionId} ${reason} while awaiting question`));
		this.notifyPendingChanged(sessionId);
	}
}

function abortError(message: string): Error {
	const error = new Error(message);
	error.name = "AbortError";
	return error;
}
