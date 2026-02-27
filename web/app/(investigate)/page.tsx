"use client"
import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { useToast } from "@/components/hooks/use-toast"
import { AdvancedSettingsDialog } from "@/components/investigate/AdvancedSettingsDialog"
import { ProgressSteps } from "@/components/investigate/ProgressSteps"
import { DashboardHeader } from "@/components/investigate/DashboardHeader"
import { ControlPanel } from "@/components/investigate/ControlPanel"
import { ResultsView } from "@/components/investigate/ResultsView"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Settings } from "lucide-react"

import { downloadCSV, downloadJSON } from "@/lib/utils"
import { extractArtifacts, API_BASE } from "@/lib/api"
import {
  health, modelStatus, search, filter, scrapeOne,
  SearchResult, ScrapedSource, Artifact, HistoryRun
} from "@/lib/api"

export default function InvestigationPage() {
  const { toast } = useToast()
  const [model, setModel] = useState("gpt-4o")
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [filteredRes, setFilteredRes] = useState<SearchResult[]>([])
  const [scrapeState, setScrapeState] = useState({ inProgress: false, percent: 0, sources: [] as ScrapedSource[] })
  const [summaryText, setSummaryText] = useState("")
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [stix, setStix] = useState<any>({})
  const [misp, setMisp] = useState<any>({})
  const [status, setStatus] = useState({ torReady: false, modelReady: true, missing: [] as string[] })
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [threads, setThreads] = useState(5)
  const [maxResults, setMaxResults] = useState(200)
  const [detailed, setDetailed] = useState(false)
  const [minStars, setMinStars] = useState(0)
  const [minForks, setMinForks] = useState(0)
  const [includeCommits, setIncludeCommits] = useState(false)
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

  async function onSearch() {
    try {
      setSearchInProgress(true)

      const sources = ["darkweb", "github", "github_code"]
      if (includeCommits) sources.push("github_commits")

      const res = await search(query, threads, maxResults, requestTimeout, useCache, loadCachedOnly, sources, minStars, minForks)
      setResults(res.results)
      setFilteredRes(res.results)
      toast({ description: "Search done" })

      // Check health/model status in background
      await checkHealth()
      try {
        const ms = await modelStatus(model)
        setStatus(s => ({ ...s, modelReady: ms.ready, missing: ms.missing }))
      } catch (e: any) {
        console.error("Failed to check model status:", e)
      }

    } catch (e: any) {
      toast({ description: e?.message || "Search failed", variant: "destructive" })
    } finally {
      setSearchInProgress(false)
    }
  }

  async function onFilter() {
    try {
      const r = await filter(model, query, results)
      setFilteredRes(r.filtered)
      // initialize selection: select all
      const m: Record<string, boolean> = {}
      r.filtered.forEach((item: SearchResult) => { m[item.link] = true })
      setSelectedMap(m)
      toast({ description: "Filtered" })
    } catch (e: any) {
      toast({ description: e?.message || "Filter failed", variant: "destructive" })
    }
  }

  async function onScrape() {
    try {
      setScrapeState(s => ({ ...s, inProgress: true, percent: 0 }))
      const selectedTargets = filteredRes.filter((it: SearchResult) => selectedMap[it.link])
      const targets = selectedTargets.slice(0, maxResults)
      if (detailed) {
        // Streaming summary: cache scraped first, then stream
        const list = targets.map((t: SearchResult) => ({ url: t.link as string, status: 'queued' }))
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
        // After sequential scrape, populate sources and extract artifacts
        const sources = Object.entries(scraped).map(([url, content]) => ({ url, excerpt: content.slice(0, 240) }))
        setScrapeState({ inProgress: false, percent: 100, sources })
        try {
          const extract = await extractArtifacts(scraped)
          setArtifacts(extract.artifacts || [])
        } catch (e: any) {
          console.error("Failed to extract artifacts:", e)
        }
        
        // Generate summary using streaming SSE
        try {
          // First cache the scraped content
          const cacheRes = await fetch(`${API_BASE}/cache_scraped`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scraped }),
          })
          if (!cacheRes.ok) {
            throw new Error(`Failed to cache scraped content: ${cacheRes.status}`)
          }
          const { id } = await cacheRes.json()
          
          // Now stream the summary
          const eventSource = new EventSource(`${API_BASE}/summary_stream?model=${encodeURIComponent(model)}&query=${encodeURIComponent(query)}&id=${id}`)
          let streamedSummary = ""
          
          eventSource.onmessage = (event) => {
            streamedSummary += event.data
            setSummaryText(streamedSummary)
          }
          
          eventSource.onerror = (error) => {
            console.error("SSE error:", error)
            eventSource.close()
            
            // Fallback to batch summary if streaming fails
            fetch(`${API_BASE}/summary`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ model, query, scraped }),
            })
              .then(res => res.json())
              .then(data => {
                setSummaryText(data.summary || "")
                setStix(data.stix || {})
                setMisp(data.misp || {})
              })
              .catch(e => {
                console.error("Fallback summary generation error:", e)
                toast({ description: "Summary generation failed", variant: "destructive" })
              })
          }
          
          eventSource.addEventListener("close", () => {
            eventSource.close()
            // After streaming completes, get artifacts, STIX, and MISP
            fetch(`${API_BASE}/summary`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ model, query, scraped }),
            })
              .then(res => res.json())
              .then(data => {
                setStix(data.stix || {})
                setMisp(data.misp || {})
              })
              .catch(e => {
                console.error("Failed to get STIX/MISP data:", e)
              })
          })
        } catch (e: any) {
          console.error("Summary generation error:", e)
          toast({ description: e?.message || "Summary generation failed", variant: "destructive" })
        }
      } else {
        // Non-detailed mode: batch scraping and summary
        const scraped: Record<string, string> = {}
        for (let i = 0; i < targets.length; i++) {
          const t = targets[i]
          const r = await scrapeOne(t)
          scraped[r.url] = r.content
          setScrapeState(s => ({ ...s, percent: Math.round((i + 1) / targets.length * 100) }))
        }
        
        const sources = Object.entries(scraped).map(([url, content]) => ({ url, excerpt: content.slice(0, 240) }))
        setScrapeState({ inProgress: false, percent: 100, sources })
        
        try {
          const extract = await extractArtifacts(scraped)
          setArtifacts(extract.artifacts || [])
        } catch (e: any) {
          console.error("Failed to extract artifacts:", e)
        }
        
        // Batch summary generation
        try {
          const summaryRes = await fetch(`${API_BASE}/summary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model, query, scraped }),
          })
          if (!summaryRes.ok) {
            throw new Error(`Summary generation failed: ${summaryRes.status}`)
          }
          const summaryData = await summaryRes.json()
          setSummaryText(summaryData.summary || "")
          setStix(summaryData.stix || {})
          setMisp(summaryData.misp || {})
        } catch (e: any) {
          console.error("Summary generation error:", e)
          toast({ description: e?.message || "Summary generation failed", variant: "destructive" })
        }
      }
      toast({ description: "Summary ready" })
    } catch (e: any) {
      setScrapeState(s => ({ ...s, inProgress: false }))
      toast({ description: e?.message || "Scrape failed", variant: "destructive" })
    }
  }

  function onLoadHistory(run: HistoryRun) {
    setQuery(run.query)
    setResults(run.results || [])

    // Restore filtered results and selection
    setFilteredRes(run.results || [])
    const m: Record<string, boolean> = {}
    if (run.results) {
      run.results.forEach((item: SearchResult) => { m[item.link] = true })
    }
    setSelectedMap(m)

    if (run.scraped && Object.keys(run.scraped).length > 0) {
      const sources = Object.entries(run.scraped).map(([url, excerpt]) => ({ url, excerpt: String(excerpt) }))
      setScrapeState({ inProgress: false, percent: 100, sources })
    } else {
      setScrapeState({ inProgress: false, percent: 0, sources: [] })
    }

    setSummaryText(run.summary || "")
    if (run.artifacts) {
      setArtifacts(Object.entries(run.artifacts).flatMap(([k, v]) => (v as any[]).map(val => ({ type: k, value: val }))))
    } else {
      setArtifacts([])
    }
    toast({ description: "History loaded" })
  }

  function downloadReport() {
    const report = `# Investigation Report
Generated by Robin Intelligence

## Query
${query}

## Summary
${summaryText}

## Top Sources
${scrapeState.sources.slice(0, 10).map(s => `- ${s.url}`).join("\n")}

## Artifacts
${artifacts.map(a => `- ${a.type}: ${a.value}`).join("\n")}
`
    const blob = new Blob([report], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "report.md"
    a.click()
  }

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-[1600px]">
      <DashboardHeader
        status={status}
        onLoadHistory={onLoadHistory}
        onOpenSettings={() => setSettingsOpen(true)}
      />

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
          <ControlPanel
            model={model} setModel={setModel}
            query={query} setQuery={setQuery}
            keywords={keywords} setKeywords={setKeywords}
            hits={hits}
          />
        </div>

        {/* Main Content: Pipeline & Results */}
        <div className="col-span-12 lg:col-span-9 space-y-6">
          <Card className="p-5 border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <ProgressSteps
              hasQuery={!!query.trim()}
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

          <ResultsView
            filteredRes={filteredRes}
            scrapeState={scrapeState}
            artifacts={artifacts}
            summaryText={summaryText}
            stix={stix}
            selectedMap={selectedMap}
            setSelectedMap={setSelectedMap}
            detailed={detailed}
            perUrl={perUrl}
            onDownloadReport={downloadReport}
            query={query}
          />
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
        minStars={minStars}
        setMinStars={setMinStars}
        minForks={minForks}
        setMinForks={setMinForks}
        includeCommits={includeCommits}
        setIncludeCommits={setIncludeCommits}
      />
    </div>
  )
}
