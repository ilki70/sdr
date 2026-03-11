import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SDR | Plataforma de Operacao Conversacional com IA",
  description: "Agentes, inbox, analytics e quality para vendas, atendimento e pos-venda.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
