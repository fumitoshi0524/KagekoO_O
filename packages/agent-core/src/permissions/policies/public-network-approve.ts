import type { NetworkToolAccess } from "../../tools/types.js";
import type { PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

const PUBLIC_NETWORK_TOOLS = new Set(["web_search", "fetch_url"]);

/** Approves only the built-in, credential-free public GET workflows. */
export class PublicNetworkApprovePolicy implements PermissionPolicy {
	name = "PublicNetworkApprove";

	evaluate({ toolName, execution }: PolicyContext): PolicyResult | undefined {
		if (!PUBLIC_NETWORK_TOOLS.has(toolName) || execution?.provenance?.kind !== "builtin" || !execution.accesses?.length)
			return undefined;
		const accesses = execution.accesses.filter((access): access is NetworkToolAccess => access.kind === "network");
		if (accesses.length !== execution.accesses.length) return undefined;
		if (!accesses.every(isPublicCredentialFreeGet)) return undefined;
		return { kind: "approve", reason: "credential-free public network read" };
	}
}

function isPublicCredentialFreeGet(access: NetworkToolAccess): boolean {
	if (access.credentialed || access.method.toUpperCase() !== "GET") return false;
	if (access.operation !== "search" && access.operation !== "fetch") return false;
	try {
		const url = new URL(access.target);
		if (url.protocol !== "http:" && url.protocol !== "https:") return false;
		if (url.username || url.password) return false;
		return !isObviouslyPrivateHostname(url.hostname);
	} catch {
		return false;
	}
}

function isObviouslyPrivateHostname(hostname: string): boolean {
	const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
	return (
		host === "localhost" ||
		host.endsWith(".localhost") ||
		host === "0.0.0.0" ||
		host === "::" ||
		host === "::1" ||
		/^127\./.test(host) ||
		/^10\./.test(host) ||
		/^192\.168\./.test(host) ||
		/^169\.254\./.test(host) ||
		/^172\.(1[6-9]|2\d|3[01])\./.test(host)
	);
}
