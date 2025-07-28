'use client';

import React, { useState } from 'react';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  OpportunityCard,
  LoadingSpinner 
} from '@/components';
import { 
  TrendingUp,
  Brain,
  Zap,
  BarChart3,
  Users,
  Clock,
  Sparkles,
  Filter,
  ArrowUp,
  ArrowDown,
  Minus,
  Calendar,
  Globe
} from 'lucide-react';
import { useTrending } from '@/hooks/useOpportunities';
import { cn } from '@/lib/utils';

interface TrendingPageProps {}

// Mock trending data to supplement API data
const trendingTechnologies = [
  { 
    name: 'Generative AI', 
    growth: '+127%', 
    opportunities: 45,
    trend: 'up',
    description: 'AI systems that generate content, code, and creative works'
  },
  { 
    name: 'Computer Vision', 
    growth: '+89%', 
    opportunities: 34,
    trend: 'up',
    description: 'AI that interprets and understands visual information'
  },
  { 
    name: 'Natural Language Processing', 
    growth: '+76%', 
    opportunities: 28,
    trend: 'up',
    description: 'AI for understanding and generating human language'
  },
  { 
    name: 'Edge AI', 
    growth: '+64%', 
    opportunities: 23,
    trend: 'up',
    description: 'AI processing directly on devices and edge computing'
  },
  { 
    name: 'Autonomous Systems', 
    growth: '+52%', 
    opportunities: 19,
    trend: 'up',
    description: 'Self-operating AI systems for robotics and automation'
  },
  { 
    name: 'AI Ethics & Safety', 
    growth: '+41%', 
    opportunities: 15,
    trend: 'up',
    description: 'Responsible AI development and governance frameworks'
  },
];

const marketIndicators = [
  {
    label: 'Global AI Market Size',
    value: '$515.31B',
    change: '+21.4%',
    trend: 'up',
    period: '2024'
  },
  {
    label: 'AI Startup Funding',
    value: '$65.2B',
    change: '+14.8%',
    trend: 'up',
    period: 'YTD 2024'
  },
  {
    label: 'AI Job Postings',
    value: '2.3M',
    change: '+31.2%',
    trend: 'up',
    period: 'Q4 2024'
  },
  {
    label: 'Patents Filed',
    value: '89,400',
    change: '+18.7%',
    trend: 'up',
    period: '2024'
  }
];

const hotIndustries = [
  { name: 'Healthcare', score: 95, opportunities: 67, growth: '+89%' },
  { name: 'Financial Services', score: 92, opportunities: 54, growth: '+76%' },
  { name: 'Retail & E-commerce', score: 88, opportunities: 41, growth: '+67%' },
  { name: 'Manufacturing', score: 85, opportunities: 38, growth: '+54%' },
  { name: 'Education', score: 82, opportunities: 29, growth: '+45%' },
  { name: 'Transportation', score: 79, opportunities: 24, growth: '+38%' }
];

export default function TrendingPage({}: TrendingPageProps) {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | '90d'>('7d');
  const [sortBy, setSortBy] = useState<'growth' | 'opportunities' | 'score'>('growth');
  
  // Fetch trending opportunities from API
  const { 
    data: trendingOpportunities, 
    isLoading, 
    error 
  } = useTrending(12);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <ArrowUp className="w-3 h-3 text-green-600" />;
      case 'down': return <ArrowDown className="w-3 h-3 text-red-600" />;
      default: return <Minus className="w-3 h-3 text-muted-foreground" />;
    }
  };

  const formatTimeRange = (range: string) => {
    switch (range) {
      case '24h': return 'Last 24 Hours';
      case '7d': return 'Last 7 Days';
      case '30d': return 'Last 30 Days';
      case '90d': return 'Last 90 Days';
      default: return 'Last 7 Days';
    }
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                <TrendingUp className="w-8 h-8 text-primary" />
                Trending AI Opportunities
              </h1>
              <p className="text-muted-foreground">
                Discover the hottest AI trends and emerging opportunities in real-time
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="gap-1">
                <Sparkles className="w-3 h-3" />
                {trendingOpportunities?.length || 0} trending
              </Badge>
            </div>
          </div>

          {/* Time Range Selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Time range:</span>
            {(['24h', '7d', '30d', '90d'] as const).map((range) => (
              <Button
                key={range}
                variant={timeRange === range ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTimeRange(range)}
                className="h-7 text-xs"
              >
                {formatTimeRange(range)}
              </Button>
            ))}
            <Separator orientation="vertical" className="h-4" />
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1">
              <Filter className="w-3 h-3" />
              Filter
            </Button>
          </div>
        </div>

        {/* Market Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {marketIndicators.map((indicator, index) => (
            <Card key={index}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted-foreground">{indicator.label}</div>
                    <div className="text-2xl font-bold">{indicator.value}</div>
                    <div className="flex items-center gap-1 text-xs">
                      {getTrendIcon(indicator.trend)}
                      <span className={cn(
                        'font-medium',
                        indicator.trend === 'up' ? 'text-green-600' : 
                        indicator.trend === 'down' ? 'text-red-600' : 'text-muted-foreground'
                      )}>
                        {indicator.change}
                      </span>
                      <span className="text-muted-foreground">vs {indicator.period}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Trending Technologies */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Brain className="w-4 h-4" />
                  Hot Technologies
                </CardTitle>
                <CardDescription>
                  Fastest growing AI technologies and their opportunity counts
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {trendingTechnologies.map((tech, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-sm">{tech.name}</div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {tech.opportunities} ops
                          </Badge>
                          <div className="flex items-center gap-1">
                            {getTrendIcon(tech.trend)}
                            <span className="text-xs font-medium text-green-600">
                              {tech.growth}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {tech.description}
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Industry Hotspots
                </CardTitle>
                <CardDescription>
                  Industries with highest AI adoption potential
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {hotIndustries.map((industry, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{industry.name}</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            Score: {industry.score}
                          </Badge>
                          <span className="text-xs text-green-600 font-medium">
                            {industry.growth}
                          </span>
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {industry.opportunities} opportunities identified
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Trending Opportunities */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="w-4 h-4" />
                    Trending Opportunities
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="text-xs">
                      Sort by: Growth
                    </Button>
                  </div>
                </div>
                <CardDescription>
                  AI opportunities gaining the most traction in the community
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <LoadingSpinner 
                    text="Loading trending opportunities..." 
                    className="py-8"
                    variant="ai-themed"
                    size="md"
                  />
                ) : error ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Globe className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <div>Unable to load trending data</div>
                    <div className="text-xs">Check your connection and try again</div>
                  </div>
                ) : trendingOpportunities?.length ? (
                  <div className="space-y-4">
                    {trendingOpportunities.map((opportunity, index) => (
                      <OpportunityCard
                        key={opportunity.id}
                        opportunity={opportunity}
                        variant="trending"
                        showTrendingBadge={true}
                        trendingRank={index + 1}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <TrendingUp className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <div>No trending opportunities found</div>
                    <div className="text-xs">Check back later for new trends</div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Real-time Updates Banner */}
        <Card className="border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <div className="flex-1">
                <div className="text-sm font-medium">Real-time Data Active</div>
                <div className="text-xs text-muted-foreground">
                  Trending data updated every 5 minutes from Reddit, GitHub, Hacker News, and Y Combinator
                </div>
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="w-3 h-3" />
                Last updated: {new Date().toLocaleTimeString()}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}