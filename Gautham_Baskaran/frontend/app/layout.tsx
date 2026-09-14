import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Project Co-Pilot",
  description: "AI strategy advisor — feasibility, approach, risks & quick wins for your AI ideas",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
