import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ThemeControls from "./ThemeControls";

const stylesheet = readFileSync(new URL("./styles.css", import.meta.url), "utf8");
const themeInitializer = readFileSync(
  new URL("../public/theme-init.js", import.meta.url),
  "utf8",
);

function hexRgb(value: string): [number, number, number] {
  const normalized = value.replace("#", "");
  return [0, 2, 4].map((offset) =>
    Number.parseInt(normalized.slice(offset, offset + 2), 16),
  ) as [number, number, number];
}

function luminance(value: string): number {
  const channels = hexRgb(value).map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(first: string, second: string): number {
  const lighter = Math.max(luminance(first), luminance(second));
  const darker = Math.min(luminance(first), luminance(second));
  return (lighter + 0.05) / (darker + 0.05);
}

describe("theme controls", () => {
  it("exposes system, light, and dark as pressed-state buttons", () => {
    const markup = renderToStaticMarkup(
      <ThemeControls onChange={() => undefined} theme="dark" />,
    );

    expect(markup).toContain('aria-label="Color theme"');
    expect(markup).toContain("System");
    expect(markup).toContain("Light");
    expect(markup).toContain('aria-pressed="true"');
    expect(markup).toContain(">Dark</button>");
  });

  it("keeps component color literals behind semantic custom properties", () => {
    const missing = [...stylesheet.matchAll(/var\(--([a-z-]+)\)/g)]
      .map((match) => match[1])
      .filter((name) => !stylesheet.includes(`--${name}:`));
    const literalOutsideToken = stylesheet
      .split("\n")
      .filter((line) => /#[0-9a-f]{3,8}|rgba?\(/i.test(line))
      .filter((line) => !line.trimStart().startsWith("--"));

    expect([...new Set(missing)]).toEqual([]);
    expect(literalOutsideToken).toEqual([]);
    expect(stylesheet).toContain(":root:not([data-theme])");
  });

  it("applies a valid stored override before the application mounts", () => {
    expect(themeInitializer).toContain('getItem("option-atlas.theme")');
    expect(themeInitializer).toContain('theme === "light" || theme === "dark"');
    expect(themeInitializer).not.toContain("system");
  });

  it("uses readable core foreground colors in both palettes", () => {
    const palettePairs = [
      ["#17221e", "#f3f6f4"],
      ["#5d6f68", "#ffffff"],
      ["#08734b", "#ffffff"],
      ["#e7efeb", "#0b1211"],
      ["#8fa19a", "#111b19"],
      ["#8df0bd", "#111b19"],
    ];

    expect(palettePairs.every(([foreground, background]) =>
      contrast(foreground, background) >= 4.5,
    )).toBe(true);
  });
});
