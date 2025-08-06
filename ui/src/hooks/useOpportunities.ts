import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  opportunitiesService, 
  Opportunity, 
  SearchParams 
} from '@/services/opportunities';

// Query keys
export const opportunityKeys = {
  all: ['opportunities'] as const,
  lists: () => [...opportunityKeys.all, 'list'] as const,
  list: (params?: SearchParams) => [...opportunityKeys.lists(), params] as const,
  details: () => [...opportunityKeys.all, 'detail'] as const,
  detail: (id: string) => [...opportunityKeys.details(), id] as const,
  search: (params: SearchParams) => [...opportunityKeys.all, 'search', params] as const,
  recommendations: () => [...opportunityKeys.all, 'recommendations'] as const,
  trending: () => [...opportunityKeys.all, 'trending'] as const,
};

// Get opportunities with filters
export const useOpportunities = (params?: SearchParams) => {
  return useQuery({
    queryKey: [...opportunityKeys.list(params), 'v2'], // Force cache invalidation
    queryFn: () => opportunitiesService.getOpportunities(params),
    staleTime: 0, // Disable caching temporarily
    cacheTime: 0, // Disable cache storage
  });
};

// Get single opportunity
export const useOpportunity = (id: string, enabled = true) => {
  return useQuery({
    queryKey: opportunityKeys.detail(id),
    queryFn: () => opportunitiesService.getOpportunity(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes for detail data
  });
};

// Search opportunities
export const useSearchOpportunities = (params: SearchParams) => {
  return useQuery({
    queryKey: opportunityKeys.search(params),
    queryFn: () => opportunitiesService.searchOpportunities(params),
    enabled: !!(params.query || Object.keys(params.filters || {}).length > 0),
    staleTime: 1 * 60 * 1000, // 1 minute for search results
  });
};

// Get recommendations
export const useRecommendations = (limit?: number) => {
  return useQuery({
    queryKey: opportunityKeys.recommendations(),
    queryFn: () => opportunitiesService.getRecommendations(limit),
    staleTime: 10 * 60 * 1000, // 10 minutes for recommendations
  });
};

// Get trending opportunities
export const useTrending = (limit?: number) => {
  return useQuery({
    queryKey: opportunityKeys.trending(),
    queryFn: () => opportunitiesService.getTrending(limit),
    staleTime: 5 * 60 * 1000, // 5 minutes for trending
  });
};

// Create opportunity mutation
export const useCreateOpportunity = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: opportunitiesService.createOpportunity,
    onSuccess: () => {
      // Invalidate and refetch opportunities list
      queryClient.invalidateQueries({ queryKey: opportunityKeys.lists() });
    },
  });
};

// Update opportunity mutation
export const useUpdateOpportunity = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Opportunity> }) =>
      opportunitiesService.updateOpportunity(id, data),
    onSuccess: (data, variables) => {
      // Update the opportunity in cache
      queryClient.setQueryData(opportunityKeys.detail(variables.id), data);
      // Invalidate lists to ensure consistency
      queryClient.invalidateQueries({ queryKey: opportunityKeys.lists() });
    },
  });
};

// Delete opportunity mutation
export const useDeleteOpportunity = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: opportunitiesService.deleteOpportunity,
    onSuccess: (_, deletedId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: opportunityKeys.detail(deletedId) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: opportunityKeys.lists() });
    },
  });
};