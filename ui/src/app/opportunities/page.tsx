'use client';

import Link from 'next/link';
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  OpportunityList, 
  SearchBar, 
  FilterPanel, 
  LoadingSpinner 
} from '@/components';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  TrendingUp,
  Users,
  Star,
  BarChart3,
  Sparkles
} from 'lucide-react';
import { useOpportunities } from '@/hooks/useOpportunities';
import { useOpportunityStore } from '@/stores/opportunityStore';
import { cn } from '@/lib/utils';
import type { OpportunityFilters, SortField, SortOrder } from '@/types';

export default function OpportunitiesPage() {
  const quickFilters = [
    { label: 'High Impact', filters: { min_impact_score: 4 } },
    { label: 'Low Complexity', filters: { implementation_complexity: 'LOW' } },
    { label: 'Recently Added', filters: { created_at: 'desc' } },
    { label: 'Top Validated', filters: { validation_score: 'desc' } },
  ];

    const searchParams = useSearchParams();
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [sortField, setSortField] = useState<SortField>('validation_score');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  
  // Store state
  const {
    filters, 
    loading, 
    error, 
    searchQuery,
    setFilters, 
    setSearchQuery 
  } = useOpportunityStore();

  // API hook
  const {
    data: opportunityData,
    isLoading,
    error: apiError,
    refetch
  } = useOpportunities({
    query: searchQuery,
    filters,
    sort_by: sortField,
    sort_order: sortOrder,
    page: 1,
    size: 12
  });

  // Debug: Test direct API call
  useEffect(() => {
    const testAPI = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/opportunities/');
        const data = await response.json();
        console.log('Direct API test:', data);
      } catch (error) {
        console.error('Direct API test failed:', error);
      }
    };
    testAPI();
  }, []);

  // Debug: Log React Query results
  useEffect(() => {
    console.log('React Query results:', {
      data: opportunityData,
      isLoading,
      error: apiError
    });
  }, [opportunityData, isLoading, apiError]);

  // Initialize from URL params
  useEffect(() => {
    const query = searchParams.get('q');
    const industry = searchParams.get('industry');
    const complexity = searchParams.get('complexity');
    
    if (query) setSearchQuery(query);
    
    const urlFilters: OpportunityFilters = {};
    if (industry) urlFilters.industry = industry;
    if (complexity) urlFilters.implementation_complexity = complexity as 'LOW' | 'MEDIUM' | 'HIGH';
    
    if (Object.keys(urlFilters).length > 0) {
      setFilters(urlFilters);
    }
  }, [searchParams, setSearchQuery, setFilters]);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleFiltersChange = (newFilters: OpportunityFilters) => {
    setFilters(newFilters);
  };

  const handleQuickFilter = (quickFilter: typeof quickFilters[0]) => {
    setFilters({ ...filters, ...quickFilter.filters });
  };

  const handleSortChange = (field: SortField, order: SortOrder) => {
    setSortField(field);
    setSortOrder(order);
  };

  const handleBookmark = (opportunityId: string) => {
    // TODO: Implement bookmark functionality
    console.log('Bookmark opportunity:', opportunityId);
  };

  const handleValidate = (opportunityId: string) => {
    // TODO: Implement validation functionality
    console.log('Validate opportunity:', opportunityId);
  };

  const clearAllFilters = () => {
    setFilters({});
    setSearchQuery('');
  };

    const activeFilterCount = Object.keys(filters).length + (searchQuery ? 1 : 0);
  const isDataLoading = loading || isLoading;
  const displayError = error || apiError?.message;
  const displayOpportunities = opportunityData?.items || [];

  // Generate trending topics from actual opportunities data
  const trendingTopics = React.useMemo(() => {
    const trendingTopicsFallback = [
      { name: 'AI-Powered Chatbots', count: 120, trend: '+15%' },
      { name: 'Predictive Analytics', count: 95, trend: '+8%' },
      { name: 'Content Generation', count: 80, trend: '+22%' },
      { name: 'Process Automation', count: 75, trend: '-5%' },
      { name: 'Personalized Recommendations', count: 60, trend: '+12%' },
    ];
    
    if (!opportunityData?.items?.length) {
      return trendingTopicsFallback;
    }
    
    // Extract and count AI solution types from real data
    const solutionCounts: Record<string, number> = {};
    opportunityData.items.forEach(opp => {
      const solution = opp.ai_solution_type;
      solutionCounts[solution] = (solutionCounts[solution] || 0) + 1;
    });
    
    return Object.entries(solutionCounts)
      .map(([name, count]) => ({
        name,
        count,
        trend: `+${Math.floor(Math.random() * 50) + 10}%` // Random trend for now
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [opportunityData?.items]);

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                AI Opportunities
              </h1>
              <p className="text-muted-foreground">
                Discover validated AI opportunities from our community
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              <Button asChild>
                <Link href="/opportunities/new">Generate New Opportunity</Link>
              </Button>
              <Badge variant="secondary" className="gap-1">
                <Sparkles className="w-3 h-3" />
                {displayOpportunities.length} opportunities
              </Badge>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-green-600" />
                  <div>
                    <div className="text-2xl font-bold">{opportunityData?.total || displayOpportunities.length}</div>
                    <div className="text-xs text-muted-foreground">Total Opportunities</div>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-blue-600" />
                  <div>
                    <div className="text-2xl font-bold">{displayOpportunities.reduce((sum, opp) => sum + (opp.validation_count || 0), 0)}</div>
                    <div className="text-xs text-muted-foreground">Community Validations</div>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Star className="w-4 h-4 text-yellow-600" />
                  <div>
                    <div className="text-2xl font-bold">{displayOpportunities.filter(opp => opp.validation_score >= 80).length}</div>
                    <div className="text-xs text-muted-foreground">High Validation Score</div>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-purple-600" />
                  <div>
                    <div className="text-2xl font-bold">
                      ${(displayOpportunities.reduce((sum, opp) => sum + (opp.market_size_estimate || 0), 0) / 1000000).toFixed(1)}M
                    </div>
                    <div className="text-xs text-muted-foreground">Total Market Size</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Search and Quick Filters */}
        <div className="space-y-4">
          <SearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            onSearch={handleSearch}
            onClear={() => setSearchQuery('')}
            placeholder="Search for AI opportunities..."
            showFilters={true}
            filterCount={activeFilterCount}
            onFilterClick={() => setShowFilters(!showFilters)}
            className="max-w-2xl"
          />

          {/* Quick Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">Quick filters:</span>
            {quickFilters.map((filter) => (
              <Button
                key={filter.label}
                variant="outline"
                size="sm"
                onClick={() => handleQuickFilter(filter)}
                className="h-7 text-xs"
              >
                {filter.label}
              </Button>
            ))}
            {activeFilterCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="h-7 text-xs text-muted-foreground hover:text-foreground"
              >
                Clear all
              </Button>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Filter Panel */}
            <div className={cn(
              'lg:block',
              showFilters ? 'block' : 'hidden'
            )}>
              <FilterPanel
                filters={filters}
                onFiltersChange={handleFiltersChange}
                onReset={clearAllFilters}
                variant="panel"
                collapsible={true}
                activeFilterCount={activeFilterCount}
              />
            </div>

            {/* Trending Topics */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  Trending Topics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {trendingTopics.map((topic) => (
                  <div key={topic.name} className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{topic.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {topic.count} opportunities
                      </div>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {topic.trend}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-3">
            {isDataLoading ? (
              <LoadingSpinner 
                text="Loading opportunities..." 
                className="py-12"
                variant="ai-themed"
                size="lg"
              />
            ) : displayError ? (
              <Card className="p-12 text-center border-destructive/20 bg-destructive/5">
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-lg font-medium text-destructive">
                      Failed to load opportunities
                    </div>
                    <p className="text-muted-foreground">{displayError}</p>
                    <Button onClick={() => refetch()} variant="outline">
                      Try Again
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <OpportunityList
                opportunities={displayOpportunities}
                loading={isDataLoading}
                error={displayError}
                currentPage={opportunityData?.page || 1}
                totalPages={opportunityData?.pages || 1}
                totalItems={opportunityData?.total || 0}
                pageSize={opportunityData?.size || 12}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                sortField={sortField}
                sortOrder={sortOrder}
                onSortChange={handleSortChange}
                onBookmark={handleBookmark}
                onValidate={handleValidate}
                onFilterToggle={() => setShowFilters(!showFilters)}
                emptyTitle="No opportunities found"
                emptyDescription="Try adjusting your search criteria or filters to find more opportunities."
                emptyAction={
                  <Button onClick={clearAllFilters} variant="outline">
                    Clear Filters
                  </Button>
                }
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}