"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plus, X, Book, Check, Sparkles, Loader2 } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { suggestPlaybooks } from "@/lib/api"
import { toast } from "@/components/hooks/use-toast"

const DEFAULT_PLAYBOOKS = {
    "Ransomware Leak Sites": "ransomware gang leak site stolen data credentials",
    "Credential Markets": "database dump credentials combo list email password",
    "Exploit Trading": "zero day exploit CVE PoC vulnerability sale",
    "Malware Infrastructure": "C2 command control malware botnet infrastructure",
    "Phishing Campaigns": "phishing kit panel credential harvester scam"
}

export function Playbooks(props: {
    onSelect: (query: string) => void
    currentQuery?: string
    currentModel?: string
}) {
    const [playbooks, setPlaybooks] = useState<Record<string, string>>(DEFAULT_PLAYBOOKS)
    const [newTitle, setNewTitle] = useState("")
    const [newQuery, setNewQuery] = useState("")
    const [open, setOpen] = useState(false)
    const [suggestOpen, setSuggestOpen] = useState(false)
    const [suggesting, setSuggesting] = useState(false)
    const [suggestions, setSuggestions] = useState<Array<{ name: string; query: string }>>([])

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

    async function handleSuggest() {
        if (!props.currentModel) {
            toast({ description: "Please select a model first", variant: "destructive" })
            return
        }
        
        setSuggesting(true)
        try {
            const result = await suggestPlaybooks(
                props.currentModel, 
                props.currentQuery || "", 
                5
            )
            setSuggestions(result.suggestions)
            setSuggestOpen(true)
            toast({ description: `Generated ${result.suggestions.length} playbook suggestions` })
        } catch (e: any) {
            toast({ description: e?.message || "Failed to generate suggestions", variant: "destructive" })
        } finally {
            setSuggesting(false)
        }
    }

    function saveSuggestion(name: string, query: string) {
        const updated = { ...playbooks, [name]: query }
        setPlaybooks(updated)
        localStorage.setItem("robin-playbooks", JSON.stringify(updated))
        toast({ description: `Saved playbook: ${name}` })
    }

    return (
        <div className="grid gap-3">
            <div className="flex items-center justify-between px-1 gap-2">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSuggest}
                    disabled={suggesting || !props.currentModel}
                    className="h-7 px-2 text-[10px] text-emerald-500 hover:text-emerald-400 hover:bg-emerald-400/5 font-black uppercase tracking-widest gap-1.5 border border-transparent hover:border-emerald-400/20 transition-all disabled:opacity-50"
                >
                    {suggesting ? (
                        <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            AI Processing...
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-3 h-3" />
                            AI Suggest
                        </>
                    )}
                </Button>
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

            {/* AI Suggestions Dialog */}
            <Dialog open={suggestOpen} onOpenChange={setSuggestOpen}>
                <DialogContent className="bg-zinc-950 border-zinc-800 max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="text-zinc-100 font-bold tracking-tight flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-emerald-400" />
                            AI-Suggested Playbooks
                        </DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-3 py-4 max-h-[60vh] overflow-y-auto">
                        {suggestions.length === 0 ? (
                            <div className="text-center text-zinc-500 py-8">
                                No suggestions available
                            </div>
                        ) : (
                            suggestions.map((suggestion, idx) => (
                                <div key={idx} className="border border-zinc-800 rounded-lg p-4 hover:border-emerald-400/30 transition-all group">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1">
                                            <h4 className="text-sm font-black text-emerald-400 mb-2">{suggestion.name}</h4>
                                            <p className="text-xs text-zinc-500 font-mono italic">QUERY: {suggestion.query}</p>
                                        </div>
                                        <div className="flex gap-2">
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => {
                                                    props.onSelect(suggestion.query)
                                                    setSuggestOpen(false)
                                                    toast({ description: "Playbook query loaded" })
                                                }}
                                                className="h-8 px-3 text-[10px] font-bold uppercase tracking-widest text-blue-400 hover:text-blue-300 hover:bg-blue-400/10"
                                            >
                                                Load
                                            </Button>
                                            <Button
                                                size="sm"
                                                onClick={() => saveSuggestion(suggestion.name, suggestion.query)}
                                                disabled={playbooks.hasOwnProperty(suggestion.name)}
                                                className="h-8 px-3 text-[10px] font-bold uppercase tracking-widest bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-600"
                                            >
                                                <Check className="w-3 h-3 mr-1" />
                                                {playbooks.hasOwnProperty(suggestion.name) ? "Saved" : "Save"}
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    <DialogFooter className="border-t border-zinc-900 pt-4">
                        <Button
                            variant="ghost"
                            onClick={() => setSuggestOpen(false)}
                            className="text-zinc-500 font-bold uppercase tracking-widest text-[10px] hover:text-zinc-300"
                        >
                            Close
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
