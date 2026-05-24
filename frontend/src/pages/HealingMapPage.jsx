import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { api } from "@/lib/api";
import { MapPin } from "lucide-react";

// Fix Leaflet icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function HealingMapPage() {
  const [parks, setParks] = useState([]);
  const [activeMood, setActiveMood] = useState("anxious");

  useEffect(() => {
    api.get("/healing/parks").then((r) => setParks(r.data.items || [])).catch(() => {});
  }, []);

  const center = parks.length ? [parks[0].lat, parks[0].lng] : [-6.2, 106.83];

  return (
    <div className="max-w-6xl mx-auto" data-testid="healing-map-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>Healing Map</h1>
          <p className="text-[#7A9690] text-sm mt-1">Lokasi sanctuary terdekat untuk menenangkan pikiranmu</p>
        </div>
        <span className="text-[11px] uppercase tracking-[0.18em] bg-[#E6F4EA] text-[#2D5F5F] px-3 py-1.5 rounded-full">Local View</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[#E8F0EA] rounded-3xl p-5" data-testid="current-mood-card">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[#4A635D]">Current Mood</div>
            <h3 className="text-xl font-medium text-[#1C302B] mt-1" style={{ fontFamily: "Outfit, sans-serif" }}>Feeling Anxious?</h3>
            <p className="text-sm text-[#4A635D] mt-2 leading-relaxed">
              We recommend Taman Menteng for some fresh air and grounding exercises. Bawa earphone, dengarkan suara alam selama 10 menit.
            </p>
          </div>

          <div className="space-y-3">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[#7A9690]">Nearby Sanctuaries</div>
            {parks.map((p) => (
              <div key={p.place_id} className="bg-white rounded-3xl p-5 shadow-[0_8px_32px_rgba(45,95,95,0.06)] flex gap-4 fade-up" data-testid={`park-card-${p.place_id}`}>
                <img src={p.image} alt={p.name} className="w-20 h-20 rounded-2xl object-cover" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-[#1C302B] flex items-center gap-1.5"><MapPin size={14} className="text-[#2D5F5F]" /> {p.name}</div>
                    <div className="text-xs text-[#7A9690]">{p.distance}</div>
                  </div>
                  <div className="text-xs text-[#7A9690] mt-0.5">{p.subtitle}</div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {p.tags?.map((t) => (
                      <span key={t} className="text-[11px] bg-[#F4F7F4] text-[#4A635D] px-2 py-1 rounded-full">{t}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-3">
          <div className="rounded-3xl overflow-hidden h-[520px] shadow-[0_8px_32px_rgba(45,95,95,0.10)] border border-[#D8E6DD]" data-testid="leaflet-map-container">
            <MapContainer center={center} zoom={14} scrollWheelZoom={true} style={{ height: "100%", width: "100%" }}>
              <TileLayer
                attribution='&copy; OpenStreetMap'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {parks.map((p) => (
                <Marker key={p.place_id} position={[p.lat, p.lng]}>
                  <Popup>
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs">{p.subtitle}</div>
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
