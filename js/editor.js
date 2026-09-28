(async function start() {
  const [campus, names, fileBuildings] = await Promise.all([
    loadJson("data/campus.json"),
    loadJson("data/names.json"),
    loadJson("data/buildings.json"),
  ]);

  let buildings = loadBuildings(fileBuildings);
  let selectedId = null;
  let mode = "select";
  let draftPoints = [];
  let draftLayer = null;
  let nextId = buildings.reduce((max, item) => {
    const num = Number(String(item.id).replace(/\D/g, "")) || 0;
    return Math.max(max, num);
  }, 0) + 1;

  const map = createMap("map");
  map.doubleClickZoom.disable();
  addCampus(map, campus);
  const layers = addBuildings(map, buildings, {
    onClick(building) { select(building.id); },
  });

  const list = document.getElementById("list");
  const status = document.getElementById("status");
  const selectEl = document.getElementById("name-select");
  const selectedLabel = document.getElementById("selected-id");
  const hint = document.getElementById("hint");

  function refreshStyles() {
    buildings.forEach((building) => {
      const layer = layers.byId.get(building.id);
      if (layer) layer.setStyle(buildingStyle(Boolean(building.name), building.id === selectedId));
    });
  }

  const nameCursor = {};

  function fillSelect() {
    const current = buildings.find((item) => item.id === selectedId);
    selectEl.innerHTML = `<option value="">Belum dinamai</option>`;
    names.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      selectEl.appendChild(opt);
    });
    selectEl.value = current?.name || "";
    selectEl.disabled = !current;
  }

  function renderList() {
    const namedCount = buildings.filter((item) => item.name).length;
    status.textContent = `${namedCount} poligon sudah dinamai · ${names.length} nama tersedia`;
    list.innerHTML = "";
    names.forEach((name) => {
      const mapped = buildings.filter((item) => item.name === name);
      const btn = document.createElement("button");
      btn.className = "item" + (mapped.length ? "" : " is-empty");
      const detail = mapped.length
        ? `${mapped.length} poligon · ${mapped.map((item) => item.id).join(", ")}`
        : "Belum dipilih";
      btn.innerHTML = `${name}<small>${detail}</small>`;
      if (mapped.length) {
        btn.addEventListener("click", () => {
          const index = nameCursor[name] || 0;
          select(mapped[index % mapped.length].id);
          nameCursor[name] = index + 1;
        });
      }
      list.appendChild(btn);
    });
  }

  function select(id) {
    selectedId = id;
    const building = buildings.find((item) => item.id === id);
    selectedLabel.textContent = building ? `${building.id}` : "Klik salah satu poligon.";
    fillSelect();
    refreshStyles();
    renderList();
    if (building) {
      const layer = layers.byId.get(id);
      if (layer) map.panTo(layer.getBounds().getCenter(), { animate: true });
    }
  }

  function persist() {
    saveBuildings(buildings);
    renderList();
    refreshStyles();
    fillSelect();
  }

  function addLayer(building) {
    const poly = L.polygon(ringToLatLngs(building.polygon), buildingStyle(Boolean(building.name), false));
    poly.buildingId = building.id;
    poly.on("click", (event) => {
      L.DomEvent.stopPropagation(event);
      if (mode === "select") select(building.id);
    });
    poly.addTo(layers.layer);
    layers.byId.set(building.id, poly);
  }

  function setMode(next) {
    mode = next;
    document.getElementById("btn-select").classList.toggle("is-on", mode === "select");
    document.getElementById("btn-draw").classList.toggle("is-on", mode === "draw");
    hint.textContent = mode === "draw"
      ? "Klik peta untuk menambah titik. Enter atau dobel-klik untuk menutup poligon."
      : "Poligon kuning = draf atap utama. Isi namanya dari daftar.";
    draftPoints = [];
    if (draftLayer) {
      map.removeLayer(draftLayer);
      draftLayer = null;
    }
  }

  function finishDraft() {
    if (draftPoints.length < 3) return;
    const ring = draftPoints.map(latLngToPct);
    ring.push(ring[0]);
    const building = {
      id: `gedung-${String(nextId++).padStart(2, "0")}`,
      name: "",
      polygon: ring,
      anchor: centroidOf(ring),
    };
    buildings.push(building);
    addLayer(building);
    persist();
    setMode("select");
    select(building.id);
  }

  map.on("click", (event) => {
    if (mode !== "draw") return;
    draftPoints.push(event.latlng);
    if (draftLayer) map.removeLayer(draftLayer);
    draftLayer = L.polygon(draftPoints, {
      color: "#f0d48a",
      weight: 2,
      fillOpacity: 0.15,
      dashArray: "5 4",
    }).addTo(map);
  });

  map.on("dblclick", (event) => {
    if (mode !== "draw") return;
    L.DomEvent.stop(event);
    finishDraft();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && mode === "draw") finishDraft();
    if (event.key === "Escape") setMode("select");
  });

  selectEl.addEventListener("change", () => {
    const building = buildings.find((item) => item.id === selectedId);
    if (!building) return;
    building.name = selectEl.value;
    persist();
  });

  document.getElementById("btn-clear-name").addEventListener("click", () => {
    const building = buildings.find((item) => item.id === selectedId);
    if (!building) return;
    building.name = "";
    persist();
  });

  document.getElementById("btn-select").addEventListener("click", () => setMode("select"));
  document.getElementById("btn-draw").addEventListener("click", () => setMode("draw"));
  document.getElementById("btn-delete").addEventListener("click", () => {
    if (!selectedId) return;
    const layer = layers.byId.get(selectedId);
    if (layer) layers.layer.removeLayer(layer);
    layers.byId.delete(selectedId);
    buildings = buildings.filter((item) => item.id !== selectedId);
    selectedId = null;
    persist();
    selectedLabel.textContent = "Klik salah satu poligon.";
  });
  document.getElementById("btn-save").addEventListener("click", async () => {
    persist();
    const saved = await publishBuildings(buildings);
    hint.textContent = saved
      ? "Nama gedung tersimpan ke data/buildings.json."
      : "Tersimpan di browser. Jalankan server lokal lalu klik Simpan lagi.";
  });
  document.getElementById("btn-download").addEventListener("click", () => {
    persist();
    downloadJson("buildings.json", buildings);
  });
  document.getElementById("btn-reset").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    window.location.reload();
  });

  fillSelect();
  renderList();
})().catch((error) => {
  document.getElementById("status").textContent = error.message;
});
