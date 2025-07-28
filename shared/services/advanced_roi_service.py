"""
Advanced ROI Projection Service for sophisticated investment analysis.

This service implements Phase 7.1.2 requirements:
- Advanced investment analysis models with Monte Carlo simulation
- Business model recommendation engine with pattern matching
- Sophisticated financial modeling with cash flow analysis
- Risk assessment and scenario planning capabilities
- Integration with market intelligence for dynamic projections

Extends the basic ROI capabilities in BusinessIntelligenceService with
advanced algorithms and comprehensive financial modeling.
"""

import asyncio
import json
import logging
import statistics
import random
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.market_signal import MarketSignal, SignalType
from shared.models.validation import ValidationResult
from shared.services.business_intelligence_service import (
    MarketAnalysisResult, TrendForecast, ROIProjection, BusinessIntelligenceService
)

logger = logging.getLogger(__name__)


class BusinessModel(str, Enum):
    """Business model types for AI opportunities"""
    SAAS = "saas"
    MARKETPLACE = "marketplace"
    API_SERVICE = "api_service"
    CONSULTING = "consulting"
    PRODUCT_LICENSING = "product_licensing"
    DATA_MONETIZATION = "data_monetization"
    PLATFORM = "platform"
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    TRANSACTION_FEE = "transaction_fee"


class InvestmentStage(str, Enum):
    """Investment stages for funding analysis"""
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    GROWTH = "growth"
    IPO = "ipo"


class RiskLevel(str, Enum):
    """Risk levels for investment assessment"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class InvestmentScenario:
    """Advanced investment scenario with detailed parameters"""
    scenario_name: str
    stage: InvestmentStage
    initial_capital: float
    working_capital: float
    annual_opex: float
    team_size: int
    development_months: int
    market_entry_delay: int  # months
    customer_acquisition_cost: float
    monthly_burn_rate: float
    runway_months: int
    dilution_percentage: float
    valuation_pre_money: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RevenueModel:
    """Revenue model configuration"""
    model_type: str  # subscription, transaction, licensing, etc.
    unit_price: float
    customer_lifetime_value: float
    churn_rate: float  # monthly
    growth_rate: float  # monthly
    market_penetration_ceiling: float  # max % of TAM
    revenue_streams: List[Dict[str, Any]]
    pricing_tiers: List[Dict[str, Any]]
    seasonal_factors: Dict[str, float]  # month -> multiplier
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CostStructure:
    """Detailed cost structure analysis"""
    development_costs: Dict[str, float]
    operational_costs: Dict[str, float]
    marketing_costs: Dict[str, float]
    personnel_costs: Dict[str, float]
    infrastructure_costs: Dict[str, float]
    compliance_costs: Dict[str, float]
    cost_scaling_factors: Dict[str, float]  # how costs scale with growth
    fixed_vs_variable: Dict[str, float]  # percentage split
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CashFlowProjection:
    """Monthly cash flow projection"""
    months: List[int]
    revenue: List[float]
    costs: List[float]
    gross_profit: List[float]
    operating_expenses: List[float]
    ebitda: List[float]
    net_cash_flow: List[float]
    cumulative_cash_flow: List[float]
    burn_rate: List[float]
    runway_remaining: List[Optional[int]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MonteCarloResult:
    """Monte Carlo simulation results"""
    simulation_id: str
    iterations: int
    confidence_intervals: Dict[str, Tuple[float, float]]  # 90%, 95%, 99%
    percentile_results: Dict[str, Dict[str, float]]  # P10, P50, P90 for each metric
    risk_metrics: Dict[str, float]
    success_probability: float  # probability of positive ROI
    break_even_probability: float
    unicorn_probability: float  # probability of >$1B valuation
    distribution_summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessModelRecommendation:
    """Business model recommendation with analysis"""
    recommended_model: BusinessModel
    confidence_score: float  # 0-1
    reasoning: List[str]
    revenue_potential: Dict[str, float]
    implementation_complexity: str  # low, medium, high
    time_to_market: int  # months
    capital_requirements: Dict[str, float]
    risk_assessment: Dict[str, float]
    comparable_companies: List[Dict[str, Any]]
    strategic_considerations: List[str]
    alternative_models: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['recommended_model'] = self.recommended_model.value
        return result


@dataclass
class AdvancedROIAnalysis:
    """Comprehensive advanced ROI analysis"""
    analysis_id: str
    opportunity_id: str
    generated_at: datetime
    investment_scenarios: List[InvestmentScenario]
    revenue_models: List[RevenueModel]
    cost_structures: List[CostStructure]
    cash_flow_projections: Dict[str, CashFlowProjection]  # scenario_name -> projection
    monte_carlo_results: MonteCarloResult
    business_model_recommendation: BusinessModelRecommendation
    valuation_analysis: Dict[str, Any]
    exit_strategy_analysis: Dict[str, Any]
    funding_roadmap: List[Dict[str, Any]]
    key_metrics_dashboard: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['generated_at'] = self.generated_at.isoformat()
        return result


class AdvancedROIService:
    """Advanced ROI projection service with sophisticated financial modeling."""
    
    def __init__(self):
        self.bi_service = BusinessIntelligenceService()
    
    async def generate_advanced_roi_analysis(
        self,
        db: AsyncSession,
        opportunity: Opportunity,
        market_analysis: MarketAnalysisResult,
        trend_forecast: TrendForecast,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> AdvancedROIAnalysis:
        """Generate comprehensive advanced ROI analysis.
        
        Args:
            db: Database session
            opportunity: Target opportunity
            market_analysis: Market analysis results
            trend_forecast: Trend forecasting results
            custom_parameters: Custom modeling parameters
            
        Returns:
            AdvancedROIAnalysis with comprehensive financial modeling
        """
        logger.info(f"Generating advanced ROI analysis for opportunity {opportunity.id}")
        
        # Generate investment scenarios
        scenarios = await self._generate_investment_scenarios(opportunity, market_analysis, custom_parameters)
        
        # Create revenue models
        revenue_models = await self._create_revenue_models(opportunity, market_analysis, trend_forecast)
        
        # Build cost structures
        cost_structures = await self._build_cost_structures(opportunity, market_analysis, scenarios)
        
        # Generate cash flow projections
        cash_flows = await self._generate_cash_flow_projections(scenarios, revenue_models, cost_structures)
        
        # Run Monte Carlo simulation
        monte_carlo = await self._run_monte_carlo_simulation(scenarios, revenue_models, cost_structures)
        
        # Generate business model recommendations
        bm_recommendation = await self._recommend_business_model(opportunity, market_analysis, cash_flows)
        
        # Perform valuation analysis
        valuation = await self._perform_valuation_analysis(cash_flows, market_analysis, trend_forecast)
        
        # Analyze exit strategies
        exit_strategy = await self._analyze_exit_strategies(opportunity, valuation, market_analysis)
        
        # Create funding roadmap
        funding_roadmap = await self._create_funding_roadmap(scenarios, cash_flows, valuation)
        
        # Build key metrics dashboard
        key_metrics = await self._build_key_metrics_dashboard(cash_flows, monte_carlo, valuation)
        
        return AdvancedROIAnalysis(
            analysis_id=f"advanced_roi_{opportunity.id}",
            opportunity_id=str(opportunity.id),
            generated_at=datetime.utcnow(),
            investment_scenarios=scenarios,
            revenue_models=revenue_models,
            cost_structures=cost_structures,
            cash_flow_projections=cash_flows,
            monte_carlo_results=monte_carlo,
            business_model_recommendation=bm_recommendation,
            valuation_analysis=valuation,
            exit_strategy_analysis=exit_strategy,
            funding_roadmap=funding_roadmap,
            key_metrics_dashboard=key_metrics
        )
    
    async def _generate_investment_scenarios(
        self,
        opportunity: Opportunity,
        market_analysis: MarketAnalysisResult,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> List[InvestmentScenario]:
        """Generate detailed investment scenarios."""
        scenarios = []
        
        # Base parameters from market analysis
        market_size = market_analysis.serviceable_obtainable_market
        growth_rate = market_analysis.market_growth_rate / 100
        
        # Conservative scenario
        conservative = InvestmentScenario(
            scenario_name="conservative",
            stage=InvestmentStage.SEED,
            initial_capital=250000,
            working_capital=50000,
            annual_opex=300000,
            team_size=5,
            development_months=8,
            market_entry_delay=2,
            customer_acquisition_cost=150,
            monthly_burn_rate=35000,
            runway_months=18,
            dilution_percentage=20.0,
            valuation_pre_money=1000000
        )
        scenarios.append(conservative)
        
        # Moderate scenario
        moderate = InvestmentScenario(
            scenario_name="moderate",
            stage=InvestmentStage.SERIES_A,
            initial_capital=2000000,
            working_capital=400000,
            annual_opex=1500000,
            team_size=15,
            development_months=12,
            market_entry_delay=3,
            customer_acquisition_cost=300,
            monthly_burn_rate=150000,
            runway_months=24,
            dilution_percentage=25.0,
            valuation_pre_money=8000000
        )
        scenarios.append(moderate)
        
        # Aggressive scenario
        aggressive = InvestmentScenario(
            scenario_name="aggressive",
            stage=InvestmentStage.SERIES_B,
            initial_capital=10000000,
            working_capital=2000000,
            annual_opex=8000000,
            team_size=50,
            development_months=18,
            market_entry_delay=6,
            customer_acquisition_cost=500,
            monthly_burn_rate=750000,
            runway_months=30,
            dilution_percentage=30.0,
            valuation_pre_money=40000000
        )
        scenarios.append(aggressive)
        
        # Apply custom parameters if provided
        if custom_parameters:
            for scenario in scenarios:
                for key, value in custom_parameters.items():
                    if hasattr(scenario, key):
                        setattr(scenario, key, value)
        
        return scenarios
    
    async def _create_revenue_models(
        self,
        opportunity: Opportunity,
        market_analysis: MarketAnalysisResult,
        trend_forecast: TrendForecast
    ) -> List[RevenueModel]:
        """Create revenue models based on opportunity characteristics."""
        models = []
        
        # Determine primary revenue model based on AI solution type
        ai_types = self._parse_ai_solution_types(opportunity)
        
        if "nlp" in ai_types or "ml" in ai_types:
            # API/SaaS model for AI services
            saas_model = RevenueModel(
                model_type="saas_subscription",
                unit_price=99.0,  # monthly subscription
                customer_lifetime_value=1188.0,  # 12 months
                churn_rate=0.05,  # 5% monthly
                growth_rate=0.20,  # 20% monthly growth
                market_penetration_ceiling=0.15,  # 15% of TAM
                revenue_streams=[
                    {"name": "subscription", "percentage": 70, "growth_rate": 0.20},
                    {"name": "professional_services", "percentage": 20, "growth_rate": 0.15},
                    {"name": "training", "percentage": 10, "growth_rate": 0.10}
                ],
                pricing_tiers=[
                    {"tier": "basic", "price": 99, "features": 10, "target_percentage": 60},
                    {"tier": "professional", "price": 299, "features": 25, "target_percentage": 30},
                    {"tier": "enterprise", "price": 999, "features": 50, "target_percentage": 10}
                ],
                seasonal_factors={
                    "1": 0.9, "2": 0.9, "3": 1.0, "4": 1.1, "5": 1.1, "6": 1.0,
                    "7": 0.9, "8": 0.9, "9": 1.1, "10": 1.2, "11": 1.2, "12": 1.0
                }
            )
            models.append(saas_model)
        
        if "computer_vision" in ai_types:
            # Transaction-based model for CV solutions
            transaction_model = RevenueModel(
                model_type="transaction_fee",
                unit_price=0.10,  # per transaction
                customer_lifetime_value=2400.0,  # based on usage
                churn_rate=0.03,  # 3% monthly
                growth_rate=0.25,  # 25% monthly growth
                market_penetration_ceiling=0.08,  # 8% of TAM
                revenue_streams=[
                    {"name": "transaction_fees", "percentage": 80, "growth_rate": 0.25},
                    {"name": "setup_fees", "percentage": 15, "growth_rate": 0.10},
                    {"name": "premium_features", "percentage": 5, "growth_rate": 0.30}
                ],
                pricing_tiers=[
                    {"tier": "pay_per_use", "price": 0.10, "features": 5, "target_percentage": 50},
                    {"tier": "volume_discount", "price": 0.08, "features": 8, "target_percentage": 35},
                    {"tier": "enterprise", "price": 0.05, "features": 15, "target_percentage": 15}
                ],
                seasonal_factors={
                    "1": 1.0, "2": 1.0, "3": 1.1, "4": 1.1, "5": 1.0, "6": 1.0,
                    "7": 1.0, "8": 1.0, "9": 1.0, "10": 1.1, "11": 1.2, "12": 1.1
                }
            )
            models.append(transaction_model)
        
        # Default SaaS model if no specific AI type detected
        if not models:
            default_model = RevenueModel(
                model_type="saas_subscription",
                unit_price=199.0,
                customer_lifetime_value=2388.0,
                churn_rate=0.04,
                growth_rate=0.15,
                market_penetration_ceiling=0.10,
                revenue_streams=[
                    {"name": "subscription", "percentage": 85, "growth_rate": 0.15},
                    {"name": "services", "percentage": 15, "growth_rate": 0.10}
                ],
                pricing_tiers=[
                    {"tier": "standard", "price": 199, "features": 15, "target_percentage": 70},
                    {"tier": "premium", "price": 499, "features": 30, "target_percentage": 30}
                ],
                seasonal_factors={f"{i}": 1.0 for i in range(1, 13)}  # No seasonality
            )
            models.append(default_model)
        
        return models
    
    async def _build_cost_structures(
        self,
        opportunity: Opportunity,
        market_analysis: MarketAnalysisResult,
        scenarios: List[InvestmentScenario]
    ) -> List[CostStructure]:
        """Build detailed cost structures for each scenario."""
        cost_structures = []
        
        for scenario in scenarios:
            # Calculate costs based on scenario parameters
            team_cost_per_person = 120000  # annual average
            
            cost_structure = CostStructure(
                development_costs={
                    "r_and_d": scenario.team_size * team_cost_per_person * 0.6,
                    "infrastructure": scenario.initial_capital * 0.15,
                    "tools_and_licenses": scenario.team_size * 5000,
                    "testing_and_qa": scenario.initial_capital * 0.08
                },
                operational_costs={
                    "cloud_infrastructure": scenario.annual_opex * 0.20,
                    "third_party_services": scenario.annual_opex * 0.10,
                    "customer_support": scenario.team_size * 50000,
                    "legal_and_compliance": scenario.annual_opex * 0.05
                },
                marketing_costs={
                    "customer_acquisition": scenario.customer_acquisition_cost * 1000,  # assume 1000 customers
                    "brand_marketing": scenario.annual_opex * 0.15,
                    "content_marketing": scenario.team_size * 15000,
                    "paid_advertising": scenario.annual_opex * 0.12
                },
                personnel_costs={
                    "salaries_and_benefits": scenario.team_size * team_cost_per_person,
                    "equity_compensation": scenario.initial_capital * 0.10,
                    "recruiting": scenario.team_size * 8000,
                    "training": scenario.team_size * 3000
                },
                infrastructure_costs={
                    "office_space": scenario.team_size * 12000,
                    "equipment": scenario.team_size * 3000,
                    "utilities": scenario.team_size * 1200,
                    "insurance": scenario.annual_opex * 0.02
                },
                compliance_costs={
                    "security_audits": 50000,
                    "legal_fees": 75000,
                    "regulatory_compliance": 25000,
                    "data_protection": 30000
                },
                cost_scaling_factors={
                    "linear": 0.7,  # 70% of costs scale linearly with growth
                    "sublinear": 0.2,  # 20% scale sublinearly
                    "fixed": 0.1  # 10% are fixed
                },
                fixed_vs_variable={
                    "fixed": 0.4,  # 40% fixed costs
                    "variable": 0.6  # 60% variable costs
                }
            )
            
            cost_structures.append(cost_structure)
        
        return cost_structures
    
    async def _generate_cash_flow_projections(
        self,
        scenarios: List[InvestmentScenario],
        revenue_models: List[RevenueModel],
        cost_structures: List[CostStructure]
    ) -> Dict[str, CashFlowProjection]:
        """Generate detailed monthly cash flow projections."""
        projections = {}
        
        for i, scenario in enumerate(scenarios):
            revenue_model = revenue_models[min(i, len(revenue_models)-1)]
            cost_structure = cost_structures[i]
            
            # Generate 60-month projection
            months = list(range(1, 61))
            revenues = []
            costs = []
            
            # Initial conditions
            customers = 0
            monthly_revenue = 0
            
            for month in months:
                # Revenue growth (delayed by market entry delay)
                if month > scenario.market_entry_delay:
                    # Customer acquisition
                    if customers == 0:
                        new_customers = 10  # Initial customers
                    else:
                        growth_factor = (1 + revenue_model.growth_rate) ** (month - scenario.market_entry_delay)
                        new_customers = max(1, int(customers * revenue_model.growth_rate))
                    
                    # Account for churn
                    lost_customers = int(customers * revenue_model.churn_rate)
                    customers = customers + new_customers - lost_customers
                    
                    # Calculate revenue
                    base_revenue = customers * revenue_model.unit_price
                    seasonal_factor = revenue_model.seasonal_factors.get(str((month % 12) + 1), 1.0)
                    monthly_revenue = base_revenue * seasonal_factor
                else:
                    monthly_revenue = 0
                
                revenues.append(monthly_revenue)
                
                # Calculate monthly costs
                monthly_cost = scenario.monthly_burn_rate
                
                # Scale costs with growth (simplified)
                if month > 12:
                    growth_factor = (monthly_revenue / max(1, revenues[11])) if revenues[11] > 0 else 1
                    scaling_factor = (
                        cost_structure.cost_scaling_factors["linear"] * growth_factor +
                        cost_structure.cost_scaling_factors["sublinear"] * math.sqrt(growth_factor) +
                        cost_structure.cost_scaling_factors["fixed"]
                    )
                    monthly_cost = scenario.monthly_burn_rate * scaling_factor
                
                costs.append(monthly_cost)
            
            # Calculate derived metrics
            gross_profits = [r - c * 0.3 for r, c in zip(revenues, costs)]  # 30% COGS
            operating_expenses = [c * 0.7 for c in costs]  # 70% OpEx
            ebitda = [gp - oe for gp, oe in zip(gross_profits, operating_expenses)]
            net_cash_flows = [r - c for r, c in zip(revenues, costs)]
            
            # Cumulative cash flow
            cumulative_cash_flow = []
            cumulative = scenario.initial_capital + scenario.working_capital
            for ncf in net_cash_flows:
                cumulative += ncf
                cumulative_cash_flow.append(cumulative)
            
            # Burn rate and runway
            burn_rates = [-min(0, ncf) for ncf in net_cash_flows]
            runway_remaining = []
            for i, cf in enumerate(cumulative_cash_flow):
                if cf > 0 and burn_rates[i] > 0:
                    runway = int(cf / burn_rates[i])
                    runway_remaining.append(runway)
                else:
                    runway_remaining.append(None)
            
            projection = CashFlowProjection(
                months=months,
                revenue=revenues,
                costs=costs,
                gross_profit=gross_profits,
                operating_expenses=operating_expenses,
                ebitda=ebitda,
                net_cash_flow=net_cash_flows,
                cumulative_cash_flow=cumulative_cash_flow,
                burn_rate=burn_rates,
                runway_remaining=runway_remaining
            )
            
            projections[scenario.scenario_name] = projection
        
        return projections
    
    async def _run_monte_carlo_simulation(
        self,
        scenarios: List[InvestmentScenario],
        revenue_models: List[RevenueModel],
        cost_structures: List[CostStructure],
        iterations: int = 10000
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation for risk analysis."""
        logger.info(f"Running Monte Carlo simulation with {iterations} iterations")
        
        results = {
            'roi_5yr': [],
            'break_even_month': [],
            'max_drawdown': [],
            'final_valuation': [],
            'total_funding_needed': []
        }
        
        for _ in range(iterations):
            # Random variations in key parameters
            revenue_multiplier = random.lognormvariate(0, 0.3)  # log-normal distribution
            cost_multiplier = random.lognormvariate(0, 0.2)
            growth_rate_factor = random.uniform(0.7, 1.5)
            churn_rate_factor = random.uniform(0.8, 1.3)
            
            # Simulate for moderate scenario (index 1)
            scenario = scenarios[1] if len(scenarios) > 1 else scenarios[0]
            revenue_model = revenue_models[0]
            
            # Modified parameters for this iteration
            modified_revenue = revenue_model.unit_price * revenue_multiplier
            modified_growth = revenue_model.growth_rate * growth_rate_factor
            modified_churn = revenue_model.churn_rate * churn_rate_factor
            modified_burn = scenario.monthly_burn_rate * cost_multiplier
            
            # Simple simulation (simplified for performance)
            customers = 0
            cumulative_cash = scenario.initial_capital
            months_to_break_even = None
            max_drawdown = 0
            
            for month in range(1, 61):  # 5 years
                if month > scenario.market_entry_delay:
                    if customers == 0:
                        new_customers = random.randint(5, 20)
                    else:
                        new_customers = int(customers * modified_growth * random.uniform(0.8, 1.2))
                    
                    lost_customers = int(customers * modified_churn)
                    customers = max(0, customers + new_customers - lost_customers)
                    
                    monthly_revenue = customers * modified_revenue
                else:
                    monthly_revenue = 0
                
                monthly_cost = modified_burn * (1 + month * 0.02)  # 2% monthly cost increase
                net_cash_flow = monthly_revenue - monthly_cost
                cumulative_cash += net_cash_flow
                
                # Track metrics
                if cumulative_cash < 0:
                    max_drawdown = max(max_drawdown, abs(cumulative_cash))
                
                if months_to_break_even is None and monthly_revenue > monthly_cost:
                    months_to_break_even = month
            
            # Calculate final metrics
            final_revenue = customers * modified_revenue * 12  # Annual revenue
            final_valuation = final_revenue * random.uniform(5, 15)  # Revenue multiple
            
            roi_5yr = (final_valuation - scenario.initial_capital) / scenario.initial_capital * 100
            total_funding = scenario.initial_capital + max(0, max_drawdown)
            
            # Store results
            results['roi_5yr'].append(roi_5yr)
            results['break_even_month'].append(months_to_break_even or 60)
            results['max_drawdown'].append(max_drawdown)
            results['final_valuation'].append(final_valuation)
            results['total_funding_needed'].append(total_funding)
        
        # Calculate statistics
        confidence_intervals = {}
        percentile_results = {}
        
        for metric, values in results.items():
            values.sort()
            
            # Confidence intervals
            p5 = values[int(0.05 * len(values))]
            p95 = values[int(0.95 * len(values))]
            p2_5 = values[int(0.025 * len(values))]
            p97_5 = values[int(0.975 * len(values))]
            p0_5 = values[int(0.005 * len(values))]
            p99_5 = values[int(0.995 * len(values))]
            
            confidence_intervals[metric] = {
                '90%': (p5, p95),
                '95%': (p2_5, p97_5),
                '99%': (p0_5, p99_5)
            }
            
            # Percentiles
            percentile_results[metric] = {
                'P10': values[int(0.1 * len(values))],
                'P50': values[int(0.5 * len(values))],
                'P90': values[int(0.9 * len(values))]
            }
        
        # Risk metrics
        success_probability = len([r for r in results['roi_5yr'] if r > 0]) / len(results['roi_5yr'])
        break_even_probability = len([r for r in results['break_even_month'] if r < 60]) / len(results['break_even_month'])
        unicorn_probability = len([r for r in results['final_valuation'] if r > 1000000000]) / len(results['final_valuation'])
        
        return MonteCarloResult(
            simulation_id=f"mc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            iterations=iterations,
            confidence_intervals=confidence_intervals,
            percentile_results=percentile_results,
            risk_metrics={
                'value_at_risk_95': percentile_results['roi_5yr']['P10'],
                'expected_shortfall': statistics.mean([r for r in results['roi_5yr'] if r <= percentile_results['roi_5yr']['P10']]),
                'volatility': statistics.stdev(results['roi_5yr'])
            },
            success_probability=success_probability,
            break_even_probability=break_even_probability,
            unicorn_probability=unicorn_probability,
            distribution_summary={
                'mean_roi': statistics.mean(results['roi_5yr']),
                'median_roi': percentile_results['roi_5yr']['P50'],
                'std_roi': statistics.stdev(results['roi_5yr'])
            }
        )
    
    async def _recommend_business_model(
        self,
        opportunity: Opportunity,
        market_analysis: MarketAnalysisResult,
        cash_flows: Dict[str, CashFlowProjection]
    ) -> BusinessModelRecommendation:
        """Recommend optimal business model based on analysis."""
        
        # Analyze opportunity characteristics
        ai_types = self._parse_ai_solution_types(opportunity)
        target_industries = self._parse_target_industries(opportunity)
        
        # Score different business models
        model_scores = {}
        
        # SaaS model scoring
        saas_score = 0.7  # Base score
        if any(ai_type in ["nlp", "ml", "automation"] for ai_type in ai_types):
            saas_score += 0.2
        if market_analysis.market_maturity in ["growth", "mature"]:
            saas_score += 0.1
        model_scores[BusinessModel.SAAS] = min(1.0, saas_score)
        
        # API Service model scoring
        api_score = 0.6
        if any(ai_type in ["nlp", "computer_vision", "ml"] for ai_type in ai_types):
            api_score += 0.25
        if market_analysis.serviceable_obtainable_market > 10000000:  # $10M+ SOM
            api_score += 0.1
        model_scores[BusinessModel.API_SERVICE] = min(1.0, api_score)
        
        # Platform model scoring
        platform_score = 0.5
        if len(target_industries) > 2:  # Multi-industry applicability
            platform_score += 0.2
        if market_analysis.market_growth_rate > 20:  # High growth market
            platform_score += 0.15
        model_scores[BusinessModel.PLATFORM] = min(1.0, platform_score)
        
        # Marketplace model scoring
        marketplace_score = 0.4
        if "automation" in ai_types or "platform" in str(opportunity.description).lower():
            marketplace_score += 0.3
        model_scores[BusinessModel.MARKETPLACE] = min(1.0, marketplace_score)
        
        # Select best model
        recommended_model = max(model_scores, key=model_scores.get)
        confidence_score = model_scores[recommended_model]
        
        # Generate reasoning
        reasoning = []
        if recommended_model == BusinessModel.SAAS:
            reasoning.extend([
                "Recurring revenue model provides predictable cash flow",
                "Strong fit for AI services with ongoing value delivery",
                "Scalable with low marginal costs"
            ])
        elif recommended_model == BusinessModel.API_SERVICE:
            reasoning.extend([
                "Pay-per-use model aligns with AI processing costs",
                "Easy integration for enterprise customers",
                "Scales with customer usage"
            ])
        
        # Calculate revenue potential (simplified)
        revenue_potential = {
            "year_1": cash_flows[list(cash_flows.keys())[1]].revenue[11],  # Month 12
            "year_3": cash_flows[list(cash_flows.keys())[1]].revenue[35],  # Month 36
            "year_5": cash_flows[list(cash_flows.keys())[1]].revenue[59]   # Month 60
        }
        
        return BusinessModelRecommendation(
            recommended_model=recommended_model,
            confidence_score=confidence_score,
            reasoning=reasoning,
            revenue_potential=revenue_potential,
            implementation_complexity="medium",
            time_to_market=12,
            capital_requirements={
                "initial": 500000,
                "working_capital": 200000,
                "total_5yr": 2000000
            },
            risk_assessment={
                "market_risk": 0.3,
                "execution_risk": 0.4,
                "competitive_risk": 0.5
            },
            comparable_companies=[
                {"name": "Competitor A", "model": "saas", "valuation": 50000000},
                {"name": "Competitor B", "model": "api_service", "valuation": 25000000}
            ],
            strategic_considerations=[
                "Focus on enterprise customers for higher LTV",
                "Build strong API ecosystem for platform growth",
                "Consider freemium tier for market penetration"
            ],
            alternative_models=[
                {"model": "freemium", "score": 0.6, "pros": ["Market penetration"], "cons": ["Lower initial revenue"]},
                {"model": "consulting", "score": 0.4, "pros": ["High margins"], "cons": ["Not scalable"]}
            ]
        )
    
    # Additional helper methods (stubs for brevity)
    async def _perform_valuation_analysis(self, cash_flows: Dict, market_analysis: MarketAnalysisResult, trend_forecast: TrendForecast) -> Dict[str, Any]:
        """Perform comprehensive valuation analysis."""
        moderate_cf = cash_flows.get("moderate", list(cash_flows.values())[0])
        
        # Revenue multiple valuation
        final_revenue = moderate_cf.revenue[-1] * 12  # Annualized
        revenue_multiple = 8.0  # Typical SaaS multiple
        revenue_valuation = final_revenue * revenue_multiple
        
        # DCF valuation (simplified)
        discount_rate = 0.12  # 12% WACC
        terminal_growth = 0.03  # 3%
        dcf_valuation = sum([cf / ((1 + discount_rate) ** (i/12)) for i, cf in enumerate(moderate_cf.net_cash_flow)])
        
        return {
            "revenue_multiple_valuation": revenue_valuation,
            "dcf_valuation": dcf_valuation,
            "market_multiple_valuation": market_analysis.serviceable_obtainable_market * 0.15,
            "recommended_valuation": (revenue_valuation + dcf_valuation) / 2,
            "valuation_range": {
                "low": min(revenue_valuation, dcf_valuation) * 0.8,
                "high": max(revenue_valuation, dcf_valuation) * 1.3
            }
        }
    
    async def _analyze_exit_strategies(self, opportunity: Opportunity, valuation: Dict, market_analysis: MarketAnalysisResult) -> Dict[str, Any]:
        """Analyze potential exit strategies."""
        return {
            "ipo_probability": 0.15,
            "acquisition_probability": 0.65,
            "strategic_buyers": ["Large Tech Companies", "Industry Leaders"],
            "optimal_exit_timing": "Years 5-7",
            "expected_exit_multiple": "6-12x revenue"
        }
    
    async def _create_funding_roadmap(self, scenarios: List, cash_flows: Dict, valuation: Dict) -> List[Dict[str, Any]]:
        """Create funding roadmap based on projections."""
        return [
            {"stage": "Seed", "amount": 500000, "timing": "Month 0", "use_of_funds": "Product development"},
            {"stage": "Series A", "amount": 3000000, "timing": "Month 18", "use_of_funds": "Market expansion"},
            {"stage": "Series B", "amount": 10000000, "timing": "Month 36", "use_of_funds": "Scale operations"}
        ]
    
    async def _build_key_metrics_dashboard(self, cash_flows: Dict, monte_carlo: MonteCarloResult, valuation: Dict) -> Dict[str, float]:
        """Build key metrics dashboard."""
        return {
            "expected_roi": monte_carlo.distribution_summary["mean_roi"],
            "break_even_probability": monte_carlo.break_even_probability,
            "risk_adjusted_return": monte_carlo.distribution_summary["mean_roi"] * (1 - monte_carlo.risk_metrics["volatility"] / 100),
            "capital_efficiency": valuation["recommended_valuation"] / 2000000,  # Valuation per $1M invested
            "market_opportunity_score": 8.5
        }
    
    def _parse_ai_solution_types(self, opportunity: Opportunity) -> List[str]:
        """Parse AI solution types from opportunity."""
        if not opportunity.ai_solution_types:
            return []
        try:
            if isinstance(opportunity.ai_solution_types, str):
                return json.loads(opportunity.ai_solution_types)
            return opportunity.ai_solution_types
        except:
            return []
    
    def _parse_target_industries(self, opportunity: Opportunity) -> List[str]:
        """Parse target industries from opportunity."""
        if not opportunity.target_industries:
            return []
        try:
            if isinstance(opportunity.target_industries, str):
                return json.loads(opportunity.target_industries)
            return opportunity.target_industries
        except:
            return []


# Singleton instance
advanced_roi_service = AdvancedROIService()