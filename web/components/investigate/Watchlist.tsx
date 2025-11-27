"use client"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { X } from "lucide-react"

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
        <Card className="p-4 space-y-4">
            <h3 className="font-semibold text-sm">Watchlist & Alerts</h3>
            <div className="flex gap-2">
                <Input
                    placeholder="Add keyword..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && add()}
                />
                <Button onClick={add} variant="secondary">Add</Button>
            </div>
            <div className="flex flex-wrap gap-2">
                {keywords.map(k => (
                    <Badge key={k} variant="outline" className="gap-1 pl-2 pr-1 py-1">
                        {k}
                        <button onClick={() => remove(k)} className="hover:text-red-400">
                            <X className="h-3 w-3" />
                        </button>
                    </Badge>
                ))}
            </div>

            {hits.length > 0 && (
                <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm space-y-2">
                    <div className="font-medium text-red-200">Alerts ({hits.length} hits)</div>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                        {hits.map((h, i) => (
                            <div key={i} className="flex justify-between text-zinc-300">
                                <span>Found "{h.keyword}"</span>
                                <span className="truncate max-w-[200px] opacity-70">{h.url}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </Card>
    )
}
