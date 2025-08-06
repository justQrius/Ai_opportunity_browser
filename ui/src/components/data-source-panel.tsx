import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  ExternalLink, 
  MessageCircle, 
  GitBranch, 
  TrendingUp, 
  Rocket, 
  Building2,
  ThumbsUp,
  Eye,
  Clock,
  Users
} from 'lucide-react';

interface DataSource {
  type: 'reddit' | 'github' | 'hackernews' | 'producthunt' | 'ycombinator';
  title: string;
  url: string;
  engagement: {
    upvotes?: number;
    comments?: number;
    views?: number;
    reactions?: number;
  };
  metadata: {
    author?: string;
    subreddit?: string;
    repository?: string;
    created_at?: string;
    labels?: string[];
  };
  content_preview: string;
  signal_type: 'pain_point' | 'feature_request' | 'discussion' | 'trend' | 'opportunity';
  relevance_score: number;
}

interface DataSourcePanelProps {
  sources: DataSource[];
  className?: string;
}

const sourceIcons = {
  reddit: MessageCircle,
  github: GitBranch,
  hackernews: TrendingUp,
  producthunt: Rocket,
  ycombinator: Building2
};

const sourceColors = {
  reddit: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  github: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
  hackernews: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  producthunt: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  ycombinator: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
};

const signalTypeColors = {
  pain_point: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  feature_request: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',  
  discussion: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
  trend: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  opportunity: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
};

export function DataSourcePanel({ sources, className }: DataSourcePanelProps) {
  const totalEngagement = sources.reduce((sum, source) => {
    return sum + (source.engagement.upvotes || 0) + (source.engagement.comments || 0);
  }, 0);

  const signalBreakdown = sources.reduce((acc, source) => {
    acc[source.signal_type] = (acc[source.signal_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="w-5 h-5" />
              Data Sources & Market Signals
            </CardTitle>
            <CardDescription>
              Real-time data from {sources.length} external sources
            </CardDescription>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-primary">{totalEngagement}</div>
            <div className="text-xs text-muted-foreground">Total Engagement</div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Signal Breakdown */}
        <div>
          <div className="text-sm font-medium mb-3">Signal Types Identified:</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(signalBreakdown).map(([type, count]) => (
              <Badge 
                key={type} 
                className={signalTypeColors[type as keyof typeof signalTypeColors]}
              >
                {type.replace('_', ' ')}: {count}
              </Badge>
            ))}
          </div>
        </div>

        <Separator />

        {/* Individual Sources */}
        <div className="space-y-4">
          <div className="text-sm font-medium">Source Details:</div>
          {sources.map((source, index) => {
            const Icon = sourceIcons[source.type];
            
            return (
              <div key={index} className="border rounded-lg p-4 space-y-3 hover:shadow-sm transition-shadow">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Icon className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{source.title}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${sourceColors[source.type]}`}
                        >
                          {source.type}
                        </Badge>
                        <Badge 
                          variant="outline"
                          className={`text-xs ${signalTypeColors[source.signal_type]}`}
                        >
                          {source.signal_type.replace('_', ' ')}
                        </Badge>
                        <div className="text-xs text-muted-foreground">
                          Score: {source.relevance_score}%
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    asChild
                    className="h-8 w-8 p-0 flex-shrink-0"
                  >
                    <a href={source.url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </Button>
                </div>

                {/* Content Preview */}
                <div className="text-xs text-muted-foreground line-clamp-2 pl-7">
                  {source.content_preview}
                </div>

                {/* Metadata and Engagement */}
                <div className="flex items-center justify-between text-xs text-muted-foreground pl-7">
                  <div className="flex items-center gap-4">
                    {source.metadata.author && (
                      <span>by {source.metadata.author}</span>
                    )}
                    {source.metadata.subreddit && (
                      <span>in r/{source.metadata.subreddit}</span>
                    )}
                    {source.metadata.repository && (
                      <span>in {source.metadata.repository}</span>
                    )}
                    {source.metadata.created_at && (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(source.metadata.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {source.engagement.upvotes && (
                      <span className="flex items-center gap-1">
                        <ThumbsUp className="w-3 h-3" />
                        {source.engagement.upvotes}
                      </span>
                    )}
                    {source.engagement.comments && (
                      <span className="flex items-center gap-1">
                        <MessageCircle className="w-3 h-3" />
                        {source.engagement.comments}
                      </span>
                    )}
                    {source.engagement.views && (
                      <span className="flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        {source.engagement.views}
                      </span>
                    )}
                  </div>
                </div>

                {/* Labels for GitHub */}
                {source.metadata.labels && source.metadata.labels.length > 0 && (
                  <div className="flex flex-wrap gap-1 pl-7">
                    {source.metadata.labels.map((label, labelIndex) => (
                      <Badge key={labelIndex} variant="secondary" className="text-xs">
                        {label}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default DataSourcePanel;