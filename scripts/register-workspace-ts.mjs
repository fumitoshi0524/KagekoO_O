/**
 * Registers the workspace TypeScript resolution hook. Use with:
 *
 *   node --experimental-transform-types --import ./scripts/register-workspace-ts.mjs <entry>
 *
 * `--experimental-transform-types` is required because the sources use
 * TypeScript-only constructs (e.g. parameter properties) that the default
 * strip-only mode cannot handle.
 */
import { register } from "node:module";

register("./workspace-ts-hook.mjs", import.meta.url);
