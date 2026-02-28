"use client"

import { Shield, Sparkles, Copy, Check, FileText, Cpu } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

export function SummaryCard({ refined, summary, isAnalyzing = false }: { refined: string; summary: string; isAnalyzing?: boolean }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (!summary) return;
    navigator.clipboard.writeText(summary)
    setCopied(true)
    toast.success("Intelligence report copied to clipboard")
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadTxt = () => {
    if (!summary) return;
    const timestamp = new Date().toLocaleString();
    const headers = [
      "==================================================",
      "             GOBLIN INTELLIGENCE REPORT            ",
      "==================================================",
      `TIMESTAMP:  ${timestamp}`,
      `QUERY:      ${refined || "N/A"}`,
      "CONFIDENTIALITY: PRIVILEGED // INTERNAL ONLY       ",
      "--------------------------------------------------",
      "\n"
    ].join("\n");

    const element = document.createElement("a");
    const file = new Blob([headers + summary], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `goblin_intel_${Date.now()}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    toast.success("Report exported as TXT");
  }

  return (
    <div className="group relative overflow-hidden rounded-xl border border-white/10 bg-zinc-900/60 backdrop-blur-md p-6 transition-all hover:border-accent/40 shadow-2xl">
      {/* Background Accent */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-48 h-48 bg-accent/5 rounded-full blur-[100px] transition-all group-hover:bg-accent/10" />

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="relative">
            {isAnalyzing && (
              <div className="absolute inset-0 bg-accent/30 rounded-full blur-md animate-ping" />
            )}
            <div className={`relative p-2.5 rounded-xl bg-zinc-800/80 border transition-colors ${isAnalyzing ? 'border-accent/50 group-hover:border-accent' : 'border-zinc-700'}`}>
              <Shield className={`w-5 h-5 ${isAnalyzing ? 'text-accent' : 'text-zinc-500'}`} />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-[12px] font-black text-zinc-100 uppercase tracking-[0.2em]">Intelligence Report</h3>
              {isAnalyzing && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-accent/10 border border-accent/20 animate-in fade-in zoom-in duration-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                  <span className="text-[9px] font-black text-accent uppercase tracking-wider">Processing</span>
                </div>
              )}
            </div>
            <p className="text-[10px] text-zinc-600 font-bold mt-1 flex items-center gap-2">
              <span className="w-1 h-3 bg-zinc-800" />
              V2.0 // DEEP_RECOGNITION_SYSTEM
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            disabled={!summary}
            className="h-9 px-4 text-zinc-400 hover:text-white hover:bg-white/5 gap-2.5 border border-transparent hover:border-white/10"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span className="text-[11px] font-bold uppercase tracking-wider">{copied ? "Copied" : "Copy"}</span>
          </Button>
        </div>
      </div>

      {refined && (
        <div className="flex items-start gap-3 mb-6 p-4 rounded-xl bg-black/60 border border-white/5 backdrop-blur-sm">
          <Cpu className="w-4 h-4 text-accent/60 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.15em]">Refined Analysis Scope</div>
            <div className="text-[13px] text-zinc-400 font-medium italic leading-relaxed selection:bg-accent/40">
              "{refined}"
            </div>
          </div>
        </div>
      )}

      <div className="relative">
        <div className={`absolute left-0 top-0 w-[2px] h-full rounded-full blur-[1px] transition-colors ${isAnalyzing ? 'bg-accent/40' : 'bg-zinc-800'}`} />
        <div className="pl-6">
          <div className="prose prose-invert max-w-none text-zinc-300 text-[15px] leading-[1.8] font-sans whitespace-pre-wrap selection:bg-accent/30 tracking-tight">
            {summary || (
              <div className="flex flex-col gap-3 py-4">
                <div className="h-4 w-3/4 bg-zinc-800/40 rounded animate-pulse" />
                <div className="h-4 w-1/2 bg-zinc-800/40 rounded animate-pulse" />
                <div className="text-zinc-600 italic text-sm mt-2">Waiting for intelligence feed...</div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-8 pt-5 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2.5">
            <FileText className="w-3.5 h-3.5 text-zinc-600" />
            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Repository:</span>
            <button
              onClick={handleDownloadTxt}
              disabled={!summary}
              className="text-[10px] text-zinc-400 hover:text-accent font-black transition-all px-2 py-0.5 rounded border border-zinc-800 hover:border-accent/40 bg-zinc-900/50"
            >
              DOWNLOAD_REPORT.txt
            </button>
          </div>
        </div>
        <div className="text-[9px] text-zinc-700 font-bold tracking-wider uppercase">
          Classification: Level 4 // Goblin Protocol
        </div>
      </div>
    </div>
  )
}
