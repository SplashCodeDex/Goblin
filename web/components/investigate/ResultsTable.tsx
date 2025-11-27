"use client"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { ExternalLink, Eye } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

export function ResultsTable(props: {
    data: any[]
    selectedMap: Record<string, boolean>
    setSelectedMap: (m: Record<string, boolean>) => void
}) {
    const { data, selectedMap, setSelectedMap } = props

    function toggle(link: string) {
        setSelectedMap({ ...selectedMap, [link]: !selectedMap[link] })
    }

    function toggleAll() {
        const allSelected = data.every(d => selectedMap[d.link])
        const newMap = { ...selectedMap }
        data.forEach(d => { newMap[d.link] = !allSelected })
        setSelectedMap(newMap)
    }

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-[50px]">
                            <Checkbox
                                checked={data.length > 0 && data.every(d => selectedMap[d.link])}
                                onCheckedChange={toggleAll}
                            />
                        </TableHead>
                        <TableHead>Title</TableHead>
                        <TableHead>Snippet</TableHead>
                        <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {data.map((item, i) => (
                        <TableRow key={i}>
                            <TableCell>
                                <Checkbox
                                    checked={!!selectedMap[item.link]}
                                    onCheckedChange={() => toggle(item.link)}
                                />
                            </TableCell>
                            <TableCell className="font-medium max-w-[200px] truncate" title={item.title}>
                                {item.title}
                                <div className="text-xs text-zinc-500 truncate">{item.link}</div>
                            </TableCell>
                            <TableCell className="max-w-[400px] truncate text-zinc-400" title={item.snippet}>
                                {item.snippet}
                            </TableCell>
                            <TableCell>
                                <div className="flex gap-2">
                                    <a href={item.link} target="_blank" rel="noreferrer">
                                        <Button variant="ghost" size="icon" className="h-8 w-8">
                                            <ExternalLink className="h-4 w-4" />
                                        </Button>
                                    </a>
                                    <Dialog>
                                        <DialogTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-8 w-8">
                                                <Eye className="h-4 w-4" />
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent>
                                            <DialogHeader>
                                                <DialogTitle>Result Preview</DialogTitle>
                                            </DialogHeader>
                                            <div className="space-y-4">
                                                <h3 className="font-bold">{item.title}</h3>
                                                <a href={item.link} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline text-sm break-all">{item.link}</a>
                                                <p className="text-zinc-300 whitespace-pre-wrap">{item.snippet}</p>
                                            </div>
                                        </DialogContent>
                                    </Dialog>
                                </div>
                            </TableCell>
                        </TableRow>
                    ))}
                    {data.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={4} className="text-center py-8 text-zinc-500">
                                No results found
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    )
}
