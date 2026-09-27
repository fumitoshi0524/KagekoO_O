import type { Transport } from "../transport/transport.js";
export interface ClientOptions {
	readonly transport: Transport;
}
