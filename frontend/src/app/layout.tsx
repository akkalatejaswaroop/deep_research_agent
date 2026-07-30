import type { Metadata } from "next";
import { Syne, Outfit, JetBrains_Mono } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

const syne = Syne({
  variable: "--font-syne",
  subsets: ["latin"],
  display: "swap",
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "REX — Recursive Exploration eXplorer",
  description: "REX: A self-improving multi-agent intelligence pipeline for recursive deep research",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${syne.variable} ${outfit.variable} ${jetbrainsMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <div className="min-h-screen flex bg-[var(--background)] text-[var(--text-1)]">
          <Sidebar />
          <div className="flex-1 relative overflow-x-hidden w-full">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
