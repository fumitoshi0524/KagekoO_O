export type TodoStatus = "pending" | "in_progress" | "completed" | "cancelled";
/** Canonical session-scoped planning item shared by tools and prompt injection. */
export interface TodoState {
	todoId: string;
	text: string;
	status: TodoStatus;
}
