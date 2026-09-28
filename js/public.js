(async function start() {
  const [campus, names, fileBuildings] = await Promise.all([
    loadJson("data/campus.json"),
    loadJson("data/names.json"),
    loadJson("data/buildings.json"),
  ]);
  const buildings = loadBuildings(fileBuildings);
  const named = buildings.filter((item) => item.name);
  const nameCursor = {};
  const map = createMap("map");
  addCampus(map, campus);
  const stage = document.getElementById("stage");
  const callout = createCallout(stage);
  const list = document.getElementById("list");
  const status = document.getElementById("status");
  const search = document.getElementById("search");
  let activeId = null;

  status.textContent = `${named.length} poligon sudah diberi nama`;
  if (!named.length) {
    const hint = document.createElement("div");
    hint.className = "hint";
    hint.textContent = "Belum ada nama di peta. Buka Editor penamaan, klik poligon, lalu pilih nama resmi.";
    stage.appendChild(hint);
  }

  let leaveTimer = null;

  const layers = addBuildings(map, named, {
    onEnter(building) {
      clearTimeout(leaveTimer);
      activate(building, false);
    },
    onLeave() {
      clearTimeout(leaveTimer);
      leaveTimer = setTimeout(deactivate, 140);
    },
    onClick(building) {
      clearTimeout(leaveTimer);
      activate(building, false);
    },
  });

  map.on("click", deactivate);
  map.on("move", () => {
    const current = named.find((item) => item.id === activeId);
    if (current) callout.show(current, map, false);
  });

  function activate(building, pan) {
    const layer = layers.byId.get(building.id);
    activeId = building.id;
    layers.byId.forEach((poly, id) => {
      poly.setStyle(buildingStyle(true, id === building.id));
    });
    callout.show(building, map, true);
    highlightList(building.name);
    if (pan && layer) map.panTo(layer.getBounds().getCenter(), { animate: true });
  }

  function deactivate() {
    activeId = null;
    layers.byId.forEach((poly) => poly.setStyle(buildingStyle(true, false)));
    callout.hide();
    highlightList("");
  }

  function highlightList(name) {
    list.querySelectorAll(".item").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.name === name);
    });
  }

  function render(filter = "") {
    const q = filter.trim().toLowerCase();
    list.innerHTML = "";
    names.forEach((name) => {
      if (q && !name.toLowerCase().includes(q) && !(SHORT[name] || "").toLowerCase().includes(q)) return;
      const mapped = named.filter((item) => item.name === name);
      const btn = document.createElement("button");
      btn.className = "item" + (mapped.length ? "" : " is-empty");
      btn.dataset.name = name;
      btn.innerHTML = `${name}<small>${mapped.length ? `${mapped.length} poligon di peta` : "Belum diberi poligon"}</small>`;
      if (mapped.length) {
        btn.addEventListener("click", () => {
          const index = nameCursor[name] || 0;
          const building = mapped[index % mapped.length];
          nameCursor[name] = index + 1;
          activate(building, true);
        });
      }
      list.appendChild(btn);
    });
  }

  search.addEventListener("input", () => render(search.value));
  render();
})().catch((error) => {
  document.getElementById("status").textContent = error.message;
});
