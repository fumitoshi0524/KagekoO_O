export interface GoalState {
	readonly goalId: string;
	readonly description: string;
	readonly completed: boolean;
	readonly budget?: { readonly maxTurns?: number; readonly maxTokens?: number };
}
