import type {
  DataQualityWarning,
  FieldProvenance,
} from "./types";

interface Props {
  warnings: DataQualityWarning[];
  title: string;
  provenance?: Record<string, FieldProvenance>;
  compact?: boolean;
}
function label(code: string): string {
  return code
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function source(field: string, provenance?: Record<string, FieldProvenance>) {
  const detail = provenance?.[field];
  if (!detail) return null;
  const origin = detail.provider_id ?? detail.method ?? detail.kind;
  return (
    <small>
      {origin} · {detail.kind} · {detail.as_of}
    </small>
  );
}

export default function WarningDisclosure({
  warnings,
  title,
  provenance,
  compact = false,
}: Props) {
  if (!warnings.length) return null;
  return (
    <details className={`warning-disclosure ${compact ? "compact" : ""}`}>
      <summary aria-label={`${title}: ${warnings.length} warnings`}>
        <span aria-hidden="true" className="warning-symbol">!</span>
        {compact ? warnings.length : `${title} (${warnings.length})`}
      </summary>
      <div className="warning-list">
        {warnings.map((warning, index) => (
          <article key={`${warning.code}-${index}`}>
            <strong>{label(warning.code)}</strong>
            <code>{warning.code}</code>
            <p>{warning.message}</p>
            {warning.fields.length ? (
              <ul>
                {warning.fields.map((field) => (
                  <li key={field}>
                    <span>{field}</span>
                    {source(field, provenance)}
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
    </details>
  );
}
