'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { notFound } from 'next/navigation';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { 
  ValidationBadge, 
  ValidationScore, 
  LoadingSpinner,
  OpportunityCard
} from '@/components';
import { ValidationForm, ValidationData } from '@/components/validation-form';
import { DeepDiveManager } from '@/components/deep-dive-manager';
import { toast } from "sonner"
import {
  ArrowLeft,
  BookmarkPlus,
  BrainCircuit,
  Share2,
  TrendingUp,
  DollarSign,
  Brain,
  Users,
  Calendar,
  Building,
  Zap,
  BarChart3,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Flag,
  ExternalLink,
  Download,
  Eye,
  Loader2
} from 'lucide-react';
import { useOpportunity } from '@/hooks/useOpportunities';
import { cn } from '@/lib/utils';
import type { Opportunity } from '@/types';


const mockBusinessIntelligence = {
  marketTrends: [
    { label: 'Market Growth Rate', value: '+23% YoY', trend: 'up' },
    { label: 'Competition Level', value: 'Medium', trend: 'stable' },
    { label: 'Investment Activity', value: 'High', trend: 'up' },
    { label: 'Time to Market', value: '6-9 months', trend: 'stable' }
  ],
  roiProjection: {
    development_cost: 250000,
    time_to_break_even: 18,
    projected_revenue_y1: 500000,
    projected_revenue_y3: 2500000,
    confidence_level: 78
  },
  technicalRequirements: [
    'Natural Language Processing Framework',
    'Cloud Infrastructure (AWS/Azure)',
    'CRM Integration APIs',
    'Machine Learning Pipeline',
    'Real-time Chat Interface'
  ]
};

const mockValidations = [
  {
    id: '1',
    user: { name: 'Sarah Chen', reputation: 892, expertise: 'AI/ML Engineering' },
    score: 95,
    comment: 'Excellent opportunity with strong market demand. The technical approach is sound and the market timing is perfect.',
    helpful_votes: 23,
    created_at: '2024-01-18T09:15:00Z'
  },
  {
    id: '2',
    user: { name: 'Marcus Johnson', reputation: 1156, expertise: 'E-commerce Strategy' },
    score: 82,
    comment: 'Good market fit, but competition is heating up. Would recommend focusing on specific verticals initially.',
    helpful_votes: 18,
    created_at: '2024-01-17T16:30:00Z'
  },
  {
    id: '3',
    user: { name: 'Elena Rodriguez', reputation: 678, expertise: 'Business Development' },
    score: 89,
    comment: 'Strong business case with clear monetization path. Implementation complexity is manageable for experienced teams.',
    helpful_votes: 15,
    created_at: '2024-01-16T11:45:00Z'
  }
];

const mockRelatedOpportunities: Opportunity[] = [
  {
    id: '2',
    title: 'Voice-Activated Shopping Assistant',
    description: 'AI-powered voice assistant for e-commerce platforms...',
    market_size_estimate: 8500000000,
    validation_score: 79,
    ai_feasibility_score: 85,
    industry: 'E-commerce',
    ai_solution_type: 'Speech Recognition',
    implementation_complexity: 'HIGH',
    validation_count: 98,
    created_at: '2024-01-10T08:20:00Z',
    updated_at: '2024-01-18T12:10:00Z'
  },
  {
    id: '3',
    title: 'Personalized Product Recommendation Engine',
    description: 'Machine learning system that analyzes customer behavior...',
    market_size_estimate: 12000000000,
    validation_score: 91,
    ai_feasibility_score: 88,
    industry: 'E-commerce',
    ai_solution_type: 'Recommendation Systems',
    implementation_complexity: 'MEDIUM',
    validation_count: 203,
    created_at: '2024-01-12T14:30:00Z',
    updated_at: '2024-01-19T09:25:00Z'
  }
];

export default function OpportunityDetailPage() {
  const params = useParams();
  const router = useRouter();
  const opportunityId = params.id as string;
  
  const [activeTab, setActiveTab] = useState<'overview' | 'validation' | 'discussion' | 'business'>('overview');
  const [bookmarked, setBookmarked] = useState(false);
  const [deepDiveWorkflowId, setDeepDiveWorkflowId] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  
  // Use real API data
  const { data: opportunity, isLoading, error } = useOpportunity(opportunityId);
  
  // Extract real agent analysis data if available
  const agentAnalysis = opportunity?.agent_analysis || null;
  const businessIntel = agentAnalysis || mockBusinessIntelligence;
  const aiCapabilities = agentAnalysis?.ai_capabilities || null;

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-6">
        <LoadingSpinner 
          text="Loading opportunity details..." 
          className="py-12"
          variant="ai-themed"
          size="lg"
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold text-red-600 mb-2">Error Loading Opportunity</h2>
          <p className="text-muted-foreground mb-4">
            {error.message || 'Failed to load opportunity details'}
          </p>
          <Button onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  if (!opportunity) {
    return notFound();
  }

  const formatMarketSize = (size: number) => {
    if (size >= 1000000000) return `$${(size / 1000000000).toFixed(1)}B`;
    if (size >= 1000000) return `$${(size / 1000000).toFixed(1)}M`;
    if (size >= 1000) return `$${(size / 1000).toFixed(1)}K`;
    return `$${size}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  const handleBookmark = () => {
    setBookmarked(!bookmarked);
    // TODO: Implement actual bookmark API call
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    // TODO: Add toast notification
    toast.success("Link copied to clipboard!");
  };

  const handleValidateSubmit = async (validationData: ValidationData) => {
    // TODO: Implement actual API call
    console.log('Submitting validation:', validationData);
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="space-y-6">
        {/* Header with Navigation */}
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.back()}
            className="gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          
          <div className="text-sm text-muted-foreground">
            <span>Opportunities</span> / <span className="text-foreground">{opportunity.title}</span>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Opportunity Header */}
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{opportunity.industry}</Badge>
                      <Badge variant="secondary">{opportunity.ai_solution_type}</Badge>
                      <Badge 
                        className={cn(
                          opportunity.implementation_complexity === 'LOW' ? 'bg-green-100 text-green-800' :
                          opportunity.implementation_complexity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        )}
                      >
                        {opportunity.implementation_complexity} Complexity
                      </Badge>
                    </div>
                    
                    <CardTitle className="text-2xl leading-tight">
                      {opportunity.title}
                    </CardTitle>
                    
                    <CardDescription className="text-base">
                      {opportunity.description}
                    </CardDescription>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant={bookmarked ? "default" : "outline"}
                      size="sm"
                      onClick={handleBookmark}
                      className="gap-2"
                    >
                      <BookmarkPlus className="w-4 h-4" />
                      {bookmarked ? 'Bookmarked' : 'Bookmark'}
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleShare}
                      className="gap-2"
                    >
                      <Share2 className="w-4 h-4" />
                      Share
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent>
                {/* Key Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Validation Score</span>
                    </div>
                    <div className="text-2xl font-bold text-green-600">
                      {opportunity.validation_score}%
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {opportunity.validation_count} validations
                    </div>
                  </div>
                  
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <DollarSign className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Market Size</span>
                    </div>
                    <div className="text-2xl font-bold text-blue-600">
                      {formatMarketSize(opportunity.market_size_estimate)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Total addressable market
                    </div>
                  </div>
                  
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <Brain className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">AI Feasibility</span>
                    </div>
                    <div className="text-2xl font-bold text-purple-600">
                      {opportunity.ai_feasibility_score}%
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Technical viability
                    </div>
                  </div>
                  
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <Calendar className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Discovery Date</span>
                    </div>
                    <div className="text-sm font-medium">
                      {formatDate(opportunity.created_at)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      First identified
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-3">
                  <ValidationForm
                    opportunityId={opportunity.id}
                    opportunityTitle={opportunity.title}
                    onSubmit={handleValidateSubmit}
                  />
                  
                  <Button variant="outline" className="gap-2">
                    <MessageSquare className="w-4 h-4" />
                    Join Discussion ({23})
                  </Button>
                  
                  <Button variant="outline" className="gap-2">
                    <ExternalLink className="w-4 h-4" />
                    View Sources
                  </Button>
                  <DeepDiveManager opportunity={opportunity} />
                </div>
              </CardContent>
            </Card>

            {/* Tab Navigation */}
            <div className="border-b">
              <nav className="-mb-px flex space-x-8">
                {[
                  { id: 'overview', label: 'Overview', icon: Eye },
                  { id: 'validation', label: 'Validation', icon: Users },
                  { id: 'discussion', label: 'Discussion', icon: MessageSquare },
                  { id: 'business', label: 'Business Intel', icon: BarChart3 }
                ].map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as 'overview' | 'validation' | 'discussion' | 'business')}
                      className={cn(
                        'flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors',
                        activeTab === tab.id
                          ? 'border-primary text-primary'
                          : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Tab Content */}
            <div>
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Building className="w-5 h-5" />
                        Market Analysis
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center">
                          <div className="text-lg font-semibold">
                            {(businessIntel as any)?.viability?.market_size_assessment || 'Large Market'}
                          </div>
                          <div className="text-sm text-muted-foreground">Market Assessment</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold">
                            {(businessIntel as any)?.viability?.competition_level || 'Medium'}
                          </div>
                          <div className="text-sm text-muted-foreground">Competition Level</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold">
                            {(businessIntel as any)?.viability?.technical_feasibility || 'High'}
                          </div>
                          <div className="text-sm text-muted-foreground">Technical Feasibility</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold">
                            {(businessIntel as any)?.viability?.roi_projection?.time_to_market || '6-12 months'}
                          </div>
                          <div className="text-sm text-muted-foreground">Time to Market</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Zap className="w-5 h-5" />
                        Technical Requirements
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {(agentAnalysis?.implementation?.required_technologies || mockBusinessIntelligence.technicalRequirements).map((req: string, index: number) => (
                          <div key={index} className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-primary rounded-full" />
                            <span className="text-sm">{req}</span>
                          </div>
                        ))}
                      </div>
                      
                      {aiCapabilities && (
                        <div className="mt-4 pt-4 border-t">
                          <div className="text-sm font-medium mb-2">AI Stack Requirements:</div>
                          <div className="space-y-1">
                            {aiCapabilities.required_ai_stack?.ml_frameworks?.map((framework: string, index: number) => (
                              <Badge key={index} variant="outline" className="mr-1 mb-1 text-xs">
                                {framework}
                              </Badge>
                            ))}
                          </div>
                          <div className="text-xs text-muted-foreground mt-2">
                            Complexity: {aiCapabilities.complexity_assessment} • 
                            Effort: {aiCapabilities.development_effort}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              )}

              {activeTab === 'validation' && (
                <div className="space-y-4">
                  {/* AI Agent Analysis */}
                  {agentAnalysis && (
                    <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20">
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <Avatar className="bg-blue-600 text-white">
                            <AvatarFallback className="bg-blue-600 text-white">AI</AvatarFallback>
                          </Avatar>
                          
                          <div className="flex-1 space-y-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="font-medium">{opportunity.generated_by || 'AI Agent'}</div>
                                <div className="text-sm text-muted-foreground">
                                  AI Analysis • {opportunity.generation_method || 'Multi-agent'} • Confidence: {((agentAnalysis.agent_confidence || 0) * 100).toFixed(0)}%
                                </div>
                              </div>
                              <ValidationBadge 
                                score={opportunity.validation_score} 
                                variant="compact"
                              />
                            </div>
                            
                            <div className="space-y-2">
                              <p className="text-sm"><strong>Market Assessment:</strong> {agentAnalysis.viability?.market_size_assessment}</p>
                              <p className="text-sm"><strong>Technical Feasibility:</strong> {agentAnalysis.viability?.technical_feasibility}</p>
                              <p className="text-sm"><strong>Competition Level:</strong> {agentAnalysis.viability?.competition_level}</p>
                              {agentAnalysis.implementation?.key_challenges && (
                                <p className="text-sm"><strong>Key Challenges:</strong> {agentAnalysis.implementation.key_challenges.join(', ')}</p>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              <span>{formatDate(opportunity.created_at)}</span>
                              <Badge variant="secondary" className="text-xs">AI Generated</Badge>
                              <Badge variant="outline" className="text-xs">{opportunity.validation_count} validations</Badge>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Data Sources Used */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        Data Sources & Validation
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <div className="text-sm font-medium mb-2">Real-time Data Sources:</div>
                          <div className="grid grid-cols-2 gap-2">
                            <Badge variant="outline" className="justify-center">Reddit r/artificial</Badge>
                            <Badge variant="outline" className="justify-center">GitHub Issues</Badge>
                            <Badge variant="outline" className="justify-center">Hacker News</Badge>
                            <Badge variant="outline" className="justify-center">Y Combinator</Badge>
                          </div>
                        </div>
                        
                        {agentAnalysis?.market_trends?.market_indicators && (
                          <div>
                            <div className="text-sm font-medium mb-2">Market Indicators:</div>
                            <div className="space-y-2 text-sm text-muted-foreground">
                              <div><strong>VC Funding:</strong> {agentAnalysis.market_trends.market_indicators.vc_funding}</div>
                              <div><strong>Job Market:</strong> {agentAnalysis.market_trends.market_indicators.job_postings}</div>
                              <div><strong>Patent Activity:</strong> {agentAnalysis.market_trends.market_indicators.patent_filings}</div>
                            </div>
                          </div>
                        )}
                        
                        {agentAnalysis?.market_trends?.hot_technologies && (
                          <div>
                            <div className="text-sm font-medium mb-2">Technology Trends:</div>
                            <div className="space-y-1">
                              {agentAnalysis.market_trends.hot_technologies.slice(0, 3).map((tech: { name: string; growth_rate: string; }, index: number) => (
                                <div key={index} className="flex justify-between text-sm">
                                  <span>{tech.name}</span>
                                  <Badge variant="secondary" className="text-xs">+{tech.growth_rate}</Badge>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Fallback to mock validations if no real data */}
                  {!agentAnalysis && mockValidations.map((validation) => (
                    <Card key={validation.id}>
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <Avatar>
                            <AvatarFallback>
                              {validation.user.name.split(' ').map(n => n[0]).join('')}
                            </AvatarFallback>
                          </Avatar>
                          
                          <div className="flex-1 space-y-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="font-medium">{validation.user.name}</div>
                                <div className="text-sm text-muted-foreground">
                                  {validation.user.expertise} • {validation.user.reputation} reputation
                                </div>
                              </div>
                              <ValidationBadge 
                                score={validation.score} 
                                variant="compact"
                              />
                            </div>
                            
                            <p className="text-sm">{validation.comment}</p>
                            
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              <span>{formatDate(validation.created_at)}</span>
                              <div className="flex items-center gap-1">
                                <Button size="sm" variant="ghost" className="h-6 px-2 gap-1">
                                  <ThumbsUp className="w-3 h-3" />
                                  {validation.helpful_votes}
                                </Button>
                                <Button size="sm" variant="ghost" className="h-6 px-2">
                                  <ThumbsDown className="w-3 h-3" />
                                </Button>
                                <Button size="sm" variant="ghost" className="h-6 px-2">
                                  <Flag className="w-3 h-3" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {activeTab === 'discussion' && (
                <div className="space-y-4">
                  {/* Agent Processing Insights */}
                  {agentAnalysis && agentAnalysis.market_trends?.predicted_opportunities && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Brain className="w-4 h-4" />
                          AI Agent Analysis & Predictions
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          <div>
                            <div className="text-sm font-medium mb-2">Market Opportunities Identified:</div>
                            <div className="space-y-2">
                              {agentAnalysis.market_trends.predicted_opportunities.map((opportunity: string, index: number) => (
                                <div key={index} className="flex items-start gap-2 text-sm">
                                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mt-2 flex-shrink-0" />
                                  <span className="text-muted-foreground">{opportunity}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                          
                          {agentAnalysis.implementation?.success_factors && (
                            <div className="pt-4 border-t">
                              <div className="text-sm font-medium mb-2">Success Factors:</div>
                              <div className="flex flex-wrap gap-1">
                                {agentAnalysis.implementation.success_factors.map((factor: string, index: number) => (
                                  <Badge key={index} variant="secondary" className="text-xs">
                                    {factor}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Data Extraction Process */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Zap className="w-4 h-4" />
                        How Agents Extract & Process Data
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-3">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900/20 rounded-full flex items-center justify-center">
                                <span className="text-orange-600 text-xs font-bold">1</span>
                              </div>
                              <div>
                                <div className="text-sm font-medium">Data Collection</div>
                                <div className="text-xs text-muted-foreground">Monitors Reddit, GitHub, HN, YC</div>
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center">
                                <span className="text-blue-600 text-xs font-bold">2</span>
                              </div>
                              <div>
                                <div className="text-sm font-medium">Signal Analysis</div>
                                <div className="text-xs text-muted-foreground">AI analyzes trends & pain points</div>
                              </div>
                            </div>
                          </div>
                          
                          <div className="space-y-3">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center">
                                <span className="text-green-600 text-xs font-bold">3</span>
                              </div>
                              <div>
                                <div className="text-sm font-medium">Opportunity Generation</div>
                                <div className="text-xs text-muted-foreground">Creates viable AI solutions</div>
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center">
                                <span className="text-purple-600 text-xs font-bold">4</span>
                              </div>
                              <div>
                                <div className="text-sm font-medium">Validation & Scoring</div>
                                <div className="text-xs text-muted-foreground">Multi-agent consensus scoring</div>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <div className="pt-4 border-t">
                          <div className="text-sm font-medium mb-2">Active Agent Types:</div>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant="outline" className="text-xs">MonitoringAgent</Badge>
                            <Badge variant="outline" className="text-xs">AnalysisAgent</Badge>
                            <Badge variant="outline" className="text-xs">ResearchAgent</Badge>
                            <Badge variant="outline" className="text-xs">TrendAgent</Badge>
                            <Badge variant="outline" className="text-xs">CapabilityAgent</Badge>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Real-time Data Sources Status */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <BarChart3 className="w-4 h-4" />
                        Live Data Source Activity
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-sm">Reddit r/artificial</span>
                            <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">Active</Badge>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm">GitHub Issues</span>
                            <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">Active</Badge>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-sm">Hacker News</span>
                            <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">Active</Badge>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm">Y Combinator</span>
                            <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">Active</Badge>
                          </div>
                        </div>
                      </div>
                      
                      <div className="mt-4 pt-4 border-t text-xs text-muted-foreground">
                        Last updated: {formatDate(opportunity.updated_at)} • 
                        Generated by: {opportunity.generated_by || 'Multi-Agent System'}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {activeTab === 'business' && (
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>ROI Projection</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <div className="text-sm text-muted-foreground">Break Even</div>
                          <div className="text-lg font-semibold">
                            {(businessIntel as any)?.viability?.roi_projection?.break_even || mockBusinessIntelligence.roiProjection.time_to_break_even} months
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Time to Market</div>
                          <div className="text-lg font-semibold">
                            {(businessIntel as any)?.viability?.roi_projection?.time_to_market || '6-12 months'}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Year 1 Revenue</div>
                          <div className="text-lg font-semibold text-green-600">
                            ${(((businessIntel as any)?.viability?.roi_projection?.projected_revenue_y1 || mockBusinessIntelligence.roiProjection.projected_revenue_y1) / 1000000).toFixed(1)}M
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">AI Confidence</div>
                          <div className="text-lg font-semibold text-blue-600">
                            {(agentAnalysis?.agent_confidence ? (agentAnalysis.agent_confidence * 100).toFixed(0) : mockBusinessIntelligence.roiProjection.confidence_level)}%
                          </div>
                        </div>
                      </div>
                      
                      {agentAnalysis?.market_trends && (
                        <div className="mt-6 pt-4 border-t">
                          <div className="text-sm font-medium mb-3">Market Trends & Opportunities:</div>
                          <div className="space-y-2">
                            {agentAnalysis.market_trends.predicted_opportunities?.slice(0, 3).map((opportunity: string, index: number) => (
                              <div key={index} className="text-sm text-muted-foreground">
                                • {opportunity}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Validation Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Community Validation</CardTitle>
              </CardHeader>
              <CardContent>
                <ValidationScore
                  score={opportunity.validation_score}
                  validationCount={opportunity.validation_count}
                  confidence={85}
                  showProgress={true}
                />
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" size="sm" className="w-full justify-start gap-2">
                  <Download className="w-4 h-4" />
                  Export Analysis
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start gap-2">
                  <Users className="w-4 h-4" />
                  Find Collaborators
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start gap-2">
                  <Flag className="w-4 h-4" />
                  Report Issue
                </Button>
              </CardContent>
            </Card>

            {/* Related Opportunities */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Related Opportunities</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockRelatedOpportunities.map((relatedOpp) => (
                  <OpportunityCard
                    key={relatedOpp.id}
                    opportunity={relatedOpp}
                    variant="compact"
                    showActions={false}
                  />
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}