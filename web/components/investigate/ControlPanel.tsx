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

export function ControlPanel({ model, setModel, query, setQuery, keywords, setKeywords, hits }: ControlPanelProps) {
    const { toast } = useToast()

    return (
        <Card className="p-5 space-y-6 border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <div>
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Control Center</h2>
                <SearchForm model={model} setModel={setModel} query={query} setQuery={setQuery} />
            </div>
            <Separator className="bg-zinc-800" />
            <Playbooks onSelect={(q) => { setQuery(q); toast({ description: "Playbook loaded" }) }} />
            <Separator className="bg-zinc-800" />
            <Watchlist keywords={keywords} setKeywords={setKeywords} hits={hits} />
        </Card>
    )
}
