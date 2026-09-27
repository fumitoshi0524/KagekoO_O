import { PlanModeGuardDenyPolicy } from "./plan-mode-guard.js";
import { InteractionRequiredDenyPolicy } from "./interaction-required-deny.js";
import { GoalStartReviewAskPermissionPolicy } from "./goal-start-review.js";
import { SensitiveFileAccessAskPermissionPolicy } from "./sensitive-file-access.js";
import { GitControlPathAccessAskPermissionPolicy } from "./git-control-path-access.js";
import { UserConfiguredDenyPermissionPolicy } from "./user-configured-deny.js";
import { UserConfiguredAskPermissionPolicy } from "./user-configured-ask.js";
import { UserConfiguredAllowPermissionPolicy } from "./user-configured-allow.js";
import { GitCwdWriteApprovePermissionPolicy } from "./git-cwd-write-approve.js";
import { SessionApprovalHistoryPolicy } from "./session-approval-history.js";
import { PlanModeToolApprovePermissionPolicy } from "./plan-mode-tool-approve.js";
import { ExitPlanModeReviewAskPermissionPolicy } from "./exit-plan-mode-review.js";
import { UnrestrictedProfileApprovePolicy } from "./unrestricted-profile-approve.js";
import { DefaultToolApprovePolicy } from "./default-tool-approve.js";
import { PublicNetworkApprovePolicy } from "./public-network-approve.js";
import { FallbackAskPolicy } from "./fallback-ask.js";
import { SystemHardlineDenyPolicy } from "./system-hardline-deny.js";
import { ManagedCapabilityPathDenyPolicy } from "./managed-capability-path.js";
import {
	ClassifiedCommandApprovePolicy,
	CommandCredentialEgressDenyPolicy,
	OpaqueCommandAskPolicy,
} from "./command-analysis.js";
import type { PermissionManagerLike, PermissionPolicy, PlanModeState } from "../types.js";
import type { HookEngine } from "../permission-manager.js";

export interface PolicyChainOptions {
	permission: PermissionManagerLike;
	planMode?: PlanModeState;
	hookEngine?: HookEngine;
}

export function createPolicyChain({
	permission,
	planMode,
	hookEngine: _hookEngine,
}: PolicyChainOptions): PermissionPolicy[] {
	return [
		// Global deny / guard policies
		new PlanModeGuardDenyPolicy(planMode),
		new SystemHardlineDenyPolicy(),
		new ManagedCapabilityPathDenyPolicy(permission),
		new CommandCredentialEgressDenyPolicy(),
		new InteractionRequiredDenyPolicy(permission),
		new UserConfiguredDenyPermissionPolicy(permission),
		// An explicit configured ask still wins. After that, a user-approved
		// session rule must precede the policy that originally asked, otherwise
		// opaque/sensitive operations can never honor the "session" choice.
		new UserConfiguredAskPermissionPolicy(permission),
		new SessionApprovalHistoryPolicy(permission),
		// Unrestricted is intentionally below hard denials and an explicit user
		// ask, but above heuristic safety asks. Otherwise an opaque shell command
		// can never run in an unattended unrestricted session.
		new UnrestrictedProfileApprovePolicy(permission),
		// Safety ask policies
		new GoalStartReviewAskPermissionPolicy(permission),
		new SensitiveFileAccessAskPermissionPolicy(permission),
		new GitControlPathAccessAskPermissionPolicy(permission),
		new OpaqueCommandAskPolicy(),
		// User-configured rules
		new UserConfiguredAllowPermissionPolicy(permission),
		// Contextual/default approvals
		new GitCwdWriteApprovePermissionPolicy(permission),
		// Mode-based approvals
		new ExitPlanModeReviewAskPermissionPolicy(permission),
		new PlanModeToolApprovePermissionPolicy(permission),
		new ClassifiedCommandApprovePolicy(permission),
		new PublicNetworkApprovePolicy(),
		new DefaultToolApprovePolicy(),
		// Fallback ask
		new FallbackAskPolicy(permission),
	];
}

export {
	PlanModeGuardDenyPolicy,
	InteractionRequiredDenyPolicy,
	GoalStartReviewAskPermissionPolicy,
	SensitiveFileAccessAskPermissionPolicy,
	GitControlPathAccessAskPermissionPolicy,
	UserConfiguredDenyPermissionPolicy,
	UserConfiguredAskPermissionPolicy,
	UserConfiguredAllowPermissionPolicy,
	GitCwdWriteApprovePermissionPolicy,
	SessionApprovalHistoryPolicy,
	PlanModeToolApprovePermissionPolicy,
	UnrestrictedProfileApprovePolicy,
	DefaultToolApprovePolicy,
	PublicNetworkApprovePolicy,
	FallbackAskPolicy,
	SystemHardlineDenyPolicy,
	ManagedCapabilityPathDenyPolicy,
	ClassifiedCommandApprovePolicy,
	CommandCredentialEgressDenyPolicy,
	OpaqueCommandAskPolicy,
};
