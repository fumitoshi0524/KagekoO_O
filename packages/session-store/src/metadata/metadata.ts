export interface SessionMetadata {
	readonly sessionId: string;
	readonly cwd: string;
	readonly title: string | null;
	readonly createdAt: number;
	readonly updatedAt: number;
	readonly archived: boolean;
}
export type SessionMetadataPatch = Partial<Pick<SessionMetadata, "title" | "archived">>;
