import { describe, expect, it, vi } from "vitest";
import { EventStreamOverflowError, type Event, type SessionClient } from "@kageko/node-sdk";

import { SessionEventStream } from "../src/tui/session-event-stream.js";

const event = (sequence: number): Event =>
	({
		type: "turn.end",
		meta: { sequence, sessionId: "s", eventId: `e-${sequence}`, occurredAt: sequence, recordedAt: sequence, schemaVersion: 1 },
		data: { result: { stopReason: "stop" } },
	}) as Event;

function iterable(values: readonly (Event | Error)[]): AsyncIterable<Event> {
	return {
		[Symbol.asyncIterator]() {
			let index = 0;
			return {
				next: async () => {
					const value = values[index++];
					if (value === undefined) return { done: true, value: undefined } as const;
					if (value instanceof Error) throw value;
					return { done: false, value } as const;
				},
				return: async () => ({ done: true, value: undefined } as const),
			};
		},
	};
}

describe("SessionEventStream", () => {
	it("recovers overflow and deduplicates replayed durable events", async () => {
		const streams = [iterable([event(1), new EventStreamOverflowError("s", 1, 1)]), iterable([event(1), event(2)])];
		const session = { events: vi.fn(() => streams.shift()!) } as unknown as SessionClient;
		const received: number[] = [];
		let active = true;
		const stream = new SessionEventStream({
			isActive: () => active,
			onEvent: (value) => {
				received.push("sequence" in value.meta ? value.meta.sequence : -1);
				if (received.length === 2) active = false;
			},
			onReconnect: vi.fn(),
			onError: vi.fn(),
		});

		await stream.start(session, 0);

		expect(received).toEqual([1, 2]);
		expect(session.events).toHaveBeenCalledWith({ fromSequence: 1 });
		expect(session.events).toHaveBeenCalledWith({ fromSequence: 2 });
	});

	it("retries a transient non-overflow iterator failure from the durable sequence", async () => {
		const streams = [iterable([new Error("temporary transport failure")]), iterable([event(1)])];
		const session = { events: vi.fn(() => streams.shift()!) } as unknown as SessionClient;
		const onError = vi.fn();
		let active = true;
		const stream = new SessionEventStream({
			isActive: () => active,
			onEvent: () => {
				active = false;
			},
			onReconnect: vi.fn(),
			onError,
		});

		await stream.start(session, 0);

		expect(session.events).toHaveBeenNthCalledWith(1, { fromSequence: 1 });
		expect(session.events).toHaveBeenNthCalledWith(2, { fromSequence: 1 });
		expect(onError).not.toHaveBeenCalled();
	});

	it("reopens a finite event tail so later turn-end events are not missed", async () => {
		const streams = [iterable([event(1)]), iterable([event(2)])];
		const session = { events: vi.fn(() => streams.shift()!) } as unknown as SessionClient;
		const received: number[] = [];
		let active = true;
		const stream = new SessionEventStream({
			isActive: () => active,
			onEvent: (value) => {
				received.push("sequence" in value.meta ? value.meta.sequence : -1);
				if (received.length === 2) active = false;
			},
			onReconnect: vi.fn(),
			onError: vi.fn(),
		});

		await stream.start(session, 0);

		expect(received).toEqual([1, 2]);
		expect(session.events).toHaveBeenNthCalledWith(2, { fromSequence: 2 });
	});
});
