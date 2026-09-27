/**
 * Node resolution hook that lets plain Node execute the workspace TypeScript
 * sources. The workspace packages export their sources ("exports":
 * "./src/index.ts") whose relative imports use ".js" specifiers, and Node's
 * type stripping does not rewrite those to the real ".ts" files. This hook
 * retries a failed ".js" resolution inside packages/ with the ".ts" sibling.
 */
export async function resolve(specifier, context, nextResolve) {
	try {
		return await nextResolve(specifier, context);
	} catch (error) {
		if (specifier.endsWith(".js") && context.parentURL?.includes("/packages/")) {
			try {
				return await nextResolve(`${specifier.slice(0, -3)}.ts`, context);
			} catch {
				// Fall through and rethrow the original resolution error.
			}
		}
		throw error;
	}
}
