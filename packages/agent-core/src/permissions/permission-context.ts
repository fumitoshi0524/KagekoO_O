export interface PermissionContext {
	readonly toolName: string;
	readonly resource?: string;
	readonly interactive: boolean;
	readonly workspaceTrusted: boolean;
}
