const PASTE_BURST_MIN_CHARS = 8;
// Keep this generous enough for synchronous TTY adapters and test doubles,
// while still requiring a genuinely rapid run of printable characters.
const PASTE_BURST_CHAR_INTERVAL_MS = 50;
const PASTE_BURST_ACTIVE_IDLE_TIMEOUT_MS = 30;
const PASTE_ENTER_SUPPRESS_WINDOW_MS = 120;

/**
 * Detects a rapid plain-text paste on terminals that do not emit bracketed
 * paste markers. The editor remains live; this only changes an imminent
 * Enter from submit to newline while the burst is active.
 */
export class PasteBurst {
	private lastPlainCharAt: number | undefined;
	private consecutivePlainChars = 0;
	private activeUntil = 0;
	private enterSuppressUntil = 0;

	onPlainChar(now: number): void {
		if (this.lastPlainCharAt !== undefined && now - this.lastPlainCharAt <= PASTE_BURST_CHAR_INTERVAL_MS)
			this.consecutivePlainChars += 1;
		else this.consecutivePlainChars = 1;
		this.lastPlainCharAt = now;
		if (this.consecutivePlainChars >= PASTE_BURST_MIN_CHARS) this.extendWindow(now);
	}

	shouldInsertNewlineInsteadOfSubmit(now: number): boolean {
		if (now <= this.activeUntil || now <= this.enterSuppressUntil) return true;
		return (
			this.lastPlainCharAt !== undefined &&
			this.consecutivePlainChars >= PASTE_BURST_MIN_CHARS &&
			now - this.lastPlainCharAt <= PASTE_BURST_CHAR_INTERVAL_MS
		);
	}

	extendWindow(now: number): void {
		this.activeUntil = now + PASTE_BURST_ACTIVE_IDLE_TIMEOUT_MS;
		this.enterSuppressUntil = now + PASTE_ENTER_SUPPRESS_WINDOW_MS;
	}

	reset(): void {
		this.lastPlainCharAt = undefined;
		this.consecutivePlainChars = 0;
		this.activeUntil = 0;
		this.enterSuppressUntil = 0;
	}
}
