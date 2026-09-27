import type { Tool, ToolContext } from "../../types.js";
import { createSkillTool } from "../../../capabilities/skills/skill-loader.js";
import { noAccess } from "../../accesses.js";

export const generateSkillTool: Tool<{ name?: string }> = {
	name: "generate_skill",
	description: "Generate a reusable SKILL.md from the most recent task in the current session record.",
	parameters: {
		type: "object",
		properties: {
			name: { type: "string", description: "Optional kebab-case skill name" },
		},
	},
	async execute({ name }: { name?: string }, { session }: ToolContext) {
		if (!session?.memory || !session?.recordStore) {
			return { output: "Memory engine or record store is not available.", isError: true };
		}
		const events = await session.recordStore.load();
		if (events.length === 0) {
			return { output: "No session events to synthesize a skill from.", isError: true };
		}
		const skill = await session.memory.generateSkill(events as import("../../../memory/types.js").SessionEvent[], {
			name,
		});
		if (!skill) {
			return { output: "Could not synthesize a skill from the session record.", isError: true };
		}
		if (session.skills) {
			const loaded = await session.skills.registerSkill(skill.filePath, "auto");
			if (!loaded) {
				return { output: `Generated skill failed runtime loading: ${skill.filePath}`, isError: true };
			}
			if (session.registry) {
				session.registry.register(createSkillTool(loaded), {
					origin: "skill",
					ownerId: loaded.source,
					accesses: noAccess(),
				});
			}
		}
		return {
			output: `Generated skill "${skill.name}" at ${skill.filePath}\nDescription: ${skill.description}\n\n${skill.instructions}`,
		};
	},
};
