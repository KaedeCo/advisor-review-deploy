/**
 * API 客户端 — 封装所有后端接口调用（部署版：API Key/Cookie 由前端 localStorage 管理）
 */

const BASE = '/advisor/api'

// ═══════════════════════════════════════════════════════════
//  localStorage 配置读写（部署版：不向服务端保存任何敏感数据）
// ═══════════════════════════════════════════════════════════

const STORAGE_KEYS = {
  deepseek: 'advisor_deepseek_key',
  tavily: 'advisor_tavily_key',
  gradchoice: 'advisor_gradchoice_token',
  letpub: 'advisor_letpub_cookie',
  platforms: 'advisor_platforms',
}

export function getLocalDeepseekKey(): string {
  return localStorage.getItem(STORAGE_KEYS.deepseek) || ''
}

export function setLocalDeepseekKey(key: string) {
  localStorage.setItem(STORAGE_KEYS.deepseek, key)
}

export function getLocalTavilyKey(): string {
  return localStorage.getItem(STORAGE_KEYS.tavily) || ''
}

export function setLocalTavilyKey(key: string) {
  localStorage.setItem(STORAGE_KEYS.tavily, key)
}

export function getLocalCookie(platform: string): string {
  const map: Record<string, string> = { gradchoice: STORAGE_KEYS.gradchoice, letpub: STORAGE_KEYS.letpub }
  return localStorage.getItem(map[platform] || '') || ''
}

export function setLocalCookie(platform: string, value: string) {
  const map: Record<string, string> = { gradchoice: STORAGE_KEYS.gradchoice, letpub: STORAGE_KEYS.letpub }
  if (map[platform]) localStorage.setItem(map[platform], value)
}

export function getLocalCookies(): Record<string, string> {
  return {
    gradchoice: getLocalCookie('gradchoice'),
    letpub: getLocalCookie('letpub'),
  }
}

// Platforms toggle stored in localStorage
export function getLocalPlatforms(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.platforms) || '{}')
  } catch { return {} }
}

export function setLocalPlatformEnabled(key: string, enabled: boolean) {
  const p = getLocalPlatforms()
  p[key] = enabled
  localStorage.setItem(STORAGE_KEYS.platforms, JSON.stringify(p))
}

// ===== 类型定义 =====

export interface Platform {
  key: string
  name: string
  enabled: boolean
  tier: number
}

export interface ReviewItem {
  author: string
  rating?: number | null
  date: string
  content: string
  source: string
  source_url: string
}

export interface AdvisorResult {
  name: string
  university: string
  department: string
  overall_score?: number | null
  review_count: number
  reviews: ReviewItem[]
  source: string
  detail_url: string
}

export interface SearchResponse {
  query: string
  results: AdvisorResult[]
  total_count: number
  platforms_used: string[]
  elapsed_seconds: number
}

export interface SentimentDetail {
  text_preview: string
  sentiment_score: number
  label: 'positive' | 'negative' | 'neutral'
}

export interface SentimentResult {
  positive_count: number
  negative_count: number
  neutral_count: number
  total_count: number
  details: SentimentDetail[]
  analyzer: string
}

export interface DeepseekResponse {
  summary: string
  pros: string[]
  cons: string[]
  risk_flags: string[]
  overall_rating?: number | null
  analyzer: string
}

// ===== API 函数 =====

/** 获取所有平台状态 */
export async function fetchPlatforms(): Promise<Record<string, Platform>> {
  const res = await fetch(`${BASE}/platforms`)
  if (!res.ok) throw new Error('获取平台列表失败')
  return res.json()
}

/** 搜索导师 */
export async function searchAdvisor(params: {
  advisor_name: string
  university?: string
  department?: string
  platforms?: string[]
}): Promise<SearchResponse> {
  const body: any = { ...params }
  // Attach keys from localStorage
  body.deepseek_key = getLocalDeepseekKey()
  body.tavily_key = getLocalTavilyKey()
  body.cookies = getLocalCookies()
  const res = await fetch(`${BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** SnowNLP 情感分析 */
export async function analyzeSentiment(
  reviewsText: string,
  advisor?: { name?: string; university?: string; department?: string; reviewCount?: number }
): Promise<SentimentResult> {
  const res = await fetch(`${BASE}/analyze/sentiment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reviews_text: reviewsText,
      advisor_name: advisor?.name || '',
      university: advisor?.university || '',
      department: advisor?.department || '',
      review_count: advisor?.reviewCount || 0,
    }),
  })
  if (!res.ok) throw new Error('情感分析失败')
  return res.json()
}

/** DeepSeek 逐条情感分类 */
export async function analyzeSentimentDeepseek(
  reviewsText: string,
  advisor?: { name?: string; university?: string; department?: string; reviewCount?: number }
): Promise<SentimentResult> {
  const res = await fetch(`${BASE}/analyze/sentiment/deepseek`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reviews_text: reviewsText,
      advisor_name: advisor?.name || '',
      university: advisor?.university || '',
      department: advisor?.department || '',
      review_count: advisor?.reviewCount || 0,
      deepseek_key: getLocalDeepseekKey(),
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** DeepSeek 深度分析 */
export async function analyzeDeepseek(
  reviewsText: string,
  advisor?: { name?: string; university?: string; department?: string; reviewCount?: number }
): Promise<DeepseekResponse> {
  const params = new URLSearchParams()
  if (advisor?.name) params.append('advisor_name', advisor.name)
  if (advisor?.university) params.append('university', advisor.university)
  if (advisor?.department) params.append('department', advisor.department)
  if (advisor?.reviewCount) params.append('review_count', String(advisor.reviewCount))
  const res = await fetch(`${BASE}/analyze/deepseek?${params.toString()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviews_text: reviewsText, deepseek_key: getLocalDeepseekKey() }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export interface SettingsData {
  platforms: Platform[]
}

/** 获取设置状态（仅返回平台列表，不含敏感信息） */
export async function fetchSettings(): Promise<SettingsData> {
  const res = await fetch(`${BASE}/settings`)
  if (!res.ok) throw new Error('获取设置失败')
  return res.json()
}

/** Tavily 连通检测（使用前端传来的 key） */
export interface TavilyCheckResult {
  available: boolean
  detail: string
}
export async function checkTavily(apiKey: string): Promise<TavilyCheckResult> {
  const res = await fetch(`${BASE}/settings/check-tavily?tavily_key=${encodeURIComponent(apiKey)}`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** 验证 GradChoice Access Token */
export interface TokenVerifyResult {
  valid: boolean
  status_code: number
  detail: string
  url: string
}
export async function verifyToken(token: string): Promise<TokenVerifyResult> {
  const res = await fetch(`${BASE}/settings/verify-token?token=${encodeURIComponent(token)}`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** 验证 LetPub PHPSESSID */
export async function verifyLetpub(phpsessid: string): Promise<{ valid: boolean; detail: string }> {
  const res = await fetch(`${BASE}/settings/verify-letpub?phpsessid=${encodeURIComponent(phpsessid)}`, { method: 'POST' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ====== 搜索历史（持久化） ======

export interface HistoryRecord {
  id: number
  query: string
  advisor_name: string
  university: string
  department: string
  total_count: number
  platforms_used: string[]
  elapsed_seconds: number
  created_at: string
}

export interface HistoryDetail extends HistoryRecord {
  results: AdvisorResult[]
}

export interface HistoryListResponse {
  records: HistoryRecord[]
  total: number
  latest: string | null
}

/** 获取搜索历史列表 */
export async function fetchHistory(limit = 50, offset = 0): Promise<HistoryListResponse> {
  const res = await fetch(`${BASE}/history?limit=${limit}&offset=${offset}`)
  if (!res.ok) throw new Error('获取历史记录失败')
  return res.json()
}

/** 获取单条历史详情 */
export async function fetchHistoryDetail(id: number): Promise<HistoryDetail> {
  const res = await fetch(`${BASE}/history/${id}`)
  if (!res.ok) throw new Error('获取历史详情失败')
  return res.json()
}

/** 删除一条历史记录 */
export async function deleteHistoryRecord(id: number): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE}/history/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** 清空所有历史 */
export async function clearAllHistory(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE}/history`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ====== 分析结果持久化 ======

export interface AnalysisRecord {
  id: number
  advisor_name: string
  university: string
  department: string
  review_count: number
  sentiment?: SentimentResult | null
  deepseek?: DeepseekResponse | null
  dimension_scores?: DimensionScores | null
  reviews_text?: string
  created_at: string
  updated_at: string
}

/** 获取分析结果列表 */
export async function fetchAnalysisList(limit = 50, offset = 0): Promise<{ records: AnalysisRecord[] }> {
  const res = await fetch(`${BASE}/analyze/list?limit=${limit}&offset=${offset}`)
  if (!res.ok) throw new Error('获取分析列表失败')
  return res.json()
}

/** 获取单条分析详情 */
export async function fetchAnalysisDetail(id: number): Promise<AnalysisRecord> {
  const res = await fetch(`${BASE}/analyze/detail/${id}`)
  if (!res.ok) throw new Error('获取分析详情失败')
  return res.json()
}

/** 删除分析记录 */
export async function deleteAnalysisRecord(id: number): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE}/analyze/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ====== 六维评分 ======

export interface DimScore {
  score: number
  reasoning: string
  red_flags: string[]
}

export interface DimensionScores {
  academic: DimScore
  mentorship: DimScore
  ethics: DimScore
  relationship: DimScore
  funding: DimScore
  career: DimScore
  overall: number
  confidence: number
}

export interface SixDimensionResponse {
  advisor_name: string
  scores: DimensionScores
  red_flags_summary: string[]
  saved: boolean
}

/** 六维并行评分（6 路 DeepSeek 并发） */
export async function analyzeDimensions(
  reviewsText: string,
  advisor?: { name?: string; university?: string; department?: string; reviewCount?: number }
): Promise<SixDimensionResponse> {
  const res = await fetch(`${BASE}/analyze/dimensions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reviews_text: reviewsText,
      advisor_name: advisor?.name || '',
      university: advisor?.university || '',
      department: advisor?.department || '',
      review_count: advisor?.reviewCount || 0,
      deepseek_key: getLocalDeepseekKey(),
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ====== 导师画像 ======

export interface AdvisorProfile {
  advisor_name: string
  university: string
  department: string
  one_line_summary: string
  teaching_style: string
  personality: string
  research_strength: string
  student_outcome: string
  risk_level: string
  keywords: string[]
  overall_recommendation: string
}

export async function generateProfile(
  reviewsText: string,
  advisor?: { name?: string; university?: string; department?: string }
): Promise<AdvisorProfile> {
  const res = await fetch(`${BASE}/analyze/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reviews_text: reviewsText,
      advisor_name: advisor?.name || '',
      university: advisor?.university || '',
      department: advisor?.department || '',
      deepseek_key: getLocalDeepseekKey(),
    }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ====== KPI 统计 ======

export interface KpiStats {
  github_advisors: number
  github_reviews: number
  unique_advisors_analyzed: number
  total_reviews_analyzed: number
  total_searches: number
  avg_search_latency: number
  total_results_returned: number
  latest_search: string | null
  total_analyses: number
  snownlp_calls: number
  deepseek_calls: number
  dim_score_calls: number
  latest_analysis: string | null
  total_platforms: number
  enabled_platforms: number
  platform_frequency: Record<string, number>
  enabled_platform_list: { key: string; name: string; tier: number }[]
  deepseek_configured: boolean
  tavily_configured: boolean
}

export async function fetchKpiStats(): Promise<KpiStats> {
  const res = await fetch(`${BASE}/stats`)
  if (!res.ok) throw new Error('获取统计数据失败')
  return res.json()
}
