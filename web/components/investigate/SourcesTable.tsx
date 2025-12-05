"use client"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"

type Source = { url: string; excerpt: string }
export function SourcesTable({ data }: { data: Source[] }) {
  if (!data?.length) return <div className="text-sm text-zinc-400">No sources yet.</div>
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-2">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>URL</TableHead>
            <TableHead>Excerpt</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((s) => (
            <TableRow key={s.url}>
              <TableCell className="max-w-[340px] truncate"><a href={s.url} className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">{s.url}</a></TableCell>
              <TableCell className="text-sm">{s.excerpt}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
