import React from "react";
import { LifeBuoy, Phone, Mail, MessageSquare, AlertTriangle } from "lucide-react";

export default function SupportPage() {
  return (
    <div className="max-w-3xl mx-auto" data-testid="support-page">
      <h1 className="text-2xl sm:text-3xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>Support & SOS</h1>
      <p className="text-[#7A9690] text-sm mt-1">We're here. Reach out anytime — bantuan profesional & sukarelawan siaga.</p>

      <div className="mt-6 bg-[#FCEFEB] rounded-3xl p-6 border border-[#F6DAD2]" data-testid="sos-card">
        <div className="flex items-center gap-3 text-[#C06C5B]"><AlertTriangle size={20} /><span className="font-semibold uppercase tracking-[0.18em] text-sm">Emergency Hotline</span></div>
        <h2 className="text-2xl font-medium text-[#1C302B] mt-2" style={{ fontFamily: "Outfit, sans-serif" }}>Butuh bantuan segera?</h2>
        <p className="text-sm text-[#4A635D] mt-2">Jika kamu atau seseorang di sekitarmu dalam bahaya, hubungi layanan darurat di bawah ini 24/7.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a href="tel:119" className="rounded-full bg-[#C06C5B] text-white px-5 py-3 text-sm font-medium flex items-center gap-2" data-testid="call-119"><Phone size={14} /> 119 ext 8 (Indonesia)</a>
          <a href="tel:+622150830381" className="rounded-full border border-[#C06C5B] text-[#C06C5B] px-5 py-3 text-sm font-medium flex items-center gap-2" data-testid="call-into-the-light"><Phone size={14} /> Into The Light: (021) 5083 0381</a>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-5">
        <div className="bg-white rounded-3xl p-5 shadow-[0_8px_32px_rgba(45,95,95,0.06)]">
          <Mail size={20} className="text-[#2D5F5F]" />
          <div className="mt-2 font-medium text-[#1C302B]">Email Support</div>
          <div className="text-xs text-[#7A9690] mt-1">support@echoaid.com</div>
        </div>
        <div className="bg-white rounded-3xl p-5 shadow-[0_8px_32px_rgba(45,95,95,0.06)]">
          <MessageSquare size={20} className="text-[#2D5F5F]" />
          <div className="mt-2 font-medium text-[#1C302B]">Live Chat</div>
          <div className="text-xs text-[#7A9690] mt-1">Mon–Fri · 09.00–21.00 WIB</div>
        </div>
        <div className="bg-white rounded-3xl p-5 shadow-[0_8px_32px_rgba(45,95,95,0.06)]">
          <LifeBuoy size={20} className="text-[#2D5F5F]" />
          <div className="mt-2 font-medium text-[#1C302B]">FAQ & Knowledge</div>
          <div className="text-xs text-[#7A9690] mt-1">Berbasis WHO LIVE LIFE</div>
        </div>
      </div>
    </div>
  );
}
