import { defineConfig } from "vitest/config";

/**
 * Product acceptance has a deliberately different universe from development
 * checks.  It starts a built executable in an isolated home/workspace and may
 * use a real PTY, but must never resolve workspace packages to source files.
 */
export default defineConfig({
	test: {
		name: "acceptance",
		include: ["test/acceptance/**/*.test.ts"],
		testTimeout: 180_000,
		fileParallelism: false,
		pool: "forks",
	},
});
