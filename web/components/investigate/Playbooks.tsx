"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, X, Book } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

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
            } catch { }
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
            <div className="flex items-center justify-between">
                <label className="text-sm text-zinc-400 font-medium flex items-center gap-2">
                    <Book className="w-4 h-4" /> Playbooks
                </label>
                <Dialog open={open} onOpenChange={setOpen}>
                    <DialogTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                            <Plus className="w-4 h-4" />
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Add Custom Playbook</DialogTitle>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid gap-2">
                                <label>Title</label>
                                <Input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="e.g. Drug Market Search" />
                            </div>
                            <div className="grid gap-2">
                                <label>Query</label>
                                <Input value={newQuery} onChange={e => setNewQuery(e.target.value)} placeholder="e.g. buy cocaine darknet market onion" />
                            </div>
                            <Button onClick={savePlaybook}>Save Playbook</Button>
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
                            className="bg-zinc-900/50 border-zinc-800 hover:bg-zinc-800 hover:text-zinc-200 pr-8"
                        >
                            {name}
                        </Button>
                        {!DEFAULT_PLAYBOOKS.hasOwnProperty(name) && (
                            <button
                                onClick={(e) => { e.stopPropagation(); deletePlaybook(name) }}
                                className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}
