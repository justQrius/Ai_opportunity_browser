'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '@/components/ui/dialog';
import { 
  Star,
  TrendingUp,
  DollarSign,
  Brain,
  Users,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ValidationFormProps {
  opportunityId: string;
  opportunityTitle: string;
  trigger?: React.ReactNode;
  onSubmit?: (validation: ValidationData) => Promise<void>;
  className?: string;
}

export type { ValidationData };
interface ValidationData {
  score: number;
  comment: string;
  aspects: {
    market_demand: number;
    technical_feasibility: number;
    business_viability: number;
    competition_level: number;
  };
}

const validationAspects = [
  {
    key: 'market_demand' as const,
    label: 'Market Demand',
    description: 'How strong is the market need for this solution?',
    icon: TrendingUp
  },
  {
    key: 'technical_feasibility' as const,
    label: 'Technical Feasibility',
    description: 'How realistic is the technical implementation?',
    icon: Brain
  },
  {
    key: 'business_viability' as const,
    label: 'Business Viability',
    description: 'How viable is this as a business opportunity?',
    icon: DollarSign
  },
  {
    key: 'competition_level' as const,
    label: 'Competition Assessment',
    description: 'How competitive is this market space?',
    icon: Users
  }
];

const scoreLabels = {
  1: 'Very Poor',
  2: 'Poor', 
  3: 'Fair',
  4: 'Good',
  5: 'Excellent'
};

export function ValidationForm({ 
  opportunityTitle, 
  trigger, 
  onSubmit
}: ValidationFormProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'aspects' | 'summary' | 'success'>('aspects');
  
  const [validation, setValidation] = useState<ValidationData>({
    score: 0,
    comment: '',
    aspects: {
      market_demand: 0,
      technical_feasibility: 0,
      business_viability: 0,
      competition_level: 0
    }
  });

  const updateAspectScore = (aspect: keyof ValidationData['aspects'], score: number) => {
    setValidation(prev => ({
      ...prev,
      aspects: {
        ...prev.aspects,
        [aspect]: score
      }
    }));
  };

  const calculateOverallScore = () => {
    const aspects = validation.aspects;
    const scores = Object.values(aspects);
    const validScores = scores.filter(score => score > 0);
    
    if (validScores.length === 0) return 0;
    
    const average = validScores.reduce((sum, score) => sum + score, 0) / validScores.length;
    return Math.round(average * 20); // Convert 1-5 scale to 0-100
  };

  const canProceedToSummary = () => {
    return Object.values(validation.aspects).every(score => score > 0);
  };

  const handleProceedToSummary = () => {
    const overallScore = calculateOverallScore();
    setValidation(prev => ({ ...prev, score: overallScore }));
    setStep('summary');
  };

  const handleSubmit = async () => {
    if (!validation.comment.trim()) return;
    
    setLoading(true);
    try {
      await onSubmit?.(validation);
      setStep('success');
    } catch (error) {
      console.error('Failed to submit validation:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setOpen(false);
    setTimeout(() => {
      setStep('aspects');
      setValidation({
        score: 0,
        comment: '',
        aspects: {
          market_demand: 0,
          technical_feasibility: 0,
          business_viability: 0,
          competition_level: 0
        }
      });
    }, 300);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button className="gap-2">
            <Users className="w-4 h-4" />
            Validate This Opportunity
          </Button>
        )}
      </DialogTrigger>
      
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Validate Opportunity</DialogTitle>
          <DialogDescription>
            Share your expert assessment of &quot;{opportunityTitle}&quot;
          </DialogDescription>
        </DialogHeader>

        {step === 'aspects' && (
          <div className="space-y-6">
            <div className="text-sm text-muted-foreground">
              Rate each aspect on a scale of 1-5 stars to help the community understand this opportunity better.
            </div>

            <div className="space-y-6">
              {validationAspects.map((aspect) => {
                const Icon = aspect.icon;
                const currentScore = validation.aspects[aspect.key];
                
                return (
                  <div key={aspect.key} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-muted-foreground" />
                      <div>
                        <div className="font-medium">{aspect.label}</div>
                        <div className="text-sm text-muted-foreground">
                          {aspect.description}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {[1, 2, 3, 4, 5].map((score) => (
                        <button
                          key={score}
                          onClick={() => updateAspectScore(aspect.key, score)}
                          className={cn(
                            'p-1 rounded transition-colors',
                            currentScore >= score
                              ? 'text-yellow-500'
                              : 'text-muted-foreground hover:text-yellow-500'
                          )}
                        >
                          <Star 
                            className={cn(
                              'w-6 h-6',
                              currentScore >= score && 'fill-current'
                            )} 
                          />
                        </button>
                      ))}
                      
                      {currentScore > 0 && (
                        <Badge variant="secondary" className="ml-2">
                          {scoreLabels[currentScore as keyof typeof scoreLabels]}
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end">
              <Button 
                onClick={handleProceedToSummary}
                disabled={!canProceedToSummary()}
                className="gap-2"
              >
                Continue to Summary
                <CheckCircle className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {step === 'summary' && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Your Overall Score: {validation.score}%
                </CardTitle>
                <CardDescription>
                  Based on your individual aspect ratings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  {validationAspects.map((aspect) => {
                    const Icon = aspect.icon;
                    const score = validation.aspects[aspect.key];
                    
                    return (
                      <div key={aspect.key} className="flex items-center gap-2">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm">{aspect.label}</span>
                        <div className="flex ml-auto">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <Star 
                              key={star}
                              className={cn(
                                'w-3 h-3',
                                star <= score 
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
              </CardContent>
            </Card>

            <div className="space-y-2">
              <Label htmlFor="validation-comment">
                Share Your Insights <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="validation-comment"
                placeholder="Share your thoughts, concerns, or recommendations about this opportunity. Your insights help the community make better decisions."
                value={validation.comment}
                onChange={(e) => setValidation(prev => ({ ...prev, comment: e.target.value }))}
                rows={4}
                className="resize-none"
              />
              <div className="text-xs text-muted-foreground">
                Minimum 50 characters required
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => setStep('aspects')}
              >
                Back to Ratings
              </Button>
              
              <Button 
                onClick={handleSubmit}
                disabled={validation.comment.trim().length < 50 || loading}
                className="gap-2"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                Submit Validation
              </Button>
            </div>
          </div>
        )}

        {step === 'success' && (
          <div className="text-center space-y-4 py-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            
            <div>
              <h3 className="text-lg font-semibold mb-2">Validation Submitted!</h3>
              <p className="text-muted-foreground">
                Thank you for contributing to the community. Your validation has been recorded and will help others evaluate this opportunity.
              </p>
            </div>
            
            <Button onClick={handleClose} className="mt-4">
              Close
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default ValidationForm;