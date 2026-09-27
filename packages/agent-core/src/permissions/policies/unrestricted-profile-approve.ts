import type { PermissionManagerLike, PermissionPolicy, PolicyResult } from "../types.js";

/** Approves requests left after non-bypassable guards and explicit user rules. */
export class UnrestrictedProfileApprovePolicy implements PermissionPolicy {
	name = "UnrestrictedProfileApprove";

	constructor(private readonly permission: PermissionManagerLike) {}

	evaluate(): PolicyResult | undefined {
		return this.permission.profile === "unrestricted"
			? { kind: "approve", reason: "unrestricted permission profile" }
			: undefined;
	}
}
