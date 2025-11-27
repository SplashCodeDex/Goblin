"use client"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Search, Filter, FileText } from "lucide-react"

export function ProgressSteps(props: {
  refined: boolean
  searchInProgress: boolean
  resultsCount: number
  filteredCount: number
  scraping: { inProgress: boolean; percent: number }
  hasSummary: boolean
  onSearch: () => Promise<void>
  onFilter: () => Promise<void>
  onScrape: () => Promise<void>
}) {
  const { refined, searchInProgress, resultsCount, filteredCount, scraping, hasSummary, onSearch, onFilter, onScrape } = props
  return (
    <div className="grid md:grid-cols-3 gap-6 relative">
      {/* Connecting lines for desktop */}
      <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-zinc-800 -z-10 -translate-y-1/2" />

      {/* Step 1: Search */}
      <div className="relative bg-zinc-900/80 backdrop-blur p-4 rounded-lg border border-zinc-800 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-100 font-medium">
            <div className="p-2 bg-blue-500/10 rounded-md text-blue-400">
              <Search className="w-4 h-4" />
            </div>
            Search
          </div>
          <span className="text-xs font-mono text-zinc-500">{resultsCount} found</span>
        </div>
        <Button
          size="sm"
          className="w-full"
          onClick={onSearch}
          disabled={!refined || searchInProgress}
          variant={resultsCount > 0 ? "outline" : "default"}
        >
          {searchInProgress ? "Searching..." : resultsCount > 0 ? "Re-run Search" : "Run Search"}
        </Button>
      </div>

      {/* Step 2: Filter */}
      <div className="relative bg-zinc-900/80 backdrop-blur p-4 rounded-lg border border-zinc-800 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-100 font-medium">
            <div className="p-2 bg-purple-500/10 rounded-md text-purple-400">
              <Filter className="w-4 h-4" />
            </div>
            Filter
          </div>
          <span className="text-xs font-mono text-zinc-500">{filteredCount} selected</span>
        </div>
        <Button
          size="sm"
          className="w-full"
          variant="secondary"
          onClick={onFilter}
          disabled={resultsCount === 0}
        >
          Apply Filters
        </Button>
      </div>

      {/* Step 3: Scrape */}
      <div className="relative bg-zinc-900/80 backdrop-blur p-4 rounded-lg border border-zinc-800 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-100 font-medium">
            <div className="p-2 bg-emerald-500/10 rounded-md text-emerald-400">
              <FileText className="w-4 h-4" />
            </div>
            Extract
          </div>
          <span className="text-xs font-mono text-zinc-500">
            {scraping.inProgress ? `${scraping.percent}%` : hasSummary ? "Complete" : "Ready"}
          </span>
        </div>

        {scraping.inProgress ? (
          <Progress value={scraping.percent} className="h-9" />
        ) : (
          <Button
            size="sm"
            className="w-full"
            onClick={onScrape}
            disabled={filteredCount === 0}
            variant={hasSummary ? "outline" : "default"}
          >
            {hasSummary ? "Re-Scrape" : "Start Extraction"}
          </Button>
        )}
      </div>
    </div>
  )
}
