/* Live availability: keeps search results fresh and counts down a checkout hold. */
(function () {
  "use strict";

  var POLL_MS = 5000;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* ---------- search results ---------- */
  var box = document.getElementById("live-results");
  if (box) {
    var query = box.getAttribute("data-query");
    var params = new URLSearchParams(query);
    var status = document.getElementById("live-status");
    var failures = 0;

    var render = function (rooms) {
      box.textContent = "";
      if (!rooms.length) {
        box.appendChild(el("div", "card empty", "No rooms are available for those filters."));
        return;
      }
      var wrap = el("div", "table-wrap");
      var table = el("table");
      var head = el("tr");
      ["Room", "Location", "Capacity", "Equipment", "Book"].forEach(function (name) {
        head.appendChild(el("th", "", name));
      });
      table.appendChild(el("thead")).appendChild(head);
      var body = el("tbody");
      rooms.forEach(function (room) {
        var row = el("tr");
        row.appendChild(el("td", "", room.name));
        row.appendChild(el("td", "", room.location));
        row.appendChild(el("td", "", String(room.capacity)));
        var tags = el("td");
        if (room.equipment.length) {
          room.equipment.forEach(function (item) {
            tags.appendChild(el("span", "tag", item.replace(/_/g, " ")));
          });
        } else {
          tags.textContent = "none";
        }
        row.appendChild(tags);
        var cell = el("td");
        var link = el("a", "button small", "Book");
        link.href = "/rooms/" + room.roomId + "/book?" + new URLSearchParams({
          date: params.get("date") || "", start: params.get("start") || "", end: params.get("end") || ""
        }).toString();
        cell.appendChild(link);
        row.appendChild(cell);
        body.appendChild(row);
      });
      table.appendChild(body);
      wrap.appendChild(table);
      box.appendChild(wrap);
    };

    var refresh = function () {
      if (document.hidden) return;
      fetch("/rooms/search?" + query + "&format=json", { headers: { Accept: "application/json" }, credentials: "same-origin" })
        .then(function (response) {
          if (response.redirected || !response.ok) throw new Error("status " + response.status);
          return response.json();
        })
        .then(function (rooms) {
          failures = 0;
          render(rooms);
          if (status) status.textContent = "Live - updated " + new Date().toLocaleTimeString();
        })
        .catch(function () {
          failures += 1;
          if (status) status.textContent = failures > 2 ? "Live updates paused - reload the page." : status.textContent;
        });
    };

    setInterval(refresh, POLL_MS);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
  }

  /* ---------- checkout hold countdown ---------- */
  var timer = document.getElementById("hold-timer");
  if (timer) {
    var left = parseInt(timer.getAttribute("data-seconds"), 10);
    var show = function () {
      if (left <= 0) {
        timer.textContent = "Your hold has run out. Reloading...";
        setTimeout(function () { window.location.reload(); }, 1200);
        return;
      }
      var minutes = Math.floor(left / 60), seconds = left % 60;
      timer.textContent = "Time left to confirm: " + minutes + ":" + (seconds < 10 ? "0" : "") + seconds;
      left -= 1;
      setTimeout(show, 1000);
    };
    show();
  }
})();
