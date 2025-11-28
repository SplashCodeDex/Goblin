"use client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Settings } from "lucide-react"
import { HistoryDialog } from "@/components/investigate/HistoryDialog"
import { HistoryRun } from "@/lib/api"

interface DashboardHeaderProps {
    status: {
        torReady: boolean
        modelReady: boolean
        missing: string[]
    }
    onLoadHistory: (run: HistoryRun) => void
    onOpenSettings: () => void
}

export function DashboardHeader({ status, onLoadHistory, onOpenSettings }: DashboardHeaderProps) {
    return (
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight">Investigation Dashboard</h1>
                <div className="flex gap-2">
                    <Badge variant={status.torReady ? "default" : "destructive"} className="h-6">
                        Tor {status.torReady ? "Ready" : "Not Ready"}
                    </Badge>
                    <Badge variant={status.modelReady ? "default" : "destructive"} className="h-6">
                        Model {status.modelReady ? "Ready" : "Missing"}
                    </Badge>
                </div>
            </div>
            <div className="flex gap-2 items-center">
                <HistoryDialog onLoad={onLoadHistory} />
                <Button variant="ghost" size="icon" onClick={onOpenSettings}>
                    <Settings className="h-4 w-4" />
                </Button>
            </div>
        </div>
    )
}
