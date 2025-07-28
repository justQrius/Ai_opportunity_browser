import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Users, 
  Shield, 
  CheckCircle, 
  XCircle,
  AlertCircle,
  Star,
  Award,
  Crown,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ValidationBadgeProps {
  score: number;
  validationCount?: number;
  className?: string;
  variant?: 'default' | 'detailed' | 'compact' | 'interactive';
  showTrend?: boolean;
  trend?: 'up' | 'down' | 'stable';
  showCount?: boolean;
  showLabel?: boolean;
  onClick?: () => void;
  animated?: boolean;
}

interface ValidationScoreProps {
  score: number;
  validationCount?: number;
  confidence?: number;
  className?: string;
  showDetails?: boolean;
  showProgress?: boolean;
}

interface ValidationStatusProps {
  status: 'pending' | 'validated' | 'disputed' | 'verified';
  className?: string;
  showLabel?: boolean;
}

interface ExpertValidationProps {
  expertLevel: 'novice' | 'intermediate' | 'expert' | 'authority';
  validationCount: number;
  averageScore: number;
  className?: string;
}

// Utility functions
const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-green-600 dark:text-green-400';
  if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
  if (score >= 40) return 'text-orange-600 dark:text-orange-400';
  return 'text-red-600 dark:text-red-400';
};

const getScoreBadgeVariant = (score: number) => {
  if (score >= 80) return 'default';
  if (score >= 60) return 'secondary';
  if (score >= 40) return 'outline';
  return 'destructive';
};

const getScoreLabel = (score: number) => {
  if (score >= 90) return 'Excellent';
  if (score >= 80) return 'Very Good';
  if (score >= 70) return 'Good';
  if (score >= 60) return 'Fair';
  if (score >= 40) return 'Poor';
  return 'Very Poor';
};

const getTrendIcon = (trend?: 'up' | 'down' | 'stable') => {
  switch (trend) {
    case 'up':
      return <TrendingUp className="w-3 h-3 text-green-500" />;
    case 'down':
      return <TrendingDown className="w-3 h-3 text-red-500" />;
    case 'stable':
      return <Minus className="w-3 h-3 text-gray-500" />;
    default:
      return null;
  }
};

// Basic validation badge
export function ValidationBadge({
  score,
  validationCount = 0,
  className,
  variant = 'default',
  showTrend = false,
  trend,
  showCount = true,
  showLabel = false,
  onClick,
  animated = false
}: ValidationBadgeProps) {
  const badgeVariant = getScoreBadgeVariant(score);
  const scoreColor = getScoreColor(score);
  const trendIcon = showTrend ? getTrendIcon(trend) : null;

  if (variant === 'compact') {
    return (
      <Badge 
        variant={badgeVariant}
        className={cn(
          'gap-1 text-xs cursor-default',
          onClick && 'cursor-pointer hover:opacity-80',
          animated && 'transition-all duration-200 hover:scale-105',
          className
        )}
        onClick={onClick}
      >
        <Shield className="w-3 h-3" />
        {score}%
        {showCount && validationCount > 0 && (
          <span className="opacity-75">({validationCount})</span>
        )}
        {trendIcon}
      </Badge>
    );
  }

  if (variant === 'detailed') {
    return (
      <Card 
        className={cn(
          'inline-block',
          onClick && 'cursor-pointer hover:shadow-md transition-shadow',
          className
        )}
        onClick={onClick}
      >
        <CardContent className="p-3">
          <div className="flex items-center gap-2">
            <div className="text-center">
              <div className={cn('text-2xl font-bold', scoreColor)}>
                {score}%
              </div>
              {showLabel && (
                <div className="text-xs text-muted-foreground">
                  {getScoreLabel(score)}
                </div>
              )}
            </div>
            
            {showCount && (
              <>
                <div className="h-8 w-px bg-border" />
                <div className="text-center">
                  <div className="flex items-center gap-1 text-sm font-medium">
                    <Users className="w-3 h-3" />
                    {validationCount}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    validations
                  </div>
                </div>
              </>
            )}
            
            {trendIcon && (
              <>
                <div className="h-8 w-px bg-border" />
                <div className="flex flex-col items-center">
                  {trendIcon}
                  <span className="text-xs text-muted-foreground capitalize">
                    {trend}
                  </span>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variant === 'interactive') {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={onClick}
        className={cn(
          'gap-2 h-8',
          animated && 'transition-all duration-200 hover:scale-105',
          className
        )}
      >
        <Shield className="w-4 h-4" />
        <span className={scoreColor}>{score}%</span>
        {showCount && validationCount > 0 && (
          <Badge variant="secondary" className="h-4 px-1 text-xs">
            {validationCount}
          </Badge>
        )}
        {trendIcon}
      </Button>
    );
  }

  // Default variant
  return (
    <div 
      className={cn(
        'inline-flex items-center gap-2',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      <Badge 
        variant={badgeVariant}
        className={cn(
          'gap-1',
          animated && 'transition-all duration-200 hover:scale-105'
        )}
      >
        <Shield className="w-3 h-3" />
        {score}%
      </Badge>
      
      {showCount && validationCount > 0 && (
        <span className="text-xs text-muted-foreground">
          ({validationCount} {validationCount === 1 ? 'validation' : 'validations'})
        </span>
      )}
      
      {showLabel && (
        <span className="text-xs text-muted-foreground">
          {getScoreLabel(score)}
        </span>
      )}
      
      {trendIcon}
    </div>
  );
}

// Detailed validation score with progress bar
export function ValidationScore({
  score,
  validationCount = 0,
  confidence = 0,
  className,
  showDetails = true,
  showProgress = true
}: ValidationScoreProps) {
  const scoreColor = getScoreColor(score);
  
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">Validation Score</span>
        </div>
        <div className={cn('text-lg font-bold', scoreColor)}>
          {score}%
        </div>
      </div>
      
      {showProgress && (
        <div className="space-y-1">
          <div className="w-full bg-muted rounded-full h-2">
            <div 
              className={cn(
                'h-2 rounded-full transition-all duration-500',
                score >= 80 ? 'bg-green-500' :
                score >= 60 ? 'bg-yellow-500' :
                score >= 40 ? 'bg-orange-500' : 'bg-red-500'
              )}
              style={{ width: `${score}%` }}
            />
          </div>
          <div className="text-xs text-muted-foreground">
            {getScoreLabel(score)}
          </div>
        </div>
      )}
      
      {showDetails && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{validationCount} validations</span>
          {confidence > 0 && (
            <span>{confidence}% confidence</span>
          )}
        </div>
      )}
    </div>
  );
}

// Validation status indicator
export function ValidationStatus({
  status,
  className,
  showLabel = true
}: ValidationStatusProps) {
  const statusConfig = {
    pending: {
      icon: AlertCircle,
      color: 'text-yellow-600 dark:text-yellow-400',
      bgColor: 'bg-yellow-100 dark:bg-yellow-900/20',
      label: 'Pending Validation'
    },
    validated: {
      icon: CheckCircle,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-100 dark:bg-green-900/20',
      label: 'Community Validated'
    },
    disputed: {
      icon: XCircle,
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-100 dark:bg-red-900/20',
      label: 'Disputed'
    },
    verified: {
      icon: Award,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900/20',
      label: 'Expert Verified'
    }
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={cn(
      'inline-flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium',
      config.bgColor,
      config.color,
      className
    )}>
      <Icon className="w-3 h-3" />
      {showLabel && config.label}
    </div>
  );
}

// Expert validation indicator
export function ExpertValidation({
  expertLevel,
  validationCount,
  averageScore,
  className
}: ExpertValidationProps) {
  const expertConfig = {
    novice: {
      icon: Users,
      color: 'text-gray-600',
      bgColor: 'bg-gray-100',
      label: 'Community',
      minValidations: 5
    },
    intermediate: {
      icon: Star,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      label: 'Experienced',
      minValidations: 10
    },
    expert: {
      icon: Award,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      label: 'Expert',
      minValidations: 15
    },
    authority: {
      icon: Crown,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
      label: 'Authority',
      minValidations: 25
    }
  };

  const config = expertConfig[expertLevel];
  const Icon = config.icon;
  const meetsThreshold = validationCount >= config.minValidations;

  return (
    <div className={cn(
      'inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border',
      meetsThreshold ? `${config.bgColor} ${config.color} border-current/20` : 'bg-muted text-muted-foreground border-muted',
      className
    )}>
      <Icon className="w-3 h-3" />
      <span>{config.label} Validated</span>
      {meetsThreshold && (
        <>
          <div className="w-px h-3 bg-current/30" />
          <div className="flex items-center gap-1">
            <Zap className="w-3 h-3" />
            <span>{averageScore}%</span>
          </div>
        </>
      )}
      <Badge variant="secondary" className="h-4 px-1 text-xs ml-1">
        {validationCount}
      </Badge>
    </div>
  );
}

export default ValidationBadge;