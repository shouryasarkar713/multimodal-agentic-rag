import type { Metadata } from "next";
import { EB_Garamond, Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppLayout } from "../components/AppLayout";

const ebGaramond = EB_Garamond({ subsets: ["latin"], variable: "--font-eb-garamond" });
const spaceGrotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-space-grotesk" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });

export const metadata: Metadata = {
  title: "Research Copilot",
  description: "Your multimodal technical research assistant with Agentic RAG",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${ebGaramond.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} font-sans antialiased text-slate-200 bg-background`}>
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  );
}
