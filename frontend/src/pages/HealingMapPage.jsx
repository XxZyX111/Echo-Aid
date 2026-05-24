import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, useMap } from "react-leaflet";
import L from "leaflet";
import { api } from "@/lib/api";
import { MapPin, LocateFixed, Loader2, Search, Heart } from "lucide-react";
import { toast } from "sonner";

// Fix Leaflet icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function MapFlyTo({ target }) {
  const map = useMap();
  useEffect(() => {
    if (target) {
      map.flyTo([target.lat, target.lng], 16, { duration: 1.2 });
    }
  }, [target, map]);
  return null;
}

export default function HealingMapPage() {
  const [parks, setParks] = useState([]);
  const [userPos, setUserPos] = useState(null);
  const [locating, setLocating] = useState(false);
  const [locError, setLocError] = useState("");
  const [search, setSearch] = useState("");
  const [flyTarget, setFlyTarget] = useState(null);
  const markerRefs = useRef({});

  const load = async (pos, q) => {
    const params = {};
    if (pos) { params.lat = pos.lat; params.lng = pos.lng; }
    if (q && q.trim()) params.q = q.trim();
    const r = await api.get("/healing/parks", { params });
    setParks(r.data.items || []);
  };

  useEffect(() => { load(userPos, ""); /* eslint-disable-next-line */ }, []);

  const onSearch = (e) => {
    e.preventDefault();
    load(userPos, search);
  };

  const detectLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Browser kamu tidak mendukung geolocation");
      return;
    }
    setLocating(true);
    setLocError("");
    navigator.geolocation.getCurrentPosition(
      async (p) => {
        const pos = { lat: p.coords.latitude, lng: p.coords.longitude };
        setUserPos(pos);
        await load(pos, search);
        setLocating(false);
        toast.success("Lokasi terdeteksi. Sanctuary terdekat ditampilkan.");
      },
      (err) => {
        setLocating(false);
        const msg = err.code === 1 ? "Izin lokasi ditolak. Aktifkan di pengaturan browser." :
                    err.code === 2 ? "Lokasi tidak tersedia." :
                    err.code === 3 ? "Pencarian lokasi timeout." : "Gagal mendeteksi lokasi.";
        setLocError(msg);
        toast.error(msg);
      },
      { enableHighAccuracy: true, timeout: 12000 }
    );
  };

  const focusPark = (p) => {
    setFlyTarget({ lat: p.lat, lng: p.lng, _ts: Date.now() });
    // open popup after a brief delay
    setTimeout(() => {
      const ref = markerRefs.current[p.place_id];
      if (ref?.openPopup) ref.openPopup();
    }, 1300);
  };

  const toggleBookmark = async (p, ev) => {
    ev?.stopPropagation?.();
    try {
      const { data } = await api.post(`/healing/parks/${p.place_id}/bookmark`);
      setParks((all) => all.map((x) => x.place_id === p.place_id ? { ...x, bookmarked: data.bookmarked } : x));
      toast.success(data.bookmarked ? `${p.name} ditandai ❤️` : `Bookmark dihapus dari ${p.name}`);
    } catch (e) {
      toast.error("Gagal menyimpan bookmark");
    }
  };

  const initialCenter = userPos
    ? [userPos.lat, userPos.lng]
    : parks.length ? [parks[0].lat, parks[0].lng] : [-6.2, 106.83];

  return (
    <div className="max-w-6xl mx-auto" data-testid="healing-map-page">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>Healing Map</h1>
          <p className="text-[#7A9690] text-sm mt-1">Lokasi sanctuary terdekat untuk menenangkan pikiranmu</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={detectLocation}
            disabled={locating}
            data-testid="detect-location-button"
            className="rounded-full bg-[#2D5F5F] text-white px-4 py-2 text-sm font-medium hover:bg-[#244C4C] transition flex items-center gap-2 disabled:opacity-60"
          >
            {locating ? <Loader2 size={14} className="animate-spin" /> : <LocateFixed size={14} />}
            {locating ? "Mencari lokasi…" : userPos ? "Refresh Lokasi" : "Gunakan Lokasi Saya"}
          </button>
          <span className="text-[11px] uppercase tracking-[0.18em] bg-[#E6F4EA] text-[#2D5F5F] px-3 py-1.5 rounded-full">
            {userPos ? "Live View" : "Local View"}
          </span>
        </div>
      </div>

      {/* Search bar */}
      <form onSubmit={onSearch} className="mb-4 flex items-center gap-2" data-testid="park-search-form">
        <div className="flex-1 flex items-center gap-3 px-4 py-3 rounded-2xl bg-white shadow-[0_8px_24px_rgba(45,95,95,0.05)] border border-[#D8E6DD] focus-within:border-[#2D5F5F] transition">
          <Search size={16} className="text-[#7A9690]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari sanctuary… (mis. Menteng, Garden, Nature)"
            className="flex-1 bg-transparent outline-none text-sm"
            data-testid="park-search-input"
          />
          {search && (
            <button type="button" onClick={() => { setSearch(""); load(userPos, ""); }} className="text-xs text-[#7A9690] hover:text-[#1C302B]" data-testid="park-search-clear">
              Clear
            </button>
          )}
        </div>
        <button
          type="submit"
          data-testid="park-search-submit"
          className="rounded-2xl bg-[#2D5F5F] text-white px-5 py-3 text-sm font-medium hover:bg-[#244C4C] transition"
        >
          Search
        </button>
      </form>

      {locError && (
        <div className="mb-3 text-sm text-[#C06C5B] bg-[#FCEFEB] px-4 py-2 rounded-xl">{locError}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[#E8F0EA] rounded-3xl p-5" data-testid="current-mood-card">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[#4A635D]">Current Mood</div>
            <h3 className="text-xl font-medium text-[#1C302B] mt-1" style={{ fontFamily: "Outfit, sans-serif" }}>Feeling Anxious?</h3>
            <p className="text-sm text-[#4A635D] mt-2 leading-relaxed">
              {userPos
                ? `Berdasarkan lokasi kamu, kami rekomendasikan ${parks[0]?.name || "sanctuary terdekat"} untuk grounding singkat.`
                : "We recommend Taman Menteng for some fresh air and grounding exercises. Aktifkan lokasi untuk rekomendasi yang lebih akurat."}
            </p>
          </div>

          <div className="space-y-3">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[#7A9690]">
              {search ? `Hasil untuk "${search}" (${parks.length})` : "Nearby Sanctuaries"}
            </div>
            {parks.length === 0 && (
              <div className="bg-white rounded-3xl p-5 text-sm text-[#7A9690] text-center shadow-[0_8px_32px_rgba(45,95,95,0.06)]">
                Tidak ada sanctuary yang cocok. Coba kata kunci lain.
              </div>
            )}
            {parks.map((p) => (
              <button
                key={p.place_id}
                onClick={() => focusPark(p)}
                data-testid={`park-card-${p.place_id}`}
                className="w-full text-left bg-white rounded-3xl p-5 shadow-[0_8px_32px_rgba(45,95,95,0.06)] flex gap-4 fade-up hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(45,95,95,0.12)] transition"
              >
                <img src={p.image} alt={p.name} className="w-20 h-20 rounded-2xl object-cover shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-[#1C302B] flex items-center gap-1.5 truncate">
                      <MapPin size={14} className="text-[#2D5F5F] shrink-0" /> {p.name}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-[#7A9690]">{p.distance}</span>
                      <button
                        onClick={(ev) => toggleBookmark(p, ev)}
                        className={`p-1.5 rounded-full transition ${p.bookmarked ? "bg-[#FCEFEB] text-[#C06C5B]" : "hover:bg-[#F4F7F4] text-[#7A9690]"}`}
                        data-testid={`bookmark-${p.place_id}`}
                        aria-label="Toggle bookmark"
                      >
                        <Heart size={14} fill={p.bookmarked ? "currentColor" : "none"} />
                      </button>
                    </div>
                  </div>
                  <div className="text-xs text-[#7A9690] mt-0.5">{p.subtitle}</div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {p.tags?.map((t) => (
                      <span key={t} className="text-[11px] bg-[#F4F7F4] text-[#4A635D] px-2 py-1 rounded-full">{t}</span>
                    ))}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="lg:col-span-3">
          <div className="rounded-3xl overflow-hidden h-[420px] sm:h-[560px] shadow-[0_8px_32px_rgba(45,95,95,0.10)] border border-[#D8E6DD] sticky top-20" data-testid="leaflet-map-container">
            <MapContainer center={initialCenter} zoom={userPos ? 14 : 13} scrollWheelZoom={true} style={{ height: "100%", width: "100%" }}>
              <TileLayer
                attribution='&copy; OpenStreetMap'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapFlyTo target={flyTarget} />
              {userPos && (
                <CircleMarker center={[userPos.lat, userPos.lng]} radius={9} pathOptions={{ color: "#2D5F5F", fillColor: "#2D5F5F", fillOpacity: 0.6 }}>
                  <Popup>Lokasi kamu</Popup>
                </CircleMarker>
              )}
              {parks.map((p) => (
                <Marker
                  key={p.place_id}
                  position={[p.lat, p.lng]}
                  ref={(ref) => { if (ref) markerRefs.current[p.place_id] = ref; }}
                >
                  <Popup>
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs">{p.subtitle}</div>
                    {p.distance_km != null && <div className="text-xs mt-1">📍 {p.distance}</div>}
                    {p.bookmarked && <div className="text-xs mt-1 text-[#C06C5B]">❤️ Bookmarked</div>}
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
