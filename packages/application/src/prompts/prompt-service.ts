import { randomUUID } from "node:crypto";
import type { PromptHandle, PromptInput } from "./prompt-parts.js";
import { PromptQueue } from "./prompt-queue.js";
import type { PromptPart } from "./prompt-parts.js";

export class PromptService {
	readonly queue = new PromptQueue();
	private readonly completions = new Map<string, { resolve(): void; reject(error: Error): void }>();
	private readonly handlers = new Map<string, (event: import("@kageko/protocol").RuntimeEvent) => void>();
	private onSubmit?: (input: PromptInput) => Promise<void>;
	private executor?: (
		input: PromptInput,
		onEvent?: (event: import("@kageko/protocol").RuntimeEvent) => void,
	) => Promise<void>;
	constructor(
		onSubmit?: (input: PromptInput) => Promise<void>,
		executor?: (
			input: PromptInput,
			onEvent?: (event: import("@kageko/protocol").RuntimeEvent) => void,
		) => Promise<void>,
	) {
		this.onSubmit = onSubmit;
		this.executor = executor;
	}
	/** Install the application-owned execution path for a live session. */
	configure({
		onSubmit,
		executor,
	}: {
		onSubmit?: (input: PromptInput) => Promise<void>;
		executor?: (
			input: PromptInput,
			onEvent?: (event: import("@kageko/protocol").RuntimeEvent) => void,
		) => Promise<void>;
	}): void {
		this.onSubmit = onSubmit;
		this.executor = executor;
	}
	async submit(
		input: PromptInput,
		onEvent?: (event: import("@kageko/protocol").RuntimeEvent) => void,
	): Promise<PromptHandle> {
		if (this.onSubmit) await this.onSubmit(input);
		return this.prompt(input, onEvent);
	}
	async drain(): Promise<PromptInput | undefined> {
		const next = this.queue.dequeue();
		if (!next) return undefined;
		if (!this.executor) {
			this.completions.get(next.turnId!)?.reject(new Error("Prompt executor is not configured"));
			this.completions.delete(next.turnId!);
			this.handlers.delete(next.turnId!);
			return next;
		}
		try {
			await this.executor(next, this.handlers.get(next.turnId!));
			this.completions.get(next.turnId!)?.resolve();
		} catch (error) {
			this.completions.get(next.turnId!)?.reject(error instanceof Error ? error : new Error(String(error)));
		}
		this.completions.delete(next.turnId!);
		this.handlers.delete(next.turnId!);
		return next;
	}
	prompt(input: PromptInput, onEvent?: (event: import("@kageko/protocol").RuntimeEvent) => void): PromptHandle {
		const turnId = input.turnId ?? randomUUID();
		let resolve!: () => void;
		let reject!: (error: Error) => void;
		const completion = new Promise<void>((res, rej) => {
			resolve = res;
			reject = rej;
		});
		// Queue cancellation may reject before its runner chain reaches the await.
		// Keep a standing observer so Node never treats that interval as unhandled.
		void completion.catch(() => {});
		this.completions.set(turnId, { resolve, reject });
		if (onEvent) this.handlers.set(turnId, onEvent);
		this.queue.enqueue({ ...input, turnId });
		return {
			turnId,
			completion,
			cancel: () => {
				this.queue.remove(turnId);
				this.completions.delete(turnId);
				this.handlers.delete(turnId);
				reject(new Error("Prompt cancelled"));
			},
		};
	}
	cancelQueued(): number {
		let count = 0;
		let next: PromptInput | undefined;
		while ((next = this.queue.dequeue())) {
			if (next.turnId) {
				this.completions.get(next.turnId)?.reject(new Error("Prompt cancelled"));
				this.completions.delete(next.turnId);
				this.handlers.delete(next.turnId);
			}
			count++;
		}
		return count;
	}
}
