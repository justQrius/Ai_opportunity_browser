'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { 
  Search, 
  X, 
  Clock, 
  TrendingUp,
  Sparkles,
  Filter,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchSuggestion {
  id: string;
  text: string;
  type: 'recent' | 'popular' | 'ai-generated';
  count?: number;
}

interface SearchBarProps {
  value?: string;
  onChange?: (value: string) => void;
  onSearch?: (query: string) => void;
  onClear?: () => void;
  placeholder?: string;
  suggestions?: SearchSuggestion[];
  recentSearches?: string[];
  loading?: boolean;
  className?: string;
  
  // Advanced search features
  showSuggestions?: boolean;
  showFilters?: boolean;
  filterCount?: number;
  onFilterClick?: () => void;
  
  // Auto-complete and debouncing
  debounceMs?: number;
  minQueryLength?: number;
  
  // Styling options
  variant?: 'default' | 'large' | 'compact';
  showSearchIcon?: boolean;
  showClearButton?: boolean;
}

const defaultSuggestions: SearchSuggestion[] = [
  { id: '1', text: 'AI chatbot for customer service', type: 'popular', count: 45 },
  { id: '2', text: 'machine learning image recognition', type: 'popular', count: 32 },
  { id: '3', text: 'natural language processing', type: 'ai-generated' },
  { id: '4', text: 'automated content generation', type: 'ai-generated' },
  { id: '5', text: 'predictive analytics', type: 'recent' },
];

export function SearchBar({
  value = '',
  onChange,
  onSearch,
  onClear,
  placeholder = 'Search AI opportunities...',
  suggestions = defaultSuggestions,
  recentSearches = [],
  loading = false,
  className,
  showSuggestions = true,
  showFilters = true,
  filterCount = 0,
  onFilterClick,
  debounceMs = 300,
  minQueryLength = 2,
  variant = 'default',
  showSearchIcon = true,
  showClearButton = true
}: SearchBarProps) {
  const [inputValue, setInputValue] = useState(value);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Debounced onChange
  const debouncedOnChange = useCallback(
    (newValue: string) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        onChange?.(newValue);
      }, debounceMs);
    },
    [onChange, debounceMs]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    debouncedOnChange(newValue);
    
    if (showSuggestions && newValue.length >= minQueryLength) {
      setShowDropdown(true);
      setHighlightedIndex(-1);
    } else {
      setShowDropdown(false);
    }
  };

  const handleSearch = useCallback((query?: string) => {
    const searchQuery = query || inputValue;
    if (searchQuery.trim()) {
      onSearch?.(searchQuery.trim());
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  }, [inputValue, onSearch]);

  const handleClear = () => {
    setInputValue('');
    onChange?.('');
    onClear?.();
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const handleSuggestionClick = (suggestion: SearchSuggestion) => {
    setInputValue(suggestion.text);
    handleSearch(suggestion.text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || suggestions.length === 0) {
      if (e.key === 'Enter') {
        handleSearch();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0) {
          handleSuggestionClick(suggestions[highlightedIndex]);
        } else {
          handleSearch();
        }
        break;
      case 'Escape':
        setShowDropdown(false);
        setHighlightedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Sync external value changes
  useEffect(() => {
    if (value !== inputValue) {
      setInputValue(value);
    }
  }, [value]);

  const sizeClasses = {
    default: 'h-10',
    large: 'h-12 text-lg',
    compact: 'h-8 text-sm'
  };

  const getSuggestionIcon = (type: SearchSuggestion['type']) => {
    switch (type) {
      case 'recent':
        return <Clock className="w-4 h-4 text-muted-foreground" />;
      case 'popular':
        return <TrendingUp className="w-4 h-4 text-muted-foreground" />;
      case 'ai-generated':
        return <Sparkles className="w-4 h-4 text-purple-500" />;
      default:
        return <Search className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const filteredSuggestions = suggestions.filter(suggestion =>
    suggestion.text.toLowerCase().includes(inputValue.toLowerCase())
  );

  return (
    <div className={cn('relative', className)}>
      <div className="relative">
        <div className="relative flex items-center">
          {showSearchIcon && (
            <Search className="absolute left-3 w-4 h-4 text-muted-foreground pointer-events-none" />
          )}
          
          <Input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (showSuggestions && inputValue.length >= minQueryLength) {
                setShowDropdown(true);
              }
            }}
            placeholder={placeholder}
            className={cn(
              sizeClasses[variant],
              showSearchIcon && 'pl-10',
              (showClearButton || showFilters) && 'pr-20'
            )}
            disabled={loading}
          />

          <div className="absolute right-2 flex items-center gap-1">
            {loading && (
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            )}
            
            {showClearButton && inputValue && !loading && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClear}
                className="h-6 w-6 p-0 hover:bg-muted"
              >
                <X className="w-3 h-3" />
              </Button>
            )}

            {showFilters && onFilterClick && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onFilterClick}
                className="h-6 w-6 p-0 hover:bg-muted relative"
              >
                <Filter className="w-3 h-3" />
                {filterCount > 0 && (
                  <Badge 
                    variant="destructive" 
                    className="absolute -top-1 -right-1 h-4 w-4 p-0 text-xs flex items-center justify-center"
                  >
                    {filterCount}
                  </Badge>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Enter key hint */}
        {inputValue && !loading && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
            <kbd className="px-1 py-0.5 text-xs bg-muted border rounded text-muted-foreground">
              ↵
            </kbd>
          </div>
        )}
      </div>

      {/* Suggestions Dropdown */}
      {showDropdown && showSuggestions && (
        <Card 
          ref={dropdownRef}
          className="absolute top-full left-0 right-0 mt-1 z-50 max-h-80 overflow-y-auto"
        >
          <CardContent className="p-2">
            {filteredSuggestions.length > 0 ? (
              <div className="space-y-1">
                {filteredSuggestions.map((suggestion, index) => (
                  <button
                    key={suggestion.id}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className={cn(
                      'w-full text-left px-3 py-2 rounded-md hover:bg-muted transition-colors',
                      'flex items-center justify-between gap-2',
                      highlightedIndex === index && 'bg-muted'
                    )}
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      {getSuggestionIcon(suggestion.type)}
                      <span className="truncate">{suggestion.text}</span>
                    </div>
                    {suggestion.count && (
                      <Badge variant="secondary" className="text-xs shrink-0">
                        {suggestion.count}
                      </Badge>
                    )}
                  </button>
                ))}
              </div>
            ) : inputValue.length >= minQueryLength ? (
              <div className="px-3 py-2 text-sm text-muted-foreground text-center">
                No suggestions found
              </div>
            ) : (
              <div className="px-3 py-2 text-sm text-muted-foreground text-center">
                Type at least {minQueryLength} characters to see suggestions
              </div>
            )}

            {/* Recent searches */}
            {recentSearches.length > 0 && inputValue.length < minQueryLength && (
              <>
                <div className="px-3 py-2 text-xs font-medium text-muted-foreground border-t mt-2 pt-3">
                  Recent Searches
                </div>
                <div className="space-y-1">
                  {recentSearches.slice(0, 3).map((search, index) => (
                    <button
                      key={index}
                      onClick={() => handleSearch(search)}
                      className="w-full text-left px-3 py-2 rounded-md hover:bg-muted transition-colors flex items-center gap-2"
                    >
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span className="truncate">{search}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default SearchBar;