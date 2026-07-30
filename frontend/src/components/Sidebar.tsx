"use client";

import { useState } from "react";
import { PanelLeftClose, PanelLeftOpen, Search, History, BrainCircuit, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  const navItems = [
    { name: "New Research", href: "/", icon: Search, shortcut: "⌘1" },
    { name: "Research History", href: "/history", icon: History, shortcut: "⌘2" },
    { name: "Learning Memory", href: "/learning-history", icon: BrainCircuit, shortcut: "⌘3" },
    { name: "Landing Architecture", href: "/landing-page", icon: Sparkles, shortcut: "⌘4" },
  ];

  return (
    <>
      {/* MOBILE OVERLAY */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-30 sm:hidden print:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* PERMANENT SIDEBAR CONTAINER (SEMI-TRANSPARENT WHEN COLLAPSED, FULLY VISIBLE ON HOVER) */}
      <aside
        className={`fixed top-0 left-0 h-screen border-r border-white/15 z-40 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col justify-between p-3 print:hidden ${
          isOpen
            ? "w-64 bg-zinc-950/98 backdrop-blur-2xl opacity-100 shadow-[10px_0_35px_rgba(0,0,0,0.95)]"
            : "w-16 bg-black/20 backdrop-blur-xs opacity-25 hover:opacity-100 hover:bg-zinc-950/95 hover:backdrop-blur-2xl hover:shadow-[10px_0_35px_rgba(0,0,0,0.95)]"
        }`}
      >
        {/* TOP SECTION: BRAND & TOGGLE */}
        <div>
          <div className="flex items-center justify-between pb-6 pt-2 border-b border-white/10 px-1">
            {isOpen ? (
              <div className="flex items-center gap-2">
                <span className="bg-white text-black text-xs font-black font-mono px-2 py-0.5 rounded shadow-[0_0_10px_rgba(255,255,255,0.4)]">
                  REX
                </span>
                <span className="text-sm font-bold font-display text-white tracking-tight">Research OS</span>
              </div>
            ) : (
              <div className="mx-auto bg-white text-black text-[11px] font-black font-mono px-1.5 py-0.5 rounded shadow-[0_0_10px_rgba(255,255,255,0.4)]">
                REX
              </div>
            )}

            <button
              onClick={() => setIsOpen(!isOpen)}
              title={isOpen ? "Collapse Sidebar" : "Expand Sidebar"}
              className={`p-1.5 rounded-lg border border-white/20 text-zinc-300 hover:text-white hover:border-white hover:bg-white/10 transition-colors ${
                isOpen ? "" : "hidden sm:block"
              }`}
            >
              {isOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
            </button>
          </div>

          {/* TOGGLE BUTTON FOR COLLAPSED VIEW ON MOBILE */}
          {!isOpen && (
            <button
              onClick={() => setIsOpen(true)}
              className="sm:hidden w-full my-2 flex justify-center p-2 rounded-lg border border-white/20 text-white bg-black"
              title="Open Navigation"
            >
              <PanelLeftOpen className="w-4 h-4" />
            </button>
          )}

          {/* NAVIGATION LINKS */}
          <nav className="mt-6 space-y-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  title={item.name}
                  className={`relative flex items-center rounded-xl transition-all duration-200 group ${
                    isOpen ? "px-3.5 py-3 gap-3.5" : "p-3 justify-center"
                  } ${
                    isActive
                      ? "bg-white text-black font-bold border border-white shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                      : "text-zinc-400 hover:bg-zinc-900 hover:text-white border border-transparent hover:border-white/20"
                  }`}
                >
                  <Icon className={`w-5 h-5 shrink-0 transition-transform group-hover:scale-110 ${isActive ? "text-black" : ""}`} strokeWidth={2} />

                  {isOpen && (
                    <div className="flex-1 flex items-center justify-between min-w-0">
                      <span className="text-xs font-semibold truncate">{item.name}</span>
                      <span className="text-[10px] font-mono opacity-50">{item.shortcut}</span>
                    </div>
                  )}

                  {/* TOOLTIP ON HOVER WHEN COLLAPSED */}
                  {!isOpen && (
                    <div className="absolute left-full ml-3 px-2.5 py-1 rounded-md bg-zinc-900 border border-white/30 text-white text-xs font-semibold whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200 shadow-xl z-50">
                      {item.name}
                    </div>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* BOTTOM QUICK STATUS / FOOTER */}
        <div className="pt-4 border-t border-white/10 text-center">
          {isOpen ? (
            <div className="space-y-1 text-left px-2">
              <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400">
                <span>System Status</span>
                <span className="text-emerald-400 font-bold">ONLINE</span>
              </div>
              <p className="text-[10px] text-zinc-500 font-mono">Cognitive OS v2.4</p>
            </div>
          ) : (
            <div className="flex justify-center" title="System Online">
              <span className="h-2 w-2 rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)] animate-pulse" />
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
