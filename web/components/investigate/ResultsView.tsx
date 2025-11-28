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
                        <Button variant="outline" size="sm" onClick={onDownloadReport}>Report</Button>
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
                <OverviewCharts artifacts={artifacts} sources={scrapeState.sources} />
                <SummaryCard refined={query} summary={summaryText} />
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
