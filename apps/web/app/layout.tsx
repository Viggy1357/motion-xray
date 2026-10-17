import type { Metadata } from "next";
import "./globals.css";

// Motion X Ray — root layout (STRUCTURE-ONLY scaffold).
export const metadata: Metadata = {
  title: "Motion X Ray",
  description: "Turn a short workout video into a rep-by-rep movement report.",
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
