/* High-contrast mode (CRB-NF-005): a header button switches it on or off and the choice is remembered. */
(function () {
  "use strict";
  var root = document.documentElement;
  var button = document.getElementById("contrast-toggle");
  if (!button) return;

  function show() {
    var on = root.getAttribute("data-contrast") === "high";
    button.setAttribute("aria-pressed", on ? "true" : "false");
    button.textContent = on ? "Normal contrast" : "High contrast";
  }

  button.addEventListener("click", function () {
    var on = root.getAttribute("data-contrast") !== "high";
    if (on) {
      root.setAttribute("data-contrast", "high");
    } else {
      root.removeAttribute("data-contrast");
    }
    try { localStorage.setItem("crb-contrast", on ? "high" : "normal"); } catch (e) { /* storage blocked */ }
    show();
  });

  show();
})();
