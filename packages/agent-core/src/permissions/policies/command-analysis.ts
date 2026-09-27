import type { PermissionManagerLike, PermissionPolicy, PolicyContext, PolicyResult } from "../types.js";

export class CommandCredentialEgressDenyPolicy implements PermissionPolicy {
	name = "CommandCredentialEgressDeny";

	evaluate({ execution }: PolicyContext): PolicyResult | undefined {
		const analysis = execution?.commandAnalysis;
		if (analysis?.effects.credentials !== "export") return undefined;
		return { kind: "deny", message: "Generic shell commands may not export credential material" };
	}
}

export class OpaqueCommandAskPolicy implements PermissionPolicy {
	name = "OpaqueCommandAsk";

	evaluate({ execution }: PolicyContext): PolicyResult | undefined {
		const analysis = execution?.commandAnalysis;
		if (!analysis || analysis.risk !== "opaque") return undefined;
		return { kind: "ask", reason: `command could not be classified safely: ${analysis.reasons.join("; ")}` };
	}
}

export class ClassifiedCommandApprovePolicy implements PermissionPolicy {
	name = "ClassifiedCommandApprove";

	constructor(private readonly permission: PermissionManagerLike) {}

	evaluate({ execution }: PolicyContext): PolicyResult | undefined {
		const analysis = execution?.commandAnalysis;
		if (!analysis) return undefined;
		if (analysis.risk === "safe") return { kind: "approve", reason: analysis.reasons.join("; ") };
		if (analysis.risk === "workspace" && this.permission.profile === "workspace") {
			return { kind: "approve", reason: analysis.reasons.join("; ") };
		}
		return undefined;
	}
}
