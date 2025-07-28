import { create } from 'zustand';
import { 
  opportunitiesService, 
  Opportunity, 
  OpportunityFilters, 
  SearchParams,
  PaginatedResponse 
} from '@/services/opportunities';

interface OpportunityState {
  opportunities: Opportunity[];
  currentOpportunity: Opportunity | null;
  filters: OpportunityFilters;
  searchQuery: string;
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    size: number;
    total: number;
    pages: number;
  };
  
  // Actions
  setOpportunities: (opportunities: Opportunity[]) => void;
  setCurrentOpportunity: (opportunity: Opportunity | null) => void;
  setFilters: (filters: OpportunityFilters) => void;
  setSearchQuery: (query: string) => void;
  searchOpportunities: (params?: SearchParams) => Promise<void>;
  loadOpportunities: (params?: SearchParams) => Promise<void>;
  loadOpportunity: (id: string) => Promise<void>;
  clearError: () => void;
  resetFilters: () => void;
}

const initialFilters: OpportunityFilters = {
  industry: undefined,
  ai_solution_type: undefined,
  min_validation_score: undefined,
  max_validation_score: undefined,
  implementation_complexity: undefined,
  market_size_min: undefined,
  market_size_max: undefined,
};

export const useOpportunityStore = create<OpportunityState>((set, get) => ({
  opportunities: [],
  currentOpportunity: null,
  filters: initialFilters,
  searchQuery: '',
  loading: false,
  error: null,
  pagination: {
    page: 1,
    size: 20,
    total: 0,
    pages: 0,
  },

  setOpportunities: (opportunities: Opportunity[]) => {
    set({ opportunities });
  },

  setCurrentOpportunity: (opportunity: Opportunity | null) => {
    set({ currentOpportunity: opportunity });
  },

  setFilters: (filters: OpportunityFilters) => {
    set({ filters: { ...get().filters, ...filters } });
  },

  setSearchQuery: (searchQuery: string) => {
    set({ searchQuery });
  },

  searchOpportunities: async (params?: SearchParams) => {
    set({ loading: true, error: null });
    try {
      const { filters, searchQuery, pagination } = get();
      
      const searchParams: SearchParams = {
        query: searchQuery || params?.query,
        filters: { ...filters, ...params?.filters },
        page: params?.page || pagination.page,
        size: params?.size || pagination.size,
        sort_by: params?.sort_by || 'validation_score',
        sort_order: params?.sort_order || 'desc',
      };

      const response: PaginatedResponse<Opportunity> = await opportunitiesService.searchOpportunities(searchParams);
      
      set({
        opportunities: response.items,
        pagination: {
          page: response.page,
          size: response.size,
          total: response.total,
          pages: response.pages,
        },
        loading: false,
      });
    } catch (error: any) {
      set({
        loading: false,
        error: error.response?.data?.message || 'Failed to search opportunities',
      });
    }
  },

  loadOpportunities: async (params?: SearchParams) => {
    set({ loading: true, error: null });
    try {
      const { filters, pagination } = get();
      
      const searchParams: SearchParams = {
        filters: { ...filters, ...params?.filters },
        page: params?.page || pagination.page,
        size: params?.size || pagination.size,
        sort_by: params?.sort_by || 'validation_score',
        sort_order: params?.sort_order || 'desc',
      };

      const response: PaginatedResponse<Opportunity> = await opportunitiesService.getOpportunities(searchParams);
      
      set({
        opportunities: response.items,
        pagination: {
          page: response.page,
          size: response.size,
          total: response.total,
          pages: response.pages,
        },
        loading: false,
      });
    } catch (error: any) {
      set({
        loading: false,
        error: error.response?.data?.message || 'Failed to load opportunities',
      });
    }
  },

  loadOpportunity: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const opportunity = await opportunitiesService.getOpportunity(id);
      set({
        currentOpportunity: opportunity,
        loading: false,
      });
    } catch (error: any) {
      set({
        loading: false,
        error: error.response?.data?.message || 'Failed to load opportunity',
      });
    }
  },

  clearError: () => {
    set({ error: null });
  },

  resetFilters: () => {
    set({ filters: initialFilters });
  },
}));