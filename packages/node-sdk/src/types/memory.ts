export interface MemoryStatus {
	readonly knowledgeEntries: number;
	readonly repoFilesIndexed: number;
	readonly profileEntries: number;
	readonly pendingLearning: number;
	/** False when the session runtime has no resident learner; absent on older servers. */
	readonly learningEnabled?: boolean;
}
