"use client"

import { useEffect, useState } from "react"
import { getHistory } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { format } from "date-fns"

export default function HistoryPage() {
    const [runs, setRuns] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        getHistory()
            .then(data => setRuns(data.runs))
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [])

    if (loading) return <div className="p-8">Loading history...</div>

    return (
        <div className="container mx-auto p-6 space-y-6">
            <h1 className="text-2xl font-bold">Investigation History</h1>
            <div className="grid gap-4">
                {runs.map((run) => (
                    <Card key={run.id} className="bg-zinc-900 border-zinc-800">
                        <CardHeader className="pb-2">
                            <div className="flex justify-between items-start">
                                <CardTitle className="text-lg font-medium text-zinc-100">
                                    {run.query}
                                </CardTitle>
                                <Badge variant="outline" className="text-zinc-400">
                                    {format(new Date(run.timestamp.replace("Z", "")), "PPpp")}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="text-sm text-zinc-400 mb-4 line-clamp-3">
                                {run.summary || "No summary available."}
                            </div>
                            <div className="flex gap-4 text-xs text-zinc-500">
                                <div>Results: {run.results?.length || 0}</div>
                                <div>Filtered: {run.filtered_results?.length || 0}</div>
                                <div>Scraped: {Object.keys(run.scraped_content || {}).length}</div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
                {runs.length === 0 && (
                    <div className="text-zinc-500 text-center py-12">
                        No history found. Run an investigation first.
                    </div>
                )}
            </div>
        </div>
    )
}
