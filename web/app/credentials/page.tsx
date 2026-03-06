"use client"
import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/hooks/use-toast"
import { verifyCredentials, breachLookupBulk, githubDorks, githubGists, credentialStats } from "@/lib/api"
import { ShieldAlert, Key, Search, Database, Github, FileText, Loader2, RefreshCw } from "lucide-react"

export default function CredentialsDashboard() {
    const { toast } = useToast()
    const [stats, setStats] = useState<any>(null)
    const [loading, setLoading] = useState(false)

    // Live Verification State
    const [verifyText, setVerifyText] = useState("")
    const [verifyResults, setVerifyResults] = useState<any>(null)

    // Breach Lookup State
    const [breachEmails, setBreachEmails] = useState("")
    const [breachResults, setBreachResults] = useState<any>(null)

    // GitHub Dorks State
    const [dorkQuery, setDorkQuery] = useState("")
    const [dorkResults, setDorkResults] = useState<any>(null)

    // GitHub Gists State
    const [gistQuery, setGistQuery] = useState("")
    const [gistResults, setGistResults] = useState<any>(null)

    useEffect(() => {
        loadStats()
    }, [])

    async function loadStats() {
        try {
            const data = await credentialStats()
            setStats(data)
        } catch (e: any) {
            toast({ description: "Failed to load stats", variant: "destructive" })
        }
    }

    async function handleVerify() {
        if (!verifyText.trim()) return
        try {
            setLoading(true)
            // Sending raw text wrapped in an array or we can just send the text, wait, API expects an array of strings
            const data = await verifyCredentials([verifyText])
            setVerifyResults(data.results[0] || data.results) // API returns a list of scan results usually per string
            toast({ description: "Verification complete" })
        } catch (e: any) {
            toast({ description: e?.message || "Verification failed", variant: "destructive" })
        } finally {
            setLoading(false)
            loadStats()
        }
    }

    async function handleBreachLookup() {
        if (!breachEmails.trim()) return
        try {
            setLoading(true)
            const emails = breachEmails.split(/[,\\n]+/).map(e => e.trim()).filter(e => e)
            const data = await breachLookupBulk(emails)
            setBreachResults(data)
            toast({ description: "Breach lookup complete" })
        } catch (e: any) {
            toast({ description: e?.message || "Lookup failed", variant: "destructive" })
        } finally {
            setLoading(false)
            loadStats()
        }
    }

    async function handleDorks() {
        if (!dorkQuery.trim()) return
        try {
            setLoading(true)
            const data = await githubDorks(dorkQuery)
            setDorkResults(data.results)
            toast({ description: "Dorking complete" })
        } catch (e: any) {
            toast({ description: e?.message || "Dorking failed", variant: "destructive" })
        } finally {
            setLoading(false)
            loadStats()
        }
    }

    async function handleGists() {
        if (!gistQuery.trim()) return
        try {
            setLoading(true)
            const data = await githubGists(gistQuery)
            setGistResults(data.results)
            toast({ description: "Gist search complete" })
        } catch (e: any) {
            toast({ description: e?.message || "Gist search failed", variant: "destructive" })
        } finally {
            setLoading(false)
            loadStats()
        }
    }

    return (
        <div className="container mx-auto p-6 space-y-6 max-w-[1600px]">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <ShieldAlert className="text-red-500 w-8 h-8" />
                        Credential Arsenal
                    </h1>
                    <p className="text-zinc-400 mt-2">Advanced hunting, verification, and OSINT for leaked credentials.</p>
                </div>
                <Button onClick={loadStats} variant="outline" size="icon">
                    <RefreshCw className="w-4 h-4" />
                </Button>
            </div>

            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                    <Card className="bg-zinc-900/50 border-zinc-800">
                        <CardHeader className="pb-2">
                            <CardDescription>Live Verifiers</CardDescription>
                            <CardTitle className="text-2xl">{stats.trufflehog?.verifiers_available || 0}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card className="bg-zinc-900/50 border-zinc-800">
                        <CardHeader className="pb-2">
                            <CardDescription>Breach Databases</CardDescription>
                            <CardTitle className="text-2xl">{stats.breach_lookup?.sources_available || 0}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card className="bg-zinc-900/50 border-zinc-800">
                        <CardHeader className="pb-2">
                            <CardDescription>GitHub Dorks</CardDescription>
                            <CardTitle className="text-2xl">{stats.github_dorks?.queries_available || 0}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card className="bg-zinc-900/50 border-zinc-800">
                        <CardHeader className="pb-2">
                            <CardDescription>Dorking Categories</CardDescription>
                            <CardTitle className="text-2xl">{stats.github_dorks?.categories || 0}</CardTitle>
                        </CardHeader>
                    </Card>
                </div>
            )}

            <Tabs defaultValue="verify" className="w-full">
                <TabsList className="grid w-full grid-cols-4 bg-zinc-900/80 mb-6 border border-zinc-800">
                    <TabsTrigger value="verify" className="flex items-center gap-2"><Key className="w-4 h-4" /> Live Verify</TabsTrigger>
                    <TabsTrigger value="breach" className="flex items-center gap-2"><Database className="w-4 h-4" /> Breach Lookup</TabsTrigger>
                    <TabsTrigger value="dorks" className="flex items-center gap-2"><Github className="w-4 h-4" /> GitHub Dorks</TabsTrigger>
                    <TabsTrigger value="gists" className="flex items-center gap-2"><FileText className="w-4 h-4" /> Gists</TabsTrigger>
                </TabsList>

                <TabsContent value="verify">
                    <Card className="border-zinc-800 bg-zinc-900/50">
                        <CardHeader>
                            <CardTitle>Live Credential Verification</CardTitle>
                            <CardDescription>Paste code, text, or raw credentials to scan and actively verify against {stats?.trufflehog?.verifiers_available || 14} services.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Textarea
                                placeholder="Paste content here (e.g. xoxb-1234...)"
                                className="min-h-[200px] font-mono text-sm bg-zinc-950/50"
                                value={verifyText}
                                onChange={(e) => setVerifyText(e.target.value)}
                            />
                            <Button onClick={handleVerify} disabled={loading || !verifyText.trim()} className="w-full sm:w-auto">
                                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                                Scan & Verify
                            </Button>

                            {verifyResults && (
                                <div className="mt-8">
                                    <h3 className="text-lg font-semibold mb-4">Results</h3>
                                    {verifyResults.credentials && verifyResults.credentials.length > 0 ? (
                                        <div className="space-y-4">
                                            {verifyResults.credentials.map((cred: any, idx: number) => (
                                                <Card key={idx} className="bg-zinc-950/50 border-zinc-800">
                                                    <CardContent className="p-4 flex flex-col gap-2">
                                                        <div className="flex justify-between items-start">
                                                            <span className="font-bold text-red-400">{cred.type}</span>
                                                            <span className={`px-2 py-1 text-xs rounded-full ${cred.verified ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
                                                                {cred.verified ? 'Verified Active' : 'Inactive/Invalid'}
                                                            </span>
                                                        </div>
                                                        <div className="font-mono text-sm break-all text-zinc-300 bg-zinc-900 p-2 rounded">
                                                            {cred.redacted || cred.raw}
                                                        </div>
                                                        {cred.context && <p className="text-xs text-zinc-500 font-mono mt-2">...{cred.context}...</p>}
                                                    </CardContent>
                                                </Card>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="p-8 text-center text-zinc-500 border border-dashed border-zinc-800 rounded-lg">
                                            No credentials found in the provided text.
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="breach">
                    <Card className="border-zinc-800 bg-zinc-900/50">
                        <CardHeader>
                            <CardTitle>Bulk Breach Lookup</CardTitle>
                            <CardDescription>Search for compromised emails across {stats?.breach_lookup?.sources_available || 7} breach databases simultaneously.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Textarea
                                placeholder="target1@example.com&#10;target2@example.com"
                                className="min-h-[150px] font-mono text-sm bg-zinc-950/50"
                                value={breachEmails}
                                onChange={(e) => setBreachEmails(e.target.value)}
                            />
                            <Button onClick={handleBreachLookup} disabled={loading || !breachEmails.trim()} className="w-full sm:w-auto">
                                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Database className="mr-2 h-4 w-4" />}
                                Lookup Emails
                            </Button>

                            {breachResults && (
                                <div className="mt-8 space-y-6">
                                    {Object.entries(breachResults).map(([email, data]: [string, any]) => (
                                        <div key={email} className="space-y-3">
                                            <h3 className="text-lg font-semibold flex items-center gap-2">
                                                {email}
                                                {data.total_breaches > 0 ? (
                                                    <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full border border-red-500/30">
                                                        {data.total_breaches} breaches
                                                    </span>
                                                ) : (
                                                    <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full border border-green-500/30">
                                                        Clear
                                                    </span>
                                                )}
                                            </h3>

                                            {data.total_breaches > 0 && (
                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                                    {Object.entries(data.sources).map(([source, sData]: [string, any]) => {
                                                        if (!sData.found || sData.breaches?.length === 0) return null;
                                                        return (
                                                            <Card key={source} className="bg-zinc-950/50 border-zinc-800">
                                                                <CardHeader className="py-3 px-4 bg-zinc-900/80 border-b border-zinc-800">
                                                                    <CardTitle className="text-sm tracking-wide text-zinc-300 capitalize">{source}</CardTitle>
                                                                </CardHeader>
                                                                <CardContent className="p-4">
                                                                    <ul className="list-disc pl-5 space-y-1 text-sm text-zinc-400">
                                                                        {sData.breaches.map((b: any, i: number) => (
                                                                            <li key={i}>
                                                                                {typeof b === 'string' ? b : (b.Name || b.Title || b.name || JSON.stringify(b))}
                                                                            </li>
                                                                        ))}
                                                                    </ul>
                                                                </CardContent>
                                                            </Card>
                                                        )
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="dorks">
                    <Card className="border-zinc-800 bg-zinc-900/50">
                        <CardHeader>
                            <CardTitle>Targeted GitHub Dorking</CardTitle>
                            <CardDescription>Run {stats?.github_dorks?.queries_available || 80}+ advanced dork queries against a specific target domain or organization.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex gap-4">
                                <Input
                                    placeholder="Target (e.g. example.com or org:acme)"
                                    className="bg-zinc-950/50 font-mono"
                                    value={dorkQuery}
                                    onChange={(e) => setDorkQuery(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleDorks()}
                                />
                                <Button onClick={handleDorks} disabled={loading || !dorkQuery.trim()} className="shrink-0">
                                    {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Github className="mr-2 h-4 w-4" />}
                                    Run Dorks
                                </Button>
                            </div>

                            {dorkResults && (
                                <div className="mt-8 space-y-4">
                                    <h3 className="text-lg font-semibold">Mined Intel ({dorkResults.length} hits)</h3>
                                    {dorkResults.length > 0 ? (
                                        <div className="grid gap-4">
                                            {dorkResults.map((res: any, idx: number) => (
                                                <Card key={idx} className="bg-zinc-950/50 border-zinc-800 overflow-hidden">
                                                    <div className="p-4 border-b border-zinc-800 bg-zinc-900/30 flex justify-between items-center">
                                                        <span className="text-sm font-medium text-blue-400 truncate max-w-[70%]">{res.title}</span>
                                                        <span className="text-xs bg-zinc-800 px-2 py-1 rounded text-zinc-300">{res.dork_category || 'General'}</span>
                                                    </div>
                                                    <div className="p-4">
                                                        <p className="text-sm text-zinc-400 font-mono whitespace-pre-wrap">{res.snippet}</p>
                                                        <a href={res.link} target="_blank" rel="noreferrer" className="text-xs text-red-400 hover:text-red-300 mt-3 inline-block">
                                                            View Source &rarr;
                                                        </a>
                                                    </div>
                                                </Card>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="p-8 text-center text-zinc-500 border border-dashed border-zinc-800 rounded-lg">
                                            No sensitive data found for this target.
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="gists">
                    <Card className="border-zinc-800 bg-zinc-900/50">
                        <CardHeader>
                            <CardTitle>Public Gist Search</CardTitle>
                            <CardDescription>Hunt for leaked configurations, tokens, and notes inside public GitHub gists.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Input
                                    placeholder="Keywords (e.g. sql password db_pass)"
                                    className="bg-zinc-950/50 font-mono w-full"
                                    value={gistQuery}
                                    onChange={(e) => setGistQuery(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleGists()}
                                />
                                <Button onClick={handleGists} disabled={loading || !gistQuery.trim()} className="shrink-0">
                                    {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                                    Search Gists
                                </Button>
                            </div>

                            {gistResults && (
                                <div className="mt-8 space-y-4">
                                    <h3 className="text-lg font-semibold">Exposed Gists ({gistResults.length} hits)</h3>
                                    {gistResults.length > 0 ? (
                                        <div className="grid gap-4">
                                            {gistResults.map((res: any, idx: number) => (
                                                <Card key={idx} className="bg-zinc-950/50 border-zinc-800 overflow-hidden">
                                                    <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
                                                        <span className="text-sm font-medium text-blue-400">{res.title}</span>
                                                    </div>
                                                    <div className="p-4">
                                                        <p className="text-sm text-zinc-400 font-mono whitespace-pre-wrap">{res.snippet}</p>
                                                        <a href={res.link} target="_blank" rel="noreferrer" className="text-xs text-red-400 hover:text-red-300 mt-3 inline-block">
                                                            View Gist &rarr;
                                                        </a>
                                                    </div>
                                                </Card>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="p-8 text-center text-zinc-500 border border-dashed border-zinc-800 rounded-lg">
                                            No matching gists found.
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

            </Tabs>
        </div>
    )
}
