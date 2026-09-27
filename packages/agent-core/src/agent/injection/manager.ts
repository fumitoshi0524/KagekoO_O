import {
	PlanModeInjector,
	AuthorizationContextInjector,
	TodoListInjector,
	GoalInjector,
	BackgroundTaskInjector,
} from "./injectors.js";
import type { Injector, InjectorSession } from "./injectors.js";

export interface InjectedMessage {
	role: string;
	content: string;
	origin?: string;
	variant?: string;
	[key: string]: unknown;
}

export interface InjectionDiagnostic {
	readonly variant: string;
	readonly error: unknown;
}

export interface InjectionManagerOptions {
	onDiagnostic?: (diagnostic: InjectionDiagnostic) => void | Promise<void>;
}

/**
 * Collects contextual system reminders and appends them to the message list.
 */
export class InjectionManager {
	readonly session: InjectorSession;
	readonly injectors: Injector[];
	private readonly onDiagnostic?: InjectionManagerOptions["onDiagnostic"];

	constructor(session: InjectorSession, { onDiagnostic }: InjectionManagerOptions = {}) {
		this.session = session;
		this.onDiagnostic = onDiagnostic;
		this.injectors = [
			new PlanModeInjector(session),
			new AuthorizationContextInjector(session),
			new TodoListInjector(session),
			new GoalInjector(session),
			new BackgroundTaskInjector(session),
		];
	}

	async inject(messages: InjectedMessage[]): Promise<void> {
		// Context injection is a derived, per-step snapshot. Removing the previous
		// snapshot prevents reminders from multiplying across tool steps/turns.
		for (let index = messages.length - 1; index >= 0; index -= 1) {
			if (messages[index]?.origin === "injection") messages.splice(index, 1);
		}
		for (const injector of this.injectors) {
			try {
				const text = await injector.getInjection();
				if (text) {
					messages.push({ role: "system", content: text, origin: "injection", variant: injector.variant });
				}
			} catch (error) {
				// One optional source must never block other injections or the turn.
				try {
					await this.onDiagnostic?.({ variant: injector.variant, error });
				} catch {
					// Diagnostics are best-effort observers too.
				}
			}
		}
	}
}
