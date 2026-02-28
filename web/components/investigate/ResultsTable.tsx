import { ExternalLink, Eye, Copy, Check, ShieldAlert, ShieldCheck, ShieldInfo, Terminal } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { SearchResult } from "@/lib/api"

export function ResultsTable(props: {
    data: SearchResult[]
    selectedMap: Record<string, boolean>
    setSelectedMap: (m: Record<string, boolean>) => void
}) {
    const { data, selectedMap, setSelectedMap } = props
    const [copyState, setCopyState] = useState<Record<string, boolean>>({})

    function toggle(link: string) {
        setSelectedMap({ ...selectedMap, [link]: !selectedMap[link] })
    }

    function toggleAll() {
        const allSelected = data.every(d => selectedMap[d.link])
        const newMap = { ...selectedMap }
        data.forEach(d => { newMap[d.link] = !allSelected })
        setSelectedMap(newMap)
    }

    const handleCopy = (text: string, id: string) => {
        navigator.clipboard.writeText(text)
        setCopyState(prev => ({ ...prev, [id]: true }))
        toast.success("Intelligence snippet copied")
        setTimeout(() => setCopyState(prev => ({ ...prev, [id]: false })), 2000)
    }

    const getThreatLevel = (item: SearchResult) => {
        const text = (item.title + item.snippet).toLowerCase()
        const highMatch = text.match(/leak|vulnerability|exploit|password|secret|key|exposed|critical|darkweb|hacker/g)
        const medMatch = text.match(/info|data|dump|breach|security|account|user/g)

        if (highMatch) return { level: "HIGH", color: "text-red-500", bg: "bg-red-500/10", border: "border-red-500/20", icon: <ShieldAlert className="w-3.5 h-3.5" /> }
        if (medMatch) return { level: "MEDIUM", color: "text-amber-500", bg: "bg-amber-500/10", border: "border-amber-500/20", icon: <ShieldInfo className="w-3.5 h-3.5" /> }
        return { level: "LOW", color: "text-zinc-500", bg: "bg-zinc-500/10", border: "border-zinc-500/20", icon: <ShieldCheck className="w-3.5 h-3.5" /> }
    }

    return (
        <div className="rounded-xl border border-white/5 bg-zinc-900/40 backdrop-blur-md overflow-hidden shadow-2xl">
            <Table>
                <TableHeader className="bg-white/5">
                    <TableRow className="hover:bg-transparent border-white/5">
                        <TableHead className="w-[50px]">
                            <Checkbox
                                checked={data.length > 0 && data.every(d => selectedMap[d.link])}
                                onCheckedChange={(_) => toggleAll()}
                                className="border-zinc-700 data-[state=checked]:bg-accent data-[state=checked]:border-accent"
                            />
                        </TableHead>
                        <TableHead className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Intelligence Node</TableHead>
                        <TableHead className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Threat Indicators</TableHead>
                        <TableHead className="text-[10px] font-black uppercase tracking-widest text-zinc-500 w-[120px]">Analysis</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {data.map((item) => {
                        const threat = getThreatLevel(item)
                        return (
                            <TableRow key={item.link} className="group hover:bg-white/[0.02] border-white/5 transition-colors">
                                <TableCell>
                                    <Checkbox
                                        checked={!!selectedMap[item.link]}
                                        onCheckedChange={(_) => toggle(item.link)}
                                        className="border-zinc-700 data-[state=checked]:bg-accent data-[state=checked]:border-accent"
                                    />
                                </TableCell>
                                <TableCell className="max-w-[300px]">
                                    <div className="flex flex-col gap-1">
                                        <div className="font-bold text-zinc-200 text-sm truncate group-hover:text-white transition-colors" title={item.title}>
                                            {item.title}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-[11px] text-zinc-500 truncate font-mono">{item.link}</span>
                                            <button
                                                onClick={() => handleCopy(item.link, item.link)}
                                                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/5 transition-all"
                                            >
                                                {copyState[item.link] ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3 text-zinc-600" />}
                                            </button>
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell className="max-w-[400px]">
                                    <div className="text-zinc-400 text-[13px] leading-relaxed line-clamp-2" title={item.snippet}>
                                        {item.snippet}
                                    </div>
                                    {item.emails && item.emails.length > 0 && (
                                        <div className="flex flex-wrap gap-1.5 mt-2">
                                            {item.emails.map(email => (
                                                <div key={email} className="group/entity flex items-center gap-1.5 rounded-full border border-white/5 bg-zinc-800/50 pl-2.5 pr-1.5 py-0.5 transition-all hover:border-accent/40">
                                                    <span className="text-[10px] font-mono text-zinc-500 group-hover/entity:text-zinc-300">{email}</span>
                                                    <button
                                                        onClick={() => handleCopy(email, email)}
                                                        className="p-1 rounded-full hover:bg-white/10"
                                                    >
                                                        {copyState[email] ? <Check className="w-2.5 h-2.5 text-green-500" /> : <Copy className="w-2.5 h-2.5 text-zinc-600" />}
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center justify-between">
                                        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded border ${threat.bg} ${threat.border} ${threat.color}`}>
                                            {threat.icon}
                                            <span className="text-[9px] font-black tracking-tighter">{threat.level}</span>
                                        </div>
                                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-all scale-95 group-hover:scale-100">
                                            <a href={item.link} target="_blank" rel="noopener noreferrer">
                                                <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-white/5 hover:text-accent">
                                                    <ExternalLink className="h-3.5 w-3.5" />
                                                </Button>
                                            </a>
                                            <Dialog>
                                                <DialogTrigger asChild>
                                                    <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-white/5 hover:text-accent">
                                                        <Eye className="h-3.5 w-3.5" />
                                                    </Button>
                                                </DialogTrigger>
                                                <DialogContent className="bg-zinc-950 border-zinc-800 max-w-2xl">
                                                    <DialogHeader>
                                                        <div className={`w-fit flex items-center gap-2 px-3 py-1 rounded-full border mb-4 ${threat.bg} ${threat.border} ${threat.color}`}>
                                                            {threat.icon}
                                                            <span className="text-[10px] font-black uppercase tracking-widest">{threat.level} SIGNIFICANCE</span>
                                                        </div>
                                                        <DialogTitle className="text-xl font-bold text-zinc-100">{item.title}</DialogTitle>
                                                    </DialogHeader>
                                                    <div className="space-y-6 mt-4">
                                                        <div className="p-3 rounded-lg bg-black/40 border border-white/5">
                                                            <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Technical Origin</div>
                                                            <a href={item.link} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline text-xs font-mono break-all italic">{item.link}</a>
                                                        </div>
                                                        <div className="space-y-2">
                                                            <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Intelligence Snippet</div>
                                                            <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap font-sans bg-zinc-900/50 p-4 rounded-xl border border-white/5">{item.snippet}</p>
                                                        </div>
                                                    </div>
                                                </DialogContent>
                                            </Dialog>
                                        </div>
                                    </div>
                                </TableCell>
                            </TableRow>
                        )
                    })}
                    {data.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={4} className="text-center py-12">
                                <div className="flex flex-col items-center gap-3">
                                    <Terminal className="w-8 h-8 text-zinc-800" />
                                    <div className="text-sm font-bold text-zinc-600 uppercase tracking-widest">No Intelligence Nodes Found</div>
                                    <p className="text-xs text-zinc-700 font-mono">ADJUST PARAMETERS OR EXPAND SCOPE</p>
                                </div>
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    )
}
