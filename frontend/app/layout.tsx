import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agente Vendedor",
  description: "Plataforma de vendas com IA.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
