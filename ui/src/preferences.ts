export const FONT_SCALE_OPTIONS = [90, 100, 115, 130] as const;
export type FontScale = (typeof FONT_SCALE_OPTIONS)[number];

export const FONT_SCALE_STORAGE_KEY = "option-atlas.font-scale";

export const THEME_OPTIONS = ["system", "light", "dark"] as const;
export type ThemePreference = (typeof THEME_OPTIONS)[number];
export const THEME_STORAGE_KEY = "option-atlas.theme";

export function normalizeFontScale(value: string | null): FontScale {
  const parsed = Number(value);
  return FONT_SCALE_OPTIONS.includes(parsed as FontScale)
    ? (parsed as FontScale)
    : 100;
}

export function stepFontScale(
  current: FontScale,
  direction: -1 | 1,
): FontScale {
  const index = FONT_SCALE_OPTIONS.indexOf(current);
  const next = Math.min(
    FONT_SCALE_OPTIONS.length - 1,
    Math.max(0, index + direction),
  );
  return FONT_SCALE_OPTIONS[next];
}

export function loadFontScale(
  storage: Pick<Storage, "getItem">,
): FontScale {
  try {
    return normalizeFontScale(storage.getItem(FONT_SCALE_STORAGE_KEY));
  } catch {
    return 100;
  }
}

export function persistFontScale(
  storage: Pick<Storage, "setItem">,
  scale: FontScale,
): void {
  try {
    storage.setItem(FONT_SCALE_STORAGE_KEY, String(scale));
  } catch {
    // A blocked storage preference must not prevent the local app from working.
  }
}

export function normalizeThemePreference(value: string | null): ThemePreference {
  return THEME_OPTIONS.includes(value as ThemePreference)
    ? (value as ThemePreference)
    : "system";
}

export function loadThemePreference(
  storage: Pick<Storage, "getItem">,
): ThemePreference {
  try {
    return normalizeThemePreference(storage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "system";
  }
}

export function persistThemePreference(
  storage: Pick<Storage, "setItem">,
  theme: ThemePreference,
): void {
  try {
    storage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // A blocked storage preference must not prevent the local app from working.
  }
}

export function applyThemePreference(
  target: Pick<HTMLElement, "dataset">,
  theme: ThemePreference,
): void {
  if (theme === "system") {
    delete target.dataset.theme;
  } else {
    target.dataset.theme = theme;
  }
}
