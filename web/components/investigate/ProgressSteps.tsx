"use client"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Search, Filter, FileText } from "lucide-react"

export function ProgressSteps(props: {
  refined: boolean
  resultsCount: number
  filteredCount: number
  scraping: { inProgress: boolean; percent: number }
  hasSummary: boolean
  onSearch: () => Promise<void>
  onFilter: () => Promise<void>
  onScrape: () => Promise<void>
}) {
  const { refined, resultsCount, filteredCount, scraping, hasSummary, onSearch, onFilter, onScrape } = props
  return (
    <div className="grid md:grid-cols-3 gap-4">
      <div className="space-y-2">
        <div className="text-sm text-zinc-400">Search</div>
        <div className="text-lg font-semibold">{resultsCount} results</div>
        <Button variant="secondary" onClick={onSearch} disabled={!refined}>Run Search</Button>
      </div>
      <div className="space-y-2">
        <div className="text-sm text-zinc-400">Filter</div>
        <div className="text-lg font-semibold">{filteredCount} selected</div>
        <Button variant="secondary" onClick={onFilter} disabled={resultsCount === 0}>Filter</Button>
      </div>
      <div className="space-y-2">
        <div className="text-sm text-zinc-400">Scrape & Summarize</div>
        <div className="text-sm">{scraping.inProgress ? `Scraping... ${scraping.percent}%` : hasSummary ? "Done" : "Idle"}</div>
        <Progress value={scraping.percent} className="h-2" />
        <Button onClick={onScrape} disabled={filteredCount === 0 || scraping.inProgress}>Scrape</Button>
      </div>
    </div>
  )
}
