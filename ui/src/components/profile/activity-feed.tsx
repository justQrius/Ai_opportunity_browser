'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Activity,
  Star, 
  MessageCircle, 
  Bookmark,
  TrendingUp,
  Calendar,
  ExternalLink
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityItem {
  id: string;
  type: 'validation' | 'discussion' | 'bookmark' | 'opportunity_created';
  title: string;
  description: string;
  timestamp: string;
  metadata?: {
    score?: number;
    opportunityId?: string;
    opportunityTitle?: string;
    comments?: number;
  };
}

interface ActivityFeedProps {
  profileId: string;
  showFilters?: boolean;
  detailed?: boolean;
  limit?: number;
  className?: string;
}

// Mock activity data
const mockActivities: ActivityItem[] = [
  {
    id: '1',
    type: 'validation',
    title: 'Validated AI Customer Service Bot',
    description: 'Provided expert validation with detailed market analysis and technical feasibility assessment.',
    timestamp: '2024-01-20T10:30:00Z',
    metadata: {
      score: 87,
      opportunityId: '123',
      opportunityTitle: 'AI-Powered Customer Service Automation for SMBs'
    }
  },
  {
    id: '2',
    type: 'discussion',
    title: 'Commented on Healthcare AI Discussion',
    description: 'Shared insights about regulatory challenges in healthcare AI implementation.',
    timestamp: '2024-01-19T15:45:00Z',
    metadata: {
      opportunityId: '456',
      opportunityTitle: 'AI Diagnostic Assistant for Rural Healthcare',
      comments: 3
    }
  },
  {
    id: '3',
    type: 'bookmark',
    title: 'Bookmarked Computer Vision Opportunity',
    description: 'Saved for later evaluation - interesting application of object detection in retail.',
    timestamp: '2024-01-19T09:15:00Z',
    metadata: {
      opportunityId: '789',
      opportunityTitle: 'Automated Inventory Management with Computer Vision'
    }
  },
  {
    id: '4',
    type: 'validation',
    title: 'Validated NLP Text Analysis Tool',
    description: 'High-scoring validation focusing on business viability and market demand.',
    timestamp: '2024-01-18T16:20:00Z',
    metadata: {
      score: 92,
      opportunityId: '321',
      opportunityTitle: 'Sentiment Analysis API for Social Media Monitoring'
    }
  },
  {
    id: '5',
    type: 'discussion',
    title: 'Started Discussion on AI Ethics',
    description: 'Initiated conversation about ethical considerations in AI opportunity evaluation.',
    timestamp: '2024-01-17T11:00:00Z',
    metadata: {
      opportunityId: '654',
      opportunityTitle: 'AI-Powered Hiring Assistant',
      comments: 12
    }
  }
];

export function ActivityFeed({ 
  profileId, 
  showFilters = false, 
  detailed = false,
  limit,
  className 
}: ActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<string>('month');

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      let filteredActivities = mockActivities;
      
      if (filter !== 'all') {
        filteredActivities = filteredActivities.filter(activity => activity.type === filter);
      }
      
      if (limit) {
        filteredActivities = filteredActivities.slice(0, limit);
      }
      
      setActivities(filteredActivities);
      setLoading(false);
    }, 500);
  }, [profileId, filter, timeRange, limit]);

  const getActivityIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'validation':
        return <Star className="w-4 h-4 text-yellow-500" />;
      case 'discussion':
        return <MessageCircle className="w-4 h-4 text-blue-500" />;
      case 'bookmark':
        return <Bookmark className="w-4 h-4 text-green-500" />;
      case 'opportunity_created':
        return <TrendingUp className="w-4 h-4 text-purple-500" />;
      default:
        return <Activity className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getActivityColor = (type: ActivityItem['type']) => {
    switch (type) {
      case 'validation':
        return 'border-l-yellow-500';
      case 'discussion':
        return 'border-l-blue-500';
      case 'bookmark':
        return 'border-l-green-500';
      case 'opportunity_created':
        return 'border-l-purple-500';
      default:
        return 'border-l-muted-foreground';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInHours = diffInMs / (1000 * 60 * 60);
    const diffInDays = diffInMs / (1000 * 60 * 60 * 24);

    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${Math.floor(diffInHours)} hours ago`;
    if (diffInDays < 7) return `${Math.floor(diffInDays)} days ago`;
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-16 bg-muted rounded-lg"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Recent Activity
          </CardTitle>
          
          {showFilters && (
            <div className="flex items-center gap-2">
              <Select value={filter} onValueChange={setFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="validation">Validations</SelectItem>
                  <SelectItem value="discussion">Discussions</SelectItem>
                  <SelectItem value="bookmark">Bookmarks</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="week">This Week</SelectItem>
                  <SelectItem value="month">This Month</SelectItem>
                  <SelectItem value="quarter">3 Months</SelectItem>
                  <SelectItem value="year">This Year</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent>
        {activities.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No activity found for the selected filters</p>
          </div>
        ) : (
          <div className="space-y-4">
            {activities.map((activity, index) => (
              <div key={activity.id}>
                <div className={cn(
                  'relative pl-4 border-l-2 pb-4',
                  getActivityColor(activity.type)
                )}>
                  {/* Activity Icon */}
                  <div className="absolute -left-2 top-1 w-4 h-4 bg-background">
                    {getActivityIcon(activity.type)}
                  </div>
                  
                  {/* Activity Content */}
                  <div className="ml-2">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h4 className="font-medium text-sm">{activity.title}</h4>
                        {detailed && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {activity.description}
                          </p>
                        )}
                        
                        {/* Metadata */}
                        {activity.metadata && (
                          <div className="flex items-center gap-3 mt-2">
                            {activity.metadata.score && (
                              <Badge variant="secondary" className="text-xs">
                                Score: {activity.metadata.score}%
                              </Badge>
                            )}
                            {activity.metadata.comments && (
                              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                <MessageCircle className="w-3 h-3" />
                                {activity.metadata.comments} replies
                              </div>
                            )}
                            {activity.metadata.opportunityTitle && (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-auto p-0 text-xs text-primary hover:text-primary/80"
                              >
                                <ExternalLink className="w-3 h-3 mr-1" />
                                View Opportunity
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                        <Calendar className="w-3 h-3" />
                        {formatTimestamp(activity.timestamp)}
                      </div>
                    </div>
                  </div>
                </div>
                
                {index < activities.length - 1 && <Separator className="ml-6" />}
              </div>
            ))}
          </div>
        )}
        
        {!limit && activities.length > 0 && (
          <div className="mt-6 text-center">
            <Button variant="outline" size="sm">
              Load More Activity
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}