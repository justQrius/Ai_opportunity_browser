'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger, SheetClose } from '@/components/ui/sheet';
import { 
  Filter, 
  X, 
  RefreshCw,
  TrendingUp,
  DollarSign,
  Brain,
  Building,
  Zap,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { OpportunityFilters } from '@/types';
import { cn } from '@/lib/utils';

interface FilterPanelProps {
  filters: OpportunityFilters;
  onFiltersChange: (filters: OpportunityFilters) => void;
  onReset?: () => void;
  className?: string;
  
  // Display options
  variant?: 'panel' | 'sheet' | 'inline';
  showApplyButton?: boolean;
  showResetButton?: boolean;
  collapsible?: boolean;
  
  // Data for select options
  industries?: string[];
  aiSolutionTypes?: string[];
  
  // Sheet props (when variant is 'sheet')
  trigger?: React.ReactNode;
  
  // Filter state
  activeFilterCount?: number;
}


const defaultIndustries = [
  'Healthcare',
  'Finance',
  'E-commerce',
  'Education',
  'Manufacturing',
  'Transportation',
  'Real Estate',
  'Entertainment',
  'Agriculture',
  'Energy',
  'Legal',
  'Marketing'
];

const defaultAiSolutionTypes = [
  'Machine Learning',
  'Natural Language Processing',
  'Computer Vision',
  'Recommendation Systems',
  'Predictive Analytics',
  'Automation',
  'Chatbots',
  'Speech Recognition',
  'Image Recognition',
  'Optimization'
];

const complexityOptions = [
  { value: 'LOW', label: 'Low Complexity', color: 'bg-green-100 text-green-800' },
  { value: 'MEDIUM', label: 'Medium Complexity', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'HIGH', label: 'High Complexity', color: 'bg-red-100 text-red-800' }
];

function FilterContent({
  filters,
  onFiltersChange,
  onReset,
  showApplyButton = false,
  showResetButton = true,
  collapsible = false,
  industries = defaultIndustries,
  aiSolutionTypes = defaultAiSolutionTypes,
  activeFilterCount = 0
}: Omit<FilterPanelProps, 'variant' | 'trigger' | 'className'>) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    industry: true,
    validation: true,
    market: true,
    complexity: true,
    ai: true
  });

  const toggleSection = (sectionId: string) => {
    if (!collapsible) return;
    setExpandedSections(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  const updateFilter = (key: keyof OpportunityFilters, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value || undefined
    });
  };

  const clearFilter = (key: keyof OpportunityFilters) => {
    const newFilters = { ...filters };
    delete newFilters[key];
    onFiltersChange(newFilters);
  };

  const hasActiveFilters = activeFilterCount > 0 || Object.keys(filters).some(key => filters[key as keyof OpportunityFilters] !== undefined);

  const SectionHeader = ({ 
    section, 
    children 
  }: { 
    section: { id: string; title: string; icon: React.ReactNode }; 
    children: React.ReactNode; 
  }) => (
    <div className="space-y-3">
      <button
        onClick={() => toggleSection(section.id)}
        className={cn(
          'flex items-center justify-between w-full py-2 text-left',
          collapsible && 'hover:text-primary transition-colors'
        )}
        disabled={!collapsible}
      >
        <div className="flex items-center gap-2">
          {section.icon}
          <span className="font-medium text-sm">{section.title}</span>
        </div>
        {collapsible && (
          expandedSections[section.id] ? 
            <ChevronUp className="w-4 h-4" /> : 
            <ChevronDown className="w-4 h-4" />
        )}
      </button>
      {(!collapsible || expandedSections[section.id]) && (
        <div className="space-y-3">
          {children}
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header with filter count and reset */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium text-sm">Filters</span>
          {hasActiveFilters && (
            <Badge variant="secondary" className="text-xs">
              {activeFilterCount || Object.keys(filters).length}
            </Badge>
          )}
        </div>
        {showResetButton && hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="text-xs gap-1 h-7"
          >
            <RefreshCw className="w-3 h-3" />
            Reset
          </Button>
        )}
      </div>

      {/* Active Filters */}
      {hasActiveFilters && (
        <div className="space-y-2">
          <span className="text-xs font-medium text-muted-foreground">Active Filters</span>
          <div className="flex flex-wrap gap-1">
            {filters.industry && (
              <Badge variant="secondary" className="text-xs gap-1">
                {filters.industry}
                <button onClick={() => clearFilter('industry')}>
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            )}
            {filters.ai_solution_type && (
              <Badge variant="secondary" className="text-xs gap-1">
                {filters.ai_solution_type}
                <button onClick={() => clearFilter('ai_solution_type')}>
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            )}
            {filters.implementation_complexity && (
              <Badge variant="secondary" className="text-xs gap-1">
                {filters.implementation_complexity} Complexity
                <button onClick={() => clearFilter('implementation_complexity')}>
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            )}
          </div>
        </div>
      )}

      <Separator />

      {/* Industry Filter */}
      <SectionHeader section={{ id: 'industry', title: 'Industry', icon: <Building className="w-4 h-4" /> }}>
        <Select
          value={filters.industry || ''}
          onValueChange={(value) => updateFilter('industry', value)}
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Select industry" />
          </SelectTrigger>
          <SelectContent>
            {industries.map((industry) => (
              <SelectItem key={industry} value={industry}>
                {industry}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </SectionHeader>

      <Separator />

      {/* AI Solution Type Filter */}
      <SectionHeader section={{ id: 'ai', title: 'AI Solution Type', icon: <Brain className="w-4 h-4" /> }}>
        <Select
          value={filters.ai_solution_type || ''}
          onValueChange={(value) => updateFilter('ai_solution_type', value)}
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Select AI solution type" />
          </SelectTrigger>
          <SelectContent>
            {aiSolutionTypes.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </SectionHeader>

      <Separator />

      {/* Validation Score Filter */}
      <SectionHeader section={{ id: 'validation', title: 'Validation Score', icon: <TrendingUp className="w-4 h-4" /> }}>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="min-validation" className="text-xs">Min Score</Label>
            <Input
              id="min-validation"
              type="number"
              min="0"
              max="100"
              value={filters.min_validation_score || ''}
              onChange={(e) => updateFilter('min_validation_score', e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="0"
              className="h-9"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="max-validation" className="text-xs">Max Score</Label>
            <Input
              id="max-validation"
              type="number"
              min="0"
              max="100"
              value={filters.max_validation_score || ''}
              onChange={(e) => updateFilter('max_validation_score', e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="100"
              className="h-9"
            />
          </div>
        </div>
      </SectionHeader>

      <Separator />

      {/* Market Size Filter */}
      <SectionHeader section={{ id: 'market', title: 'Market Size', icon: <DollarSign className="w-4 h-4" /> }}>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="min-market" className="text-xs">Min Size ($)</Label>
            <Input
              id="min-market"
              type="number"
              min="0"
              value={filters.market_size_min || ''}
              onChange={(e) => updateFilter('market_size_min', e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="0"
              className="h-9"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="max-market" className="text-xs">Max Size ($)</Label>
            <Input
              id="max-market"
              type="number"
              min="0"
              value={filters.market_size_max || ''}
              onChange={(e) => updateFilter('market_size_max', e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="No limit"
              className="h-9"
            />
          </div>
        </div>
      </SectionHeader>

      <Separator />

      {/* Implementation Complexity Filter */}
      <SectionHeader section={{ id: 'complexity', title: 'Implementation Complexity', icon: <Zap className="w-4 h-4" /> }}>
        <div className="space-y-2">
          {complexityOptions.map((option) => (
            <label key={option.value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="complexity"
                value={option.value}
                checked={filters.implementation_complexity === option.value}
                onChange={(e) => updateFilter('implementation_complexity', e.target.checked ? option.value : undefined)}
                className="sr-only"
              />
              <Button
                type="button"
                variant={filters.implementation_complexity === option.value ? "default" : "outline"}
                size="sm"
                onClick={() => updateFilter('implementation_complexity', 
                  filters.implementation_complexity === option.value ? undefined : option.value
                )}
                className="w-full justify-start text-xs h-8"
              >
                {option.label}
              </Button>
            </label>
          ))}
        </div>
      </SectionHeader>

      {/* Apply Button (for sheet variant) */}
      {showApplyButton && (
        <>
          <Separator />
          <SheetClose asChild>
            <Button className="w-full">
              Apply Filters
            </Button>
          </SheetClose>
        </>
      )}
    </div>
  );
}

export function FilterPanel({
  filters,
  onFiltersChange,
  onReset,
  className,
  variant = 'panel',
  showApplyButton = false,
  showResetButton = true,
  collapsible = false,
  industries,
  aiSolutionTypes,
  trigger,
  activeFilterCount
}: FilterPanelProps) {
  if (variant === 'sheet') {
    return (
      <Sheet>
        <SheetTrigger asChild>
          {trigger || (
            <Button variant="outline" className="gap-2">
              <Filter className="w-4 h-4" />
              Filters
              {activeFilterCount && activeFilterCount > 0 && (
                <Badge variant="destructive" className="h-4 w-4 p-0 text-xs">
                  {activeFilterCount}
                </Badge>
              )}
            </Button>
          )}
        </SheetTrigger>
        <SheetContent side="left" className="w-80 overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Filter Opportunities</SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            <FilterContent
              filters={filters}
              onFiltersChange={onFiltersChange}
              onReset={onReset}
              showApplyButton={true}
              showResetButton={showResetButton}
              collapsible={collapsible}
              industries={industries}
              aiSolutionTypes={aiSolutionTypes}
              activeFilterCount={activeFilterCount}
            />
          </div>
        </SheetContent>
      </Sheet>
    );
  }

  if (variant === 'inline') {
    return (
      <div className={cn('space-y-4', className)}>
        <FilterContent
          filters={filters}
          onFiltersChange={onFiltersChange}
          onReset={onReset}
          showApplyButton={showApplyButton}
          showResetButton={showResetButton}
          collapsible={collapsible}
          industries={industries}
          aiSolutionTypes={aiSolutionTypes}
          activeFilterCount={activeFilterCount}
        />
      </div>
    );
  }

  // Default panel variant
  return (
    <Card className={cn('w-full max-w-sm', className)}>
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Filter Opportunities</CardTitle>
      </CardHeader>
      <CardContent>
        <FilterContent
          filters={filters}
          onFiltersChange={onFiltersChange}
          onReset={onReset}
          showApplyButton={showApplyButton}
          showResetButton={showResetButton}
          collapsible={collapsible}
          industries={industries}
          aiSolutionTypes={aiSolutionTypes}
          activeFilterCount={activeFilterCount}
        />
      </CardContent>
    </Card>
  );
}

export default FilterPanel;