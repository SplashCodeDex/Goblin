"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/hooks/use-toast"
import { getConfig, updateConfig } from "@/lib/api"
import { Loader2, Save } from "lucide-react"

export default function SettingsPage() {
    const { toast } = useToast()
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [config, setConfig] = useState<Record<string, any>>({})

    useEffect(() => {
        loadConfig()
    }, [])

    async function loadConfig() {
        try {
            const data = await getConfig()
            setConfig(data)
        } catch (e) {
            toast({ description: "Failed to load settings", variant: "destructive" })
        } finally {
            setLoading(false)
        }
    }

    async function onSave() {
        try {
            setSaving(true)
            await updateConfig(config)
            toast({ description: "Settings saved successfully" })
            // Reload to get masked values back if needed, or just keep as is
            await loadConfig()
        } catch (e) {
            toast({ description: "Failed to save settings", variant: "destructive" })
        } finally {
            setSaving(false)
        }
    }

    function handleChange(key: string, value: string) {
        setConfig(prev => ({ ...prev, [key]: value }))
    }

    if (loading) {
        return <div className="flex items-center justify-center h-screen"><Loader2 className="animate-spin" /></div>
    }

    return (
        <div className="container mx-auto p-6 max-w-4xl space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <Button onClick={onSave} disabled={saving}>
                    {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                    Save Changes
                </Button>
            </div>

            <Tabs defaultValue="llm" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="llm">LLM Providers</TabsTrigger>
                    <TabsTrigger value="integrations">Integrations</TabsTrigger>
                    <TabsTrigger value="network">Network & Tor</TabsTrigger>
                    <TabsTrigger value="scraping">Scraping</TabsTrigger>
                </TabsList>

                <TabsContent value="llm">
                    <Card>
                        <CardHeader>
                            <CardTitle>LLM Configuration</CardTitle>
                            <CardDescription>Manage API keys for various LLM providers.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-2">
                                <Label>OpenAI API Key</Label>
                                <Input
                                    type="password"
                                    value={config.OPENAI_API_KEY || ""}
                                    onChange={e => handleChange("OPENAI_API_KEY", e.target.value)}
                                    placeholder="sk-..."
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label>Anthropic API Key</Label>
                                <Input
                                    type="password"
                                    value={config.ANTHROPIC_API_KEY || ""}
                                    onChange={e => handleChange("ANTHROPIC_API_KEY", e.target.value)}
                                    placeholder="sk-ant-..."
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label>Google API Key</Label>
                                <Input
                                    type="password"
                                    value={config.GOOGLE_API_KEY || ""}
                                    onChange={e => handleChange("GOOGLE_API_KEY", e.target.value)}
                                    placeholder="AIza..."
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label>Ollama Base URL</Label>
                                <Input
                                    value={config.OLLAMA_BASE_URL || ""}
                                    onChange={e => handleChange("OLLAMA_BASE_URL", e.target.value)}
                                    placeholder="http://localhost:11434"
                                />
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="integrations">
                    <Card>
                        <CardHeader>
                            <CardTitle>External Integrations</CardTitle>
                            <CardDescription>Configure connections to external services.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-2">
                                <Label>GitHub Token</Label>
                                <Input
                                    type="password"
                                    value={config.GITHUB_TOKEN || ""}
                                    onChange={e => handleChange("GITHUB_TOKEN", e.target.value)}
                                    placeholder="ghp_..."
                                />
                                <p className="text-xs text-muted-foreground">Required for higher rate limits and searching code/commits.</p>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="network">
                    <Card>
                        <CardHeader>
                            <CardTitle>Network & Tor</CardTitle>
                            <CardDescription>Configure Tor proxy settings for dark web access.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="grid gap-2">
                                    <Label>Tor SOCKS Host</Label>
                                    <Input
                                        value={config.TOR_SOCKS_HOST || "127.0.0.1"}
                                        onChange={e => handleChange("TOR_SOCKS_HOST", e.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label>Tor SOCKS Port</Label>
                                    <Input
                                        type="number"
                                        value={config.TOR_SOCKS_PORT || "9050"}
                                        onChange={e => handleChange("TOR_SOCKS_PORT", e.target.value)}
                                    />
                                </div>
                            </div>
                            <div className="grid gap-2">
                                <Label>Tor Control Port</Label>
                                <Input
                                    type="number"
                                    value={config.TOR_CONTROL_PORT || "9051"}
                                    onChange={e => handleChange("TOR_CONTROL_PORT", e.target.value)}
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label>Tor Control Password</Label>
                                <Input
                                    type="password"
                                    value={config.TOR_PASSWORD || ""}
                                    onChange={e => handleChange("TOR_PASSWORD", e.target.value)}
                                    placeholder="Optional"
                                />
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="scraping">
                    <Card>
                        <CardHeader>
                            <CardTitle>Scraping Limits</CardTitle>
                            <CardDescription>Control resource usage for scraping.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-2">
                                <Label>Max Scrape Characters</Label>
                                <Input
                                    type="number"
                                    value={config.MAX_SCRAPE_CHARS || "1200"}
                                    onChange={e => handleChange("MAX_SCRAPE_CHARS", e.target.value)}
                                />
                                <p className="text-xs text-muted-foreground">Maximum characters to extract per page to prevent context overflow.</p>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}
