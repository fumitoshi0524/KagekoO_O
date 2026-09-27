import * as fs from "node:fs/promises";
import * as path from "node:path";
import { isDeepStrictEqual } from "node:util";
import { Script } from "node:vm";
import { validateMcpServerConfig } from "../capabilities/mcp/mcp-manager.js";
import { AUTO_TOOL_ARGUMENTS_PLACEHOLDER } from "../tools/auto-loader.js";
import type { RequiredCapabilityContract } from "./learning/event.js";
import type { CapabilityManifest, LlmClient, SessionEvent, SynthesizedCapability } from "./types.js";

const MAX_DESCRIPTION_BYTES = 4 * 1024;
const MAX_REQUIREMENT_BYTES = 24 * 1024;
// Capability synthesis includes executable source, and is materially larger
// than skill/summary generation. Real providers can legitimately need more
// than one minute for this response, especially on the first request.
export const DEFAULT_CAPABILITY_SYNTHESIS_TIMEOUT_MS = 120_000;
// A coherent MCP server must emit the protocol loop plus multiple public
// operations and often deterministic shared-state handling. That response is
// materially larger than a single-operation Tool, so give it its own bounded
// production deadline instead of treating a legitimate long generation as a
// failed learner run.
export const DEFAULT_MCP_SYNTHESIS_TIMEOUT_MS = 300_000;

export interface CapabilitySynthesizerOptions {
	cwd: string;
	/** Directory for auto-generated tool manifests, injected by the composition root. */
	autoToolsDir: string;
	/** Directory for auto-generated MCP manifests, injected by the composition root. */
	autoMcpDir: string;
	llm?: LlmClient;
	/** Bound a provider call so resident learning can never hang indefinitely. */
	timeoutMs?: number;
	/** Optional larger bound for MCP synthesis. An explicit timeoutMs also overrides this default. */
	mcpTimeoutMs?: number;
}

export interface SynthesizeCapabilityInput {
	description: string;
	context?: string;
	proposedKind?: "tool" | "mcp";
	/**
	 * Structured public tool contracts from the capability-gap event. When this
	 * is a non-empty array it is authoritative; otherwise the free-text
	 * `Required public tool contracts:` marker in the last user prompt is used.
	 */
	requiredContracts?: readonly RequiredCapabilityContract[];
	recentEvents?: SessionEvent[];
	/** Optional caller abort signal (e.g. the learner run's), linked into the synthesis abort. */
	signal?: AbortSignal;
}

/**
 * Synthesize a safe command-wrapper manifest and, when possible, a self-contained
 * implementation for a missing capability.
 *
 * The LLM is asked to propose either a local tool manifest or an MCP server
 * manifest, plus a Node.js script that implements it using only built-in modules.
 */
export class CapabilitySynthesizer {
	readonly cwd: string;
	readonly llm?: LlmClient;
	readonly autoToolsDir: string;
	readonly autoMcpDir: string;
	readonly timeoutMs: number;
	readonly mcpTimeoutMs: number;

	constructor({ cwd, autoToolsDir, autoMcpDir, llm, timeoutMs, mcpTimeoutMs }: CapabilitySynthesizerOptions) {
		this.cwd = cwd;
		this.llm = llm;
		this.autoToolsDir = autoToolsDir;
		this.autoMcpDir = autoMcpDir;
		this.timeoutMs = timeoutMs ?? DEFAULT_CAPABILITY_SYNTHESIS_TIMEOUT_MS;
		this.mcpTimeoutMs = mcpTimeoutMs ?? timeoutMs ?? DEFAULT_MCP_SYNTHESIS_TIMEOUT_MS;
	}

	async synthesize({
		description,
		context = "",
		proposedKind,
		requiredContracts,
		recentEvents = [],
		signal,
	}: SynthesizeCapabilityInput): Promise<SynthesizedCapability | undefined> {
		if (!this.llm || !description) return undefined;

		// Capability synthesis must retain the authoritative user requirement.
		// Taking the last N generic events loses it after an agent performs several
		// discovery calls, leaving the learner to invent public names and schemas
		// from a lossy summary in `description`/`context`.
		const requirement = [...recentEvents]
			.reverse()
			.find(
				(event) => event.type === "user.prompt" && (event.data.origin === undefined || event.data.origin === "user"),
			);
		const requirementText =
			requirement?.type === "user.prompt" ? capUtf8(requirement.data.content, MAX_REQUIREMENT_BYTES) : "";
		// Structured contracts from the capability-gap event outrank the free-text
		// marker; the marker stays as the fallback for prompts that carry the
		// authoritative contract only in prose (including the benchmark suites).
		const requiredToolContracts =
			requiredContracts && requiredContracts.length > 0
				? [...requiredContracts]
				: extractRequiredToolContracts(requirementText);
		const requiredKind = resolveRequiredKind(requiredToolContracts, proposedKind);
		const synthesisTimeoutMs = requiredKind === "mcp" ? this.mcpTimeoutMs : this.timeoutMs;

		const prompt = [
			"You are designing a safe external-command wrapper for an AI coding assistant.",
			"The assistant currently cannot do the following:",
			`Description: ${description}`,
			context ? `Context: ${context}` : "",
			requiredKind ? `Required capability kind: ${requiredKind}` : "",
			proposedKind && proposedKind !== requiredKind
				? `Agent architecture hint: ${proposedKind}. This hint conflicts with the authoritative public-contract topology and is not binding.`
				: "",
			requirementText ? `Authoritative user requirement:\n${requirementText}` : "",
			"",
			"Implement the supplied requirement rather than an imagined substitute.",
			"The authoritative user requirement, public contracts, and behavior examples outrank the gap Description and Context. Summary words such as normalize or validate do not authorize transformations or restrictions absent from those authoritative inputs.",
			"If it contains required public tool contracts, preserve every tool name and recursive input schema exactly; do not rename, simplify, or add public operations.",
			"Do not impose input restrictions that are stricter than the public schema. For example, a JSON Schema number accepts finite non-integer values unless an integer or multipleOf constraint is explicitly present.",
			"Treat supplied behavior examples as executable semantics to generalize from. Never hard-code their argument or result values.",
			"Preserve arbitrary input strings, identifiers, object keys, nested JSON values, and ordering unless the authoritative contract or example explicitly demonstrates a transformation. Do not strip namespace prefixes, normalize names, or invent validation rules.",
			"Match demonstrated output object shapes and defaults exactly. When an example constructs a new output object, emit only its demonstrated fields and defaults; do not spread undeclared input fields into that output. Preserve the original values of every field that is emitted.",
			"Counters whose names describe changes or removals must count values that actually changed or were removed, not every value visited, unless the authoritative contract explicitly defines another meaning.",
			"Keep transformation scope and traversal scope distinct. A recursive safety scan does not authorize recursively applying merge, deletion, normalization, or validation semantics. When a contract says an array or scalar is replaced atomically, preserve its nested values exactly during the copy except for the narrowly stated safety rule, including null values that would have another meaning at the merge layer.",
			"Treat documented call sequences, lifecycle rules, and preconditions as executable behavior requirements even when described as typical usage. An out-of-order stateful operation must return the documented deterministic failure and must not mutate state.",
			"When an acknowledgement echoes accepted arguments, preserve the caller's original JSON values in the response. Internal rounding, clamping, or normalization must not silently change reported inputs unless the contract says it should.",
			"Preserve the examples' result-status semantics. Text that begins with 'Error:' is still a successful MCP tool result unless the contract or example explicitly marks it isError; do not infer isError from wording alone.",
			"Choose one local tool for one independent operation, including operations with structured JSON input or output. Choose one MCP server only when two or more public operations share state or one coherent service boundary.",
			"The word 'tool' in a supplied public contract does not imply MCP. When Required capability kind is present, it is a binding architecture constraint: return exactly that manifest kind without wrapping one operation in an MCP server or splitting it into extra operations.",
			"Before responding, self-check the implementation with several varied inputs, including arbitrary strings with punctuation or namespace prefixes, deeply nested objects, optional fields omitted, and finite fractional numbers. Reject any implementation that changes or rejects them without contract authority.",
			"Propose either a local tool manifest or an MCP server manifest, AND provide a self-contained Node.js implementation.",
			"The implementation should use only Node.js built-in modules (e.g. node:sqlite, http, https, fs, readline).",
			"The implementation is saved as a CommonJS .cjs file, so require(...) and module.exports are supported.",
			"",
			"For tools:",
			`  - The manifest args MUST be exactly [${JSON.stringify(AUTO_TOOL_ARGUMENTS_PLACEHOLDER)}].`,
			"  - The script will be invoked as: node <script-path> '<complete JSON function arguments>'. Parse process.argv[2] once as an object, then read named fields from that object.",
			"  - Never use one positional argv entry per property. The single JSON envelope preserves omitted optional fields, nested objects, arrays, booleans, numbers, null, and strings without ambiguous empty-string sentinels.",
			"  - Print the final result to stdout as plain text or JSON.",
			"  - If calls need durable session state, store it beneath process.cwd(). The generated script/install directory is immutable and may be shared across workspaces or sessions; never write mutable state beside __filename or under __dirname.",
			"",
			"For MCP servers:",
			"  - The script must read JSON-RPC messages from stdin and write JSON-RPC responses to stdout.",
			"  - Implement initialize, tools/list, and tools/call.",
			"  - In the actual tools/list JSON-RPC response, publish each schema under the MCP wire field inputSchema (camelCase), even when the authoritative contract records call that source field input_schema.",
			"  - Print each response as a single JSON object followed by an actual LF byte. Because the JavaScript source is nested inside JSON, use String.fromCharCode(10) when writing the delimiter; never emit the two literal characters backslash+n.",
			"",
			"Respond with ONLY a JSON object in this shape:",
			"",
			'{"manifest":{"kind":"tool","name":"kebab-case-name","description":"...","parameters":{"type":"object","properties":{"file":{"type":"string"}},"required":["file"]},"command":"node","args":["{{__args_json}}"]},"code":"const fs=require(\\"fs\\"); const {file}=JSON.parse(process.argv[2]); console.log(fs.readFileSync(file,\\"utf8\\"));"}',
			'{"manifest":{"kind":"mcp","name":"kebab-case-name","description":"...","command":"node","args":[]},"code":"// read JSON-RPC from stdin and respond..."}',
			'{"manifest":{"kind":"none"}}',
			"",
			'If you cannot propose a safe wrapper, return {"manifest":{"kind":"none"}}.',
		]
			.filter(Boolean)
			.join("\n");

		// Link a caller signal (e.g. the learner run's abort) into the synthesis
		// abort so an abandoned run cancels its provider call.
		const abortController = new AbortController();
		const onExternalAbort = () => abortController.abort(signal?.reason);
		try {
			if (signal) {
				if (signal.aborted) abortController.abort(signal.reason);
				else signal.addEventListener("abort", onExternalAbort, { once: true });
			}
			const startedAt = Date.now();
			const messages: Array<{ role: "user" | "assistant"; content: string }> = [{ role: "user", content: prompt }];
			let lastIssue = "invalid JSON response";

			// One bounded repair gives the resident learner a chance to correct a
			// malformed manifest or an architecture-kind violation. Both attempts
			// share one deadline so shutdown latency remains bounded.
			for (let attempt = 0; attempt < 2; attempt += 1) {
				const remainingMs = synthesisTimeoutMs - (Date.now() - startedAt);
				if (remainingMs <= 0) throw new Error("Capability synthesis timed out.");
				const response = await withTimeout(
					this.llm.chat({ messages, tools: [], signal: abortController.signal }),
					remainingMs,
					abortController,
				);
				const content = response.content ?? "";
				const candidate = normalizeCandidate(content, requiredKind, requiredToolContracts);
				if (candidate.result) {
					if (attempt === 0 && requiredKind === "tool" && requiredToolContracts.length === 1) {
						messages.push(
							{ role: "assistant", content },
							{
								role: "user",
								content: [
									"The proposal is structurally valid but has not been executed. Perform a strict adversarial review before it can enter the pending capability queue.",
									"Re-read every authoritative behavior sentence and public example. Check omitted optional fields, empty and nested JSON values, exact output shape and counters, ordering, collisions, error codes, atomic rollback, JSON Pointer escaping, array bounds, and prototype-pollution keys wherever relevant. Counters describing changes or removals count actual changes or removals rather than items merely visited unless the contract says otherwise. Check rule interactions and phase boundaries: deep-copy or recursive safety traversal must not accidentally reapply merge, deletion, normalization, or validation semantics inside values declared to replace atomically.",
									`Keep manifest args exactly [${JSON.stringify(AUTO_TOOL_ARGUMENTS_PLACEHOLDER)}] and parse that complete JSON argument object once from process.argv[2].`,
									"Return ONLY the complete corrected JSON capability object. If no correction is needed, return the complete proposal unchanged. Do not return a review or explanation.",
								].join(" "),
							},
						);
						continue;
					}
					return candidate.result;
				}
				if (candidate.none) return undefined;
				lastIssue = candidate.issue;
				if (attempt === 0) {
					messages.push(
						{ role: "assistant", content },
						{
							role: "user",
							content: [
								`The proposal was rejected because ${lastIssue}.`,
								requiredKind
									? `Return exactly one ${requiredKind} manifest. The required kind is not optional.`
									: "Return one valid minimal manifest.",
								"Preserve the authoritative public names, schemas, and behavior. Respond with only the corrected JSON object.",
							].join(" "),
						},
					);
				}
			}

			throw new Error(`Capability proposal remained invalid after repair: ${lastIssue}`);
		} catch (error) {
			// A capability request is a user-visible learning action. Silently
			// discarding a provider or manifest failure makes the request
			// impossible to audit or retry from the pending-learning surface.
			throw new Error(`Capability synthesis failed: ${error instanceof Error ? error.message : String(error)}`, {
				cause: error,
			});
		} finally {
			signal?.removeEventListener("abort", onExternalAbort);
		}
	}

	async writeToolManifest(manifest: CapabilityManifest, code?: string): Promise<string> {
		const name = sanitizeCapabilityName(manifest.name);
		if (!name) throw new Error("Invalid capability name.");
		if (manifest.kind !== "tool") throw new Error("Expected tool manifest.");

		const dir = path.join(this.autoToolsDir, name);
		await fs.mkdir(dir, { recursive: true });

		let command = manifest.command;
		let args = manifest.args ?? [];

		if (typeof code === "string" && code.length > 0) {
			// Generated examples intentionally permit require(...). Use .cjs so the
			// wrapper remains executable even when the workspace package is ESM.
			const scriptPath = path.join(dir, "tool.cjs");
			await fs.writeFile(scriptPath, code, "utf-8");
			command = "node";
			// Manifest args stay relative to the project root; the on-disk format is unchanged.
			args = [toPosixRelativePath(this.cwd, scriptPath), ...args];
		}

		const filePath = path.join(dir, "manifest.json");
		const content = JSON.stringify(
			{
				name,
				description: capDescription(manifest.description),
				parameters: manifest.parameters,
				command,
				args,
			},
			null,
			2,
		);
		await fs.writeFile(filePath, content, "utf-8");
		return filePath;
	}

	async writeMcpManifest(manifest: CapabilityManifest, code?: string): Promise<string> {
		const name = sanitizeCapabilityName(manifest.name);
		if (!name) throw new Error("Invalid capability name.");
		if (manifest.kind !== "mcp") throw new Error("Expected MCP manifest.");

		const dir = path.join(this.autoMcpDir, name);
		await fs.mkdir(dir, { recursive: true });

		let command = manifest.command;
		let args = manifest.args ?? [];

		if (typeof code === "string" && code.length > 0) {
			// MCP output is model-generated CommonJS by contract. A .js child of an
			// ESM workspace would parse successfully but crash before initialize.
			const scriptPath = path.join(dir, "server.cjs");
			await fs.writeFile(scriptPath, code, "utf-8");
			command = "node";
			args = [toPosixRelativePath(this.cwd, scriptPath)];
		}

		const filePath = path.join(dir, "manifest.json");
		const content = JSON.stringify(
			{
				name,
				description: capDescription(manifest.description),
				command,
				args,
			},
			null,
			2,
		);
		await fs.writeFile(filePath, content, "utf-8");
		return filePath;
	}
}

/**
 * Validate a structured capability candidate through the exact same pipeline
 * used for raw LLM synthesis responses (kind forcing from contracts, exact
 * name/schema equality, args placeholder, parse-only syntax check, and
 * manifest structural validation). Used by the learner-agent tools, which
 * receive an already-parsed candidate instead of raw model text.
 */
export function validateCapabilityCandidate(
	candidate: unknown,
	proposedKind?: "tool" | "mcp",
	requiredContracts: readonly RequiredCapabilityContract[] = [],
): { result?: SynthesizedCapability; none?: boolean; issue: string } {
	if (!candidate || typeof candidate !== "object") {
		return { issue: "the candidate was not a JSON capability object" };
	}
	const contracts = [...requiredContracts];
	const requiredKind = resolveRequiredKind(contracts, proposedKind);
	return normalizeCandidate(JSON.stringify(candidate), requiredKind, contracts);
}

function normalizeCandidate(
	content: string,
	proposedKind?: "tool" | "mcp",
	requiredToolContracts: RequiredToolContract[] = [],
): { result?: SynthesizedCapability; none?: boolean; issue: string } {
	const parsed = parseManifestJson(content);
	if (!parsed) return { issue: "the response was not a valid JSON capability object" };
	const { manifest, code } = normalizeResponse(parsed);
	if (!manifest) return { issue: "the response did not contain a capability manifest" };
	if (manifest.kind === "none") return { none: true, issue: "no safe capability was proposed" };
	if (proposedKind && manifest.kind !== proposedKind) {
		return { issue: `manifest kind ${manifest.kind} does not match required kind ${proposedKind}` };
	}
	if (manifest.kind === "tool" && requiredToolContracts.length > 0) {
		if (requiredToolContracts.length !== 1) {
			return { issue: `one local tool cannot expose ${requiredToolContracts.length} required public operations` };
		}
		const contract = requiredToolContracts[0]!;
		if (manifest.name !== contract.name) {
			return { issue: `manifest name ${String(manifest.name)} does not match exact public name ${contract.name}` };
		}
		if (!isDeepStrictEqual(manifest.parameters, contract.inputSchema)) {
			return { issue: `manifest parameters do not match the exact public schema for ${contract.name}` };
		}
	}
	if (manifest.kind === "tool" && !isDeepStrictEqual(manifest.args, [AUTO_TOOL_ARGUMENTS_PLACEHOLDER])) {
		return {
			issue: `local tool manifest args must be exactly [${JSON.stringify(AUTO_TOOL_ARGUMENTS_PLACEHOLDER)}] so the implementation receives one complete JSON argument object`,
		};
	}
	if (typeof code !== "string" || code.trim().length === 0) {
		return { issue: "the proposal did not include a self-contained Node.js implementation" };
	}
	try {
		// Parse only; never execute untrusted generated code in the application
		// process. The benchmark performs runtime and protocol checks separately.
		new Script(code, { filename: manifest.kind === "mcp" ? "server.cjs" : "tool.cjs" });
	} catch (error) {
		const detail = error instanceof Error ? error.message.split("\n")[0] : String(error);
		return { issue: `the generated CommonJS implementation has invalid JavaScript syntax: ${detail}` };
	}
	if (manifest.kind === "mcp" && /\binput_schema\s*:/.test(code) && !/\binputSchema\s*:/.test(code)) {
		return {
			issue: "the MCP tools/list implementation uses input_schema instead of the required inputSchema wire field",
		};
	}
	manifest.name = sanitizeCapabilityName(manifest.name);
	if (!manifest.name) return { issue: "the manifest name was missing or invalid" };
	if (!validateManifest(manifest)) return { issue: "the manifest failed structural validation" };
	return { result: { manifest, code }, issue: "" };
}

type RequiredToolContract = RequiredCapabilityContract;

/**
 * The agent's proposed kind is useful evidence when no exact public surface is
 * available. Once the user supplies that surface, its operation topology is
 * authoritative when it necessarily implies a shared service boundary. One
 * exact public operation is always represented by the smaller local tool; any
 * durable state it needs belongs under the workspace cwd. This prevents an
 * architecture hint from inflating one operation into an MCP server.
 */
function resolveRequiredKind(
	contracts: RequiredToolContract[],
	proposedKind?: "tool" | "mcp",
): "tool" | "mcp" | undefined {
	if (contracts.length > 1) return "mcp";
	if (contracts.length === 1) return "tool";
	return proposedKind;
}

function extractRequiredToolContracts(requirement: string): RequiredToolContract[] {
	const marker = /Required public tool contracts[^:\n]*:/i.exec(requirement);
	if (!marker) return [];
	const start = requirement.indexOf("[", marker.index + marker[0].length);
	if (start < 0) return [];
	let depth = 0;
	let inString = false;
	let escaped = false;
	for (let index = start; index < requirement.length; index += 1) {
		const char = requirement[index]!;
		if (inString) {
			if (escaped) escaped = false;
			else if (char === "\\") escaped = true;
			else if (char === '"') inString = false;
			continue;
		}
		if (char === '"') inString = true;
		else if (char === "[") depth += 1;
		else if (char === "]") {
			depth -= 1;
			if (depth !== 0) continue;
			try {
				const parsed = JSON.parse(requirement.slice(start, index + 1));
				if (!Array.isArray(parsed)) return [];
				return parsed.flatMap((value): RequiredToolContract[] => {
					if (!value || typeof value !== "object") return [];
					const record = value as Record<string, unknown>;
					const inputSchema = record["input_schema"] ?? record["inputSchema"];
					if (typeof record["name"] !== "string" || !inputSchema || typeof inputSchema !== "object") return [];
					return [{ name: record["name"], inputSchema: inputSchema as Record<string, unknown> }];
				});
			} catch {
				return [];
			}
		}
	}
	return [];
}

function parseManifestJson(text: string): unknown {
	// Strip a markdown fence if present — both ```json and bare ``` fences.
	const cleaned = text
		.replace(/^```(?:json)?\s*/i, "")
		.replace(/\s*```\s*$/, "")
		.trim();
	if (!cleaned) return undefined;
	try {
		return JSON.parse(cleaned);
	} catch {
		return undefined;
	}
}

function normalizeResponse(parsed: unknown): { manifest: CapabilityManifest | undefined; code: string | undefined } {
	const obj = parsed as { manifest?: unknown; code?: unknown; kind?: unknown } | undefined;
	if (obj && typeof obj === "object" && obj.manifest && typeof obj.manifest === "object") {
		return { manifest: obj.manifest as CapabilityManifest, code: typeof obj.code === "string" ? obj.code : undefined };
	}
	// Backward compatibility: the whole object is the manifest.
	if (obj && typeof obj === "object" && (obj.kind === "tool" || obj.kind === "mcp" || obj.kind === "none")) {
		return { manifest: obj as CapabilityManifest, code: undefined };
	}
	return { manifest: undefined, code: undefined };
}

const ARG_SHELL_META_RE = /[;&|<>$`\\"\r\n\t]/;

function toPosixRelativePath(from: string, to: string): string {
	return path.relative(from, to).split(path.sep).join("/");
}

export function capDescription(description: unknown, maxBytes: number = MAX_DESCRIPTION_BYTES): string {
	return capUtf8(typeof description === "string" ? description : "", maxBytes);
}

function capUtf8(value: unknown, maxBytes: number): string {
	const text = typeof value === "string" ? value : String(value ?? "");
	const buf = Buffer.from(text, "utf-8");
	if (buf.length <= maxBytes) return text;
	return buf.subarray(0, maxBytes).toString("utf-8");
}

function withTimeout<T>(promise: Promise<T>, ms: number, abortController: AbortController): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => {
			const error = new Error("Capability synthesis timed out.");
			abortController.abort(error);
			reject(error);
		}, ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}

export function validateManifest(manifest: CapabilityManifest): boolean {
	if (!manifest || (manifest.kind !== "tool" && manifest.kind !== "mcp")) return false;
	if (!manifest.name || !manifest.description || !manifest.command) return false;
	if (!Array.isArray(manifest.args)) return false;
	if (manifest.kind === "tool") {
		if (!manifest.parameters || typeof manifest.parameters !== "object") return false;
	}
	for (const arg of manifest.args) {
		if (typeof arg !== "string") return false;
		if (arg.includes("..")) return false;
		if (path.isAbsolute(arg)) return false;
		if (ARG_SHELL_META_RE.test(arg)) return false;
	}
	return validateMcpServerConfig({ command: manifest.command, args: manifest.args });
}

function sanitizeCapabilityName(name: unknown): string | undefined {
	if (!name) return undefined;
	const cleaned = String(name)
		.toLowerCase()
		.replace(/[^a-z0-9_-]+/g, "-")
		.replace(/^-+|-+$/g, "");
	if (!cleaned || cleaned.length > 64) return undefined;
	return cleaned;
}
