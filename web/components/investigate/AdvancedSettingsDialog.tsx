"use client"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"

export function AdvancedSettingsDialog(props: {
  open: boolean
  onClose: () => void
  threads: number
  setThreads: (n: number) => void
  maxResults: number
  setMaxResults: (n: number) => void
  detailed?: boolean
  setDetailed?: (v: boolean) => void
  requestTimeout: number
  setRequestTimeout: (n: number) => void
  useCache: boolean
  setUseCache: (v: boolean) => void
  loadCachedOnly: boolean
  setLoadCachedOnly: (v: boolean) => void
  translate: boolean
  setTranslate: (v: boolean) => void
  minStars: number
  setMinStars: (n: number) => void
  minForks: number
  setMinForks: (n: number) => void
  includeCommits: boolean
  setIncludeCommits: (v: boolean) => void
  sourceWeights: { darkweb: number; github: number; github_code: number; github_commits: number }
  setSourceWeights: (w: { darkweb: number; github: number; github_code: number; github_commits: number }) => void
}) {
  const {
    open, onClose, threads, setThreads, maxResults, setMaxResults, detailed, setDetailed,
    requestTimeout, setRequestTimeout, useCache, setUseCache, loadCachedOnly, setLoadCachedOnly, translate, setTranslate,
    sourceWeights, setSourceWeights
  } = props
  
  // Calculate distribution preview
  const totalWeight = sourceWeights.darkweb + sourceWeights.github + sourceWeights.github_code + sourceWeights.github_commits
  const normalized = {
    darkweb: totalWeight > 0 ? (sourceWeights.darkweb / totalWeight) * 100 : 25,
    github: totalWeight > 0 ? (sourceWeights.github / totalWeight) * 100 : 25,
    github_code: totalWeight > 0 ? (sourceWeights.github_code / totalWeight) * 100 : 25,
    github_commits: totalWeight > 0 ? (sourceWeights.github_commits / totalWeight) * 100 : 25,
  }
  
  const distribution = {
    darkweb: Math.round(maxResults * (normalized.darkweb / 100)),
    github: Math.round(maxResults * (normalized.github / 100)),
    github_code: Math.round(maxResults * (normalized.github_code / 100)),
    github_commits: Math.round(maxResults * (normalized.github_commits / 100)),
  }
  
  function applyPreset(preset: 'balanced' | 'darkweb-focus' | 'github-focus') {
    const presets = {
      'balanced': { darkweb: 0.25, github: 0.25, github_code: 0.25, github_commits: 0.25 },
      'darkweb-focus': { darkweb: 0.70, github: 0.20, github_code: 0.05, github_commits: 0.05 },
      'github-focus': { darkweb: 0.20, github: 0.50, github_code: 0.20, github_commits: 0.10 },
    }
    setSourceWeights(presets[preset])
  }
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Advanced settings</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-2">
            <label className="text-sm">Threads (1-16)</label>
            <Input type="number" min={1} max={16} value={threads} onChange={e => setThreads(Number(e.target.value))} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm">Max results to process (cap)</label>
            <Input type="number" min={10} max={500} value={maxResults} onChange={e => setMaxResults(Number(e.target.value))} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm">Request timeout (seconds)</label>
            <Input type="number" min={5} max={90} value={requestTimeout} onChange={e => setRequestTimeout(Number(e.target.value))} />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="useCache" checked={useCache} onCheckedChange={(v)=> setUseCache(Boolean(v))} />
            <Label htmlFor="useCache" className="text-sm">Use disk cache</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="loadCachedOnly" checked={loadCachedOnly} onCheckedChange={(v)=> setLoadCachedOnly(Boolean(v))} />
            <Label htmlFor="loadCachedOnly" className="text-sm">Load cached only (Offline mode)</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="translate" checked={translate} onCheckedChange={(v)=> setTranslate(Boolean(v))} />
            <Label htmlFor="translate" className="text-sm">Auto-translate non-English content</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="detailed" checked={!!detailed} onCheckedChange={(v)=> setDetailed?.(Boolean(v))} />
            <Label htmlFor="detailed" className="text-sm">Detailed per-URL progress (sequential)</Label>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold">GitHub Filters</label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs">Min Stars</label>
                <Input type="number" min={0} value={props.minStars} onChange={e => props.setMinStars(Number(e.target.value))} />
              </div>
              <div>
                <label className="text-xs">Min Forks</label>
                <Input type="number" min={0} value={props.minForks} onChange={e => props.setMinForks(Number(e.target.value))} />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <Checkbox id="includeCommits" checked={props.includeCommits} onCheckedChange={(v)=> props.setIncludeCommits(Boolean(v))} />
              <Label htmlFor="includeCommits" className="text-sm">Search Commit History (Secrets)</Label>
            </div>
          </div>
          
          {/* Source Weight Distribution */}
          <div className="grid gap-3 pt-2 border-t border-zinc-800">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold">Source Distribution</label>
              <Badge variant="outline" className="text-xs">
                {distribution.darkweb + distribution.github + distribution.github_code + distribution.github_commits} results
              </Badge>
            </div>
            
            {/* Presets */}
            <div className="flex gap-2">
              <Button 
                size="sm" 
                variant="outline" 
                className="flex-1 h-7 text-xs"
                onClick={() => applyPreset('balanced')}
              >
                Balanced
              </Button>
              <Button 
                size="sm" 
                variant="outline" 
                className="flex-1 h-7 text-xs"
                onClick={() => applyPreset('darkweb-focus')}
              >
                Darkweb Focus
              </Button>
              <Button 
                size="sm" 
                variant="outline" 
                className="flex-1 h-7 text-xs"
                onClick={() => applyPreset('github-focus')}
              >
                GitHub Focus
              </Button>
            </div>
            
            {/* Darkweb Slider */}
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-400">Darkweb</label>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500 font-mono">{normalized.darkweb.toFixed(0)}%</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {distribution.darkweb}
                  </Badge>
                </div>
              </div>
              <Slider
                value={[sourceWeights.darkweb * 100]}
                onValueChange={(v) => setSourceWeights({...sourceWeights, darkweb: v[0] / 100})}
                max={100}
                step={5}
                className="w-full"
              />
            </div>
            
            {/* GitHub Repos Slider */}
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-400">GitHub Repos</label>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500 font-mono">{normalized.github.toFixed(0)}%</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {distribution.github}
                  </Badge>
                </div>
              </div>
              <Slider
                value={[sourceWeights.github * 100]}
                onValueChange={(v) => setSourceWeights({...sourceWeights, github: v[0] / 100})}
                max={100}
                step={5}
                className="w-full"
              />
            </div>
            
            {/* GitHub Code Slider */}
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-400">GitHub Code</label>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500 font-mono">{normalized.github_code.toFixed(0)}%</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {distribution.github_code}
                  </Badge>
                </div>
              </div>
              <Slider
                value={[sourceWeights.github_code * 100]}
                onValueChange={(v) => setSourceWeights({...sourceWeights, github_code: v[0] / 100})}
                max={100}
                step={5}
                className="w-full"
              />
            </div>
            
            {/* GitHub Commits Slider */}
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-400">GitHub Commits</label>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500 font-mono">{normalized.github_commits.toFixed(0)}%</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {distribution.github_commits}
                  </Badge>
                </div>
              </div>
              <Slider
                value={[sourceWeights.github_commits * 100]}
                onValueChange={(v) => setSourceWeights({...sourceWeights, github_commits: v[0] / 100})}
                max={100}
                step={5}
                className="w-full"
              />
            </div>
            
            <div className="text-xs text-zinc-500 italic mt-1">
              💡 Weights auto-normalize. Total percentage may not equal 100%.
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="secondary" onClick={onClose}>Close</Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  )
}
