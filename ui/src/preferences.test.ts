import { describe, expect, it } from "vitest";

import {
  FONT_SCALE_STORAGE_KEY,
  loadFontScale,
  normalizeFontScale,
  persistFontScale,
  stepFontScale,
} from "./preferences";

describe("font scale preference", () => {
  it("accepts supported sizes and resets invalid stored values", () => {
    expect(normalizeFontScale("115")).toBe(115);
    expect(normalizeFontScale("200")).toBe(100);
    expect(normalizeFontScale(null)).toBe(100);
  });

  it("steps within the supported accessibility bounds", () => {
    expect(stepFontScale(100, 1)).toBe(115);
    expect(stepFontScale(90, -1)).toBe(90);
    expect(stepFontScale(130, 1)).toBe(130);
  });

  it("loads and persists without exposing storage failures", () => {
    const values = new Map<string, string>([[FONT_SCALE_STORAGE_KEY, "130"]]);
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    };

    expect(loadFontScale(storage)).toBe(130);
    persistFontScale(storage, 90);
    expect(values.get(FONT_SCALE_STORAGE_KEY)).toBe("90");
  });
});
