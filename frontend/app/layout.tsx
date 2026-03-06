import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Super Vendedor",
  description: "Plataforma de agentes comerciais com IA para operar funis, canais e fechamento.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
