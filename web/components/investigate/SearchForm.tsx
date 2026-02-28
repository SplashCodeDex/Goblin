"use client"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select"

import { Cpu, Terminal, Sparkles } from "lucide-react"

export function SearchForm(props: {
  model: string
  setModel: (v: string) => void
  query: string
  setQuery: (v: string) => void
}) {
  const { model, setModel, query, setQuery } = props
  return (
    <div className="grid gap-6">
      <div className="grid gap-2.5">
        <label className="text-[10px] font-black text-zinc-500 uppercase tracking-wider flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-accent/50" />
          Active Processor
        </label>
        <Select value={model} onValueChange={setModel}>
          <SelectTrigger className="w-full bg-black/40 border-zinc-800 hover:border-zinc-700 transition-colors text-zinc-300 font-semibold text-xs">
            <SelectValue placeholder="Select a model" />
          </SelectTrigger>
          <SelectContent className="bg-zinc-950 border-zinc-800">
            <SelectItem value="gemini-2.5-flash" className="text-xs hover:bg-white/5">gemini-2.5-flash</SelectItem>
            <SelectItem value="gpt-4.1" className="text-xs hover:bg-white/5">gpt-4.1</SelectItem>
            <SelectItem value="gpt-4o" className="text-xs hover:bg-white/5">gpt-4o</SelectItem>
            <SelectItem value="claude-3-5-sonnet-latest" className="text-xs hover:bg-white/5">claude-3-5-sonnet-latest</SelectItem>
            <SelectItem value="llama3.1" className="text-xs hover:bg-white/5">llama3.1</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-2.5">
        <label className="text-[10px] font-black text-zinc-500 uppercase tracking-wider flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-accent/50" />
          Intelligence Query
        </label>
        <Textarea
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="INPUT SEARCH PARAMETERS..."
          className="min-h-[100px] bg-black/40 border-zinc-800 focus-visible:ring-accent/30 text-zinc-200 font-medium text-[13px] leading-relaxed placeholder:text-zinc-700 resize-none selection:bg-accent/30 py-3"
        />
      </div>
    </div>
  )
}
