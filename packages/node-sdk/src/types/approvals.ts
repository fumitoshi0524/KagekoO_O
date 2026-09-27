export type ApprovalDecision = "once" | "session" | "deny";
export interface ApprovalRequest {
	readonly id: string;
	readonly action: string;
	readonly risk?: "low" | "medium" | "high";
	readonly preview?: string;
}
export type ApprovalHandler = (request: ApprovalRequest) => Promise<ApprovalDecision>;
export interface QuestionRequest {
	readonly id: string;
	readonly prompt: string;
	readonly options?: readonly string[];
}
export type QuestionAnswer = string | readonly string[];
export type QuestionHandler = (request: QuestionRequest) => Promise<QuestionAnswer>;
/** A serializable request retained by application until it is answered or cancelled. */
export type PendingInteraction =
	| {
			readonly kind: "approval";
			readonly sessionId: string;
			readonly request: ApprovalRequest;
			readonly createdAt: number;
	  }
	| {
			readonly kind: "question";
			readonly sessionId: string;
			readonly request: QuestionRequest;
			readonly createdAt: number;
	  };
