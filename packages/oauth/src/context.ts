import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { AuthContext } from "./types.js";
import { kagekoHomeDir } from "./home-dir.js";

/**
 * Create an AuthContext for OAuth auth resolution.
 *
 * Reads environment variables from `process.env` and checks file existence,
 * resolving a leading `~` to the user's homedir.
 */
export function createAuthContext(): AuthContext {
	return {
		async env(name: string): Promise<string | undefined> {
			const value = process.env[name];
			return typeof value === "string" && value.trim().length > 0 ? value : undefined;
		},

		async fileExists(filePath: string): Promise<boolean> {
			let resolved = filePath;
			if (resolved.startsWith("~")) {
				resolved = path.join(kagekoHomeDir(), resolved.slice(1));
			}
			try {
				await fs.access(resolved);
				return true;
			} catch {
				return false;
			}
		},
	};
}
