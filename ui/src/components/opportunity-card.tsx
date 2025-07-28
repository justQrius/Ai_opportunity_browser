import React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { 
  TrendingUp, 
  Brain, 
  Users, 
  DollarSign, 
  Clock,
  Star,
  BookmarkPlus,
  ExternalLink 
} from 'lucide-react';
import { Opportunity } from '@/types';
import { cn } from '@/lib/utils';

interface OpportunityCardProps {
  opportunity: Opportunity;
  className?: string;
  variant?: 'default' | 'compact' | 'featured' | 'trending';
  showActions?: boolean;
  showTrendingBadge?: boolean;
  trendingRank?: number;
  onBookmark?: (opportunityId: string) => void;
  onValidate?: (opportunityId: string) => void;
}

const complexityColors = {
  LOW: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  MEDIUM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  HIGH: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
};

const getValidationColor = (score: number) => {
  if (score >= 80) return 'text-green-600 dark:text-green-400';
  if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
};

const formatMarketSize = (size: number) => {
  if (size >= 1000000000) return `$${(size / 1000000000).toFixed(1)}B`;
  if (size >= 1000000) return `$${(size / 1000000).toFixed(1)}M`;
  if (size >= 1000) return `$${(size / 1000).toFixed(1)}K`;
  return `$${size}`;
};

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  });
};

export function OpportunityCard({ 
  opportunity, 
  className,
  variant = 'default',
  showActions = true,
  showTrendingBadge = false,
  trendingRank,
  onBookmark,
  onValidate 
}: OpportunityCardProps) {
  const isCompact = variant === 'compact';
  const isFeatured = variant === 'featured';
  const isTrending = variant === 'trending';

  return (
    <Card className={cn(
      'group transition-all duration-200 hover:shadow-lg hover:scale-[1.02]',
      isFeatured && 'border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent',
      className
    )}>
      <CardHeader className={cn('pb-3', isCompact && 'pb-2')}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              {isFeatured && (
                <Badge variant="secondary" className="gap-1">
                  <Star className="w-3 h-3" />
                  Featured
                </Badge>
              )}
              {(isTrending || showTrendingBadge) && trendingRank && (
                <Badge variant="secondary" className="gap-1 bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300">
                  <TrendingUp className="w-3 h-3" />
                  #{trendingRank}
                </Badge>
              )}
              <Badge variant="outline" className="text-xs">
                {opportunity.industry}
              </Badge>
              <Badge 
                className={cn('text-xs', complexityColors[opportunity.implementation_complexity])}
              >
                {opportunity.implementation_complexity}
              </Badge>
            </div>
            
            <CardTitle className={cn(
              'text-lg leading-tight group-hover:text-primary transition-colors',
              isCompact && 'text-base'
            )}>
              <Link 
                href={`/opportunities/${opportunity.id}`}
                className="hover:underline"
              >
                {opportunity.title}
              </Link>
            </CardTitle>
            
            {!isCompact && (
              <CardDescription className="line-clamp-2 mt-2">
                {opportunity.description}
              </CardDescription>
            )}
          </div>
          
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="bg-primary/10 text-primary text-xs">
              <Brain className="w-4 h-4" />
            </AvatarFallback>
          </Avatar>
        </div>
      </CardHeader>

      <CardContent className={cn('pt-0', isCompact && 'py-2')}>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Validation Score</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={cn('text-lg font-semibold', getValidationColor(opportunity.validation_score))}>
                {opportunity.validation_score}%
              </div>
              <div className="text-xs text-muted-foreground">
                ({opportunity.validation_count} votes)
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="w-4 h-4 text-muted-foreground" />
              <span className="text-muted-foreground">Market Size</span>
            </div>
            <div className="text-lg font-semibold text-green-600 dark:text-green-400">
              {formatMarketSize(opportunity.market_size_estimate)}
            </div>
          </div>
        </div>

        {!isCompact && (
          <>
            <div className="flex items-center justify-between text-sm text-muted-foreground mb-4">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4" />
                <span>AI Feasibility: {opportunity.ai_feasibility_score}%</span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>{formatDate(opportunity.created_at)}</span>
              </div>
            </div>

            <Separator className="mb-4" />
          </>
        )}

        {showActions && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-xs gap-1">
                <Brain className="w-3 h-3" />
                {opportunity.ai_solution_type}
              </Badge>
            </div>
            
            <div className="flex items-center gap-2">
              {onBookmark && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.preventDefault();
                    onBookmark(opportunity.id);
                  }}
                  className="h-8 w-8 p-0 hover:bg-primary/10"
                >
                  <BookmarkPlus className="w-4 h-4" />
                </Button>
              )}
              
              {onValidate && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.preventDefault();
                    onValidate(opportunity.id);
                  }}
                  className="text-xs"
                >
                  <Users className="w-3 h-3 mr-1" />
                  Validate
                </Button>
              )}
              
              <Button variant="ghost" size="sm" asChild className="h-8 w-8 p-0">
                <Link href={`/opportunities/${opportunity.id}`}>
                  <ExternalLink className="w-4 h-4" />
                </Link>
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default OpportunityCard;