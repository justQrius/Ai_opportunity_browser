import React from 'react';
import { OpportunityCard } from './opportunity-card';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { 
  ChevronLeft, 
  ChevronRight, 
  Grid3X3, 
  List,
  Filter,
  SortAsc,
  Search
} from 'lucide-react';
import { Opportunity, SortField, SortOrder } from '@/types';
import { cn } from '@/lib/utils';

interface OpportunityListProps {
  opportunities: Opportunity[];
  loading?: boolean;
  error?: string | null;
  className?: string;
  
  // Pagination
  currentPage?: number;
  totalPages?: number;
  pageSize?: number;
  totalItems?: number;
  onPageChange?: (page: number) => void;
  
  // View options
  viewMode?: 'grid' | 'list';
  onViewModeChange?: (mode: 'grid' | 'list') => void;
  
  // Sorting
  sortField?: SortField;
  sortOrder?: SortOrder;
  onSortChange?: (field: SortField, order: SortOrder) => void;
  
  // Actions
  onBookmark?: (opportunityId: string) => void;
  onValidate?: (opportunityId: string) => void;
  onFilterToggle?: () => void;
  
  // Empty state
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
}

const LoadingSkeleton = ({ count = 6 }: { count?: number }) => (
  <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
    {Array.from({ length: count }).map((_, i) => (
      <Card key={i} className="animate-pulse">
        <CardContent className="p-6">
          <div className="space-y-4">
            <div className="flex gap-2">
              <div className="h-4 bg-muted rounded w-16"></div>
              <div className="h-4 bg-muted rounded w-12"></div>
            </div>
            <div className="h-6 bg-muted rounded w-3/4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded"></div>
              <div className="h-4 bg-muted rounded w-2/3"></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="h-3 bg-muted rounded w-1/2"></div>
                <div className="h-5 bg-muted rounded w-1/3"></div>
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-muted rounded w-1/2"></div>
                <div className="h-5 bg-muted rounded w-1/3"></div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

const EmptyState = ({ 
  title = "No opportunities found", 
  description = "Try adjusting your search criteria or filters.",
  action 
}: { 
  title?: string; 
  description?: string; 
  action?: React.ReactNode; 
}) => (
  <Card className="p-12 text-center">
    <CardContent className="space-y-4">
      <div className="mx-auto w-16 h-16 bg-muted rounded-full flex items-center justify-center">
        <Search className="w-8 h-8 text-muted-foreground" />
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-medium">{title}</h3>
        <p className="text-muted-foreground">{description}</p>
      </div>
      {action && <div className="pt-2">{action}</div>}
    </CardContent>
  </Card>
);

const ErrorState = ({ error }: { error: string }) => (
  <Card className="p-12 text-center border-destructive/20 bg-destructive/5">
    <CardContent className="space-y-4">
      <div className="mx-auto w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center">
        <Search className="w-8 h-8 text-destructive" />
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-medium text-destructive">Error loading opportunities</h3>
        <p className="text-muted-foreground">{error}</p>
      </div>
    </CardContent>
  </Card>
);

const Pagination = ({ 
  currentPage = 1, 
  totalPages = 1, 
  onPageChange 
}: { 
  currentPage?: number; 
  totalPages?: number; 
  onPageChange?: (page: number) => void; 
}) => {
  if (totalPages <= 1) return null;

  const getVisiblePages = () => {
    const delta = 2;
    const range = [];
    const rangeWithDots = [];

    for (let i = Math.max(2, currentPage - delta); 
         i <= Math.min(totalPages - 1, currentPage + delta); 
         i++) {
      range.push(i);
    }

    if (currentPage - delta > 2) {
      rangeWithDots.push(1, '...');
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (currentPage + delta < totalPages - 1) {
      rangeWithDots.push('...', totalPages);
    } else {
      if (totalPages > 1) rangeWithDots.push(totalPages);
    }

    return rangeWithDots;
  };

  return (
    <div className="flex items-center justify-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange?.(currentPage - 1)}
        disabled={currentPage <= 1}
        className="gap-1"
      >
        <ChevronLeft className="w-4 h-4" />
        Previous
      </Button>
      
      <div className="flex items-center gap-1">
        {getVisiblePages().map((page, index) => (
          <Button
            key={index}
            variant={page === currentPage ? "default" : "outline"}
            size="sm"
            onClick={() => typeof page === 'number' && onPageChange?.(page)}
            disabled={typeof page !== 'number'}
            className="w-8 h-8 p-0"
          >
            {page}
          </Button>
        ))}
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange?.(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="gap-1"
      >
        Next
        <ChevronRight className="w-4 h-4" />
      </Button>
    </div>
  );
};

export function OpportunityList({
  opportunities,
  loading = false,
  error = null,
  className,
  currentPage = 1,
  totalPages = 1,
  pageSize = 12,
  totalItems = 0,
  onPageChange,
  viewMode = 'grid',
  onViewModeChange,
  sortField,
  sortOrder,
  onSortChange,
  onBookmark,
  onValidate,
  onFilterToggle,
  emptyTitle,
  emptyDescription,
  emptyAction
}: OpportunityListProps) {
  
  if (loading) {
    return (
      <div className={cn('space-y-6', className)}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('space-y-6', className)}>
        <ErrorState error={error} />
      </div>
    );
  }

  if (opportunities.length === 0) {
    return (
      <div className={cn('space-y-6', className)}>
        <EmptyState 
          title={emptyTitle}
          description={emptyDescription}
          action={emptyAction}
        />
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground">
            {totalItems > 0 && (
              <>
                Showing {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, totalItems)} of {totalItems} opportunities
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Toggle */}
          {onFilterToggle && (
            <Button variant="outline" size="sm" onClick={onFilterToggle} className="gap-2">
              <Filter className="w-4 h-4" />
              Filters
            </Button>
          )}

          {/* Sort Options */}
          {onSortChange && (
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSortChange('validation_score', sortOrder === 'desc' ? 'asc' : 'desc')}
                className={cn(
                  'gap-1',
                  sortField === 'validation_score' && 'bg-muted'
                )}
              >
                <SortAsc className="w-4 h-4" />
                Score
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSortChange('created_at', sortOrder === 'desc' ? 'asc' : 'desc')}
                className={cn(
                  'gap-1',
                  sortField === 'created_at' && 'bg-muted'
                )}
              >
                <SortAsc className="w-4 h-4" />
                Date
              </Button>
            </div>
          )}

          {/* View Mode Toggle */}
          {onViewModeChange && (
            <div className="flex items-center border rounded-md p-1">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => onViewModeChange('grid')}
                className="h-7 w-7 p-0"
              >
                <Grid3X3 className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => onViewModeChange('list')}
                className="h-7 w-7 p-0"
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Opportunities Grid/List */}
      <div className={cn(
        'grid gap-4',
        viewMode === 'grid' ? 
          'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 
          'grid-cols-1'
      )}>
        {opportunities.map((opportunity) => (
          <OpportunityCard
            key={opportunity.id}
            opportunity={opportunity}
            variant={viewMode === 'list' ? 'compact' : 'default'}
            onBookmark={onBookmark}
            onValidate={onValidate}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center pt-4">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={onPageChange}
          />
        </div>
      )}
    </div>
  );
}

export default OpportunityList;