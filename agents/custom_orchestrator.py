"""
Custom orchestrator that uses DSPy's raw text generation without structured output
to avoid Gemini API compatibility issues.
"""
import dspy
import asyncio
import os
import re
import logging

logger = logging.getLogger(__name__)

class CustomOrchestrator:
    def __init__(self):
        # Configure DSPy for text generation only
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        logger.info("Using custom orchestrator with Gemini 1.5 Flash")
        self.llm = dspy.LM(
            model="gemini/gemini-1.5-flash",
            api_key=gemini_key,
            max_tokens=2048,
            temperature=0.7,  # Higher temperature for more varied responses
            # Disable caching
            cache=False
        )
        dspy.settings.configure(lm=self.llm, max_bootstrapped_demos=0, max_labeled_demos=0)
        
        # Create a simple text completion predictor
        self.text_generator = dspy.Predict("question -> answer")

    def _extract_section(self, text, section_name):
        """Extract a specific section from formatted text"""
        pattern = rf"{section_name}:\s*(.*?)(?=\n\n|\n[A-Z][a-z]+:|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text  # Fallback to full text if section not found

    async def analyze_opportunity(self, topic):
        """
        Analyze opportunity using sequential text generation calls
        """
        logger.info(f"Starting custom orchestration for topic: {topic}...")
        
        try:
            # Step 1: Market Research
            logger.info("Step 1: Conducting market research...")
            market_prompt = f"""
            Conduct comprehensive market research for: {topic}
            
            Provide a detailed analysis covering:
            - Current market size and growth trends
            - Key customer segments and their needs
            - Market gaps and opportunities
            - Technology trends relevant to this space
            
            Format your response as a structured report.
            """
            
            def run_market_research():
                return self.text_generator(question=market_prompt)
            
            market_result = await asyncio.to_thread(run_market_research)
            market_research = market_result.answer
            logger.info(f"Market research completed: {len(market_research)} characters")
            
            # Step 2: Competitive Analysis
            logger.info("Step 2: Performing competitive analysis...")
            competitive_prompt = f"""
            Based on this market research:
            
            {market_research}
            
            Analyze the competitive landscape for {topic}, including:
            - Top 3-5 key competitors and their positioning
            - Competitive strengths and weaknesses
            - Market differentiation opportunities
            - Barriers to entry and competitive moats
            
            Provide a structured competitive analysis.
            """
            
            def run_competitive_analysis():
                return self.text_generator(question=competitive_prompt)
            
            competitive_result = await asyncio.to_thread(run_competitive_analysis)
            competitive_analysis = competitive_result.answer
            logger.info(f"Competitive analysis completed: {len(competitive_analysis)} characters")
            
            # Step 3: AI Opportunity Synthesis
            logger.info("Step 3: Synthesizing AI opportunity...")
            synthesis_prompt = f"""
            Based on this market research and competitive analysis:
            
            MARKET RESEARCH:
            {market_research}
            
            COMPETITIVE ANALYSIS:
            {competitive_analysis}
            
            Synthesize a specific, actionable AI opportunity for {topic}. 
            
            IMPORTANT: Structure your response EXACTLY as follows (no markdown formatting, no asterisks):
            
            Title: [Concise opportunity title]
            
            Description: [2-3 paragraph description of the opportunity including target users, AI solution approach, market potential, and implementation considerations]
            
            Summary: [1-2 sentences executive summary under 400 characters that captures the key value proposition and business opportunity]
            """
            
            def run_synthesis():
                return self.text_generator(question=synthesis_prompt)
            
            synthesis_result = await asyncio.to_thread(run_synthesis)
            ai_opportunity = synthesis_result.answer
            logger.info(f"Synthesis completed: {len(ai_opportunity)} characters")
            
            logger.info("\n--- Generated AI Opportunity ---")
            logger.info(ai_opportunity[:500] + "..." if len(ai_opportunity) > 500 else ai_opportunity)
            
            return ai_opportunity
            
        except Exception as e:
            logger.error(f"Custom orchestration failed: {e}")
            raise