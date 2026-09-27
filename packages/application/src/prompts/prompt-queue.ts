import type { PromptInput } from "./prompt-parts.js";

export class PromptQueue {
	private readonly items: PromptInput[] = [];
	enqueue(input: PromptInput): void {
		this.items.push(input);
	}
	dequeue(): PromptInput | undefined {
		return this.items.shift();
	}
	remove(turnId: string): PromptInput | undefined {
		const index = this.items.findIndex((item) => item.turnId === turnId);
		return index < 0 ? undefined : this.items.splice(index, 1)[0];
	}
	get size(): number {
		return this.items.length;
	}
	clear(): void {
		this.items.length = 0;
	}
}
