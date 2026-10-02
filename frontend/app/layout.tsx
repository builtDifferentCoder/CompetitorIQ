import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CompetitorIQ — AI Competitive Intelligence Engine",
  description:
    "Autonomous planning, parallel web exploration, and human-in-the-loop competitive research for startup founders.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-zinc-100 min-h-screen antialiased selection:bg-amber-500/20 selection:text-amber-200">
        {children}
      </body>
    </html>
  );
}
