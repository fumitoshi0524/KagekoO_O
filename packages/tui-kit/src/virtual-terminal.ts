import { EventEmitter } from "node:events";
import type { TerminalPort } from "./terminal.js";

/** Deterministic terminal double used by renderer and controller tests. */
export class VirtualTerminal extends EventEmitter implements TerminalPort {
	isTTY = true;
	columns = 80;
	rows = 24;
	readonly writes: string[] = [];
	rawMode = false;
	get isRaw(): boolean {
		return this.rawMode;
	}
	write(value: string): boolean {
		this.writes.push(value);
		return true;
	}
	setRawMode(enabled: boolean): void {
		this.rawMode = enabled;
	}
	resume(): void {}
	pause(): void {}
	input(value: string): void {
		this.emit("data", value);
	}
	resize(columns: number, rows: number): void {
		this.columns = columns;
		this.rows = rows;
		this.emit("resize");
	}
}
