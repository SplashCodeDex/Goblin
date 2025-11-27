"use client"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

const playbooks = {
    "Ransomware investigation": "ransomware gang leak site credentials logs",
    "Credential leak": "database dump credentials password email combo leak",
    "Zero-day chatter": "zero day exploit sale PoC CVE leak"
}

export function Playbooks(props: {
    onSelect: (query: string) => void
}) {
    return (
        <div className="grid gap-2">
            <label className="text-sm text-zinc-400">Playbooks</label>
            <div className="flex flex-wrap gap-2">
                {Object.entries(playbooks).map(([name, query]) => (
                    <Button
                        key={name}
                        variant="outline"
                        size="sm"
                        onClick={() => props.onSelect(query)}
                        className="bg-zinc-900/50 border-zinc-800 hover:bg-zinc-800 hover:text-zinc-200"
                    >
                        {name}
                    </Button>
                ))}
            </div>
        </div>
    )
}
