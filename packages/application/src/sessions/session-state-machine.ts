export type SessionStatus = "created" | "ready" | "running" | "closing" | "closed" | "failed";

const ALLOWED_TRANSITIONS: Readonly<Record<SessionStatus, readonly SessionStatus[]>> = {
	created: ["ready", "closing", "failed"],
	ready: ["running", "closing", "failed"],
	running: ["ready", "closing", "failed"],
	closing: ["closed", "failed"],
	closed: [],
	failed: ["closing", "closed"],
};

export class SessionStateMachine {
	private _status: SessionStatus = "created";
	get status(): SessionStatus {
		return this._status;
	}
	transition(next: SessionStatus): void {
		if (next === this._status) return;
		if (!ALLOWED_TRANSITIONS[this._status].includes(next)) {
			throw new Error(`Invalid session state transition: ${this._status} -> ${next}`);
		}
		this._status = next;
	}
}
