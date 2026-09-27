import * as fs from "node:fs/promises";
import * as path from "node:path";
import * as crypto from "node:crypto";

export interface PlanModeOptions {
	cwd: string;
	/**
	 * Directory that holds plan files, injected by the composition root
	 * (which points it at the project's plans directory). Required before
	 * {@link PlanMode.enter} can create a plan file.
	 */
	plansDir?: string;
}

/**
 * Lightweight plan-mode state. While active, writes are funneled to a single
 * plan file under the injected `plansDir`.
 */
export class PlanMode {
	readonly cwd: string;
	readonly plansDir?: string;
	active = false;
	planId: string | undefined = undefined;
	planFilePath: string | undefined = undefined;
	hasWrites = false;

	constructor({ cwd, plansDir }: PlanModeOptions) {
		this.cwd = cwd;
		this.plansDir = plansDir;
	}

	async enter(): Promise<string> {
		if (this.active) throw new Error("Already in plan mode");
		if (!this.plansDir) throw new Error("PlanMode requires an injected plansDir");
		const planId = crypto.randomBytes(4).toString("hex");
		const planFilePath = path.join(this.plansDir, `${planId}.md`);
		try {
			await fs.mkdir(path.dirname(planFilePath), { recursive: true });
			await fs.writeFile(planFilePath, "", "utf-8");
		} catch (err) {
			// Do not leave half-entered state behind when the plan file cannot
			// be created (T-m10).
			this.planId = undefined;
			this.planFilePath = undefined;
			this.hasWrites = false;
			throw err;
		}
		this.planId = planId;
		this.planFilePath = planFilePath;
		this.hasWrites = false;
		this.active = true;
		return planFilePath;
	}

	async exit(): Promise<string> {
		if (!this.active) throw new Error("Not in plan mode");
		const data = await this.data();
		this.active = false;
		this.planId = undefined;
		this.planFilePath = undefined;
		this.hasWrites = false;
		return data;
	}

	markWrite(): void {
		this.hasWrites = true;
	}

	async data(): Promise<string> {
		if (!this.planFilePath) return "";
		try {
			return await fs.readFile(this.planFilePath, "utf-8");
		} catch {
			return "";
		}
	}

	isPlanFile(targetPath: string | undefined): boolean {
		if (!this.planFilePath || !targetPath) return false;
		const resolved = path.isAbsolute(targetPath) ? path.normalize(targetPath) : path.resolve(this.cwd, targetPath);
		const planPath = path.resolve(this.planFilePath);
		// Case-fold on case-insensitive filesystems, matching the tool
		// scheduler's normalizePath behavior (win32 + darwin).
		if (process.platform === "win32" || process.platform === "darwin") {
			return resolved.toLowerCase() === planPath.toLowerCase();
		}
		return resolved === planPath;
	}
}
