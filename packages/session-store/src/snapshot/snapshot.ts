export interface Snapshot {
	readonly schemaVersion: number;
	readonly sessionId: string;
	readonly sequence: number;
	readonly state: unknown;
}
