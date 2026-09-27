/**
 * Shared types for the memory subsystem.
 */

import type { ChatOptions, ChatResponse } from "../ports/llm.js";
import type { DurableEvent } from "@kageko/protocol";

/** Provider vocabulary is owned by the model foundation package, not duplicated here. */
export type TextGenerationClient = Pick<{ chat(options: ChatOptions): Promise<ChatResponse> }, "chat">;

/** @deprecated Use TextGenerationClient. */
export type LlmClient = TextGenerationClient;

/** A validated event loaded from the durable session journal. */
export type SessionEvent = DurableEvent;

export interface RepoSymbol {
	type: string;
	name: string;
}

export interface RepoChunk {
	name: string;
	content: string;
}

export interface RepoIndexEntry {
	path: string;
	size: number;
	mtime: number;
	hash: string;
	language: string;
	symbols: RepoSymbol[];
	chunks: RepoChunk[];
	summary: string;
	summaryAt?: number;
	content?: string;
	/** Internal marker used during incremental indexing. */
	_unchanged?: boolean;
}

export interface KnowledgeEntry {
	id: string;
	source: string;
	title: string;
	summary: string;
	content: string;
	tags: string[];
	createdAt: number;
	updatedAt: number;
	_fp?: string;
}

export type ProfileScope = "user" | "project";

export interface ProfileEntry {
	id: string;
	scope: ProfileScope | string;
	fact: string;
	createdAt: number;
}

export interface GraphNode {
	id: string;
	language: string;
	symbols: string[];
}

export interface GraphEdge {
	from: string;
	to: string;
	type: string;
	symbol?: string;
}

export interface RepoGraph {
	nodes: GraphNode[];
	edges: GraphEdge[];
	generatedAt: number;
}

export interface SynthesizedSkill {
	name: string;
	description: string;
	instructions: string;
}

export interface CapabilityManifest {
	kind: "tool" | "mcp" | "none";
	name?: string;
	description?: string;
	parameters?: Record<string, unknown>;
	command?: string;
	args?: string[];
}

export interface SynthesizedCapability {
	manifest: CapabilityManifest;
	code?: string;
}
