export interface EventSink<T = unknown> {
	publish(event: T): Promise<void>;
}
