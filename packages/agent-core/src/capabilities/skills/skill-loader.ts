import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { Skill } from "./skill.js";
import type { Tool, ToolResult } from "../../tools/types.js";
export type SkillTool = Tool;

export interface SkillLoader {
	load(): Promise<readonly Skill[]>;
}
export interface SkillRoot {
	path: string;
	source: string;
}
export interface LoadedSkill {
	name: string;
	description: string;
	path: string;
	dir: string;
	content: string;
	source: string;
	metadata: { type: string; name?: string; description?: string; learnedThroughTurns?: number };
}
export interface SkillToolDefinition {
	type: "function";
	function: { name: string; description: string; parameters: { type: "object"; properties: Record<string, unknown> } };
}
export interface SkillDiagnostic {
	readonly file: string;
	readonly message: string;
}

/** Owns discovery and parsing of local skill files. */
export class SkillRegistry {
	readonly skills: Map<string, LoadedSkill> = new Map();
	readonly diagnostics: SkillDiagnostic[] = [];
	clear(): void {
		this.skills.clear();
		this.diagnostics.splice(0, this.diagnostics.length);
	}
	async loadRoots(roots: SkillRoot[]): Promise<void> {
		for (const root of roots) await this.loadRoot(root.path, root.source);
	}
	async loadRoot(root: string, source: string): Promise<void> {
		let entries: string[];
		try {
			entries = await fs.readdir(root);
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
			throw error;
		}
		for (const entry of entries) {
			const file = path.join(root, entry);
			const stat = await fs.stat(file).catch(() => null);
			if (!stat) continue;
			let candidate: string | undefined;
			if (stat.isDirectory()) {
				const skillFile = path.join(file, "SKILL.md");
				const skillStat = await fs.stat(skillFile).catch(() => null);
				// Container directories such as `skills/auto` are valid discovery
				// roots, not malformed skills. Only register an actual SKILL.md.
				if (skillStat?.isFile()) candidate = skillFile;
			} else if (stat.isFile() && entry.endsWith(".md") && entry !== "SKILL.md") candidate = file;
			if (candidate) await this.registerSkill(candidate, source);
		}
	}
	async registerSkill(file: string, source: string): Promise<LoadedSkill | undefined> {
		try {
			const skill = parseSkillText({ skillMdPath: file, source, text: await fs.readFile(file, "utf-8") });
			this.skills.set(skill.name.toLowerCase(), skill);
			return skill;
		} catch (error) {
			this.diagnostics.push({ file, message: (error as Error).message });
			return undefined;
		}
	}
	get(name: string): LoadedSkill | undefined {
		return this.skills.get(name.toLowerCase());
	}
	list(): LoadedSkill[] {
		return [...this.skills.values()];
	}
	asToolDefinitions(): SkillToolDefinition[] {
		return this.list()
			.filter((skill) => skill.metadata.type !== "reference")
			.map((skill) => ({
				type: "function",
				function: {
					name: `skill_${skill.name}`,
					description: skillToolDescription(skill.description),
					parameters: {
						type: "object",
						properties: { arguments: { type: "string", description: "Arguments to pass to the skill" } },
					},
				},
			}));
	}
}
export function parseSkillText({
	skillMdPath,
	source,
	text,
}: {
	skillMdPath: string;
	source: string;
	text: string;
}): LoadedSkill {
	const lines = text.split(/\r?\n/);
	const close = lines[0]?.trim() === "---" ? lines.findIndex((line, index) => index > 0 && line.trim() === "---") : -1;
	if (lines[0]?.trim() === "---" && close < 0) throw new Error("Missing closing frontmatter fence");
	const metadata: Record<string, string> = {};
	if (close >= 0)
		for (const line of lines.slice(1, close)) {
			const index = line.indexOf(":");
			if (index >= 0)
				metadata[line.slice(0, index).trim()] = line
					.slice(index + 1)
					.trim()
					.replace(/^['\"]|['\"]$/g, "");
		}
	const body = lines
		.slice(close >= 0 ? close + 1 : 0)
		.join("\n")
		.trim();
	const fallbackName =
		path.basename(skillMdPath).toLowerCase() === "skill.md"
			? path.basename(path.dirname(skillMdPath))
			: path.basename(skillMdPath, path.extname(skillMdPath));
	const name = (metadata["name"] ?? fallbackName)
		.toLowerCase()
		.replace(/[^a-z0-9_-]+/g, "-")
		.replace(/^-+|-+$/g, "");
	if (skillMdPath.endsWith("SKILL.md") && (!metadata["name"] || !metadata["description"]))
		throw new Error(`Missing required frontmatter field name/description in ${skillMdPath}`);
	return {
		name: name || "unnamed",
		description:
			metadata["description"] ?? body.split(/\r?\n/).find(Boolean)?.slice(0, 240) ?? "No description provided.",
		path: skillMdPath,
		dir: path.dirname(skillMdPath),
		content: body,
		source,
		metadata: {
			name: metadata["name"],
			description: metadata["description"],
			type: metadata["type"] ?? "prompt",
			learnedThroughTurns: parseNonNegativeInteger(metadata["learned-through-turns"]),
		},
	};
}

function parseNonNegativeInteger(value: string | undefined): number | undefined {
	if (value === undefined || !/^\d+$/.test(value)) return undefined;
	const parsed = Number(value);
	return Number.isSafeInteger(parsed) ? parsed : undefined;
}
export async function parseSkillFromFile(skillMdPath: string, source: string): Promise<LoadedSkill> {
	return parseSkillText({ skillMdPath, source, text: await fs.readFile(skillMdPath, "utf-8") });
}
export class FileSkillLoader implements SkillLoader {
	constructor(private readonly roots: readonly SkillRoot[]) {}
	async load(): Promise<readonly Skill[]> {
		const registry = new SkillRegistry();
		await registry.loadRoots([...this.roots]);
		return registry.list().map((skill) => ({
			id: skill.name,
			name: skill.name,
			instructions: skill.content,
			description: skill.description,
			sourcePath: skill.path,
		}));
	}
}
export function createSkillTool(skill: Pick<LoadedSkill, "name" | "description">): SkillTool {
	return {
		name: `skill_${skill.name}`,
		description: skillToolDescription(skill.description),
		parameters: {
			type: "object",
			properties: { arguments: { type: "string", description: "Arguments to pass to the skill" } },
		},
		execute({ arguments: args = "" }, { session }): ToolResult {
			const loaded = session?.skills?.get(skill.name);
			if (!loaded) return { output: "Skill not found.", isError: true };
			return {
				output: args ? `${loaded.content}\n\n<arguments>\n${wrapCodeBlock(args)}\n</arguments>` : loaded.content,
			};
		},
	};
}

function skillToolDescription(description: string): string {
	return `Learned procedure; invoke before task operations when this matches the request. This returns instructions rather than performing the task: ${description}`;
}

function wrapCodeBlock(value: unknown): string {
	const content = String(value);
	let fence = "```";
	while (content.includes(fence)) fence += "`";
	return `${fence}\n${content}\n${fence}`;
}
