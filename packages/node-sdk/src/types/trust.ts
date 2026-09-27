export interface WorkspaceTrustStatus {
	readonly workspace: string;
	readonly hasSecurityConfiguration: boolean;
	readonly trusted: boolean;
	readonly findings?: readonly string[];
	readonly manifest?: string;
	readonly reason?: "not_trusted" | "configuration_changed";
}
