"use client"
import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/hooks/use-toast"
import { AdvancedSettingsDialog } from "@/components/investigate/AdvancedSettingsDialog"
import { Settings } from "lucide-react"

import { SearchForm } from "@/components/investigate/SearchForm"
import { Playbooks } from "@/components/investigate/Playbooks"
import { Watchlist } from "@/components/investigate/Watchlist"
import { HistoryDialog } from "@/components/investigate/HistoryDialog"
import { ProgressSteps } from "@/components/investigate/ProgressSteps"
import { SourcesTable } from "@/components/investigate/SourcesTable"
import { SummaryCard } from "@/components/investigate/SummaryCard"
import { ArtifactsTable } from "@/components/investigate/ArtifactsTable"
import { ResultsTable } from "@/components/investigate/ResultsTable"

import { refine, search, filter, scrape, summary, health, scrapeOne, modelStatus } from "@/lib/api"

export default function InvestigatePage() {
  const { toast } = useToast()
  const [model, setModel] = useState("gemini-2.5-flash")

  function downloadCSV(data: any[]) {
    const headers = Object.keys(data[0] || {}).join(",")
    const rows = data.map(row => Object.values(row).map(v => `"${String(v).replace(/"/g, '""')}"`).join(","))
    const csv = [headers, ...rows].join("\n")
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "sources.csv"
    a.click()
  }

  function downloadJSON(data: any[]) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "sources.json"
    a.click()
  }
  const [query, setQuery] = useState("")

  const [refinedText, setRefinedText] = useState("")
  const [results, setResults] = useState<any[]>([])
  const [filteredRes, setFilteredRes] = useState<any[]>([])
  const [scrapeState, setScrapeState] = useState({ inProgress: false, percent: 0, sources: [] as { url: string; excerpt: string }[] })
  const [summaryText, setSummaryText] = useState("")
  const [artifacts, setArtifacts] = useState<any[]>([])
  const [stix, setStix] = useState<any>({})
  const [misp, setMisp] = useState<any>({})
  const [status, setStatus] = useState({ torReady: false, modelReady: true, missing: [] as string[] })
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [threads, setThreads] = useState(5)
  const [maxResults, setMaxResults] = useState(200)
  const [detailed, setDetailed] = useState(false)
  const [requestTimeout, setRequestTimeout] = useState(30)
  const [useCache, setUseCache] = useState(true)
  const [loadCachedOnly, setLoadCachedOnly] = useState(false)
  const [translate, setTranslate] = useState(true)
  const [perUrl, setPerUrl] = useState<{ url: string; status: string }[]>([])
  const [selectedMap, setSelectedMap] = useState<Record<string, boolean>>({})
  const [keywords, setKeywords] = useState<string[]>([])
  const [hits, setHits] = useState<{ keyword: string; url: string }[]>([])

  const [searchInProgress, setSearchInProgress] = useState(false)

  // Watchlist logic
  useEffect(() => {
    if (scrapeState.sources.length === 0 || keywords.length === 0) {
      setHits([])
      return
    }
    const newHits: { keyword: string; url: string }[] = []
    scrapeState.sources.forEach(s => {
      keywords.forEach(k => {
        if (s.excerpt.toLowerCase().includes(k.toLowerCase())) {
          newHits.push({ keyword: k, url: s.url })
        }
      })
    })
    setHits(newHits)
  }, [scrapeState.sources, keywords])

  async function checkHealth() {
    try {
      const h = await health()
      setStatus(prev => ({ ...prev, torReady: !!h.tor }))
    } catch {
      setStatus(prev => ({ ...prev, torReady: false }))
    }
  }

  async function onRefine() {
    try {
      const r = await refine(model, query)
      setRefinedText(r.refined)
      toast({ description: "Refined" })
      await checkHealth()
      try {
        const ms = await modelStatus(model)
        setStatus(s => ({ ...s, modelReady: ms.ready, missing: ms.missing }))
      } catch { }
    } catch (e: any) {
      toast({ description: e?.message || "Refine failed", variant: "destructive" })
    }
  }
  async function onSearch() {
    try {
      setSearchInProgress(true)
      const r = await search(refinedText, threads, maxResults, requestTimeout, useCache, loadCachedOnly)
      setResults(r.results)
      toast({ description: "Search done" })
    } catch (e: any) {
      toast({ description: e?.message || "Search failed", variant: "destructive" })
    } finally {
      setSearchInProgress(false)
    }
  }
  async function onFilter() {
    try {
      const r = await filter(model, refinedText, results)
      setFilteredRes(r.filtered)
      // initialize selection: select all
      const m: Record<string, boolean> = {}
      r.filtered.forEach((item: any) => { m[item.link] = true })
      setSelectedMap(m)
      toast({ description: "Filtered" })
    } catch (e: any) {
      toast({ description: e?.message || "Filter failed", variant: "destructive" })
    }
  }
  async function onScrape() {
    try {
      setScrapeState(s => ({ ...s, inProgress: true, percent: 0 }))
      const selectedTargets = filteredRes.filter((it: any) => selectedMap[it.link])
      const targets = selectedTargets.slice(0, maxResults)
      if (detailed) {
        // Streaming summary: cache scraped first, then stream
        const list = targets.map((t: any) => ({ url: t.link as string, status: 'queued' }))
        setPerUrl(list)
        const scraped: Record<string, string> = {}
        for (let i = 0; i < targets.length; i++) {
          const t = targets[i]
          setPerUrl(prev => prev.map(x => x.url === t.link ? { ...x, status: 'running' } : x))
          const r = await scrapeOne(t)
          scraped[r.url] = r.content
          setPerUrl(prev => prev.map(x => x.url === t.link ? { ...x, status: 'done' } : x))
          setScrapeState(s => ({ ...s, percent: Math.round((i + 1) / targets.length * 100) }))
        }
        const sources = Object.entries(scraped).map(([url, excerpt]) => ({ url, excerpt: String(excerpt) }))
        setScrapeState({ inProgress: false, percent: 100, sources })
        const s = await summary(model, query, scraped)
        setSummaryText(s.summary)
        setArtifacts(Object.entries(s.artifacts || {}).flatMap(([k, v]) => (v as any[]).map(val => ({ type: k, value: val }))))
        setStix(s.stix)
        setMisp(s.misp)
      } else {
        const r = await scrape(targets, threads, requestTimeout, useCache, loadCachedOnly, translate)
        const sources = Object.entries(r.scraped).map(([url, excerpt]) => ({ url, excerpt: String(excerpt) }))
        setScrapeState({ inProgress: false, percent: 100, sources })
        const s = await summary(model, query, r.scraped)
        setSummaryText(s.summary)
        setArtifacts(Object.entries(s.artifacts || {}).flatMap(([k, v]) => (v as any[]).map(val => ({ type: k, value: val }))))
        setStix(s.stix)
        setMisp(s.misp)
      }
      toast({ description: "Summary ready" })
    } catch (e: any) {
      setScrapeState(s => ({ ...s, inProgress: false }))
      toast({ description: e?.message || "Scrape failed", variant: "destructive" })
    }
  }

  function onLoadHistory(run: any) {
    setQuery(run.query)
    setRefinedText(run.refined || "")
    setResults(run.results || [])
    if (run.scraped && Object.keys(run.scraped).length > 0) {
      const sources = Object.entries(run.scraped).map(([url, excerpt]) => ({ url, excerpt: String(excerpt) }))
      setScrapeState({ inProgress: false, percent: 100, sources })
    }
    setSummaryText(run.summary || "")
    if (run.artifacts) {
      setArtifacts(Object.entries(run.artifacts).flatMap(([k, v]) => (v as any[]).map(val => ({ type: k, value: val }))))
    }
    toast({ description: "History loaded" })
  }

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-[1600px]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Investigation Dashboard</h1>
          <div className="flex gap-2">
            <Badge variant={status.torReady ? "default" : "destructive"} className="h-6">Tor {status.torReady ? "Ready" : "Not Ready"}</Badge>
            <Badge variant={status.modelReady ? "default" : "destructive"} className="h-6">Model {status.modelReady ? "Ready" : "Missing"}</Badge>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <HistoryDialog onLoad={onLoadHistory} />
          <Button variant="ghost" size="icon" onClick={() => setSettingsOpen(true)}>
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Inline warnings */}
      {(!status.torReady || !status.modelReady) && (
        <div className="grid gap-2">
          {!status.torReady && (
            <div className="rounded-md border border-yellow-500/30 bg-yellow-500/10 text-yellow-200 px-3 py-2 text-sm">
              Tor SOCKS proxy not detected. Searches may return empty.
            </div>
          )}
          {!status.modelReady && (
            <div className="rounded-md border border-red-500/30 bg-red-500/10 text-red-200 px-3 py-2 text-sm">
              Missing model configuration: {status.missing.join(", ")}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Sidebar: Controls */}
        <div className="col-span-12 lg:col-span-3 space-y-6">
          <Card className="p-5 space-y-6 border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <div>
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Control Center</h2>
              <SearchForm model={model} setModel={setModel} query={query} setQuery={setQuery} onRefine={onRefine} refined={refinedText} />
            </div>
            <Separator className="bg-zinc-800" />
            <Playbooks onSelect={(q) => { setQuery(q); toast({ description: "Playbook loaded" }) }} />
            <Separator className="bg-zinc-800" />
            <Watchlist keywords={keywords} setKeywords={setKeywords} hits={hits} />
          </Card>
        </div>

        {/* Main Content: Pipeline & Results */}
        <div className="col-span-12 lg:col-span-9 space-y-6">
          <Card className="p-5 border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <ProgressSteps
              refined={!!refinedText}
              searchInProgress={searchInProgress}
              resultsCount={results.length}
              filteredCount={filteredRes.length}
              scraping={{ inProgress: scrapeState.inProgress, percent: scrapeState.percent }}
              hasSummary={!!summaryText}
              onSearch={onSearch}
              onFilter={onFilter}
              onScrape={onScrape}
            />
          </Card>

          <Tabs defaultValue="overview" className="space-y-4">
            <div className="flex items-center justify-between">
              <TabsList className="bg-zinc-900/50 border border-zinc-800">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="results">Results ({filteredRes.length})</TabsTrigger>
                <TabsTrigger value="sources">Sources ({scrapeState.sources.length})</TabsTrigger>
                <TabsTrigger value="artifacts">Artifacts ({artifacts.length})</TabsTrigger>
              </TabsList>

              {/* Exports Toolbar */}
              {scrapeState.sources.length > 0 && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => downloadCSV(scrapeState.sources)}>CSV</Button>
                  <Button variant="outline" size="sm" onClick={() => downloadJSON(scrapeState.sources)}>JSON</Button>
                  {stix && Object.keys(stix).length > 0 && (
                    <Button variant="outline" size="sm" onClick={() => downloadJSON(stix)}>STIX</Button>
                  )}
                </div>
              )}
            </div>

            {detailed && perUrl.length > 0 && (
              <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-3">
                <div className="text-sm font-medium mb-2">Per-URL progress</div>
                <div className="grid gap-2 text-sm max-h-40 overflow-y-auto">
                  {perUrl.map(item => (
                    <div key={item.url} className="flex items-center justify-between">
                      <span className="truncate max-w-[70%] text-zinc-400">{item.url}</span>
                      <span className={item.status === 'done' ? "text-green-400" : "text-zinc-500"}>{item.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <TabsContent value="overview" className="mt-0">
              <SummaryCard refined={refinedText} summary={summaryText} />
            </TabsContent>
            <TabsContent value="results" className="mt-0">
              <ResultsTable data={filteredRes} selectedMap={selectedMap} setSelectedMap={setSelectedMap} />
            </TabsContent>
            <TabsContent value="sources" className="mt-0">
              <SourcesTable data={scrapeState.sources} />
            </TabsContent>
            <TabsContent value="artifacts" className="mt-0">
              <ArtifactsTable data={artifacts} />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <AdvancedSettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        threads={threads}
        setThreads={setThreads}
        maxResults={maxResults}
        setMaxResults={setMaxResults}
        detailed={detailed}
        setDetailed={setDetailed}
        requestTimeout={requestTimeout}
        setRequestTimeout={setRequestTimeout}
        useCache={useCache}
        setUseCache={setUseCache}
        loadCachedOnly={loadCachedOnly}
        setLoadCachedOnly={setLoadCachedOnly}
        translate={translate}
        setTranslate={setTranslate}
      />
    </div>
  )
}
