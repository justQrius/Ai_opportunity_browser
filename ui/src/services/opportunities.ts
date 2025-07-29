import apiClient from './api';
import { Opportunity } from '@/types';

export interface OpportunityFilters {
  industry?: string;
  ai_solution_type?: string;
  min_validation_score?: number;
  max_validation_score?: number;
  implementation_complexity?: string;
  market_size_min?: number;
  market_size_max?: number;
}

// Re-export from types for backwards compatibility
export type { Opportunity } from '@/types';

export interface SearchParams {
  query?: string;
  filters?: OpportunityFilters;
  page?: number;
  size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface ApiOpportunity {
  id: string;
  title: string;
  description: string;
  market_size?: number;
  validation_score: number;
  ai_feasibility_score?: number;
  target_industries?: string[];
  industry?: string;
  ai_solution_types?: string[];
  ai_solution_type?: string;
  implementation_complexity?: string;
  validation_count?: number;
  created_at: string;
  updated_at: string;
  generated_by?: string;
  generation_method?: string;
  agent_analysis?: Opportunity['agent_analysis'];
}

// Helper function to transform API opportunity to frontend format
const transformOpportunity = (apiOpp: ApiOpportunity): Opportunity => ({
  id: apiOpp.id,
  title: apiOpp.title,
  description: apiOpp.description,
  market_size_estimate: apiOpp.market_size || 0,
  validation_score: apiOpp.validation_score,
  ai_feasibility_score: apiOpp.ai_feasibility_score || 7.5, // Default value
  industry: Array.isArray(apiOpp.target_industries) ? apiOpp.target_industries[0] || 'Technology' : apiOpp.industry || 'Technology',
  ai_solution_type: Array.isArray(apiOpp.ai_solution_types) ? apiOpp.ai_solution_types[0] || 'Machine Learning' : apiOpp.ai_solution_type || 'Machine Learning',
  implementation_complexity: (apiOpp.implementation_complexity?.toUpperCase() || 'MEDIUM') as 'LOW' | 'MEDIUM' | 'HIGH',
  validation_count: apiOpp.validation_count || 0,
  created_at: apiOpp.created_at,
  updated_at: apiOpp.updated_at,
  generated_by: apiOpp.generated_by,
  generation_method: apiOpp.generation_method,
  agent_analysis: apiOpp.agent_analysis,
});

export const opportunitiesService = {
  // Get all opportunities with optional filters
  getOpportunities: async (params?: SearchParams): Promise<PaginatedResponse<Opportunity>> => {
    const response = await apiClient.get('/opportunities/', { params });
    const data = response.data;
    
    // Transform API response to match frontend interface
    return {
      items: data.items.map(transformOpportunity),
      total: data.total_count,
      page: data.pagination.page,
      size: data.pagination.page_size,
      pages: data.pagination.total_pages,
    };
  },

  // Get a single opportunity by ID
  getOpportunity: async (id: string): Promise<Opportunity> => {
    const response = await apiClient.get(`/opportunities/${id}`);
    return transformOpportunity(response.data);
  },

  // Search opportunities
  searchOpportunities: async (params: SearchParams): Promise<PaginatedResponse<Opportunity>> => {
    try {
      // Backend expects POST request with search criteria in body
      const searchBody = {
        query: params.query || '',
        filters: params.filters || {},
        page: params.page || 1,
        size: params.size || 12,
        sort_by: params.sort_by || 'validation_score',
        sort_order: params.sort_order || 'desc'
      };
      
      const response = await apiClient.post('/opportunities/search', searchBody);
      const data = response.data;
      
      // Transform API response to match frontend interface
      return {
        items: data.items.map(transformOpportunity),
        total: data.total_count,
        page: data.pagination.page,
        size: data.pagination.page_size,
        pages: data.pagination.total_pages,
      };
    } catch (error) {
      // If search endpoint fails, fallback to main endpoint with filters
      console.warn('Search endpoint unavailable, using fallback:', error);
      return opportunitiesService.getOpportunities(params);
    }
  },

  // Get recommendations for current user
  getRecommendations: async (limit?: number): Promise<Opportunity[]> => {
    try {
      // Backend expects POST request with recommendation criteria (requires auth)
      const recommendationBody = {
        limit: limit || 10,
        include_preferences: true,
        include_interactions: true
      };
      
      const response = await apiClient.post('/opportunities/recommendations', recommendationBody);
      return response.data.map(transformOpportunity);
    } catch (error) {
      // If authentication fails or endpoint unavailable, fallback to main endpoint
      console.warn('Recommendations endpoint unavailable, using fallback:', error);
      const response = await apiClient.get('/opportunities/', {
        params: { 
          size: limit || 10,
          sort_by: 'validation_score',
          sort_order: 'desc'
        }
      });
      const data = response.data;
      return data.items.map(transformOpportunity);
    }
  },

  // Get trending opportunities (using main endpoint with recent sorting)
  getTrending: async (limit?: number): Promise<Opportunity[]> => {
    // Since /trending endpoint doesn't exist, use main endpoint with recent sorting
    const response = await apiClient.get('/opportunities/', {
      params: { 
        size: limit || 10,
        sort_by: 'created_at',
        sort_order: 'desc'
      }
    });
    const data = response.data;
    return data.items.map(transformOpportunity);
  },

  // Create a new opportunity (if user has permission)
  createOpportunity: async (data: Partial<Opportunity>): Promise<Opportunity> => {
    const response = await apiClient.post('/opportunities/', data);
    return transformOpportunity(response.data);
  },

  // Update an opportunity (if user has permission)
  updateOpportunity: async (id: string, data: Partial<Opportunity>): Promise<Opportunity> => {
    const response = await apiClient.put(`/opportunities/${id}`, data);
    return transformOpportunity(response.data);
  },

  // Delete an opportunity (if user has permission)
  deleteOpportunity: async (id: string): Promise<void> => {
    await apiClient.delete(`/opportunities/${id}`);
  },
};