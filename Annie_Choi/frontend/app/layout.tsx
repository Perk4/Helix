import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mindful Coach",
  description: "An AI wellness assistant for stress management and mindfulness.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
