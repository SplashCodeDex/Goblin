"use client"

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts'
import { Card } from "@/components/ui/card"
import { Artifact, ScrapedSource } from "@/lib/api"

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

export function OverviewCharts({ artifacts, sources }: { artifacts: Artifact[], sources: ScrapedSource[] }) {
    // Process artifacts data
    const artifactCounts = artifacts.reduce((acc: Record<string, number>, curr: Artifact) => {
        acc[curr.type] = (acc[curr.type] || 0) + 1
        return acc
    }, {})

    const artifactData = Object.entries(artifactCounts).map(([name, value]) => ({ name, value }))

    // Process sources data (top domains)
    const domainCounts = sources.reduce((acc: Record<string, number>, curr: ScrapedSource) => {
        try {
            const domain = new URL(curr.url).hostname
            acc[domain] = (acc[domain] || 0) + 1
        } catch (e: any) {
            console.error("Failed to parse URL:", curr.url, e)
        }
        return acc
    }, {})

    const sourceData = Object.entries(domainCounts)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 5)

    if (artifactData.length === 0 && sourceData.length === 0) return null

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Card className="p-4 border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
                <h3 className="text-sm font-medium mb-4 text-zinc-400">Artifact Distribution</h3>
                <div className="h-[200px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={artifactData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {artifactData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px' }}
                                itemStyle={{ color: '#e4e4e7' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
                <div className="flex flex-wrap gap-2 justify-center mt-2">
                    {artifactData.map((entry, index) => (
                        <div key={entry.name} className="flex items-center gap-1 text-xs text-zinc-500">
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                            {entry.name} ({entry.value})
                        </div>
                    ))}
                </div>
            </Card>

            <Card className="p-4 border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
                <h3 className="text-sm font-medium mb-4 text-zinc-400">Top Sources</h3>
                <div className="h-[200px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={sourceData} layout="vertical" margin={{ left: 20 }}>
                            <XAxis type="number" hide />
                            <YAxis
                                dataKey="name"
                                type="category"
                                width={100}
                                tick={{ fill: '#71717a', fontSize: 12 }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <Tooltip
                                cursor={{ fill: '#27272a' }}
                                contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px' }}
                                itemStyle={{ color: '#e4e4e7' }}
                            />
                            <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={20} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </Card>
        </div>
    )
}
