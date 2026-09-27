import type { CapabilityService } from "./capability-service.js";
import { SkillRegistry, type SkillRoot } from "@kageko/agent-core";

/** Application owner for session-scoped skill snapshots. */
export class SkillService {
	private readonly registries = new Map<string, SkillRegistry>();

	constructor(readonly capabilities: CapabilityService) {}

	async prepare(roots: readonly SkillRoot[]): Promise<SkillRegistry> {
		const registry = new SkillRegistry();
		await registry.loadRoots([...roots]);
		return registry;
	}

	commit(sessionId: string, registry: SkillRegistry): void {
		this.registries.set(sessionId, registry);
		this.capabilities.replace(
			sessionId,
			"skill",
			registry.list().map((skill) => ({ id: skill.name, description: skill.description, source: skill.path })),
		);
	}

	get(sessionId: string): SkillRegistry | undefined {
		return this.registries.get(sessionId);
	}

	release(sessionId: string): void {
		this.registries.delete(sessionId);
		this.capabilities.replace(sessionId, "skill", []);
	}
}
