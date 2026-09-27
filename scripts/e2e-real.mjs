#!/usr/bin/env node
/**
 * Real end-to-end LLM validation through the public node-sdk surface.
 *
 * Starts an in-process harness via `KagekoHarness.local` in a temporary
 * directory and asks the model to reply with "pong". Exits 0 when the
 * response contains "pong", and 1 otherwise — including when the turn does
 * not complete before the overall timeout (KAGEKO_E2E_TIMEOUT_MS, default
 * 180000), so CI cannot hang indefinitely.
 *
 * Runtime caveat: the workspace packages export their TypeScript sources
 * ("exports": "./src/index.ts") whose relative imports use ".js" specifiers,
 * and bare `node scripts/e2e-real.mjs` cannot load those. Run through the
 * committed type-stripping hook instead (this is what `npm run test:e2e`
 * does):
 *
 *   node --experimental-transform-types --import ./scripts/register-workspace-ts.mjs scripts/e2e-real.mjs
 *
 * Note: `discoverModels` is imported from the foundation package
 * `@kageko/kosong` because the node-sdk does not expose an equivalent
 * model-discovery capability.
 *
 * Usage:
 *   KAGEKO_E2E_PROVIDER=openai KAGEKO_E2E_MODEL_NAME=gpt-4o-mini KAGEKO_E2E_API_KEY=sk-... npm run test:e2e
 *   KAGEKO_E2E_PROVIDER=anthropic KAGEKO_E2E_MODEL_NAME=claude-sonnet-4-20250514 KAGEKO_E2E_API_KEY=sk-... npm run test:e2e
 *   KAGEKO_E2E_PROVIDER=faux npm run test:e2e   # offline smoke; the faux model
 *     never says "pong", so expect FAIL — but it proves the full wiring
 *     (session creation, prompt, turn events) completes instead of hanging.
 */
import { KagekoHarness } from "@kageko/node-sdk";
import { discoverModels } from "@kageko/kosong";
import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";

const provider = process.env.KAGEKO_E2E_PROVIDER || "openai";
let modelName = process.env.KAGEKO_E2E_MODEL_NAME;
const apiKey = process.env.KAGEKO_E2E_API_KEY;
const timeoutMs = Number.parseInt(process.env.KAGEKO_E2E_TIMEOUT_MS ?? "", 10) || 180000;

if (!apiKey && provider !== "faux") {
	console.error(
		"Set KAGEKO_E2E_API_KEY to run the real LLM end-to-end test.\n" +
			"Required: KAGEKO_E2E_PROVIDER, KAGEKO_E2E_API_KEY.\n" +
			"Optional: KAGEKO_E2E_MODEL_NAME, KAGEKO_E2E_TIMEOUT_MS.\n" +
			"Offline smoke: KAGEKO_E2E_PROVIDER=faux (no API key needed).",
	);
	process.exit(1);
}

if (!modelName && provider === "faux") {
	modelName = "faux";
}

if (!modelName) {
	try {
		const models = await discoverModels(provider, { apiKey });
		if (models.length === 0) {
			console.error("Model discovery returned no models.");
			process.exit(1);
		}
		modelName = models[0].id;
	} catch (err) {
		console.error("Model discovery failed:", err);
		process.exit(1);
	}
}

const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-e2e-"));
let harness;

try {
	harness = KagekoHarness.local({
		cwd: tmpDir,
		permission: "unrestricted",
		provider,
		model: modelName,
		apiKey,
	});

	const session = await harness.client.createSession({ cwd: tmpDir });

	let text = "";
	let timeoutHandle;
	await Promise.race([
		session.promptAndWait(
			{ parts: [{ type: "text", text: "Reply with the single word 'pong' and nothing else." }] },
			(event) => {
				if (event.type === "assistant.text") text += event.data.content;
			},
		),
		new Promise((_, reject) => {
			timeoutHandle = setTimeout(
				() => reject(new Error(`Timed out after ${timeoutMs}ms waiting for turn completion`)),
				timeoutMs,
			);
			timeoutHandle.unref?.();
		}),
	]).finally(() => clearTimeout(timeoutHandle));

	if (text.toLowerCase().includes("pong")) {
		console.log(`PASS: provider=${provider} model=${modelName}`);
		process.exitCode = 0;
	} else {
		console.error(`FAIL: provider=${provider} model=${modelName} response=`, text);
		process.exitCode = 1;
	}
} catch (err) {
	console.error(`ERROR: provider=${provider} model=${modelName}`, err);
	process.exitCode = 1;
} finally {
	await harness?.close().catch(() => {});
	await fs.rm(tmpDir, { recursive: true, force: true }).catch(() => {});
}
