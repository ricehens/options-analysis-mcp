(function () {
  try {
    var theme = window.localStorage.getItem("option-atlas.theme");
    if (theme === "light" || theme === "dark") {
      document.documentElement.dataset.theme = theme;
    }
  } catch (_error) {
    // System appearance remains active when local storage is unavailable.
  }
})();
