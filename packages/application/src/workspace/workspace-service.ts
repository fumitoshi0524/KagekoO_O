import path from "node:path";
export class WorkspaceService {
	constructor(readonly cwd: string) {}
	get root(): string {
		return path.resolve(this.cwd);
	}
	contains(target: string): boolean {
		const root = this.root;
		const resolved = path.resolve(target);
		return resolved === root || resolved.startsWith(`${root}${path.sep}`);
	}
}
