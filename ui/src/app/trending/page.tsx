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
  Clock,
  Sparkles,
  ArrowUp,
  ArrowDown,
  Minus,
  Filter,
  Globe
} from 'lucide-react';
import { useTrending } from '@/hooks/useOpportunities';
import { cn } from '@/lib/utils';

export default function TrendingPage() {
  const marketIndicators = [
    { label: 'Total Opportunities', value: '1,280', trend: 'up', change: '+5.2%', period: '7d' },
    { label: 'Market Size', value: '$4.5B', trend: 'up', change: '+12%', period: '30d' },
    { label: 'Community Validations', value: '25.6k', trend: 'up', change: '+8.1%', period: '7d' },
    { label: 'New Opportunities (24h)', value: '42', trend: 'down', change: '-3.5%', period: '24h' },
  ];

  const trendingTechnologies = [
    { name: 'Large Language Models (LLMs)', opportunities: 152, growth: '+25%', trend: 'up', description: 'Advanced models for text generation and understanding.' },
    { name: 'Generative Adversarial Networks (GANs)', opportunities: 89, growth: '+18%', trend: 'up', description: 'For creating realistic images, video, and audio.' },
    { name: 'Reinforcement Learning', opportunities: 76, growth: '+12%', trend: 'up', description: 'Training models through trial and error.' },
    { name: 'Computer Vision', opportunities: 112, growth: '+9%', trend: 'down', description: 'Analyzing and understanding visual data.' },
  ];

  const hotIndustries = [
    { name: 'Healthcare', score: 92, growth: '+15%', opportunities: 215 },
    { name: 'Finance', score: 88, growth: '+11%', opportunities: 180 },
    { name: 'E-commerce', score: 85, growth: '+20%', opportunities: 150 },
    { name: 'Education', score: 82, growth: '+18%', opportunities: 132 },
  ];
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | '90d'>('7d');
  
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