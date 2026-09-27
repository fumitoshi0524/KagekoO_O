/**
 * Interactive composition boundary.  UI lifecycle and event coordination live
 * in `app.ts`; consumers deliberately import only this stable public surface.
 */
export { KagekoTui } from "./app.js";
export type { KagekoTuiOptions } from "./app.js";
