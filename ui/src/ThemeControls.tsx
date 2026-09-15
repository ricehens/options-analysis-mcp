import { THEME_OPTIONS } from "./preferences";
import type { ThemePreference } from "./preferences";

interface ThemeControlsProps {
  onChange: (theme: ThemePreference) => void;
  theme: ThemePreference;
}

export default function ThemeControls({
  onChange,
  theme,
}: ThemeControlsProps) {
  return (
    <div className="preference-card theme-card">
      <span>Appearance</span>
      <div aria-label="Color theme" className="theme-controls" role="group">
        {THEME_OPTIONS.map((option) => (
          <button
            aria-pressed={theme === option}
            key={option}
            onClick={() => onChange(option)}
            title={
              option === "system"
                ? "Follow the device appearance"
                : `Always use ${option} appearance`
            }
            type="button"
          >
            {option[0].toUpperCase() + option.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
