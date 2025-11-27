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

export function SearchForm(props: {
  model: string
  setModel: (v: string) => void
  query: string
  setQuery: (v: string) => void
  onRefine: () => Promise<void>
  refined: string
}) {
  const { model, setModel, query, setQuery, onRefine, refined } = props
  return (
    <div className="grid gap-6">
      <div className="grid gap-2">
        <label className="text-sm text-zinc-300">Model</label>
        <Select value={model} onValueChange={setModel}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select a model" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="gemini-2.5-flash">gemini-2.5-flash</SelectItem>
            <SelectItem value="gpt-4.1">gpt-4.1</SelectItem>
            <SelectItem value="gpt4o">gpt4o</SelectItem>
            <SelectItem value="claude-3-5-sonnet-latest">claude-3-5-sonnet-latest</SelectItem>
            <SelectItem value="llama3.1">llama3.1</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-2">
        <label className="text-sm text-zinc-300">Query</label>
        <Textarea value={query} onChange={e => setQuery(e.target.value)} placeholder="Enter dark web search query" />
      </div>
      <div className="flex gap-3 items-center">
        <Button onClick={onRefine} className="px-5">Refine</Button>
        {refined && <span className="text-sm text-zinc-400 truncate">Refined: {refined}</span>}
      </div>
    </div>
  )
}
