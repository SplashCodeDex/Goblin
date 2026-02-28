"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, X, Book, Check } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"

const DEFAULT_PLAYBOOKS = {
    "Ransomware investigation": "ransomware gang leak site credentials logs",
    "Credential leak": "database dump credentials password email combo leak",
    "Zero-day chatter": "zero day exploit sale PoC CVE leak"
}

export function Playbooks(props: {
    onSelect: (query: string) => void
}) {
    const [playbooks, setPlaybooks] = useState<Record<string, string>>(DEFAULT_PLAYBOOKS)
    const [newTitle, setNewTitle] = useState("")
    const [newQuery, setNewQuery] = useState("")
    const [open, setOpen] = useState(false)

    useEffect(() => {
        const saved = localStorage.getItem("robin-playbooks")
        if (saved) {
            try {
                setPlaybooks({ ...DEFAULT_PLAYBOOKS, ...JSON.parse(saved) })
            } catch (e: any) {
                console.error("Failed to parse saved playbooks:", e)
            }
        }
    }, [])

    function savePlaybook() {
        if (!newTitle.trim() || !newQuery.trim()) return
        const updated = { ...playbooks, [newTitle]: newQuery }
        setPlaybooks(updated)
        localStorage.setItem("robin-playbooks", JSON.stringify(updated))
        setNewTitle("")
        setNewQuery("")
        setOpen(false)
    }

    function deletePlaybook(key: string) {
        const { [key]: _, ...rest } = playbooks
        setPlaybooks(rest)
        localStorage.setItem("robin-playbooks", JSON.stringify(rest))
    }

    return (
        <div className="grid gap-3">
            <div className="flex items-center justify-between px-1">
                <div /> {/* Left spacer to align with parent if needed */}
                <Dialog open={open} onOpenChange={setOpen}>
                    <DialogTrigger asChild>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-[10px] text-zinc-500 hover:text-accent hover:bg-accent/5 font-black uppercase tracking-widest gap-1.5 border border-transparent hover:border-accent/20 transition-all"
                        >
                            <Plus className="w-3 h-3" />
                            Initialize Custom
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-zinc-950 border-zinc-800">
                        <DialogHeader>
                            <DialogTitle className="text-zinc-100 font-bold tracking-tight">Add Tactical Playbook</DialogTitle>
                        </DialogHeader>
                        <div className="grid gap-5 py-4">
                            <div className="grid gap-2">
                                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Protocol Name</label>
                                <Input
                                    value={newTitle}
                                    onChange={e => setNewTitle(e.target.value)}
                                    placeholder="e.g. DARK_MARKET_INTEL"
                                    className="h-10 bg-black/40 border-zinc-800 text-sm font-semibold focus-visible:ring-accent/30"
                                />
                            </div>
                            <div className="grid gap-2">
                                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Logic Query</label>
                                <Input
                                    value={newQuery}
                                    onChange={e => setNewQuery(e.target.value)}
                                    placeholder="Enter reconnaissance parameters..."
                                    className="h-10 bg-black/40 border-zinc-800 text-sm font-semibold focus-visible:ring-accent/30"
                                />
                            </div>
                            <DialogFooter className="mt-6 pt-6 border-t border-zinc-900 flex items-center gap-4">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setOpen(false)}
                                    className="text-zinc-500 font-bold uppercase tracking-widest text-[10px] hover:text-red-400 hover:bg-red-400/5 transition-all h-10 px-6"
                                >
                                    Cancel / Abort
                                </Button>
                                <Button
                                    onClick={savePlaybook}
                                    disabled={!newTitle.trim() || !newQuery.trim()}
                                    className="flex-1 bg-zinc-100 hover:bg-white disabled:bg-zinc-800 disabled:text-zinc-600 text-zinc-950 font-black uppercase tracking-widest h-10 shadow-lg shadow-white/5 transition-all gap-2"
                                >
                                    <Check className="w-4 h-4" />
                                    Save Playbook
                                </Button>
                            </DialogFooter>
                        </div>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="flex flex-wrap gap-2">
                {Object.entries(playbooks).map(([name, query]) => (
                    <div key={name} className="group relative">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => props.onSelect(query)}
                            className="h-auto py-2.5 px-4 bg-zinc-950/40 border-zinc-800 hover:border-accent/40 hover:bg-accent/[0.03] transition-all group overflow-hidden pr-10"
                        >
                            <div className="flex flex-col items-start gap-1">
                                <span className="text-[11px] font-black text-zinc-300 group-hover:text-accent transition-colors">{name}</span>
                                <span className="text-[9px] text-zinc-600 font-bold truncate max-w-[120px] italic">RECON_PARAMS: {query}</span>
                            </div>
                        </Button>
                        {!DEFAULT_PLAYBOOKS.hasOwnProperty(name) && (
                            <button
                                onClick={(e) => { e.stopPropagation(); deletePlaybook(name) }}
                                className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-400/10 rounded-full transition-all"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        )}
                        {/* Subtle ping indicator for interaction */}
                        <div className="absolute -left-1 -top-1 w-2 h-2 rounded-full bg-accent/20 blur-sm opacity-0 group-hover:opacity-100 animate-pulse transition-opacity" />
                    </div>
                ))}
            </div>
        </div>
    )
}
