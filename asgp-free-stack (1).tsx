import { useState } from "react";

const modules = [
  {
    id: 1, emoji: "👤", title: "User Management", titleAr: "إدارة المستخدمين",
    color: "#00d4ff", cost: "$0/mo",
    features: ["User Registration", "Company Registration", "Team Management", "Role Permissions"],
    tools: [
      { name: "Supabase", role: "Auth + PostgreSQL DB + Row Level Security", free: "50k users free", link: "https://supabase.com" },
      { name: "NextAuth.js", role: "OAuth login (Google, GitHub, etc.)", free: "100% free", link: "https://next-auth.js.org" },
      { name: "Resend", role: "Transactional emails (invites, alerts)", free: "3k emails/mo free", link: "https://resend.com" },
    ],
    code: `// Supabase auth + role-based access (via REST API)
// No SDK needed — use fetch() directly

const SUPABASE_URL = 'https://your-project.supabase.co'
const SUPABASE_KEY = 'your-anon-key'

// Register company user
async function signUp(email, password, role, companyId) {
  const res = await fetch(\`\${SUPABASE_URL}/auth/v1/signup\`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SUPABASE_KEY
    },
    body: JSON.stringify({
      email, password,
      data: { role, company_id: companyId }
    })
  })
  return res.json()
}

// Fetch user's projects (RLS enforced server-side)
async function getProjects(token) {
  const res = await fetch(\`\${SUPABASE_URL}/rest/v1/projects\`, {
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': \`Bearer \${token}\`
    }
  })
  return res.json()
}

// SQL policy (run once in Supabase dashboard):
// CREATE POLICY "user_own_data" ON projects
//   USING (auth.uid() = user_id);`
  },
  {
    id: 2, emoji: "🔍", title: "Search Intelligence Engine", titleAr: "محرك تحليل البحث",
    color: "#7c3aed", cost: "$0/mo",
    features: ["Keyword Research", "Competitor Analysis", "Keyword Clustering", "Volume & Difficulty"],
    tools: [
      { name: "Google Search Console API", role: "Real keyword data, impressions, clicks, rankings", free: "Free with GSC account", link: "https://developers.google.com/webmaster-tools" },
      { name: "DataForSEO (free tier)", role: "Keyword volume, CPC, competitor keywords", free: "100 requests/day free", link: "https://dataforseo.com" },
      { name: "Scrapy + Playwright", role: "Crawl competitor pages, extract keywords & content", free: "100% free", link: "https://scrapy.org" },
      { name: "spaCy + KeyBERT", role: "NLP keyword extraction and clustering by topic/intent", free: "100% free", link: "https://github.com/MaartenGr/KeyBERT" },
    ],
    code: `# Keyword clustering with KeyBERT (free NLP)
from keybert import KeyBERT
from sklearn.cluster import KMeans
import numpy as np

kw_model = KeyBERT()

def extract_and_cluster(content_list, n_clusters=5):
    all_keywords = []
    for content in content_list:
        kws = kw_model.extract_keywords(content, top_n=10)
        all_keywords.extend([k[0] for k in kws])
    
    # Cluster by semantic similarity
    # Returns: {cluster_0: ['seo', 'search', ...], ...}
    return cluster_keywords(all_keywords, n_clusters)

# GSC API — get real ranking data
from googleapiclient.discovery import build
service = build('searchconsole', 'v1', credentials=creds)
response = service.searchanalytics().query(
    siteUrl='https://mohrek.com',
    body={'startDate':'2025-01-01','endDate':'2025-08-01',
          'dimensions':['query'],'rowLimit':1000}
).execute()`
  },
  {
    id: 3, emoji: "⚙️", title: "SEO Optimization Engine", titleAr: "محرك تحسين SEO",
    color: "#10b981", cost: "$0/mo",
    features: ["Site Audit", "On-Page Optimization", "Technical SEO", "Backlink Monitoring"],
    tools: [
      { name: "Scrapy + BeautifulSoup", role: "Full site crawler — headings, meta, schema, speed issues", free: "100% free", link: "https://scrapy.org" },
      { name: "Lighthouse CLI", role: "Speed, Core Web Vitals, accessibility scores via API", free: "100% free", link: "https://github.com/GoogleChrome/lighthouse" },
      { name: "schema.org + JSON-LD", role: "Auto-generate and validate structured data", free: "100% free", link: "https://schema.org" },
      { name: "OpenLinkProfiler API", role: "Free backlink data — linking domains and anchor texts", free: "Free tier available", link: "https://openlinkprofiler.org" },
    ],
    code: `# Full SEO audit in Python — free
import requests
from bs4 import BeautifulSoup
import subprocess, json

def full_seo_audit(url):
    r = requests.get(url, timeout=10)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    issues = []
    
    # Check heading hierarchy
    h1s = soup.find_all('h1')
    if len(h1s) != 1:
        issues.append({'severity':'critical','issue':f'{len(h1s)} H1 tags found'})
    
    # Check meta description
    meta = soup.find('meta', attrs={'name':'description'})
    if not meta or len(meta.get('content','')) < 50:
        issues.append({'severity':'warning','issue':'Missing/short meta description'})
    
    # Check JSON-LD schema
    schemas = soup.find_all('script', type='application/ld+json')
    if not schemas:
        issues.append({'severity':'critical','issue':'No JSON-LD schema found'})
    
    # Lighthouse for Core Web Vitals
    result = subprocess.run(
        ['lighthouse', url, '--output=json', '--quiet'],
        capture_output=True, text=True
    )
    lh = json.loads(result.stdout)
    lcp = lh['audits']['largest-contentful-paint']['numericValue']
    
    return {'url': url, 'issues': issues, 'lcp_ms': lcp}`
  },
  {
    id: 4, emoji: "✍️", title: "AI Content Engine", titleAr: "محرك المحتوى بالذكاء الاصطناعي",
    color: "#f59e0b", cost: "$0–5/mo",
    features: ["Content Generation", "Content Optimization", "Semantic Optimization", "FAQ Generation"],
    tools: [
      { name: "Ollama (Local LLMs)", role: "Run LLaMA 3 / Mistral locally — zero API cost for content generation", free: "100% free", link: "https://ollama.ai" },
      { name: "Claude API (free tier)", role: "Arabic content generation, GEO-optimized articles, semantic analysis", free: "Free via claude.ai", link: "https://anthropic.com" },
      { name: "Hugging Face (AraBERT)", role: "Arabic semantic analysis and entity extraction", free: "100% free", link: "https://huggingface.co" },
      { name: "LangChain", role: "Chain LLM calls for multi-step content pipelines", free: "100% free", link: "https://langchain.com" },
    ],
    code: `# AI Content Generation — free with Ollama
import ollama
import json

def generate_seo_article(keyword, competitors_content, lang='ar'):
    prompt = f"""
You are an expert SEO content writer.
Target keyword: {keyword}
Language: {'Arabic' if lang=='ar' else 'English'}

Write an SEO-optimized article that:
1. Starts with a direct answer in first 60 words
2. Uses keyword naturally 3-5 times
3. Includes FAQ section with 5 questions
4. Uses H2/H3 heading structure
5. Targets AI search citation (GEO-optimized)

Output JSON: {{title, meta_description, content, faqs}}
"""
    response = ollama.chat(
        model='llama3',  # or 'mistral', 'arabic-llama'
        messages=[{'role':'user','content': prompt}],
        format='json'
    )
    return json.loads(response['message']['content'])

# Example
article = generate_seo_article(
    keyword='تحسين محركات البحث بالذكاء الاصطناعي',
    competitors_content=[],
    lang='ar'
)`
  },
  {
    id: 5, emoji: "📢", title: "Paid Ads Management", titleAr: "إدارة إعلانات البحث",
    color: "#ef4444", cost: "$0/mo",
    features: ["Google Ads API", "Campaign Management", "AI Bidding Suggestions", "Performance Analysis"],
    tools: [
      { name: "Google Ads API", role: "Create/manage campaigns, get performance data, keyword suggestions", free: "Free API (ad spend billed separately)", link: "https://developers.google.com/google-ads/api" },
      { name: "Microsoft Ads API", role: "Bing ads management and keyword data", free: "Free API", link: "https://ads.microsoft.com" },
      { name: "Python google-ads library", role: "Official free Python client for Google Ads API", free: "100% free", link: "https://github.com/googleads/google-ads-python" },
    ],
    code: `# Google Ads API — free Python client
from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_dict({
    'developer_token': 'YOUR_TOKEN',
    'client_id': 'CLIENT_ID',
    'client_secret': 'SECRET',
    'refresh_token': 'REFRESH_TOKEN',
    'login_customer_id': 'CUSTOMER_ID'
})

# Get campaign performance
ga_service = client.get_service('GoogleAdsService')
query = """
    SELECT campaign.name, metrics.clicks,
           metrics.impressions, metrics.cost_micros,
           metrics.conversions
    FROM campaign
    WHERE segments.date DURING LAST_30_DAYS
    ORDER BY metrics.cost_micros DESC
"""
response = ga_service.search(customer_id='123', query=query)

# AI bidding suggestion
def suggest_bid(keyword, competition, budget):
    # Simple ML model or LLM-based suggestion
    prompt = f"Keyword: {keyword}, Competition: {competition}, Budget: {budget}. Suggest optimal CPC bid and strategy."
    # Call Ollama locally for suggestion
    return ollama.chat(model='llama3', messages=[{'role':'user','content':prompt}])`
  },
  {
    id: 6, emoji: "📊", title: "Analytics Dashboard", titleAr: "لوحة التحليلات",
    color: "#00d4ff", cost: "$0/mo",
    features: ["Traffic & Rankings", "Conversions & ROI", "Keyword Performance", "Competitor Tracking"],
    tools: [
      { name: "Apache Superset", role: "Full BI dashboard — charts, funnels, KPIs, drill-downs", free: "100% free open source", link: "https://superset.apache.org" },
      { name: "Metabase", role: "Easier BI alternative — beautiful dashboards, self-hosted", free: "100% free self-hosted", link: "https://metabase.com" },
      { name: "Google Analytics API", role: "Traffic, conversions, user behavior data", free: "Free", link: "https://developers.google.com/analytics" },
      { name: "Recharts / Chart.js", role: "Embed charts directly in your React frontend", free: "100% free", link: "https://recharts.org" },
    ],
    code: `// React dashboard with Recharts — free
import { LineChart, Line, XAxis, YAxis, Tooltip, 
         BarChart, Bar, ResponsiveContainer } from 'recharts'

function SEODashboard({ data }) {
  return (
    <div className="dashboard">
      {/* Rankings over time */}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data.rankings}>
          <XAxis dataKey="date" />
          <YAxis reversed domain={[1, 100]} />
          <Tooltip />
          <Line dataKey="position" stroke="#00d4ff" />
        </LineChart>
      </ResponsiveContainer>

      {/* Keyword traffic */}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data.keywords}>
          <XAxis dataKey="keyword" />
          <YAxis />
          <Bar dataKey="clicks" fill="#7c3aed" />
          <Bar dataKey="impressions" fill="#10b981" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}`
  },
];

const mvpPhases = [
  {
    phase: 1, title: "MVP — Launch in 8 weeks", color: "#00d4ff",
    items: [
      { task: "Supabase setup (auth + DB)", weeks: "Week 1", free: true },
      { task: "GSC API + keyword data", weeks: "Week 2", free: true },
      { task: "Site crawler (Scrapy)", weeks: "Week 3", free: true },
      { task: "Basic SEO audit report", weeks: "Week 4", free: true },
      { task: "React dashboard + Recharts", weeks: "Week 5-6", free: true },
      { task: "Deploy on Railway/Render", weeks: "Week 7-8", free: true },
    ]
  },
  {
    phase: 2, title: "Growth — Weeks 9–16", color: "#7c3aed",
    items: [
      { task: "Ollama AI content engine", weeks: "Week 9-10", free: true },
      { task: "Competitor analysis module", weeks: "Week 11-12", free: true },
      { task: "Google Ads API integration", weeks: "Week 13-14", free: true },
      { task: "Arabic NLP with AraBERT", weeks: "Week 15-16", free: true },
    ]
  },
  {
    phase: 3, title: "Scale — Weeks 17–24", color: "#10b981",
    items: [
      { task: "AI ranking prediction (ML model)", weeks: "Week 17-18", free: true },
      { task: "Perplexity API visibility scoring", weeks: "Week 19-20", free: true },
      { task: "Advanced analytics (Superset)", weeks: "Week 21-22", free: true },
      { task: "White-label for agencies", weeks: "Week 23-24", free: false },
    ]
  },
];

const totalCost = [
  { item: "Supabase (DB + Auth)", monthly: "$0", note: "Free up to 50k users" },
  { item: "Railway/Render (Hosting)", monthly: "$0", note: "Free tier available" },
  { item: "Ollama (AI Content)", monthly: "$0", note: "Run locally on your machine" },
  { item: "Google APIs (GSC, GA, Ads)", monthly: "$0", note: "Free API access" },
  { item: "Scrapy (Crawler)", monthly: "$0", note: "Open source" },
  { item: "Apache Superset", monthly: "$0", note: "Self-hosted, open source" },
  { item: "Perplexity API", monthly: "$0", note: "Free tier 100 req/day" },
  { item: "DataForSEO", monthly: "$0", note: "100 free requests/day" },
  { item: "TOTAL", monthly: "$0–5", note: "Only pay when you scale" },
];

export default function App() {
  const [tab, setTab] = useState("modules");
  const [activeModule, setActiveModule] = useState(0);
  const [showCode, setShowCode] = useState(false);

  const tabs = [
    { id: "modules", label: "🧩 6 Modules" },
    { id: "roadmap", label: "🗺️ MVP Roadmap" },
    { id: "cost", label: "💰 Free Cost Breakdown" },
    { id: "arch", label: "🏗️ Architecture" },
  ];

  const mod = modules[activeModule];

  return (
    <div style={{ background: "#050a12", minHeight: "100vh", color: "#e2eaf4", fontFamily: "'IBM Plex Mono', monospace", padding: "24px 16px" }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 10, color: "#00d4ff", letterSpacing: 3, textTransform: "uppercase", marginBottom: 8 }}>◆ AI Search Growth Platform</div>
          <div style={{ fontFamily: "sans-serif", fontSize: 26, fontWeight: 800, marginBottom: 4 }}>ASGP — Free Stack Implementation</div>
          <div style={{ color: "#5a7a99", fontSize: 12 }}>Build your SEMrush/Ahrefs alternative · $0/month to start · 6 Modules · 3 Phases</div>
        </div>

        {/* Stat row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 24 }}>
          {[
            { v: "6", l: "Modules", c: "#00d4ff" },
            { v: "20+", l: "Free Tools", c: "#7c3aed" },
            { v: "$0", l: "Monthly Cost", c: "#10b981" },
            { v: "8wk", l: "MVP Timeline", c: "#f59e0b" },
          ].map((s, i) => (
            <div key={i} style={{ background: "#0c1420", border: `1px solid #1a2d45`, borderTop: `2px solid ${s.c}`, padding: "14px 12px" }}>
              <div style={{ fontFamily: "sans-serif", fontSize: 26, fontWeight: 800, color: s.c }}>{s.v}</div>
              <div style={{ fontSize: 10, color: "#5a7a99", textTransform: "uppercase", letterSpacing: 1, marginTop: 4 }}>{s.l}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, background: "#0c1420", border: "1px solid #1a2d45", padding: 4, marginBottom: 24, overflowX: "auto" }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              flex: 1, minWidth: 130, padding: "9px 12px", border: "none", cursor: "pointer", fontSize: 11,
              fontFamily: "monospace", letterSpacing: 0.5, whiteSpace: "nowrap",
              background: tab === t.id ? "#00d4ff" : "transparent",
              color: tab === t.id ? "#000" : "#5a7a99",
              fontWeight: tab === t.id ? 700 : 400,
            }}>{t.label}</button>
          ))}
        </div>

        {/* MODULES TAB */}
        {tab === "modules" && (
          <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16 }}>
            {/* Sidebar */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {modules.map((m, i) => (
                <div key={i} onClick={() => { setActiveModule(i); setShowCode(false); }}
                  style={{ background: activeModule === i ? m.color : "#0c1420", border: `1px solid ${activeModule === i ? m.color : "#1a2d45"}`, padding: "12px 16px", cursor: "pointer", transition: "all 0.2s" }}>
                  <div style={{ fontSize: 18, marginBottom: 4 }}>{m.emoji}</div>
                  <div style={{ fontFamily: "sans-serif", fontWeight: 700, fontSize: 13, color: activeModule === i ? "#000" : "#e2eaf4", marginBottom: 2 }}>Module {m.id}</div>
                  <div style={{ fontSize: 11, color: activeModule === i ? "rgba(0,0,0,0.7)" : "#5a7a99" }}>{m.title}</div>
                  <div style={{ fontSize: 10, marginTop: 6, color: activeModule === i ? "#000" : m.color, fontWeight: 700 }}>{m.cost}</div>
                </div>
              ))}
            </div>

            {/* Detail */}
            <div>
              <div style={{ background: "#0c1420", border: `1px solid #1a2d45`, borderTop: `3px solid ${mod.color}`, padding: "20px 24px", marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                  <div>
                    <div style={{ fontFamily: "sans-serif", fontSize: 20, fontWeight: 800, marginBottom: 4 }}>{mod.emoji} {mod.title}</div>
                    <div style={{ fontFamily: "Cairo, sans-serif", fontSize: 14, color: "#5a7a99" }}>{mod.titleAr}</div>
                  </div>
                  <div style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.4)", color: "#10b981", padding: "6px 16px", fontSize: 13, fontWeight: 700 }}>{mod.cost}/mo</div>
                </div>

                <div style={{ fontSize: 11, color: "#5a7a99", letterSpacing: 2, textTransform: "uppercase", marginBottom: 10 }}>Features Covered</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
                  {mod.features.map((f, i) => (
                    <span key={i} style={{ background: `${mod.color}15`, border: `1px solid ${mod.color}40`, color: mod.color, fontSize: 11, padding: "3px 12px" }}>{f}</span>
                  ))}
                </div>

                <div style={{ fontSize: 11, color: "#5a7a99", letterSpacing: 2, textTransform: "uppercase", marginBottom: 10 }}>Free Tools Stack</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
                  {mod.tools.map((tool, i) => (
                    <div key={i} style={{ background: "#060e18", border: "1px solid #1a2d45", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontFamily: "sans-serif", fontWeight: 700, fontSize: 13, color: mod.color, marginBottom: 4 }}>{tool.name}</div>
                        <div style={{ fontSize: 11, color: "#a0bcd4", lineHeight: 1.7 }}>{tool.role}</div>
                      </div>
                      <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.3)", color: "#10b981", fontSize: 10, padding: "3px 10px", whiteSpace: "nowrap", flexShrink: 0 }}>{tool.free}</div>
                    </div>
                  ))}
                </div>

                <button onClick={() => setShowCode(!showCode)}
                  style={{ background: showCode ? mod.color : "transparent", border: `1px solid ${mod.color}`, color: showCode ? "#000" : mod.color, fontFamily: "monospace", fontSize: 11, padding: "8px 20px", cursor: "pointer", letterSpacing: 1 }}>
                  {showCode ? "▲ HIDE CODE" : "▼ VIEW CODE SAMPLE"}
                </button>
              </div>

              {showCode && (
                <div style={{ background: "#060e18", border: "1px solid #1a2d45", borderLeft: `3px solid ${mod.color}`, padding: "20px 24px" }}>
                  <div style={{ fontSize: 10, color: "#5a7a99", letterSpacing: 2, textTransform: "uppercase", marginBottom: 12 }}>Implementation Code</div>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: 11, lineHeight: 1.9, color: "#a0bcd4", margin: 0 }}>{mod.code}</pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ROADMAP TAB */}
        {tab === "roadmap" && (
          <div>
            {mvpPhases.map((phase, pi) => (
              <div key={pi} style={{ marginBottom: 28 }}>
                <div style={{ background: "#0c1420", border: `1px solid #1a2d45`, borderLeft: `4px solid ${phase.color}`, padding: "16px 20px", marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 10, color: phase.color, letterSpacing: 2, textTransform: "uppercase", marginBottom: 4 }}>Phase {phase.phase}</div>
                    <div style={{ fontFamily: "sans-serif", fontWeight: 800, fontSize: 16 }}>{phase.title}</div>
                  </div>
                  <div style={{ fontSize: 11, color: "#10b981", background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.3)", padding: "4px 14px" }}>$0 cost</div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {phase.items.map((item, ii) => (
                    <div key={ii} style={{ background: "#0c1420", border: "1px solid #1a2d45", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{ width: 18, height: 18, border: `2px solid ${phase.color}`, borderRadius: "50%", background: `${phase.color}20`, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{item.task}</span>
                      </div>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span style={{ fontSize: 10, color: "#5a7a99" }}>{item.weeks}</span>
                        <span style={{ fontSize: 10, color: item.free ? "#10b981" : "#f59e0b", border: `1px solid`, borderColor: item.free ? "rgba(16,185,129,0.4)" : "rgba(245,158,11,0.4)", background: item.free ? "rgba(16,185,129,0.08)" : "rgba(245,158,11,0.08)", padding: "2px 8px" }}>
                          {item.free ? "FREE" : "PAID"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* COST TAB */}
        {tab === "cost" && (
          <div>
            <div style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.3)", borderLeft: "3px solid #10b981", padding: "14px 20px", fontSize: 12, color: "#6ee7b7", marginBottom: 24, lineHeight: 1.8 }}>
              <strong style={{ display: "block", color: "#10b981", fontFamily: "sans-serif", marginBottom: 4 }}>✓ TOTAL COST TO BUILD ASGP: $0–5/month</strong>
              All core modules can be built and launched with zero monthly cost. You only pay when you scale to thousands of users.
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr>
                  {["Tool / Service", "Monthly Cost", "Free Limit"].map(h => (
                    <th key={h} style={{ background: "#111c2e", padding: "12px 16px", textAlign: "left", border: "1px solid #1a2d45", fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#5a7a99" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {totalCost.map((row, i) => (
                  <tr key={i} style={{ background: row.item === "TOTAL" ? "#111c2e" : "#0c1420" }}>
                    <td style={{ padding: "12px 16px", border: "1px solid #1a2d45", fontFamily: row.item === "TOTAL" ? "sans-serif" : "monospace", fontWeight: row.item === "TOTAL" ? 800 : 400, color: row.item === "TOTAL" ? "#00d4ff" : "#e2eaf4" }}>{row.item}</td>
                    <td style={{ padding: "12px 16px", border: "1px solid #1a2d45", color: row.monthly === "$0" ? "#10b981" : "#f59e0b", fontWeight: 700, fontFamily: "sans-serif", fontSize: 16 }}>{row.monthly}</td>
                    <td style={{ padding: "12px 16px", border: "1px solid #1a2d45", color: "#5a7a99", fontSize: 11 }}>{row.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[
                { title: "When to start paying", color: "#f59e0b", items: ["100+ active companies on platform", "Millions of keywords to process", "Need dedicated GPU for ML models", "White-label for agencies"] },
                { title: "Scale-up tools (when ready)", color: "#7c3aed", items: ["Vercel Pro — $20/mo (better hosting)", "Supabase Pro — $25/mo (more DB)", "OpenAI API — pay per token", "BigQuery — pay per query"] },
              ].map((box, i) => (
                <div key={i} style={{ background: "#0c1420", border: "1px solid #1a2d45", borderTop: `2px solid ${box.color}`, padding: "16px 20px" }}>
                  <div style={{ fontFamily: "sans-serif", fontWeight: 700, fontSize: 13, color: box.color, marginBottom: 12 }}>{box.title}</div>
                  {box.items.map((item, j) => <div key={j} style={{ fontSize: 11, color: "#a0bcd4", lineHeight: 2.2, borderBottom: "1px solid #111c2e" }}>→ {item}</div>)}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ARCH TAB */}
        {tab === "arch" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 20 }}>
              {[
                { layer: "Frontend", color: "#00d4ff", tech: ["React.js + TypeScript", "Recharts (dashboards)", "TailwindCSS", "NextAuth.js (login)"] },
                { layer: "Backend API", color: "#7c3aed", tech: ["FastAPI (Python)", "Node.js (optional)", "REST + WebSockets", "Redis (job queue)"] },
                { layer: "Database", color: "#10b981", tech: ["Supabase (PostgreSQL)", "Redis (caching)", "BigQuery (analytics)", "S3/R2 (file storage)"] },
                { layer: "AI Layer", color: "#f59e0b", tech: ["Ollama (local LLMs)", "Claude / GPT API", "Hugging Face models", "LangChain pipelines"] },
                { layer: "Data Sources", color: "#ef4444", tech: ["Google Search Console", "Google Analytics", "Google Ads API", "Scrapy crawler"] },
                { layer: "Infrastructure", color: "#00d4ff", tech: ["Railway / Render (free)", "Cloudflare (CDN free)", "GitHub Actions (CI/CD)", "Docker containers"] },
              ].map((layer, i) => (
                <div key={i} style={{ background: "#0c1420", border: "1px solid #1a2d45", borderTop: `2px solid ${layer.color}`, padding: "14px 16px" }}>
                  <div style={{ fontFamily: "sans-serif", fontWeight: 700, fontSize: 13, color: layer.color, marginBottom: 10 }}>{layer.layer}</div>
                  {layer.tech.map((t, j) => <div key={j} style={{ fontSize: 11, color: "#a0bcd4", lineHeight: 2, borderBottom: "1px solid #111c2e" }}>· {t}</div>)}
                </div>
              ))}
            </div>

            <div style={{ background: "#060e18", border: "1px solid #1a2d45", borderLeft: "3px solid #00d4ff", padding: "20px 24px" }}>
              <div style={{ fontSize: 10, color: "#5a7a99", letterSpacing: 2, textTransform: "uppercase", marginBottom: 16 }}>Data Flow</div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                {["User/Company", "→", "React Frontend", "→", "FastAPI Backend", "→", "AI Layer (Ollama)", "→", "PostgreSQL + BigQuery", "→", "Dashboard"].map((item, i) => (
                  <span key={i} style={{ fontSize: i % 2 === 1 ? 16 : 11, color: i % 2 === 1 ? "#00d4ff" : "#a0bcd4", background: i % 2 === 0 ? "#0c1420" : "transparent", border: i % 2 === 0 ? "1px solid #1a2d45" : "none", padding: i % 2 === 0 ? "6px 12px" : "0", borderRadius: 0 }}>{item}</span>
                ))}
              </div>
            </div>
          </div>
        )}

        <div style={{ marginTop: 36, borderTop: "1px solid #1a2d45", paddingTop: 20, display: "flex", justifyContent: "space-between", fontSize: 11, color: "#5a7a99", flexWrap: "wrap", gap: 8 }}>
          <span>AI Search Growth Platform · ASGP</span>
          <span style={{ color: "#10b981" }}>Build cost: $0 → Scale like SEMrush</span>
        </div>
      </div>
    </div>
  );
}
