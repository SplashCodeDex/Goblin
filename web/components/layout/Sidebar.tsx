"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { LayoutDashboard, History, CalendarClock, Settings, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"

const navItems = [
    { name: "Investigate", href: "/", icon: LayoutDashboard },
    { name: "History", href: "/history", icon: History },
    { name: "Schedule", href: "/schedule", icon: CalendarClock },
]

export function Sidebar() {
    const pathname = usePathname()
    const [isCollapsed, setIsCollapsed] = useState(false)

    return (
        <div
            className={cn(
                "flex flex-col h-screen bg-zinc-950 border-r border-zinc-800 transition-all duration-300 ease-in-out relative",
                isCollapsed ? "w-20" : "w-64"
            )}
        >
            <div className="p-6 flex items-center justify-between overflow-hidden whitespace-nowrap">
                {!isCollapsed && (
                    <div className="flex items-center gap-2 font-bold text-xl text-white fade-in">
                        <span className="text-red-500">Robin</span> Intel
                    </div>
                )}
                {isCollapsed && (
                    <div className="w-full flex justify-center font-bold text-xl text-red-500">R</div>
                )}
            </div>

            <nav className="flex-1 px-3 space-y-2">
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
                                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/50",
                                isCollapsed && "justify-center px-2"
                            )}
                            title={isCollapsed ? item.name : undefined}
                        >
                            <Icon className="w-5 h-5 min-w-[20px]" />
                            {!isCollapsed && <span className="truncate fade-in">{item.name}</span>}
                        </Link>
                    )
                })}
            </nav>

            <div className="p-4 border-t border-zinc-800 flex flex-col gap-4">
                <Button
                    variant="ghost"
                    size="icon"
                    className="w-full flex items-center justify-center text-zinc-500 hover:text-white"
                    onClick={() => setIsCollapsed(!isCollapsed)}
                >
                    {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
                </Button>

                {!isCollapsed && (
                    <div className="text-xs text-zinc-500 text-center fade-in">
                        v1.0.0 • Connected
                    </div>
                )}
            </div>
        </div>
    )
}
