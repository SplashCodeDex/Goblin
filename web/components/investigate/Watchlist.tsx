"use client"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { X, Search, Activity, ShieldAlert, Plus } from "lucide-react"

export function Watchlist(props: {
    keywords: string[]
    setKeywords: (k: string[]) => void
    hits: { keyword: string; url: string }[]
}) {
    const { keywords, setKeywords, hits } = props
    const [input, setInput] = useState("")

    function add() {
        if (input && !keywords.includes(input)) {
            setKeywords([...keywords, input])
            setInput("")
        }
    }

    function remove(k: string) {
        setKeywords(keywords.filter(x => x !== k))
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Activity className="w-3.5 h-3.5 text-zinc-500" />
                    <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Recon Watchlist</span>
                </div>
                {hits.length > 0 && (
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 animate-pulse">
                        <ShieldAlert className="w-2.5 h-2.5 text-red-500" />
                        <span className="text-[9px] font-black text-red-500 uppercase tracking-wider">Breach Alert</span>
                    </div>
                )}
            </div>

            <div className="grid gap-4">
                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-600" />
                        <Input
                            placeholder="Register keyword..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && add()}
                            className="pl-9 h-9 bg-black/40 border-zinc-800 text-xs font-semibold focus-visible:ring-accent/30 placeholder:text-zinc-700"
                        />
                    </div>
                    <Button onClick={add} variant="secondary" size="sm" className="h-9 px-3 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-bold uppercase text-[10px] tracking-widest gap-1.5">
                        <Plus className="w-3 h-3" />
                        Add
                    </Button>
                </div>

                <div className="flex flex-wrap gap-1.5 min-h-[32px]">
                    {keywords.map(k => (
                        <Badge key={k} variant="outline" className="gap-1.5 pl-2.5 pr-1 py-1 bg-zinc-900/50 border-zinc-800 text-[10px] font-bold text-zinc-400 group hover:border-accent/40 transition-all">
                            {k}
                            <button onClick={() => remove(k)} className="p-0.5 rounded-full hover:bg-red-500/10 hover:text-red-400 transition-colors">
                                <X className="h-2.5 w-2.5" />
                            </button>
                        </Badge>
                    ))}
                    {keywords.length === 0 && <span className="text-[10px] text-zinc-700 italic font-semibold mt-2">NO ACTIVE WATCHLIST PARAMETERS...</span>}
                </div>
            </div>

            {hits.length > 0 && (
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 space-y-3 backdrop-blur-sm relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-2 opacity-10">
                        <ShieldAlert className="w-12 h-12 text-red-500" />
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-1 h-3 bg-red-500 rounded-full" />
                        <div className="text-[10px] font-black text-red-400 uppercase tracking-wider">Active Hits Detected ({hits.length})</div>
                    </div>
                    <div className="max-h-32 overflow-y-auto space-y-1.5 pr-2 scrollbar-thin scrollbar-thumb-red-500/20 scrollbar-track-transparent">
                        {hits.map((h, i) => (
                            <div key={i} className="flex flex-col gap-0.5 p-2 rounded bg-black/40 border border-white/5 group hover:border-red-500/20 transition-all">
                                <div className="flex items-center justify-between">
                                    <span className="text-[11px] font-black text-zinc-300 uppercase tracking-wider group-hover:text-red-400 transition-colors">MATCH: {h.keyword}</span>
                                    <span className="text-[8px] font-bold text-zinc-600 uppercase">Alert_ID: {i.toString(16).padStart(4, '0')}</span>
                                </div>
                                <span className="truncate text-[10px] font-medium text-zinc-500 italic">{h.url}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
