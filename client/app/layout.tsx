import type { Metadata } from "next";
import UFHeader from "../components/UFHeader";
import UFFooter from "../components/UFFooter";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mango Identification",
  description: "Identify mango varieties.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-screen flex-col supports-[min-height:100dvh]:min-h-dvh">
        <UFHeader />
        <div className="min-w-0 flex-1">{children}</div>
        <UFFooter />
      </body>

    </html>
  );
}
