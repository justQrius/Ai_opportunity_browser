import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers/providers";
import { Navigation } from "@/components/navigation";
import { AuthProvider } from "@/components/auth/auth-provider";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Opportunity Browser",
  description: "Discover and validate AI-solvable market opportunities through autonomous agent-based discovery and community-driven validation.",
  keywords: ["AI", "opportunities", "market validation", "entrepreneurs", "business intelligence"],
  authors: [{ name: "AI Opportunity Browser Team" }],
  creator: "AI Opportunity Browser",
  publisher: "AI Opportunity Browser",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://ai-opportunity-browser.com",
    siteName: "AI Opportunity Browser",
    title: "AI Opportunity Browser",
    description: "Discover and validate AI-solvable market opportunities",
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Opportunity Browser",
    description: "Discover and validate AI-solvable market opportunities",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased font-sans`}
      >
        <Providers>
          <AuthProvider>
            <Navigation />
            <main className="min-h-screen">
              {children}
            </main>
            <Toaster />
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
