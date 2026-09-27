import { createKagekoClient, KagekoClient } from "./client/kageko-client.js";
import { SessionClient } from "./session.js";
import { InProcessTransport } from "./transport/in-process-transport.js";
import type { InProcessHandler } from "./transport/in-process-transport.js";
import { createLocalHarness } from "@kageko/application";

export type LocalHarnessOptions = Parameters<typeof createLocalHarness>[0];

export interface DiagnosticEvent {
	readonly code: string;
	readonly message: string;
	readonly error?: unknown;
	readonly sessionId?: string;
	readonly eventType?: string;
}

export class KagekoHarness {
	private constructor(readonly client: KagekoClient) {}
	static inProcess(application: InProcessHandler): KagekoHarness {
		return new KagekoHarness(createKagekoClient(new InProcessTransport(application)));
	}
	static local(options: LocalHarnessOptions = {}): KagekoHarness {
		const application = createLocalHarness(options);
		return KagekoHarness.inProcess({
			handle: (method, payload, context) =>
				application.handle(method, payload, context) as ReturnType<InProcessHandler["handle"]>,
			subscribe: (sessionId, listener) => application.subscribe(sessionId, listener),
			subscribeAll: (listener) => application.subscribeAll(listener),
			openEventStream: (sessionId, fromSequence, listener, context) =>
				application.openEventStream(sessionId, fromSequence, listener, context),
			close: () => application.close(),
		});
	}
	resume(sessionId: string): SessionClient {
		return this.client.session(sessionId);
	}
	close(): Promise<void> {
		return this.client.close();
	}
}
