import type { ActivityRecord, ConnectionState, Overlay, QueuedPrompt, TranscriptRecord, TuiState } from "./types.js";

export const initialTuiState = (): TuiState => ({
	overlay: "none",
	submitting: false,
	connection: "ready",
	turnLive: false,
	transcript: [],
	activities: new Map(),
	queue: [],
});
export type TuiAction =
	| { type: "overlay"; value: Overlay }
	| { type: "connection"; value: ConnectionState }
	| { type: "submitting"; value: boolean }
	| { type: "turn"; value: boolean }
	| { type: "session"; value?: string }
	| { type: "record"; value: TranscriptRecord }
	| { type: "replace"; id: string; patch: Partial<TranscriptRecord> }
	| { type: "activity"; value: ActivityRecord }
	| { type: "queue"; value: QueuedPrompt[] }
	| { type: "reset-session"; value?: string };

export function reduceTui(state: TuiState, action: TuiAction): TuiState {
	switch (action.type) {
		case "overlay":
			return { ...state, overlay: action.value };
		case "connection":
			return { ...state, connection: action.value };
		case "submitting":
			return { ...state, submitting: action.value };
		case "turn":
			return { ...state, turnLive: action.value };
		case "session":
			return { ...state, sessionId: action.value };
		case "record":
			return { ...state, transcript: [...state.transcript, action.value] };
		case "replace":
			return {
				...state,
				transcript: state.transcript.map((record) =>
					record.id === action.id ? { ...record, ...action.patch } : record,
				),
			};
		case "activity": {
			const activities = new Map(state.activities);
			activities.set(action.value.id, action.value);
			return { ...state, activities };
		}
		case "queue":
			return { ...state, queue: action.value };
		case "reset-session":
			return { ...initialTuiState(), sessionId: action.value };
	}
}
