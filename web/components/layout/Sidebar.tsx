"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { LayoutDashboard, History, CalendarClock, Settings } from "lucide-react"

const navItems = [
    { name: "Investigate", href: "/", icon: LayoutDashboard },
    { name: "History", href: "/history", icon: History },
    { name: "Schedule", href: "/schedule", icon: CalendarClock },
]

export function Sidebar() {
    const pathname = usePathname()

    return (
        <div className="flex flex-col h-screen w-64 bg-zinc-950 border-r border-zinc-800">
            <div className="p-6">
                <div className="flex items-center gap-2 font-bold text-xl text-white">
                    <span className="text-red-500">Robin</span> Intelligence
                </div>
            </div>
            <nav className="flex-1 px-4 space-y-2">
                {navItems.map((item) => {
                    const Icon = item.icon
                    const isActive = pathname === item.href
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                                isActive
                                    ? "bg-zinc-800 text-white"
                                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                            )}
                        >
                            <Icon className="w-4 h-4" />
                            {item.name}
                        </Link>
                    )
                })}
            </nav>
            <div className="p-4 border-t border-zinc-800">
                <div className="text-xs text-zinc-500">
                    v1.0.0 • Connected
                </div>
            </div>
        </div>
    )
}
