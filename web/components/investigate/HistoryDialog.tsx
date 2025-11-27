"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { getHistory } from "@/lib/api"
import { format } from "date-fns"
import { History } from "lucide-react"

export function HistoryDialog(props: { onLoad: (run: any) => void }) {
    const [open, setOpen] = useState(false)
    const [runs, setRuns] = useState<any[]>([])

    useEffect(() => {
        if (open) {
            getHistory().then(r => setRuns(r.runs)).catch(console.error)
        }
    }, [open])

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" size="icon" title="History">
                    <History className="h-4 w-4" />
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Investigation History</DialogTitle>
                </DialogHeader>
                <ScrollArea className="h-[400px]">
                    <div className="space-y-2">
                        {runs.map((run, i) => (
                            <div key={i} className="flex items-center justify-between p-3 border rounded-md hover:bg-zinc-800/50 cursor-pointer" onClick={() => { props.onLoad(run); setOpen(false) }}>
                                <div>
                                    <div className="font-medium">{run.query}</div>
                                    <div className="text-xs text-zinc-400">{format(new Date(run.timestamp), "PPpp")}</div>
                                </div>
                                <Button variant="ghost" size="sm">Load</Button>
                            </div>
                        ))}
                        {runs.length === 0 && <div className="text-center text-zinc-500 py-8">No history found</div>}
                    </div>
                </ScrollArea>
            </DialogContent>
        </Dialog>
    )
}
