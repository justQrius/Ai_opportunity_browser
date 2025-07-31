'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BrainCircuit, Loader2, TrendingUp, Users, DollarSign, Target, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/services/api';
import type { Opportunity } from '@/types';

interface WorkflowResult {
  contextual_research?: {
    status: string;
    research_report: {
      summary: string;
      key_findings: string[];
      confidence_score: number;
    };
    market_research: {
      market_size: {
        total_addressable_market: number;
        serviceable_addressable_market: number;
        serviceable_obtainable_market: number;
        currency: string;
      };
      growth_rate: number;
      key_players: Array<{
        name: string;
        market_share: number;
        revenue: number;
        strengths: string[];
        weaknesses: string[];
      }>;
      market_trends: string[];
      customer_segments: Array<{
        segment: string;
        size: number;
        characteristics: string[];
        pain_points: string[];
      }>;
      barriers_to_entry: string[];
    };
  };
  competitive_analysis?: {
    status: string;
    research_report: {
      summary: string;
      key_findings: string[];
      confidence_score: number;
    };
    competitive_analysis: {
      direct_competitors: Array<{
        name: string;
        description: string;
        strengths: string[];
        weaknesses: string[];
        market_position: string;
        funding: number;
      }>;
      indirect_competitors: Array<{
        name: string;
        description: string;
        threat_level: string;
        differentiation: string;
      }>;
      competitive_advantages: string[];
      market_gaps: string[];
      pricing_analysis: {
        pricing_models: string[];
        price_ranges: {
          low: number;
          medium: number;
          high: number;
        };
        pricing_trends: string;
      };
    };
  };
}

interface DeepDiveManagerProps {
  opportunity: Opportunity;
}

export function DeepDiveManager({ opportunity }: DeepDiveManagerProps) {
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<WorkflowResult | null>(null);
  const [workflowState, setWorkflowState] = useState<string>('');
  const [hasActiveWorkflow, setHasActiveWorkflow] = useState(false);

  const handleDeepDive = async () => {
    if (!opportunity || hasActiveWorkflow) return;

    try {
      const response = await apiClient.post(`/opportunities/${opportunity.id}/deep-dive`);
      const data = response.data;

      setWorkflowId(data.workflow_id);
      setIsPolling(true);
      setHasActiveWorkflow(true);
      setWorkflowState('running');
      setAnalysisResults(null); // Clear previous results
      
      toast.success("Deep Dive Started", {
        description: `AI agents are now analyzing "${opportunity.title}". Results will appear below.`,
      });
    } catch (error: unknown) {
      let errorMessage = "An unknown error occurred.";
      if (error instanceof Error) {
        // Type guard to check if error has response property
        if ('response' in error && typeof error.response === 'object' && error.response !== null) {
          const errorResponse = error.response as { data?: { detail?: string } };
          if (errorResponse.data?.detail) {
            errorMessage = errorResponse.data.detail;
          }
        } else if (error.message) {
          errorMessage = error.message;
        }
      }
      toast.error("Failed to start deep dive.", {
        description: errorMessage,
      });
    }
  };

  useEffect(() => {
    if (!isPolling || !workflowId) return;

    const interval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/workflows/${workflowId}/status`);
        const data = response.data;
        
        setWorkflowState(data.state);

        if (data.state === 'completed' || data.state === 'failed') {
          setIsPolling(false);
          setHasActiveWorkflow(false);
          
          // Store the results even if workflow failed (partial results may be available)
          if (data.results) {
            setAnalysisResults(data.results);
            toast.success(`Deep dive analysis complete!`, {
              description: `Comprehensive market and competitive insights are now available below.`,
            });
          } else {
            toast.error(`Analysis ${data.state}`, {
              description: `The deep dive analysis could not be completed. Please try again.`,
            });
          }
          
          // Keep workflowId for result display but stop polling
          // Don't clear workflowId here so results remain accessible
        }
      } catch (error) {
        setIsPolling(false);
        setHasActiveWorkflow(false);
        setWorkflowState('error');
        console.error("Failed to poll workflow status:", error);
        toast.error("Analysis monitoring failed", {
          description: "Unable to track analysis progress. Please try again.",
        });
      }
    }, 3000); // Poll every 3 seconds for faster feedback

    return () => clearInterval(interval);
  }, [isPolling, workflowId, opportunity.title]);

  const formatCurrency = (amount: number) => {
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
    if (amount >= 1e3) return `$${(amount / 1e3).toFixed(1)}K`;
    return `$${amount}`;
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'running': return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      default: return <AlertCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Deep Dive Button */}
      <div className="flex items-center gap-4">
        <Button 
          onClick={handleDeepDive} 
          variant="default" 
          className="gap-2" 
          disabled={hasActiveWorkflow}
          data-testid="deep-dive-button"
        >
          {hasActiveWorkflow ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <BrainCircuit className="w-4 h-4" />
          )}
          {hasActiveWorkflow ? 'Analyzing...' : 'Deep Dive'}
        </Button>
        
        {workflowId && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {getStateIcon(workflowState)}
            <span>Workflow: {workflowId}</span>
            {workflowState && (
              <Badge variant={workflowState === 'completed' ? 'default' : workflowState === 'failed' ? 'destructive' : 'secondary'}>
                {workflowState}
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Analysis Results */}
      {analysisResults && (
        <div className="space-y-6" data-testid="deep-dive-results">
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold">AI Deep Dive Analysis</h3>
          </div>

          {/* Market Research Results */}
          {analysisResults.contextual_research && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-500" />
                  Market Research
                </CardTitle>
                <CardDescription>
                  {analysisResults.contextual_research.research_report.summary}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Market Size */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="w-4 h-4 text-green-500" />
                      <span className="font-medium">Total Addressable Market</span>
                    </div>
                    <p className="text-2xl font-bold text-green-600">
                      {formatCurrency(analysisResults.contextual_research.market_research.market_size.total_addressable_market)}
                    </p>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Target className="w-4 h-4 text-blue-500" />
                      <span className="font-medium">Serviceable Market</span>
                    </div>
                    <p className="text-2xl font-bold text-blue-600">
                      {formatCurrency(analysisResults.contextual_research.market_research.market_size.serviceable_addressable_market)}
                    </p>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="w-4 h-4 text-purple-500" />
                      <span className="font-medium">Growth Rate</span>
                    </div>
                    <p className="text-2xl font-bold text-purple-600">
                      {(analysisResults.contextual_research.market_research.growth_rate * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Key Findings */}
                <div>
                  <h4 className="font-medium mb-2">Key Findings</h4>
                  <ul className="space-y-1">
                    {analysisResults.contextual_research.research_report.key_findings.map((finding, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span className="text-sm">{finding}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Market Trends */}
                <div>
                  <h4 className="font-medium mb-2">Market Trends</h4>
                  <div className="flex flex-wrap gap-2">
                    {analysisResults.contextual_research.market_research.market_trends.map((trend, index) => (
                      <Badge key={index} variant="outline">
                        {trend}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Key Players */}
                {analysisResults.contextual_research.market_research.key_players.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Key Market Players</h4>
                    <div className="space-y-2">
                      {analysisResults.contextual_research.market_research.key_players.map((player, index) => (
                        <div key={index} className="p-3 border rounded-lg">
                          <div className="flex justify-between items-start mb-2">
                            <h5 className="font-medium">{player.name}</h5>
                            <Badge variant="secondary">
                              {(player.market_share * 100).toFixed(1)}% market share
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">
                            Revenue: {formatCurrency(player.revenue)}
                          </p>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="font-medium text-green-600">Strengths:</span>
                              <ul className="list-disc list-inside">
                                {player.strengths.map((strength, i) => (
                                  <li key={i}>{strength}</li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <span className="font-medium text-red-600">Weaknesses:</span>
                              <ul className="list-disc list-inside">
                                {player.weaknesses.map((weakness, i) => (
                                  <li key={i}>{weakness}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Competitive Analysis Results */}
          {analysisResults.competitive_analysis && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-orange-500" />
                  Competitive Analysis
                </CardTitle>
                <CardDescription>
                  {analysisResults.competitive_analysis.research_report.summary}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Competitive Advantages */}
                <div>
                  <h4 className="font-medium mb-2">Competitive Advantages</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {analysisResults.competitive_analysis.competitive_analysis.competitive_advantages.map((advantage, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 bg-green-50 border-l-4 border-green-500 rounded">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span className="text-sm">{advantage}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Market Gaps */}
                <div>
                  <h4 className="font-medium mb-2">Market Gaps & Opportunities</h4>
                  <div className="space-y-2">
                    {analysisResults.competitive_analysis.competitive_analysis.market_gaps.map((gap, index) => (
                      <div key={index} className="flex items-start gap-2 p-2 bg-blue-50 border-l-4 border-blue-500 rounded">
                        <Target className="w-4 h-4 text-blue-500 mt-0.5" />
                        <span className="text-sm">{gap}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Direct Competitors */}
                {analysisResults.competitive_analysis.competitive_analysis.direct_competitors.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Direct Competitors</h4>
                    <div className="space-y-3">
                      {analysisResults.competitive_analysis.competitive_analysis.direct_competitors.map((competitor, index) => (
                        <div key={index} className="p-4 border rounded-lg">
                          <div className="flex justify-between items-start mb-2">
                            <h5 className="font-medium">{competitor.name}</h5>
                            <div className="flex gap-2">
                              <Badge variant="outline">{competitor.market_position}</Badge>
                              <Badge variant="secondary">
                                {formatCurrency(competitor.funding)} funding
                              </Badge>
                            </div>
                          </div>
                          <p className="text-sm text-muted-foreground mb-3">{competitor.description}</p>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="font-medium text-green-600">Strengths:</span>
                              <ul className="list-disc list-inside">
                                {competitor.strengths.map((strength, i) => (
                                  <li key={i}>{strength}</li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <span className="font-medium text-red-600">Weaknesses:</span>
                              <ul className="list-disc list-inside">
                                {competitor.weaknesses.map((weakness, i) => (
                                  <li key={i}>{weakness}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Pricing Analysis */}
                {analysisResults.competitive_analysis.competitive_analysis.pricing_analysis && (
                  <div>
                    <h4 className="font-medium mb-2">Pricing Analysis</h4>
                    <div className="p-4 border rounded-lg">
                      <div className="grid grid-cols-3 gap-4 mb-3">
                        <div className="text-center">
                          <p className="text-sm text-muted-foreground">Low</p>
                          <p className="font-bold text-green-600">
                            ${analysisResults.competitive_analysis.competitive_analysis.pricing_analysis.price_ranges.low}
                          </p>
                        </div>
                        <div className="text-center">
                          <p className="text-sm text-muted-foreground">Medium</p>
                          <p className="font-bold text-yellow-600">
                            ${analysisResults.competitive_analysis.competitive_analysis.pricing_analysis.price_ranges.medium}
                          </p>
                        </div>
                        <div className="text-center">
                          <p className="text-sm text-muted-foreground">High</p>
                          <p className="font-bold text-red-600">
                            ${analysisResults.competitive_analysis.competitive_analysis.pricing_analysis.price_ranges.high}
                          </p>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div>
                          <span className="font-medium">Pricing Models:</span>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {analysisResults.competitive_analysis.competitive_analysis.pricing_analysis.pricing_models.map((model, index) => (
                              <Badge key={index} variant="outline">{model}</Badge>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="font-medium">Pricing Trends:</span>
                          <p className="text-sm text-muted-foreground mt-1">
                            {analysisResults.competitive_analysis.competitive_analysis.pricing_analysis.pricing_trends}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Analysis Confidence */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <span className="font-medium">Analysis Confidence</span>
                <div className="flex items-center gap-2">
                  {analysisResults.contextual_research && (
                    <Badge variant="outline">
                      Market: {(analysisResults.contextual_research.research_report.confidence_score * 100).toFixed(0)}%
                    </Badge>
                  )}
                  {analysisResults.competitive_analysis && (
                    <Badge variant="outline">
                      Competitive: {(analysisResults.competitive_analysis.research_report.confidence_score * 100).toFixed(0)}%
                    </Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}