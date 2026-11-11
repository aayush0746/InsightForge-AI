export interface DocumentMetadata {
  document_id: string;
  filename: string;
  file_size_bytes: number;
  total_pages: number;
  total_chunks: number;
  upload_timestamp: string;
  status: 'processing' | 'indexed' | 'error';
  error_message?: string;
}

export interface Citation {
  source_filename: string;
  page_number: number;
  chunk_id: string;
  snippet: string;
  document_id?: string;
  relevance_score?: number;
}

export interface ChartData {
  type: 'bar' | 'line' | 'pie';
  title: string;
  data: Array<{ name: string; value: number }>;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  question: string;
  document_ids?: string[];
  use_reranker?: boolean;
  enable_web_search?: boolean;
  top_k?: number;
  top_n?: number;
  history?: Array<{ role: string; content: string }>;
}

export interface ChatResponse {
  question: string;
  answer: string;
  citations: Citation[];
  retrieved_chunks_count: number;
  reranked_chunks_count: number;
  is_grounded: boolean;
  unanswered_reason?: string;
  chart_data?: ChartData;
}

export interface AgentExecutionStep {
  agent_name: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  details: string;
  execution_time_seconds: number;
  data?: Record<string, any>;
}

export interface FactCheckItem {
  claim: string;
  is_supported: boolean;
  confidence: number;
  source_citation?: string;
  note: string;
}

export interface ResearchRequest {
  question: string;
  document_ids?: string[];
  deep_analysis?: boolean;
  enable_web_search?: boolean;
  max_subtasks?: number;
}

export interface ResearchReport {
  research_id: string;
  question: string;
  created_at: string;
  executive_summary: string;
  methodology: string;
  key_findings: string[];
  evidence_analysis: string;
  ai_interpretations: string[];
  conflicts_or_gaps: string[];
  risks_and_limitations: string[];
  recommendations: string[];
  citations: Citation[];
  fact_check_results: FactCheckItem[];
  grounding_score: number;
  agent_steps: AgentExecutionStep[];
  chart_data?: ChartData;
}

export interface ResearchReportSummary {
  research_id: string;
  question: string;
  created_at: string;
  grounding_score: number;
  key_findings_count: number;
  citations_count: number;
}

export interface EvaluationMetrics {
  relevance: number;
  accuracy: number;
  clarity: number;
  completeness: number;
  actionability: number;
  faithfulness: number;
  overall: number;
  feedback: string;
}

export interface PromptRunResult {
  prompt_name: string;
  prompt_template: string;
  generated_answer: string;
  metrics: EvaluationMetrics;
  execution_time_seconds: number;
}

export interface EvaluationRequest {
  question: string;
  prompts: Record<string, string>;
  context?: string;
  save_to_history?: boolean;
}

export interface EvaluationRunRecord {
  run_id: string;
  timestamp: string;
  question: string;
  results: Record<string, PromptRunResult>;
  best_prompt_name: string;
}

export interface PromptTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  template: string;
}

export interface EvaluationHistorySummary {
  run_id: string;
  timestamp: string;
  question: string;
  best_prompt_name: string;
  prompts_compared_count: number;
}

export interface SystemSettings {
  model_name: string;
  temperature: number;
  chunk_size: number;
  chunk_overlap: number;
  retrieval_top_k: number;
  rerank_top_n: number;
  hybrid_alpha: number;
  available_models: string[];
}

export interface SystemHealth {
  status: string;
  version: string;
  gemini_api_configured: boolean;
  embedding_model: string;
  cross_encoder_model: string;
  chroma_db_status: string;
  total_indexed_documents: number;
  total_chunks: number;
}

export interface DocumentComparisonResult {
  doc_a_name: string;
  doc_b_name: string;
  executive_summary: string;
  comparison_matrix: Array<{
    dimension: string;
    doc_a: string;
    doc_b: string;
    difference: string;
  }>;
  added_clauses: string[];
  removed_clauses: string[];
  conflicts_or_changes: Array<{
    clause: string;
    doc_a_version: string;
    doc_b_version: string;
    impact: string;
  }>;
  risk_assessment: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  color: string;
  icon: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
  thread_count: number;
  document_count: number;
}

export interface ThreadMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: Citation[];
  is_grounded?: boolean;
  chart_data?: ChartData;
}

export interface ProjectThread {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ThreadMessage[];
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
  provider: 'google' | 'email';
  role: string;
  created_at: string;
}

export interface AuthResponse {
  success: boolean;
  access_token: string;
  token_type: string;
  user: User;
  message: string;
}

