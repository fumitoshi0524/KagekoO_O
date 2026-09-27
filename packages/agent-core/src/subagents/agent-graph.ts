import { randomUUID } from "node:crypto";

export type AgentRole = "coordinator" | "executor" | "learner";
export type AgentEdgeKind = "plan" | "dispatch" | "result" | "observes" | "tool-promoted" | "run";

/** Redacted, serializable role policy shown in graph snapshots. Credentials never enter this shape. */
export interface AgentGraphNodeConfiguration {
	readonly model?: {
		readonly provider?: string;
		readonly modelName?: string;
		readonly authMode?: "api" | "oauth";
		readonly contextLength?: number;
		readonly maxContextSize?: number;
		readonly maxOutputTokens?: number;
	};
	readonly systemPrompt?: string;
	readonly permissionProfile?: string;
	readonly interactionMode?: string;
	readonly tools?: readonly string[];
	readonly maxSteps?: number;
}

export interface AgentGraphNode {
	readonly id: string;
	readonly role: AgentRole;
	readonly parentId?: string;
	readonly status: "resident" | "running" | "completed" | "failed";
	readonly label?: string;
	readonly configuration?: AgentGraphNodeConfiguration;
}
export interface AgentGraphEdge {
	readonly from: string;
	readonly to: string;
	readonly kind: AgentEdgeKind;
	readonly createdAt: number;
	readonly payload?: unknown;
}

/** Coordinator -> executor(s) -> results; a resident learner observes the graph. */
export class AgentGraph {
	private readonly nodes = new Map<string, AgentGraphNode>();
	private readonly edges: AgentGraphEdge[] = [];
	register(node: Omit<AgentGraphNode, "status"> & { readonly status?: AgentGraphNode["status"] }): AgentGraphNode {
		// Store a defensive copy and hand back another: caller-side mutation of
		// the input (or of the returned node) must not leak into graph state.
		const value: AgentGraphNode = cloneNode({ ...node, status: node.status ?? "resident" });
		this.nodes.set(value.id, value);
		return cloneNode(value);
	}
	registerResidentLearner(
		id: string,
		parentId: string,
		label = "resident learning agent",
		configuration?: AgentGraphNodeConfiguration,
	): AgentGraphNode {
		return this.register({ id, role: "learner", parentId, label, configuration, status: "resident" });
	}
	/** Starts executable work. A learner is resident and can never be started. */
	start(
		role: AgentRole,
		parentId: string,
		label?: string,
		configuration?: AgentGraphNodeConfiguration,
	): AgentGraphNode {
		if (role !== "executor") throw new Error("Only executor agents can be started; learners are resident observers");
		const id = randomUUID();
		// Validate the dispatch endpoint BEFORE registering, so a failed start
		// cannot leave an orphan `running` node behind.
		if (!this.nodes.has(parentId)) {
			throw new Error(`Cannot link unknown agent graph endpoint(s): ${parentId} -> ${id} (dispatch)`);
		}
		const node = this.register({ id, role, parentId, label, configuration, status: "running" });
		this.link(parentId, id, "dispatch");
		return node;
	}
	/** Records the resident learner observing or promoting a capability; no run node is created. */
	observe(learnerId: string, targetId: string, kind: "observes" | "tool-promoted", payload?: unknown): void {
		const learner = this.nodes.get(learnerId);
		if (!learner || learner.role !== "learner" || learner.status !== "resident")
			throw new Error("Only a resident learner may observe the agent graph");
		this.link(learnerId, targetId, kind, payload);
	}
	/**
	 * Starts a bounded background learning run for the resident learner. Unlike
	 * `observe()` (a pure observation edge) this creates a real `running` node,
	 * linked from the resident learner with a `run` edge, so a run's lifecycle
	 * (`finish()` -> `result` edge back to the learner) is recorded honestly in
	 * the graph. The resident learner node itself stays resident.
	 */
	startLearnerRun(learnerId: string, label?: string): AgentGraphNode {
		const learner = this.nodes.get(learnerId);
		if (!learner || learner.role !== "learner" || learner.status !== "resident")
			throw new Error("Only a resident learner may start a learning run");
		const id = randomUUID();
		const node = this.register({ id, role: "learner", parentId: learnerId, label, status: "running" });
		this.link(learnerId, id, "run");
		return node;
	}
	/**
	 * Terminal state transition. Idempotent: finishing an already-finished node
	 * is a no-op (the first terminal status and `result` edge win), so a second
	 * call can never append a duplicate `result` edge. The graph has no
	 * diagnostic channel, so the no-op is silent by design.
	 */
	finish(id: string, status: "completed" | "failed", payload?: unknown): void {
		const node = this.nodes.get(id);
		if (!node) return;
		if (node.status === "completed" || node.status === "failed") return;
		this.nodes.set(id, { ...node, status });
		if (node.parentId) this.link(id, node.parentId, "result", payload);
	}
	/**
	 * Adds an edge between two registered nodes. Unknown endpoints are a
	 * caller bug: silently dropping the edge used to orphan executor nodes
	 * (e.g. an empty coordinator id), so this throws instead.
	 */
	link(from: string, to: string, kind: AgentEdgeKind, payload?: unknown): void {
		if (!this.nodes.has(from) || !this.nodes.has(to)) {
			throw new Error(`Cannot link unknown agent graph endpoint(s): ${from} -> ${to} (${kind})`);
		}
		this.edges.push({ from, to, kind, createdAt: Date.now(), payload: clonePayload(payload) });
	}
	snapshot(): { readonly nodes: readonly AgentGraphNode[]; readonly edges: readonly AgentGraphEdge[] } {
		// Defensive copies all the way down: mutating a snapshot must never
		// reach into the graph's internal state.
		return { nodes: [...this.nodes.values()].map(cloneNode), edges: this.edges.map(cloneEdge) };
	}
}

function cloneNode(node: AgentGraphNode): AgentGraphNode {
	return { ...node, configuration: cloneConfiguration(node.configuration) };
}

function cloneConfiguration(
	configuration: AgentGraphNodeConfiguration | undefined,
): AgentGraphNodeConfiguration | undefined {
	if (!configuration) return undefined;
	return {
		...configuration,
		...(configuration.model ? { model: { ...configuration.model } } : {}),
		...(configuration.tools ? { tools: [...configuration.tools] } : {}),
	};
}

function cloneEdge(edge: AgentGraphEdge): AgentGraphEdge {
	return { ...edge, payload: clonePayload(edge.payload) };
}

/** Payloads are opaque observer data; deep-copy plain data, pass primitives through. */
function clonePayload(payload: unknown): unknown {
	if (!payload || typeof payload !== "object") return payload;
	try {
		return structuredClone(payload);
	} catch {
		// Non-cloneable payloads (functions, class instances) are kept by
		// reference rather than failing the graph operation.
		return payload;
	}
}
