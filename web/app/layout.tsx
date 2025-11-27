import "./globals.css"
import type { Metadata } from "next"
import { Sidebar } from "@/components/layout/Sidebar"
import { Toaster } from "@/components/ui/toaster"

export const metadata: Metadata = {
  title: "Robin UI",
  description: "Next.js UI for Robin",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-black text-white flex">
        <Sidebar />
        <main className="flex-1 overflow-auto h-screen">
          {children}
        </main>
        <Toaster />
      </body>
    </html>
  )
}
