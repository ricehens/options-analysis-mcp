import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import WarningDisclosure from "./WarningDisclosure";

describe("warning disclosure", () => {
  it("renders nothing when there are no warnings", () => {
    expect(
      renderToStaticMarkup(
        <WarningDisclosure title="Contract warnings" warnings={[]} />,
      ),
    ).toBe("");
  });

  it("renders codes, messages, fields, and field provenance", () => {
    const markup = renderToStaticMarkup(
      <WarningDisclosure
        provenance={{
          as_of: {
            kind: "provider",
            provider_id: "schwab",
            as_of: "2026-09-14T12:00:00Z",
            method: null,
          },
        }}
        title="Contract warnings"
        warnings={[
          {
            code: "stale_quote",
            message: "The quote is stale.",
            fields: ["as_of"],
          },
        ]}
      />,
    );

    expect(markup).toContain("Contract warnings (1)");
    expect(markup).toContain("stale_quote");
    expect(markup).toContain("The quote is stale.");
    expect(markup).toContain("as_of");
    expect(markup).toContain("schwab · provider · 2026-09-14T12:00:00Z");
  });

  it("uses the compact count treatment for table cells", () => {
    const markup = renderToStaticMarkup(
      <WarningDisclosure
        compact
        title="SPY call warnings"
        warnings={[{ code: "missing_market", message: "No market.", fields: [] }]}
      />,
    );

    expect(markup).toContain("warning-disclosure compact");
    expect(markup).toContain("SPY call warnings: 1 warnings");
  });
});
