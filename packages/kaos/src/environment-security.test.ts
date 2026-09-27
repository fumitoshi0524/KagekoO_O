import { describe, expect, it } from "vitest";
import { safeInheritedEnvironment, scrubEnvironment } from "./environment.js";

describe("child process environment boundary", () => {
	it("removes common credentials and Node injection settings by default", () => {
		const inherited = {
			PATH: "/usr/bin",
			KAGEKO_API_KEY: "secret-key",
			OPENAI_API_KEY: "another-secret",
			DATABASE_URL: "postgres://user:password@host/db",
			NODE_OPTIONS: "--require ./injected.js",
			NODE_PATH: "./untrusted-modules",
		};
		for (const result of [scrubEnvironment(inherited), safeInheritedEnvironment(inherited)]) {
			expect(result).toEqual({ PATH: "/usr/bin" });
		}
	});
});
