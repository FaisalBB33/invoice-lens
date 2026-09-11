import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Invoice Lens",
  description: "A focused AI invoice processing pipeline.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
