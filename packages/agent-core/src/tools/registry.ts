import Ajv from "ajv";
import { allAccess } from "./accesses.js";
import type {
	Tool,
	ToolExecution,
	ToolParameters,
	McpToolDescriptor,
	ValidateFunction,
	RegisteredTool,
	ToolRegistrationOptions,
	ToolOriginKind,
	ToolProvenance,
} from "./types.js";

const ajv = new Ajv({ strict: false });

interface JsonSchema {
	type?: string;
	additionalProperties?: boolean | JsonSchema;
	properties?: Record<string, JsonSchema>;
	patternProperties?: Record<string, JsonSchema>;
	items?: JsonSchema | JsonSchema[];
	allOf?: JsonSchema[];
	anyOf?: JsonSchema[];
	oneOf?: JsonSchema[];
	if?: JsonSchema;
	then?: JsonSchema;
	else?: JsonSchema;
	[key: string]: unknown;
}

function isSchema(value: unknown): value is JsonSchema {
	return value !== null && typeof value === "object";
}

function normalizeSchema(schema: unknown): unknown {
	if (!isSchema(schema)) return schema;
	const out: JsonSchema = { ...schema };
	if (out.properties && isSchema(out.properties)) {
		const properties: Record<string, JsonSchema> = {};
		for (const key of Object.keys(out.properties)) {
			properties[key] = normalizeSchema(out.properties[key]) as JsonSchema;
		}
		out.properties = properties;
	}
	if (out.patternProperties && isSchema(out.patternProperties)) {
		const patternProperties: Record<string, JsonSchema> = {};
		for (const key of Object.keys(out.patternProperties)) {
			patternProperties[key] = normalizeSchema(out.patternProperties[key]) as JsonSchema;
		}
		out.patternProperties = patternProperties;
	}
	if (out.additionalProperties && isSchema(out.additionalProperties)) {
		out.additionalProperties = normalizeSchema(out.additionalProperties) as JsonSchema;
	}
	if (out.items) {
		out.items = Array.isArray(out.items)
			? out.items.map((item) => normalizeSchema(item) as JsonSchema)
			: (normalizeSchema(out.items) as JsonSchema);
	}
	for (const combiner of ["allOf", "anyOf", "oneOf"] as const) {
		if (Array.isArray(out[combiner])) {
			out[combiner] = out[combiner].map((item) => normalizeSchema(item) as JsonSchema);
		}
	}
	for (const conditional of ["if", "then", "else"] as const) {
		if (out[conditional]) {
			out[conditional] = normalizeSchema(out[conditional]) as JsonSchema;
		}
	}
	return out;
}

export class ToolRegistry {
	private readonly tools = new Map<string, RegisteredTool>();
	private readonly _validators = new Map<string, ValidateFunction>();
	private readonly _mcpToolNames = new Set<string>();
	private registrationSequence = 0;

	register<TArgs = Record<string, unknown>>(
		tool: Tool<TArgs>,
		options: ToolRegistrationOptions = { origin: "user", accesses: allAccess() },
	): string {
		if (!tool || typeof tool.name !== "string" || !tool.name) {
			throw new Error("Tool must have a non-empty string name");
		}
		if (typeof tool.execute !== "function" && typeof tool.resolveExecution !== "function") {
			throw new Error(`Tool ${tool.name} must have an execute function or a resolveExecution function`);
		}
		validateRegistrationName(tool.name, options.origin);
		const existing = this.tools.get(tool.name);
		if (existing) {
			throw new Error(
				`Tool registration collision for ${tool.name}: ${options.origin}:${options.ownerId ?? options.origin} ` +
					`would shadow ${existing.provenance.kind}:${existing.provenance.ownerId}`,
			);
		}
		if (typeof tool.resolveExecution !== "function" && !options.accesses?.length) {
			throw new Error(`Tool ${tool.name} must declare static accesses or implement resolveExecution`);
		}
		const registrationId = `${options.origin}:${++this.registrationSequence}`;
		this.tools.set(tool.name, {
			tool: tool as Tool<Record<string, unknown>>,
			staticAccesses: options.accesses?.map((access) => ({ ...access })),
			provenance: {
				kind: options.origin,
				ownerId: options.ownerId ?? options.origin,
				registrationId,
			},
		});
		return registrationId;
	}

	resolveExecution(toolName: string, args: Record<string, unknown>, context = {}): ToolExecution {
		const registered = this.tools.get(toolName);
		if (!registered) {
			throw new Error(`Unknown tool: ${toolName}`);
		}
		const { tool } = registered;

		let execution: ToolExecution;
		if (typeof tool.resolveExecution === "function") {
			execution = tool.resolveExecution(args, context);
		} else {
			execution = {};
		}
		if (!execution || typeof execution !== "object") {
			execution = {};
		}
		if (typeof execution.execute !== "function") {
			if (typeof tool.execute === "function") {
				execution.execute = tool.execute;
			} else {
				throw new Error(`Tool ${toolName} has no executable function`);
			}
		}
		if (!Array.isArray(execution.accesses)) {
			execution.accesses = registered.staticAccesses?.map((access) => ({ ...access })) ?? allAccess();
		}
		if (execution.stopBatchAfterThis === undefined) {
			execution.stopBatchAfterThis = false;
		}
		execution.provenance = { ...registered.provenance };
		return execution;
	}

	registerMcpTool(serverName: string, tool: McpToolDescriptor): string {
		const qualifiedName = `mcp__${serverName}__${tool.name}`;
		this.register(
			{
				name: qualifiedName,
				description: tool.description ?? `MCP tool ${tool.name} from server ${serverName}`,
				parameters: tool.inputSchema ?? { type: "object", properties: {} },
				execute: async (args, context) => {
					const mcp = context.mcp;
					if (!mcp) {
						throw new Error("MCP manager is not available in tool context");
					}
					const result = await mcp.callTool(serverName, tool.name, args, { signal: context.signal });
					return { output: formatMcpResult(result) };
				},
			},
			{ origin: "mcp", ownerId: serverName, accesses: allAccess() },
		);
		this._mcpToolNames.add(qualifiedName);
		return qualifiedName;
	}

	isMcpTool(name: string): boolean {
		return this._mcpToolNames.has(name);
	}

	get(name: string): Tool<Record<string, unknown>> | undefined {
		return this.tools.get(name)?.tool;
	}

	getRegistration(name: string): RegisteredTool | undefined {
		const registered = this.tools.get(name);
		return registered
			? {
					tool: registered.tool,
					provenance: { ...registered.provenance },
					staticAccesses: registered.staticAccesses?.map((access) => ({ ...access })),
				}
			: undefined;
	}

	/**
	 * Removes extension tools owned by a capability snapshot. Built-ins are never
	 * removed by application reloads; callers must name the provenance they own.
	 */
	removeWhere(predicate: (provenance: ToolProvenance) => boolean): void {
		for (const [name, registered] of this.tools) {
			if (!predicate(registered.provenance)) continue;
			this.tools.delete(name);
			this._validators.delete(name);
			this._mcpToolNames.delete(name);
		}
	}

	list(): Tool<Record<string, unknown>>[] {
		return Array.from(this.tools.values(), (registered) => registered.tool);
	}

	/** Expose tools to the LLM as function definitions. */
	asFunctions(): Array<{
		type: "function";
		function: { name: string; description: string; parameters: ToolParameters };
	}> {
		return this.list().map((t) => ({
			type: "function",
			function: {
				name: t.name,
				description: t.description ?? "",
				parameters: t.parameters ?? { type: "object", properties: {} },
			},
		}));
	}

	validateArgs(toolName: string, args: Record<string, unknown>): void {
		const tool = this.get(toolName);
		if (!tool) {
			throw new Error(`Unknown tool: ${toolName}`);
		}
		let validate = this._validators.get(toolName);
		if (!validate) {
			const schema = normalizeSchema(tool.parameters ?? { type: "object", properties: {} }) as Record<string, unknown>;
			validate = ajv.compile(schema);
			this._validators.set(toolName, validate);
		}
		if (!validate(args)) {
			throw new Error(`Invalid arguments for ${toolName}: ${ajv.errorsText(validate.errors)}`);
		}
	}
}

const RESERVED_PREFIXES: Record<Exclude<ToolRegistrationOptions["origin"], "builtin">, string> = {
	skill: "skill_",
	project_auto: "auto__",
	plugin: "plugin__",
	mcp: "mcp__",
	user: "user__",
};

function validateRegistrationName(name: string, origin: ToolRegistrationOptions["origin"]): void {
	if (origin === "builtin") {
		if (Object.values(RESERVED_PREFIXES).some((prefix) => name.startsWith(prefix))) {
			throw new Error(`Built-in tool ${name} uses a reserved extension namespace`);
		}
		return;
	}
	const requiredPrefix = RESERVED_PREFIXES[origin];
	if (!name.startsWith(requiredPrefix)) {
		throw new Error(`${origin} tool ${name} must use the ${requiredPrefix} namespace`);
	}
}

interface McpContentPart {
	type?: string;
	text?: string;
}

function formatMcpResult(result: unknown): string {
	const content = result && typeof result === "object" ? (result as Record<string, unknown>)["content"] : undefined;
	if (Array.isArray(content)) {
		return content
			.map((c: unknown) => {
				const part = c as McpContentPart;
				if (part && typeof part === "object" && part.type === "text") {
					return String(part.text ?? "");
				}
				return JSON.stringify(c);
			})
			.join("\n");
	}
	return JSON.stringify(result);
}

export type { Tool };
