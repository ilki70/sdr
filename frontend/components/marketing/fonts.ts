import { Space_Grotesk, Instrument_Serif } from "next/font/google";

export const marketingSans = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-marketing-sans",
});

export const marketingSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: "italic",
  variable: "--font-marketing-serif",
});
