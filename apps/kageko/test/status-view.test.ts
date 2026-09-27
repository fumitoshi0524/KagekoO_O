import { describe, expect, it } from "vitest";
import { renderRowText } from "@kageko/tui-kit";

import { footerLines } from "../src/tui/views/status-view.js";

describe("footer permission policy badge", () => {
	it("shows the active profile and unattended interaction mode", () => {
		const rows = footerLines(
			"none",
			{
				atTail: true,
				queued: 0,
				cwd: "/workspace",
				permissionProfile: "unrestricted",
				interactionMode: "unattended",
			},
			80,
		);

		expect(renderRowText(rows[0]!)).toContain("perm:unrestricted unattended");
		expect(rows[0]!.spans.find((span) => String(span.text).includes("perm:unrestricted"))).toMatchObject({
			tone: "warning",
			bold: true,
		});
	});
});
