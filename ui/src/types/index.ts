// Common types used throughout the application

export interface User {
  id: string;
  email: string;
  full_name: string;
  expertise_domains: string[];
  reputation_score: number;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface Opportunity {
  id: string;
  title: string;
  description: string;
  market_size_estimate: number;
  validation_score: number;
  ai_feasibility_score: number;
  industry: string;
  ai_solution_type: string;
  implementation_complexity: 'LOW' | 'MEDIUM' | 'HIGH';
  validation_count: number;
  created_at: string;
  updated_at: string;
  // Additional fields from AI agents
  generated_by?: string;
  generation_method?: string;
  agent_analysis?: {
    viability?: {
      market_size_assessment?: string;
      competition_level?: string;
      technical_feasibility?: string;
      roi_projection?: {
        time_to_market?: string;
        break_even?: string;
        projected_revenue_y1?: number;
      };
    };
    implementation?: {
      required_technologies?: string[];
      team_requirements?: string[];
      estimated_timeline?: string;
      key_challenges?: string[];
      success_factors?: string[];
    };
    ai_capabilities?: {
      required_ai_stack?: {
        ml_frameworks?: string[];
        cloud_services?: string[];
        data_tools?: string[];
      };
      complexity_assessment?: string;
      ai_maturity_level?: string;
      development_effort?: string;
      success_probability?: string;
    };
    market_trends?: {
      hot_technologies?: Array<{
        name: string;
        growth_rate: string;
        adoption: string;
      }>;
      market_indicators?: {
        vc_funding?: string;
        job_postings?: string;
        patent_filings?: string;
      };
      predicted_opportunities?: string[];
    };
    agent_confidence?: number;
  };
}

export interface OpportunityFilters {
  industry?: string;
  ai_solution_type?: string;
  min_validation_score?: number;
  max_validation_score?: number;
  implementation_complexity?: string;
  market_size_min?: number;
  market_size_max?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  message: string;
  error_code?: string;
  details?: Record<string, any>;
}

export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

// Form types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  email: string;
  password: string;
  confirmPassword: string;
  full_name: string;
  expertise_domains?: string[];
}

// Component prop types
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
}

// Theme types
export type Theme = 'light' | 'dark' | 'system';

// Status types
export type Status = 'idle' | 'loading' | 'success' | 'error';

// Sort options
export type SortOrder = 'asc' | 'desc';
export type SortField = 'validation_score' | 'market_size_estimate' | 'created_at' | 'title';