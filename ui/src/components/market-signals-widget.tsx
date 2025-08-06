import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle,
  Lightbulb,
  MessageSquare,
  Activity,
  BarChart3,
  Zap
} from 'lucide-react';

interface MarketSignal {
  type: 'pain_point' | 'feature_request' | 'trend' | 'opportunity' | 'discussion';
  title: string;
  source: string;
  strength: number; // 0-100
  engagement: number;
  trend_direction: 'up' | 'down' | 'stable';
  time_period: string;
}

interface MarketSignalsWidgetProps {
  signals: MarketSignal[];
  className?: string;
}

const signalIcons = {
  pain_point: AlertTriangle,
  feature_request: Lightbulb,
  trend: TrendingUp,
  opportunity: Zap,
  discussion: MessageSquare
};

const signalColors = {
  pain_point: 'text-red-600',
  feature_request: 'text-blue-600',
  trend: 'text-green-600',
  opportunity: 'text-purple-600',
  discussion: 'text-gray-600'
};

const trendIcons = {
  up: TrendingUp,
  down: TrendingDown,
  stable: Activity
};

const trendColors = {
  up: 'text-green-600',
  down: 'text-red-600',
  stable: 'text-gray-600'
};

export function MarketSignalsWidget({ signals, className }: MarketSignalsWidgetProps) {
  // Group signals by type
  const signalsByType = signals.reduce((acc, signal) => {
    if (!acc[signal.type]) acc[signal.type] = [];
    acc[signal.type].push(signal);
    return acc;
  }, {} as Record<string, MarketSignal[]>);

  // Calculate overall metrics
  const totalEngagement = signals.reduce((sum, signal) => sum + signal.engagement, 0);
  const avgStrength = signals.reduce((sum, signal) => sum + signal.strength, 0) / signals.length;
  const strongSignals = signals.filter(signal => signal.strength >= 70).length;

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Market Signal Analysis
            </CardTitle>
            <CardDescription>
              Real-time analysis of {signals.length} market signals
            </CardDescription>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-primary">{strongSignals}</div>
            <div className="text-xs text-muted-foreground">Strong Signals</div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Overall Metrics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-lg font-semibold">{signals.length}</div>
            <div className="text-xs text-muted-foreground">Total Signals</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold">{totalEngagement.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">Total Engagement</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold">{avgStrength.toFixed(0)}%</div>
            <div className="text-xs text-muted-foreground">Avg Strength</div>
          </div>
        </div>

        {/* Signal Type Breakdown */}
        <div className="space-y-4">
          <div className="text-sm font-medium">Signal Breakdown:</div>
          {Object.entries(signalsByType).map(([type, typeSignals]) => {
            const Icon = signalIcons[type as keyof typeof signalIcons];
            const avgTypeStrength = typeSignals.reduce((sum, s) => sum + s.strength, 0) / typeSignals.length;
            const upTrend = typeSignals.filter(s => s.trend_direction === 'up').length;
            const totalTypeEngagement = typeSignals.reduce((sum, s) => sum + s.engagement, 0);
            
            return (
              <div key={type} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${signalColors[type as keyof typeof signalColors]}`} />
                    <span className="text-sm font-medium capitalize">
                      {type.replace('_', ' ')} ({typeSignals.length})
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <TrendingUp className="w-3 h-3 text-green-600" />
                    <span>{upTrend}/{typeSignals.length} trending up</span>
                    <span>•</span>
                    <span>{totalTypeEngagement} engagement</span>
                  </div>
                </div>
                
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span>Signal Strength</span>
                    <span>{avgTypeStrength.toFixed(0)}%</span>
                  </div>
                  <Progress value={avgTypeStrength} className="h-2" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Top Signals */}
        <div className="space-y-3">
          <div className="text-sm font-medium">Strongest Signals:</div>
          {signals
            .sort((a, b) => b.strength - a.strength)
            .slice(0, 5)
            .map((signal, index) => {
              const Icon = signalIcons[signal.type];
              const TrendIcon = trendIcons[signal.trend_direction];
              
              return (
                <div key={index} className="flex items-center gap-3 p-3 border rounded-lg hover:shadow-sm transition-shadow">
                  <Icon className={`w-4 h-4 flex-shrink-0 ${signalColors[signal.type]}`} />
                  
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{signal.title}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-xs">{signal.source}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {signal.engagement.toLocaleString()} engagement
                      </span>
                      <span className="text-xs text-muted-foreground">•</span>
                      <span className="text-xs text-muted-foreground">{signal.time_period}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <TrendIcon className={`w-3 h-3 ${trendColors[signal.trend_direction]}`} />
                    <div className="text-right">
                      <div className="text-sm font-semibold">{signal.strength}%</div>
                      <div className="text-xs text-muted-foreground">strength</div>
                    </div>
                  </div>
                </div>
              );
            })}
        </div>

        {/* Real-time Status */}
        <div className="pt-4 border-t">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Last updated: {new Date().toLocaleTimeString()}</span>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span>Live data stream</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default MarketSignalsWidget;