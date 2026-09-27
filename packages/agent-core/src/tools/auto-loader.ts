import * as fs from "node:fs/promises";
import * as path from "node:path";
import { spawn } from "node:child_process";
import type { EnvironmentScrubber } from "../ports/workspace.js";
import { validateMcpServerConfig } from "../capabilities/mcp/mcp-manager.js";
import type { Tool, ToolContext, ToolResult } from "./types.js";

const AUTO_TOOL_TIMEOUT_MS = 30000;
const AUTO_TOOL_OUTPUT_CAP = 10000;
export const AUTO_TOOL_ARGUMENTS_PLACEHOLDER = "{{__args_json}}";

const DANGEROUS_EVAL_FLAGS = new Set(["-e", "--eval", "-c", "-p", "--print", "-r", "--require"]);
const DANGEROUS_EVAL_PREFIXES = ["--eval=", "--print=", "--require="];

export interface AutoToolManifest {
	name: string;
	description: string;
	command: string;
	args: string[];
	parameters: Record<string, unknown>;
}

interface AutoToolExecutionOptions {
	timeout?: number;
	cwd?: string;
	windowsHide?: boolean;
}

interface AutoToolExecutionResult {
	stdout: string;
	stderr: string;
	exitCode: number | null;
}

/**
 * Load auto-generated tool manifests from `.kageko/tools/auto/` and
 * register them as executable tools.
 *
 * Supports the package layout (`<name>/manifest.json`) and falls back to the
 * legacy flat layout (`<name>.json`) for backwards compatibility.
 */
export async function loadAutoTools(root: string, scrubEnvironment: EnvironmentScrubber): Promise<Tool[]> {
	const tools: Tool[] = [];
	const entries = await safeReaddir(root);
	for (const entry of entries) {
		const entryPath = path.join(root, entry);
		let filePath: string;
		try {
			const stat = await fs.stat(entryPath);
			if (stat.isDirectory()) {
				filePath = path.join(entryPath, "manifest.json");
			} else if (entry.endsWith(".json")) {
				filePath = entryPath;
			} else {
				continue;
			}
			const text = await fs.readFile(filePath, "utf-8");
			const manifest = JSON.parse(text) as unknown;
			if (validateToolManifest(manifest)) {
				tools.push(createAutoTool(manifest, scrubEnvironment));
			}
		} catch {
			// Ignore unreadable manifests.
		}
	}
	return tools;
}

function createAutoTool(manifest: AutoToolManifest, scrubEnvironment: EnvironmentScrubber): Tool {
	return {
		name: `auto__${normalizeExtensionName(manifest.name)}`,
		description: manifest.description,
		parameters: manifest.parameters,
		async execute(args: Record<string, unknown>, context: ToolContext): Promise<ToolResult> {
			try {
				const required = new Set(
					Array.isArray(manifest.parameters["required"])
						? manifest.parameters["required"].filter((value): value is string => typeof value === "string")
						: [],
				);
				const substituted = manifest.args.map((template) => substitute(template, args, required));
				if (isInterpreterCommand(manifest.command) && hasCodeExecutionFlag(substituted)) {
					return { output: "Auto tool uses a forbidden interpreter execution flag.", isError: true };
				}
				const { stdout, stderr } = await execFileCapped(
					manifest.command,
					substituted,
					{
						timeout: AUTO_TOOL_TIMEOUT_MS,
						cwd: context.session?.cwd ?? process.cwd(),
						windowsHide: true,
					},
					scrubEnvironment,
				);
				let output = stdout;
				if (stderr) output += `\nstderr: ${stderr}`;
				return { output: output.slice(0, AUTO_TOOL_OUTPUT_CAP) };
			} catch (err) {
				return { output: `Auto tool failed: ${(err as Error).message}`, isError: true };
			}
		},
	};
}

function normalizeExtensionName(name: string): string {
	const normalized = name.replace(/[^A-Za-z0-9_]/g, "_").replace(/^_+|_+$/g, "");
	if (!normalized) throw new Error(`Auto tool name ${JSON.stringify(name)} has no usable characters`);
	return normalized;
}

function substitute(template: string, args: Record<string, unknown>, required: ReadonlySet<string>): string {
	if (template === AUTO_TOOL_ARGUMENTS_PLACEHOLDER) return JSON.stringify(args ?? {});
	return String(template).replace(/\{\{(\w+)\}\}/g, (_, key: string) => {
		const value = args?.[key];
		if (value === undefined) {
			if (required.has(key)) throw new Error(`Missing required auto-tool argument: ${key}`);
			return "";
		}
		if (typeof value === "string") return value;
		const serialized = JSON.stringify(value);
		return serialized === undefined ? String(value) : serialized;
	});
}

function validateToolManifest(manifest: unknown): manifest is AutoToolManifest {
	if (!manifest || typeof manifest !== "object") return false;
	const m = manifest as Record<string, unknown>;
	return (
		typeof m["name"] === "string" &&
		m["name"].length > 0 &&
		typeof m["description"] === "string" &&
		validateMcpServerConfig({ command: m["command"], args: m["args"] }) &&
		m["parameters"] !== null &&
		typeof m["parameters"] === "object" &&
		// Narrow command/args to their expected types for the manifest guard.
		typeof m["command"] === "string" &&
		Array.isArray(m["args"])
	);
}

function isInterpreterCommand(command: string): boolean {
	const base = path.basename(command.replaceAll("\\", "/"), path.extname(command)).toLowerCase();
	return /^(?:python|node|ruby|perl|php)[\d.]*$/.test(base) || /^nodejs[\d.]*$/.test(base);
}

function hasCodeExecutionFlag(args: string[]): boolean {
	return args.some((arg) => {
		if (typeof arg !== "string") return false;
		if (DANGEROUS_EVAL_FLAGS.has(arg)) return true;
		if (DANGEROUS_EVAL_PREFIXES.some((prefix) => arg.startsWith(prefix))) return true;
		return /^-[^-]+$/.test(arg) && [...arg.slice(1)].some((flag) => "ecpr".includes(flag));
	});
}

function execFileCapped(
	command: string,
	args: string[],
	options: AutoToolExecutionOptions,
	scrubEnvironment: EnvironmentScrubber,
): Promise<AutoToolExecutionResult> {
	return new Promise((resolve, reject) => {
		const proc = spawn(command, args, {
			...options,
			env: scrubEnvironment(process.env),
			stdio: ["ignore", "pipe", "pipe"],
		});
		let stdout: Buffer = Buffer.alloc(0);
		let stderr: Buffer = Buffer.alloc(0);
		let killed = false;
		const timer: ReturnType<typeof setTimeout> | undefined = options.timeout
			? setTimeout(() => {
					killed = true;
					proc.kill();
				}, options.timeout)
			: undefined;
		const accumulate = (target: Buffer, chunk: Buffer): Buffer => {
			if (killed) return target;
			const remaining = AUTO_TOOL_OUTPUT_CAP - target.length;
			if (chunk.length > remaining) {
				target = Buffer.concat([target, chunk.subarray(0, Math.max(0, remaining))]);
				killed = true;
				proc.kill();
				return target;
			}
			return Buffer.concat([target, chunk]);
		};
		proc.stdout?.on("data", (chunk: Buffer) => {
			stdout = accumulate(stdout, chunk);
		});
		proc.stderr?.on("data", (chunk: Buffer) => {
			stderr = accumulate(stderr, chunk);
		});
		proc.on("error", (err: Error) => {
			clearTimeout(timer);
			reject(err);
		});
		proc.on("close", (exitCode: number | null) => {
			clearTimeout(timer);
			resolve({
				stdout: stdout.toString("utf-8"),
				stderr: stderr.toString("utf-8"),
				exitCode: exitCode ?? null,
			});
		});
	});
}

async function safeReaddir(dir: string): Promise<string[]> {
	try {
		return await fs.readdir(dir);
	} catch {
		return [];
	}
}
