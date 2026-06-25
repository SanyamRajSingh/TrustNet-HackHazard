import { create } from 'zustand';

export interface ExtractedEntities {
  company_name: string | null;
  email: string | null;
  phone_number: string | null;
  website_url: string | null;
  recruiter_name: string | null;
  job_title: string | null;
  location: string | null;
  salary_mentioned: number | null;
  fee_amount: number | null;
  urgency_indicators: boolean;
  personal_email_for_corp_contact: boolean;
  language_detected: string;
  red_flags: string[];
}

export interface EvidenceItem {
  category: string;
  finding: string;
  severity: 'critical' | 'warning' | 'info' | 'positive';
  details?: string;
}

export interface CategoryScore {
  score: number;
  weight: number;
  weighted_score: number;
  evidence: EvidenceItem[];
}

export interface InvestigationResult {
  id: string;
  trust_score: number;
  confidence_score: number;
  verdict: string;
  verdict_label: string;
  verdict_color: string;
  entities: ExtractedEntities;
  category_scores: Record<string, CategoryScore>;
  evidence: EvidenceItem[];
  hindi_explanation: string | null;
  graph_connections: { flagged_count: number; rings: string[]; nodes: any[]; relationships: any[] } | null;
  blockchain_tx_hash: string | null;
  processing_ms: number;
  created_at: string;
}

interface AppState {
  // Investigation
  rawInput: string;
  isLoading: boolean;
  currentResult: InvestigationResult | null;
  investigationHistory: InvestigationResult[];

  // Voice
  isRecording: boolean;
  audioBase64: string | null;
  transcript: string | null;

  // UI
  activeTab: string;
  isMobileMenuOpen: boolean;

  // Actions
  setRawInput: (input: string) => void;
  setIsLoading: (loading: boolean) => void;
  setCurrentResult: (result: InvestigationResult | null) => void;
  addToHistory: (result: InvestigationResult) => void;
  setIsRecording: (recording: boolean) => void;
  setAudioBase64: (audio: string | null) => void;
  setTranscript: (transcript: string | null) => void;
  setActiveTab: (tab: string) => void;
  setMobileMenuOpen: (open: boolean) => void;
  clearResult: () => void;
}

export const useStore = create<AppState>((set) => ({
  rawInput: '',
  isLoading: false,
  currentResult: null,
  investigationHistory: [],
  isRecording: false,
  audioBase64: null,
  transcript: null,
  activeTab: 'text',
  isMobileMenuOpen: false,

  setRawInput: (input) => set({ rawInput: input }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setCurrentResult: (result) => set({ currentResult: result }),
  addToHistory: (result) =>
    set((state) => ({
      investigationHistory: [result, ...state.investigationHistory].slice(0, 50),
    })),
  setIsRecording: (recording) => set({ isRecording: recording }),
  setAudioBase64: (audio) => set({ audioBase64: audio }),
  setTranscript: (transcript) => set({ transcript }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setMobileMenuOpen: (open) => set({ isMobileMenuOpen: open }),
  clearResult: () => set({ currentResult: null, rawInput: '' }),
}));
