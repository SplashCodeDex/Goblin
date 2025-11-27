export function SummaryCard({ refined, summary }: { refined: string; summary: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4">
      <div className="text-accent font-semibold mb-2">Refined Query</div>
      <div className="text-sm mb-4">{refined || "—"}</div>
      <div className="text-accent font-semibold mb-2">Investigation Summary</div>
      <div className="prose prose-invert max-w-none whitespace-pre-wrap text-sm">{summary || "—"}</div>
    </div>
  )
}
