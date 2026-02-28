"use client"
import { Card } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { useToast } from "@/components/hooks/use-toast"
import { SearchForm } from "@/components/investigate/SearchForm"
import { Playbooks } from "@/components/investigate/Playbooks"
import { Watchlist } from "@/components/investigate/Watchlist"

interface ControlPanelProps {
    model: string
    setModel: (v: string) => void
    query: string
    setQuery: (v: string) => void
    keywords: string[]
    setKeywords: (v: string[]) => void
    hits: { keyword: string; url: string }[]
}

import { Terminal, Command, Settings2 } from "lucide-react"

export function ControlPanel({ model, setModel, query, setQuery, keywords, setKeywords, hits }: ControlPanelProps) {
    const { toast } = useToast()

    return (
        <Card className="p-0 overflow-hidden border-zinc-800 bg-zinc-900/60 backdrop-blur-md shadow-2xl">
            {/* Header section */}
            <div className="p-5 border-b border-white/5 bg-white/[0.02]">
                <div className="flex items-center gap-2.5 mb-6">
                    <div className="p-2 rounded-lg bg-accent/10 border border-accent/20">
                        <Settings2 className="w-4 h-4 text-accent" />
                    </div>
                    <div>
                        <h2 className="text-[11px] font-black text-zinc-100 uppercase tracking-[0.15em] leading-none">Control Center</h2>
                        <p className="text-[9px] text-zinc-500 font-semibold mt-1.5 uppercase tracking-wider">System Configuration // V2</p>
                    </div>
                </div>

                <SearchForm model={model} setModel={setModel} query={query} setQuery={setQuery} />
            </div>

            <div className="p-5 space-y-8">
                <section>
                    <div className="flex items-center gap-2 mb-4">
                        <Command className="w-3.5 h-3.5 text-zinc-500" />
                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Tactical Playbooks</span>
                    </div>
                    <Playbooks onSelect={(q) => { setQuery(q); toast({ description: "Playbook loaded" }) }} />
                </section>

                <Separator className="bg-white/5" />

                <section>
                    <Watchlist keywords={keywords} setKeywords={setKeywords} hits={hits} />
                </section>
            </div>
        </Card>
    )
}
