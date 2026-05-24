import React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Home as HomeIcon,
  Notebook,
  Map as MapIcon,
  Sparkles,
  Stethoscope,
  MessageSquare,
  User,
  Settings as SettingsIcon,
  LifeBuoy,
  Bell,
  CalendarDays,
} from "lucide-react";
import { useAuth } from "@/lib/auth";

const links = [
  { to: "/", label: "Home", icon: HomeIcon, end: true, testid: "nav-home" },
  { to: "/journal", label: "Journal & MoodTracker", icon: Notebook, testid: "nav-journal" },
  { to: "/healing-map", label: "Healing Map", icon: MapIcon, testid: "nav-healing-map" },
  { to: "/meditation", label: "Meditation", icon: Sparkles, testid: "nav-meditation" },
  { to: "/consultation", label: "Consultation", icon: Stethoscope, testid: "nav-consultation" },
  { to: "/echochat", label: "EchoChat", icon: MessageSquare, testid: "nav-echochat" },
  { to: "/profile", label: "Profile", icon: User, testid: "nav-profile" },
];

const footerLinks = [
  { to: "/settings", label: "Settings", icon: SettingsIcon, testid: "nav-settings" },
  { to: "/support", label: "Support", icon: LifeBuoy, testid: "nav-support" },
];

function Sidebar() {
  return (
    <aside className="hidden md:flex w-64 shrink-0 border-r border-[#D8E6DD] bg-white/80 backdrop-blur-sm flex-col">
      <div className="px-6 pt-7 pb-6 flex items-center gap-3" data-testid="brand-logo">
        <div className="w-10 h-10 rounded-2xl bg-[#2D5F5F] grid place-items-center text-white shadow-[0_8px_24px_rgba(45,95,95,0.25)]">
          <span className="font-semibold">E</span>
        </div>
        <div>
          <div className="font-semibold text-[#1C302B] tracking-tight">EchoAid</div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[#7A9690]">Sanctuary</div>
        </div>
      </div>
      <nav className="px-3 flex-1 space-y-1">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            data-testid={l.testid}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-2xl text-sm transition-all ${
                isActive
                  ? "bg-[#E8F0EA] text-[#1C302B] font-semibold"
                  : "text-[#4A635D] hover:bg-[#F4F7F4]"
              }`
            }
          >
            <l.icon size={18} strokeWidth={1.6} />
            <span>{l.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-3 pb-6 space-y-1">
        {footerLinks.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            data-testid={l.testid}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-2xl text-sm transition-all ${
                isActive
                  ? "bg-[#E8F0EA] text-[#1C302B] font-semibold"
                  : "text-[#4A635D] hover:bg-[#F4F7F4]"
              }`
            }
          >
            <l.icon size={18} strokeWidth={1.6} />
            <span>{l.label}</span>
          </NavLink>
        ))}
      </div>
    </aside>
  );
}

function Topbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "short" });
  return (
    <header className="h-16 px-5 sm:px-8 flex items-center justify-between border-b border-[#D8E6DD] bg-white/70 backdrop-blur-md sticky top-0 z-30">
      <div className="flex items-center gap-2 text-[#4A635D] text-sm">
        <CalendarDays size={16} strokeWidth={1.6} />
        <span data-testid="topbar-date">{today}</span>
      </div>
      <div className="flex items-center gap-3">
        <button
          className="w-9 h-9 rounded-full bg-[#F4F7F4] grid place-items-center text-[#4A635D] hover:bg-[#E8F0EA] transition"
          data-testid="topbar-notifications"
          aria-label="Notifications"
        >
          <Bell size={16} strokeWidth={1.6} />
        </button>
        <button
          onClick={() => navigate("/profile")}
          className="w-9 h-9 rounded-full overflow-hidden border border-[#D8E6DD] hover:ring-2 hover:ring-[#E8F0EA] transition"
          data-testid="topbar-avatar"
          aria-label="Profile"
        >
          <img
            src={user?.avatar_url || "https://static.prod-images.emergentagent.com/jobs/7fb04be7-ed7d-415a-b6ee-6f602642e7b9/images/cae4a84b4f820dfffa26e94765de3c6b836dda3ec59cffca36818667d4582b00.png"}
            alt="avatar"
            className="w-full h-full object-cover"
          />
        </button>
      </div>
    </header>
  );
}

function MobileNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-[#D8E6DD]">
      <div className="grid grid-cols-5">
        {links.slice(0, 5).map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            data-testid={`mobile-${l.testid}`}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 py-2 text-[11px] ${
                isActive ? "text-[#2D5F5F]" : "text-[#7A9690]"
              }`
            }
          >
            <l.icon size={18} strokeWidth={1.6} />
            <span>{l.label.split(" ")[0]}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

export default function Layout() {
  return (
    <div className="min-h-screen flex bg-[#F4F7F4]">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar />
        <main className="flex-1 p-5 sm:p-8 pb-24 md:pb-12">
          <Outlet />
        </main>
        <MobileNav />
      </div>
    </div>
  );
}
