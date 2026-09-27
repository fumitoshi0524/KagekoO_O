/**
 * Vitest setup file: makes every test worker hermetic.
 *
 * - Deletes credential-shaped environment variables (suffixes `_API_KEY`,
 *   `_TOKEN`, `_SECRET`, `_PASSWORD`, plus an explicit provider list) so no
 *   test can accidentally read real credentials from the developer machine.
 *   Tests that need one of these variables must set it themselves.
 * - Pins `TZ=UTC` so time-sensitive assertions are timezone-independent.
 */

const CREDENTIAL_SUFFIX = /(?:_API_KEY|_TOKEN|_SECRET|_PASSWORD)$/;

// Explicit list for documentation value; every entry is also covered by
// CREDENTIAL_SUFFIX. Mirrors the provider env table in
// packages/application/src/harness/composition-root.ts.
const EXPLICIT_SCRUB: readonly string[] = [
	"KAGEKO_API_KEY",
	"KIMI_API_KEY",
	"KIMI_CODING_API_KEY",
	"KIMI_CN_API_KEY",
	"OPENAI_API_KEY",
	"ANTHROPIC_API_KEY",
	"ANTHROPIC_TOKEN",
	"CLAUDE_CODE_OAUTH_TOKEN",
	"GOOGLE_API_KEY",
	"GEMINI_API_KEY",
	"MISTRAL_API_KEY",
	"QWEN_API_KEY",
	"DASHSCOPE_API_KEY",
	"XAI_API_KEY",
	"MINIMAX_API_KEY",
	"DEEPSEEK_API_KEY",
];

for (const key of Object.keys(process.env)) {
	if (CREDENTIAL_SUFFIX.test(key) || EXPLICIT_SCRUB.includes(key)) {
		delete process.env[key];
	}
}

process.env["TZ"] = "UTC";
