export interface Skill {
	readonly id: string;
	readonly name: string;
	readonly instructions: string;
	readonly description?: string;
	readonly sourcePath?: string;
}
