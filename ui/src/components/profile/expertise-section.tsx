'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Brain, 
  Star, 
  TrendingUp, 
  Award,
  Plus
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExpertiseSectionProps {
  expertise: string[];
  reputationScore: number;
  onAddExpertise?: () => void;
  isEditable?: boolean;
  className?: string;
}

// Mock expertise levels for demonstration
const expertiseLevels = {
  'Machine Learning': { level: 4, validations: 23 },
  'Natural Language Processing': { level: 3, validations: 15 },
  'Computer Vision': { level: 4, validations: 18 },
  'Product Strategy': { level: 5, validations: 31 },
  'Deep Learning': { level: 3, validations: 12 },
  'Data Science': { level: 4, validations: 20 }
};

export function ExpertiseSection({ 
  expertise, 
  reputationScore,
  onAddExpertise,
  isEditable = true,
  className 
}: ExpertiseSectionProps) {
  const getReputationProgress = (score: number) => {
    // Calculate progress to next level
    if (score < 500) return { current: score, next: 500, progress: (score / 500) * 100, nextLevel: 'Intermediate' };
    if (score < 2000) return { current: score - 500, next: 1500, progress: ((score - 500) / 1500) * 100, nextLevel: 'Advanced' };
    if (score < 5000) return { current: score - 2000, next: 3000, progress: ((score - 2000) / 3000) * 100, nextLevel: 'Expert' };
    return { current: score - 5000, next: null, progress: 100, nextLevel: 'Master' };
  };

  const reputationProgress = getReputationProgress(reputationScore);

  const getLevelColor = (level: number) => {
    switch (level) {
      case 5: return 'bg-purple-100 text-purple-800';
      case 4: return 'bg-blue-100 text-blue-800';
      case 3: return 'bg-green-100 text-green-800';
      case 2: return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getLevelLabel = (level: number) => {
    switch (level) {
      case 5: return 'Expert';
      case 4: return 'Advanced';
      case 3: return 'Intermediate';
      case 2: return 'Beginner';
      default: return 'Learning';
    }
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Reputation Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Star className="w-4 h-4 text-yellow-500" />
            Reputation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold">{reputationScore.toLocaleString()}</span>
            <Badge variant="outline">
              {reputationProgress.nextLevel}
            </Badge>
          </div>
          
          {reputationProgress.next && (
            <>
              <Progress value={reputationProgress.progress} className="h-2" />
              <div className="text-xs text-muted-foreground text-center">
                {reputationProgress.current.toLocaleString()} / {reputationProgress.next.toLocaleString()} to {reputationProgress.nextLevel}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Expertise Areas */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Brain className="w-4 h-4" />
              Expertise Areas
            </CardTitle>
            {isEditable && onAddExpertise && (
              <Button variant="ghost" size="sm" onClick={onAddExpertise} className="gap-2">
                <Plus className="w-4 h-4" />
                Add
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {expertise.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground">
              <Brain className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No expertise areas added yet</p>
              {isEditable && onAddExpertise && (
                <Button variant="outline" size="sm" onClick={onAddExpertise} className="mt-2 gap-2">
                  <Plus className="w-4 h-4" />
                  Add Your First Expertise
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {expertise.map((area) => {
                const details = expertiseLevels[area as keyof typeof expertiseLevels];
                const level = details?.level || 1;
                const validations = details?.validations || 0;
                
                return (
                  <div key={area} className="flex items-center justify-between p-3 rounded-lg border">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium">{area}</span>
                        <Badge className={getLevelColor(level)}>
                          {getLevelLabel(level)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <TrendingUp className="w-3 h-3" />
                        <span>{validations} validations</span>
                      </div>
                    </div>
                    
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star 
                          key={star}
                          className={cn(
                            'w-4 h-4',
                            star <= level 
                              ? 'text-yellow-500 fill-current' 
                              : 'text-muted-foreground'
                          )} 
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Achievement Highlights */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Award className="w-4 h-4 text-orange-500" />
            Recent Achievements
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-2 rounded-lg bg-muted/50">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                <Star className="w-4 h-4 text-blue-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Top Validator</p>
                <p className="text-xs text-muted-foreground">
                  Ranked #3 in Machine Learning validations this month
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3 p-2 rounded-lg bg-muted/50">
              <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-green-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Reputation Milestone</p>
                <p className="text-xs text-muted-foreground">
                  Reached 2,500 reputation points
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3 p-2 rounded-lg bg-muted/50">
              <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
                <Brain className="w-4 h-4 text-purple-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Expert Recognition</p>
                <p className="text-xs text-muted-foreground">
                  Achieved Expert level in Product Strategy
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}