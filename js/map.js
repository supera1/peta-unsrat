const IMG = { w: 4000, h: 2256 };
const STORAGE_KEY = "peta-unsrat-buildings";

const SHORT = {
  "KANTOR PUSAT UNSRAT": "Kantor Pusat",
  "FAKULTAS KEDOKTERAN": "Kedokteran",
  "FAKULTAS TEKNIK": "Teknik",
  "FAKULTAS PERTANIAN": "Pertanian",
  "FAKULTAS PETERNAKAN": "Peternakan",
  "FAKULTAS PERIKANAN DAN ILMU KELAUTAN": "FPIK",
  "FAKULTAS EKONOMI DAN BISNIS": "FEB",
  "FAKULTAS HUKUM": "Hukum",
  "FAKULTAS SOSIAL DAN ILMU POLITIK": "FISIP",
  "FAKULTAS ILMU BUDAYA": "Ilmu Budaya",
  "FAKULTAS MATEMATIKA DAN ILMU PENGETAHUAN ALAM": "FMIPA",
  "FAKULTAS KESEHATAN MASYARAKAT": "FKM",
  "PASCA SARJANA": "Pascasarjana",
  "LEMBAGA PENJAMIN MUTU DAN PENGEMBANGAN PEMBELAJARAN": "LPMPP",
  "LEMBAGA PENELITIAN DAN PENGABDIAN KEPADA MASYARAKAT": "LPPM",
  "Unit Penunjang Akademik (UPA) Bimbingan Konseling": "UPA BK",
  "Unit Penunjang Akademik (UPA) Teknologi Informasi dan Komunikasi": "UPA TIK",
  "Unit Penunjang Akademik (UPA) Laboratorium Terpadu": "UPA Lab Terpadu",
  "Unit Penunjang Akademik (UPA) Percetakan dan Penerbitan": "UPA Percetakan",
  "Unit Penunjang Akademik (UPA) Bahasa": "UPA Bahasa",
  "Unit Penunjang Akademik (UPA) Perpustakaan": "UPA Perpustakaan",
  "Unit Penunjang Akademik (UPA) Pengembangan Karier dan Kewirausahaan": "UPA Karier",
  "Unit Penunjang Akademik (UPA) Laboratorium Biomolekuler": "UPA Biomolekuler",
  "AUDITORIUM UNSRAT": "Auditorium",
  "BIRO AKADEMIK DAN KEMAHASISWAAN": "Biro Akademik",
  "KLINIK UNSRAT": "Klinik",
  "LAPANGAN SEPAKBOLA": "Lapangan Sepakbola",
  "LAPANGAN FUTSAL": "Lapangan Futsal",
  "LAPANGAN TENIS": "Lapangan Tenis",
  "KOLAM CINTA": "Kolam Cinta",
  "GERBANG UTAMA": "Gerbang Utama",
  "MESJID KAMPUS": "Mesjid Kampus",
  "GEREJA KAMPUS": "Gereja Kampus",
};

function pctToLatLng(point) {
  const x = point[0] / 100 * IMG.w;
  const y = point[1] / 100 * IMG.h;
  return [IMG.h - y, x];
}

function latLngToPct(latlng) {
  return [
    Number((latlng.lng / IMG.w * 100).toFixed(3)),
    Number(((IMG.h - latlng.lat) / IMG.h * 100).toFixed(3)),
  ];
}

function ringToLatLngs(ring) {
  return ring.map(pctToLatLng);
}

function centroidOf(ring) {
  const pts = ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1]
    ? ring.slice(0, -1)
    : ring;
  const x = pts.reduce((sum, p) => sum + p[0], 0) / pts.length;
  const y = pts.reduce((sum, p) => sum + p[1], 0) / pts.length;
  return [Number(x.toFixed(3)), Number(y.toFixed(3))];
}

async function loadJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gagal memuat ${path}`);
  return res.json();
}

const RETIRED_IDS = new Set(["gedung-01"]);

function loadBuildings(fileBuildings) {
  let stored = [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) stored = JSON.parse(raw);
  } catch {}
  if (!Array.isArray(stored) || !stored.length) return fileBuildings;
  return stored.filter((item) => item && item.id && item.polygon && !RETIRED_IDS.has(item.id));
}

function saveBuildings(buildings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(buildings));
  return publishBuildings(buildings);
}

function publishBuildings(buildings) {
  const named = buildings.filter((item) => item && item.name).length;
  if (!named) return Promise.resolve(false);
  return fetch("/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildings),
  }).then((res) => res.ok).catch(() => false);
}

function createMap(el) {
  const bounds = [[0, 0], [IMG.h, IMG.w]];
  const map = L.map(el, {
    crs: L.CRS.Simple,
    minZoom: -2,
    maxZoom: 2,
    zoomSnap: 0.25,
    zoomDelta: 0.5,
    attributionControl: false,
  });
  L.imageOverlay("assets/campus.jpg", bounds).addTo(map);
  map.fitBounds(bounds, { padding: [10, 10] });
  map.setMaxBounds(L.latLngBounds(bounds).pad(0.15));
  return map;
}

function campusStyle() {
  return {
    color: "#c23b3b",
    weight: 1.6,
    dashArray: "6 8",
    fill: false,
    opacity: 0.7,
    interactive: false,
  };
}

function buildingStyle(named, active) {
  if (named) {
    return {
      color: active ? "#f0d48a" : "rgba(240,212,138,0.9)",
      weight: active ? 2.4 : 1.6,
      fillColor: "#d4a017",
      fillOpacity: active ? 0.34 : 0.14,
    };
  }
  return {
    color: "rgba(240,212,138,0.75)",
    weight: 1.4,
    fillColor: "#f0d48a",
    fillOpacity: 0.18,
    dashArray: "4 3",
  };
}

function addCampus(map, campus) {
  const ring = campus.geometry.coordinates[0];
  return L.polygon(ringToLatLngs(ring), campusStyle()).addTo(map);
}

function addBuildings(map, buildings, options) {
  const layer = L.layerGroup().addTo(map);
  const byId = new Map();
  buildings.forEach((building) => {
    const poly = L.polygon(ringToLatLngs(building.polygon), buildingStyle(Boolean(building.name), false));
    poly.buildingId = building.id;
    poly.addTo(layer);
    byId.set(building.id, poly);
    if (options.onEnter) poly.on("mouseover", () => options.onEnter(building, poly));
    if (options.onLeave) poly.on("mouseout", () => options.onLeave(building, poly));
    if (options.onClick) poly.on("click", (event) => {
      L.DomEvent.stopPropagation(event);
      options.onClick(building, poly);
    });
  });
  return { layer, byId };
}

function createCallout(stage) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "100%");
  svg.classList.add("callout-layer");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.classList.add("callout-line");
  svg.appendChild(path);
  const card = document.createElement("div");
  card.className = "callout-card";
  stage.appendChild(svg);
  stage.appendChild(card);
  let shownId = null;

  function hide() {
    shownId = null;
    path.classList.remove("is-in");
    path.removeAttribute("d");
    card.classList.remove("is-in");
    card.innerHTML = "";
  }

  function show(building, map, animate = true) {
    const anchor = building.anchor || centroidOf(building.polygon);
    const origin = map.getContainer().getBoundingClientRect();
    const stageBox = stage.getBoundingClientRect();
    const point = map.latLngToContainerPoint(pctToLatLng(anchor));
    point.x += origin.left - stageBox.left;
    point.y += origin.top - stageBox.top;
    const width = stage.clientWidth;
    const height = stage.clientHeight;
    const cardW = 250;
    const goRight = point.x < width * 0.55;
    const x2 = goRight ? Math.min(width - 28, point.x + 110) : Math.max(28, point.x - 110);
    const y2 = Math.max(70, Math.min(height - 90, point.y - 70));
    const elbowX = goRight ? point.x + 36 : point.x - 36;
    path.setAttribute("d", `M ${point.x} ${point.y} L ${elbowX} ${point.y - 18} L ${x2} ${y2}`);
    card.style.left = `${goRight ? x2 : x2 - cardW}px`;
    card.style.top = `${y2 - 28}px`;
    const restart = animate && shownId !== building.id;
    shownId = building.id;
    if (!restart) {
      path.classList.add("is-in");
      card.classList.add("is-in");
      return;
    }
    card.innerHTML = `<strong>${building.name}</strong><span>${SHORT[building.name] || "Gedung utama"}</span>`;
    path.classList.remove("is-in");
    card.classList.remove("is-in");
    void path.getBoundingClientRect();
    path.classList.add("is-in");
    card.classList.add("is-in");
  }

  return { show, hide };
}

function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
