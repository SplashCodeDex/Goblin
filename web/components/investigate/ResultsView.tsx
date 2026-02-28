"use client"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { OverviewCharts } from "@/components/investigate/OverviewCharts"
import { SummaryCard } from "@/components/investigate/SummaryCard"
import { ResultsTable } from "@/components/investigate/ResultsTable"
import { SourcesTable } from "@/components/investigate/SourcesTable"
import { ArtifactsTable } from "@/components/investigate/ArtifactsTable"
import { downloadCSV, downloadJSON } from "@/lib/utils"
import { SearchResult, ScrapedSource, Artifact } from "@/lib/api"
import { CheckCircle2, Loader2, Globe, AlertCircle, Terminal } from "lucide-react"

interface ResultsViewProps {
    filteredRes: SearchResult[]
    scrapeState: { inProgress: boolean; percent: number; sources: ScrapedSource[] }
    artifacts: Artifact[]
    summaryText: string
    stix: any
    selectedMap: Record<string, boolean>
    setSelectedMap: (m: Record<string, boolean>) => void
    detailed: boolean
    perUrl: { url: string; status: string }[]
    onDownloadReport: () => void
    query: string
}

export function ResultsView({
    filteredRes, scrapeState, artifacts, summaryText, stix, selectedMap, setSelectedMap, detailed, perUrl, onDownloadReport, query
}: ResultsViewProps) {
    return (
        <Tabs defaultValue="overview" className="space-y-4">
            <div className="grid grid-cols-3 items-center min-h-[48px] mb-6">
                <div /> {/* Left spacer */}

                <div className="flex justify-center">
                    <TabsList className="bg-zinc-900/60 border border-zinc-800/50 backdrop-blur-sm p-1">
                        <TabsTrigger value="overview" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-accent">Overview</TabsTrigger>
                        <TabsTrigger value="results" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-accent">Results ({filteredRes.length})</TabsTrigger>
                        <TabsTrigger value="sources" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-accent">Sources ({scrapeState.sources.length})</TabsTrigger>
                        <TabsTrigger value="artifacts" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-accent">Artifacts ({artifacts.length})</TabsTrigger>
                    </TabsList>
                </div>

                <div className="flex justify-end gap-2">
                    {scrapeState.sources.length > 0 && (
                        <>
                            <Button variant="outline" size="sm" onClick={onDownloadReport} className="border-zinc-800 hover:bg-zinc-800 hover:text-accent">Report</Button>
                            <Button variant="outline" size="sm" onClick={() => downloadCSV(scrapeState.sources, "sources.csv")} className="border-zinc-800 hover:bg-zinc-800 hover:text-accent font-mono text-[10px]">CSV</Button>
                            <Button variant="outline" size="sm" onClick={() => downloadJSON(scrapeState.sources, "sources.json")} className="border-zinc-800 hover:bg-zinc-800 hover:text-accent font-mono text-[10px]">JSON</Button>
                            {stix && Object.keys(stix).length > 0 && (
                                <Button variant="outline" size="sm" onClick={() => downloadJSON(stix, "stix.json")} className="border-zinc-800 hover:bg-zinc-800 hover:text-accent font-mono text-[10px]">STIX</Button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {detailed && perUrl.length > 0 && (
                <div className="rounded-xl border border-white/10 bg-zinc-900/40 backdrop-blur-md p-4 mb-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Terminal className="w-4 h-4 text-zinc-500" />
                        <div className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Live Extraction Pulse</div>
                    </div>
                    <div className="grid gap-2 text-sm max-h-56 overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent pr-2">
                        {perUrl.map(item => (
                            <div key={item.url} className="group flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/5 hover:border-white/10 transition-all">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className="shrink-0">
                                        {item.status === 'done' ? (
                                            <CheckCircle2 className="w-4 h-4 text-green-500" />
                                        ) : item.status === 'error' ? (
                                            <AlertCircle className="w-4 h-4 text-red-500" />
                                        ) : (
                                            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 min-w-0">
                                        <Globe className="w-3 h-3 text-zinc-600 shrink-0" />
                                        <span className="truncate text-zinc-400 font-mono text-[13px]">{item.url}</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 ml-4">
                                    <span className={`text-[11px] font-bold uppercase tracking-tighter px-2 py-0.5 rounded ${item.status === 'done'
                                        ? "bg-green-500/10 text-green-400"
                                        : item.status === 'error'
                                            ? "bg-red-500/10 text-red-400"
                                            : "bg-blue-500/10 text-blue-400 animate-pulse"
                                        }`}>
                                        {item.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <TabsContent value="overview" className="mt-0">
                <OverviewCharts artifacts={artifacts} sources={scrapeState.sources} />
                <SummaryCard refined={query} summary={summaryText} isAnalyzing={scrapeState.inProgress} />
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
    )
}
