import { describe, expect, it } from "vitest";

import {
  applyThemePreference,
  FONT_SCALE_STORAGE_KEY,
  loadFontScale,
  loadThemePreference,
  normalizeFontScale,
  normalizeThemePreference,
  persistFontScale,
  persistThemePreference,
  stepFontScale,
  THEME_STORAGE_KEY,
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

describe("theme preference", () => {
  it("accepts supported modes and resets invalid values to system", () => {
    expect(normalizeThemePreference("light")).toBe("light");
    expect(normalizeThemePreference("dark")).toBe("dark");
    expect(normalizeThemePreference("sepia")).toBe("system");
    expect(normalizeThemePreference(null)).toBe("system");
  });

  it("loads and persists the preference", () => {
    const values = new Map<string, string>([[THEME_STORAGE_KEY, "dark"]]);
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    };

    expect(loadThemePreference(storage)).toBe("dark");
    persistThemePreference(storage, "light");
    expect(values.get(THEME_STORAGE_KEY)).toBe("light");
  });

  it("uses an explicit attribute only for forced modes", () => {
    const target = { dataset: {} as DOMStringMap };

    applyThemePreference(target, "dark");
    expect(target.dataset.theme).toBe("dark");
    applyThemePreference(target, "system");
    expect(target.dataset.theme).toBeUndefined();
  });
});
