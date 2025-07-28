"""Y Combinator data source plugin for market signal extraction."""

import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncIterator
from pydantic import BaseModel
from bs4 import BeautifulSoup
import json

from .base import (
    DataSourcePlugin,
    PluginMetadata,
    PluginConfig,
    PluginStatus,
    RawData,
    DataSourceType,
    PluginError,
    PluginNetworkError,
    PluginRateLimitError
)


class YCombinatorConfig(PluginConfig):
    """Y Combinator-specific configuration."""
    keywords: List[str] = [
        "AI", "machine learning", "automation", "SaaS", "B2B", "productivity",
        "developer tools", "fintech", "healthtech", "edtech", "marketplace",
        "platform", "infrastructure", "analytics", "security"
    ]
    industries: List[str] = [
        "Artificial Intelligence", "Machine Learning", "Developer Tools",
        "Productivity", "SaaS", "Fintech", "Healthcare", "Education",
        "Marketplace", "Infrastructure", "Analytics", "Security"
    ]
    batch_years: List[str] = ["2024", "2023", "2022"]  # Recent batches
    max_companies_per_batch: int = 200
    include_failed_companies: bool = False
    min_funding_amount: int = 0  # In USD


class YCCompany(BaseModel):
    """Y Combinator company data structure."""
    id: str
    name: str
    description: str
    long_description: Optional[str] = None
    batch: str
    status: str  # "Active", "Inactive", "Acquired", "IPO"
    tags: List[str] = []
    location: str
    website: Optional[str] = None
    founded_year: Optional[int] = None
    team_size: Optional[str] = None
    funding_amount: Optional[str] = None
    valuation: Optional[str] = None
    industries: List[str] = []


class YCombinatorPlugin(DataSourcePlugin):
    """Y Combinator data source plugin for extracting market signals."""
    
    def __init__(self, config: YCombinatorConfig):
        super().__init__(config)
        self.yc_config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = "https://www.ycombinator.com"
        # YC uses a public directory, no auth required
    
    async def initialize(self) -> None:
        """Initialize Y Combinator web scraping."""
        try:
            # Create HTTP session with proper headers to avoid blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                headers=headers
            )
            
            await self.set_status(PluginStatus.ACTIVE)
            
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Initialization failed: {e}")
            raise PluginError(f"Failed to initialize Y Combinator plugin: {e}")
    
    async def shutdown(self) -> None:
        """Clean shutdown of Y Combinator plugin."""
        if self._session:
            await self._session.close()
        await self.set_status(PluginStatus.INACTIVE)
    
    async def health_check(self) -> bool:
        """Check Y Combinator website connectivity."""
        try:
            if not self._session:
                return False
            
            # Test access to YC companies directory
            url = f"{self._base_url}/companies"
            async with self._session.get(url) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def fetch_data(self, params: Dict[str, Any]) -> AsyncIterator[RawData]:
        """Fetch data from Y Combinator based on parameters."""
        if not await self._check_rate_limit():
            raise PluginRateLimitError("Rate limit exceeded")
        
        try:
            # Extract parameters
            keywords = params.get("keywords", self.yc_config.keywords)
            industries = params.get("industries", self.yc_config.industries)
            batch_years = params.get("batch_years", self.yc_config.batch_years)
            max_companies = params.get("max_companies_per_batch", self.yc_config.max_companies_per_batch)
            include_failed = params.get("include_failed_companies", self.yc_config.include_failed_companies)
            min_funding = params.get("min_funding_amount", self.yc_config.min_funding_amount)
            
            # Fetch companies from each batch
            for batch_year in batch_years:
                async for raw_data in self._fetch_batch_companies(
                    batch_year, keywords, industries, max_companies, include_failed, min_funding
                ):
                    await self._increment_request_count()
                    yield raw_data
                    
                # Be respectful - delay between batches
                await asyncio.sleep(2)
                    
        except Exception as e:
            await self.set_status(PluginStatus.ERROR, f"Data fetching failed: {e}")
            raise PluginError(f"Failed to fetch Y Combinator data: {e}")
    
    def get_metadata(self) -> PluginMetadata:
        """Return Y Combinator plugin metadata."""
        return PluginMetadata(
            name="ycombinator_plugin",
            version="1.0.0",
            description="Y Combinator data source plugin for market signal extraction",
            author="AI Opportunity Browser",
            source_type="YCOMBINATOR",  # Add to enum if needed
            supported_signal_types=[
                "startup_validation", "market_trend", "founder_insight",
                "industry_analysis", "investment_signal", "innovation_trend"
            ],
            rate_limit_per_hour=100,  # Be conservative with scraping
            requires_auth=False,
            config_schema={
                "keywords": {"type": "array", "items": {"type": "string"}},
                "industries": {"type": "array", "items": {"type": "string"}},
                "batch_years": {"type": "array", "items": {"type": "string"}},
                "max_companies_per_batch": {"type": "integer", "minimum": 1, "maximum": 500},
                "include_failed_companies": {"type": "boolean"},
                "min_funding_amount": {"type": "integer", "minimum": 0}
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Y Combinator plugin configuration."""
        # All fields are optional for YC since it's public data
        
        if "batch_years" in config:
            batch_years = config["batch_years"]
            if not isinstance(batch_years, list) or not all(isinstance(year, str) for year in batch_years):
                return False
        
        if "max_companies_per_batch" in config:
            max_companies = config["max_companies_per_batch"]
            if not isinstance(max_companies, int) or max_companies < 1 or max_companies > 500:
                return False
        
        return True
    
    async def _fetch_batch_companies(
        self,
        batch_year: str,
        keywords: List[str],
        industries: List[str],
        max_companies: int,
        include_failed: bool,
        min_funding: int
    ) -> AsyncIterator[RawData]:
        """Fetch companies from a specific YC batch."""
        
        # YC companies directory endpoint (more reliable)
        # Use the companies directory page which we can scrape
        url = f"{self._base_url}/companies"
        
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    raise PluginNetworkError(f"YC API error: {response.status}")
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                processed_count = 0
                
                # Find company entries in the HTML
                company_elements = soup.find_all('div', class_='company')
                if not company_elements:
                    # Try alternative selectors
                    company_elements = soup.find_all('a', href=lambda x: x and '/companies/' in str(x))
                
                for company_element in company_elements:
                    if processed_count >= max_companies:
                        break
                    
                    # Parse company data from HTML
                    company = self._parse_company_html(company_element)
                    if not company:
                        continue
                    
                    # Filter by batch year
                    if batch_year not in company.batch:
                        continue
                    
                    # Filter by status if needed
                    if not include_failed and company.status in ["Inactive", "Dead"]:
                        continue
                    
                    # Filter by funding if specified
                    if min_funding > 0 and company.funding_amount:
                        funding_value = self._parse_funding_amount(company.funding_amount)
                        if funding_value < min_funding:
                            continue
                    
                    # Check relevance
                    if not self._is_company_relevant(company, keywords, industries):
                        continue
                    
                    # Convert to RawData
                    raw_data = await self._normalize_company_data(company, keywords)
                    if raw_data:
                        yield raw_data
                        processed_count += 1
                    
                    # Small delay to be respectful
                    await asyncio.sleep(0.1)
                        
        except aiohttp.ClientError as e:
            raise PluginNetworkError(f"Network error fetching YC data: {e}")
        except json.JSONDecodeError as e:
            # Fallback to scraping if JSON API is not available
            async for raw_data in self._scrape_companies_fallback(
                batch_year, keywords, industries, max_companies, include_failed
            ):
                yield raw_data
    
    def _parse_company_data(self, data: Dict[str, Any]) -> Optional[YCCompany]:
        """Parse raw company data from YC API."""
        try:
            return YCCompany(
                id=str(data.get("id", "")),
                name=data.get("name", ""),
                description=data.get("one_liner", ""),
                long_description=data.get("long_description"),
                batch=data.get("batch", ""),
                status=data.get("status", "Active"),
                tags=data.get("tags", []),
                location=data.get("location", ""),
                website=data.get("website"),
                founded_year=data.get("founded_year"),
                team_size=data.get("team_size"),
                funding_amount=data.get("funding_amount"),
                valuation=data.get("valuation"),
                industries=data.get("industries", [])
            )
        except Exception:
            return None
    
    def _parse_company_html(self, element) -> Optional[YCCompany]:
        """Parse company data from HTML element."""
        try:
            # Extract basic information from HTML element
            # This is a simplified parser - adjust based on actual YC HTML structure
            if hasattr(element, 'get') and element.get('href'):
                # It's a link element
                name = element.get_text(strip=True) or "Unknown Company"
                company_url = element.get('href')
                company_id = company_url.split('/')[-1] if company_url else ""
            else:
                # It's a div or other element
                name_element = element.find('h3') or element.find('a') or element
                name = name_element.get_text(strip=True) if name_element else "Unknown Company"
                company_id = name.lower().replace(' ', '-').replace('.', '')
            
            # Create a minimal company object for now
            # In a real implementation, you'd scrape more details
            return YCCompany(
                id=company_id,
                name=name,
                description=f"Company from Y Combinator batch",
                batch="W24",  # Default batch - would be extracted from context
                status="Active",
                tags=[],
                location="Unknown",
                website=None,
                founded_year=None,
                team_size=None,
                funding_amount=None,
                valuation=None,
                industries=[]
            )
        except Exception:
            return None
    
    async def _scrape_companies_fallback(
        self,
        batch_year: str,
        keywords: List[str],
        industries: List[str],
        max_companies: int,
        include_failed: bool
    ) -> AsyncIterator[RawData]:
        """Fallback scraping method if JSON API is not available."""
        
        # Scrape YC companies directory page
        url = f"{self._base_url}/companies?batch={batch_year}"
        
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find company elements (this would need to be adjusted based on YC's HTML structure)
                company_elements = soup.find_all('div', class_='company-item')  # Adjust selector
                
                processed_count = 0
                for element in company_elements:
                    if processed_count >= max_companies:
                        break
                    
                    company = self._parse_company_element(element)
                    if not company:
                        continue
                    
                    # Apply filters
                    if not include_failed and company.status in ["Inactive", "Dead"]:
                        continue
                    
                    if not self._is_company_relevant(company, keywords, industries):
                        continue
                    
                    # Convert to RawData
                    raw_data = await self._normalize_company_data(company, keywords)
                    if raw_data:
                        yield raw_data
                        processed_count += 1
                    
                    await asyncio.sleep(0.1)
                    
        except Exception:
            # Silently fail for scraping fallback
            pass
    
    def _parse_company_element(self, element) -> Optional[YCCompany]:
        """Parse company data from HTML element."""
        try:
            # This would need to be implemented based on YC's actual HTML structure
            name_elem = element.find('h3')
            name = name_elem.text.strip() if name_elem else ""
            
            desc_elem = element.find('p')
            description = desc_elem.text.strip() if desc_elem else ""
            
            return YCCompany(
                id=name.lower().replace(' ', '-'),
                name=name,
                description=description,
                batch="Unknown",
                status="Active",
                location="",
                tags=[],
                industries=[]
            )
        except Exception:
            return None
    
    def _is_company_relevant(
        self, 
        company: YCCompany, 
        keywords: List[str], 
        industries: List[str]
    ) -> bool:
        """Check if company is relevant based on keywords and industries."""
        
        # Check description for keywords
        content = f"{company.name} {company.description} {company.long_description or ''}"
        if self._contains_keywords(content, keywords):
            return True
        
        # Check tags and industries
        company_categories = company.tags + company.industries
        if any(cat in industries for cat in company_categories):
            return True
        
        return False
    
    async def _normalize_company_data(
        self, 
        company: YCCompany, 
        keywords: List[str]
    ) -> Optional[RawData]:
        """Normalize Y Combinator company data into RawData format."""
        
        # Combine all text content
        full_content = f"{company.name}\n{company.description}"
        if company.long_description:
            full_content += f"\n\n{company.long_description}"
        
        # Determine signal type
        signal_type = self._classify_signal_type(company)
        
        # Calculate relevance score
        relevance_score = self._calculate_relevance_score(company, keywords)
        
        return RawData(
            source="ycombinator",
            source_id=company.id,
            source_url=f"{self._base_url}/companies/{company.id}" if company.website else None,
            title=company.name,
            content=self._clean_content(full_content),
            raw_content=full_content,
            author="Y Combinator",
            author_reputation=100.0,  # YC has high reputation
            upvotes=0,  # YC doesn't have voting
            downvotes=0,
            comments_count=0,
            shares_count=0,
            views_count=0,
            extracted_at=datetime.now(),
            metadata={
                "signal_type": signal_type,
                "relevance_score": relevance_score,
                "batch": company.batch,
                "status": company.status,
                "location": company.location,
                "website": company.website,
                "founded_year": company.founded_year,
                "team_size": company.team_size,
                "funding_amount": company.funding_amount,
                "valuation": company.valuation,
                "tags": company.tags,
                "industries": company.industries
            }
        )
    
    def _contains_keywords(self, content: str, keywords: List[str]) -> bool:
        """Check if content contains any of the specified keywords."""
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in keywords)
    
    def _classify_signal_type(self, company: YCCompany) -> str:
        """Classify the type of market signal based on company data."""
        
        # AI/ML companies
        ai_indicators = ["ai", "artificial intelligence", "machine learning", "ml", "automation"]
        if any(indicator in " ".join(company.tags + company.industries).lower() for indicator in ai_indicators):
            return "ai_startup"
        
        # B2B SaaS
        if "B2B" in company.tags or "SaaS" in company.tags:
            return "b2b_solution"
        
        # Developer tools
        if "Developer Tools" in company.industries or "developer" in company.description.lower():
            return "developer_tool"
        
        # Based on status
        if company.status == "Acquired":
            return "acquisition_signal"
        elif company.status == "IPO":
            return "ipo_signal"
        elif company.status == "Inactive":
            return "failure_analysis"
        
        return "startup_validation"  # Default
    
    def _calculate_relevance_score(self, company: YCCompany, keywords: List[str]) -> float:
        """Calculate relevance score for the company."""
        score = 0.0
        
        # Batch recency (newer batches get higher scores)
        try:
            batch_year = int(company.batch.split()[1]) if len(company.batch.split()) > 1 else 2020
            current_year = datetime.now().year
            years_old = current_year - batch_year
            score += max(0, 5 - years_old)  # Up to 5 points for recency
        except:
            pass
        
        # Status bonus
        status_scores = {
            "Active": 5,
            "Acquired": 8,
            "IPO": 10,
            "Inactive": 1
        }
        score += status_scores.get(company.status, 3)
        
        # Keyword matches
        content = f"{company.name} {company.description} {company.long_description or ''}".lower()
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in content)
        score += keyword_matches * 2
        
        # Funding/valuation bonus
        if company.funding_amount or company.valuation:
            score += 3
        
        return score
    
    def _parse_funding_amount(self, funding_str: str) -> int:
        """Parse funding amount string to integer value."""
        if not funding_str:
            return 0
        
        # Remove currency symbols and spaces
        clean_str = re.sub(r'[^\d\.\w]', '', funding_str.upper())
        
        # Extract number and multiplier
        match = re.search(r'(\d+\.?\d*)[KMB]?', clean_str)
        if not match:
            return 0
        
        amount = float(match.group(1))
        
        if 'K' in clean_str:
            amount *= 1000
        elif 'M' in clean_str:
            amount *= 1000000
        elif 'B' in clean_str:
            amount *= 1000000000
        
        return int(amount)
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text."""
        # Remove extra whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        return content.strip()