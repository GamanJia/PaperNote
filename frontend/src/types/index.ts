export type LLMProviderType = "openai-compatible" | "ollama";

export interface LLMConfig {
  provider_type: LLMProviderType;
  base_url?: string | null;
  model_name: string;
  api_key?: string | null;
  temperature: number;
  max_tokens: number;
}

export interface SearchFilters {
  journals: string[];
  conferences: string[];
  year_start?: number | null;
  year_end?: number | null;
  date_start?: string | null;
  date_end?: string | null;
}

export interface SearchQueryInput {
  keywords: string[];
  research_direction?: string | null;
  paper_description?: string | null;
}

export interface SearchParams {
  max_results: number;
  enable_llm_filter: boolean;
  enable_keyword_expansion: boolean;
  sort_by: "relevance" | "date_desc" | "year_desc";
  sources: string[];
  llm_concurrency: number;
  cache_ttl_minutes: number;
}

export interface SearchRequest {
  filters: SearchFilters;
  query: SearchQueryInput;
  params: SearchParams;
  model: LLMConfig;
}

export interface ParsedQuery {
  topic: string;
  keywords: string[];
  expanded_keywords: string[];
  exclude_keywords: string[];
  venue_hints: string[];
}

export interface SearchStats {
  started_at: string;
  finished_at: string;
  duration_ms: number;
  total_candidates: number;
  deduped_candidates: number;
  final_results: number;
  source_counts: Record<string, number>;
  failed_sources: string[];
}

export interface PaperResult {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  year?: number | null;
  published_date?: string | null;
  venue?: string | null;
  source: string;
  doi?: string | null;
  url?: string | null;
  pdf_url?: string | null;
  keywords: string[];
  citation_count: number;
  arxiv_id?: string | null;
  is_relevant: boolean;
  relevance_score: number;
  tags: string[];
  summary: string;
  reason: string;
  innovation: string;
  match_points: string[];
}

export interface SearchResponse {
  search_id: string;
  parsed_query: ParsedQuery;
  total_candidates: number;
  results: PaperResult[];
  stats: SearchStats;
}

export interface HistorySummary {
  id: string;
  title: string;
  created_at: string;
  total_candidates: number;
  final_results: number;
}

export interface HistoryDetail {
  id: string;
  title: string;
  created_at: string;
  request: SearchRequest;
  parsed_query: ParsedQuery;
  stats: Record<string, unknown>;
  candidates: PaperResult[];
  results: PaperResult[];
  exports: Array<{
    file_name: string;
    format: string;
    row_count: number;
    created_at: string;
  }>;
}

export interface AppSettings {
  default_model: LLMConfig;
  enabled_sources: string[];
  default_export_format: "csv" | "xlsx" | "markdown";
}

export interface SourceItem {
  id: string;
  name: string;
}

export interface ExportResponse {
  file_name: string;
  format: string;
  row_count: number;
  created_at: string;
  download_url: string;
  absolute_path: string;
}
