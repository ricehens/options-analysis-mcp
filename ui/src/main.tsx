import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { applyThemePreference, loadThemePreference } from "./preferences";
import "./styles.css";

applyThemePreference(
  document.documentElement,
  loadThemePreference(window.localStorage),
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
