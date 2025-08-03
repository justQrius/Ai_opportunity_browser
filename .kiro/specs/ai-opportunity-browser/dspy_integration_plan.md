# DSPy Integration Plan for AI Opportunity Browser

## 1. Introduction & Goals

The current multi-agent system, located in the `agents/` directory, relies on a complex, manually orchestrated architecture. Key files like `orchestrator.py` and `planner_agent.py` implement an imperative workflow that is brittle, difficult to maintain, and challenging to optimize. Each step is a rigid, hard-coded prompt chain, making the system resistant to change and improvement.

This plan proposes a refactoring to replace the existing system with a declarative, self-optimizing pipeline using the **DSPy framework**. DSPy shifts the paradigm from "prompt engineering" to "programming," where models and pipelines are defined programmatically and can be systematically optimized with data.

The primary goals of this integration are:
*   **Increase Reliability**: Replace brittle prompt chains with a robust, data-driven pipeline.
*   **Simplify the Codebase**: Consolidate complex logic into a single, declarative DSPy module.
*   **Improve Performance**: Leverage DSPy's optimizers (`teleprompters`) to compile the pipeline for higher accuracy and lower latency.
*   **Enhance Adaptability**: Easily swap and test different LLMs without rewriting the core logic.

## 2. Proposed DSPy Architecture

The new architecture will be centralized in a new file, `agents/dspy_modules.py`. This file will contain the core building blocks of our pipeline: `Signatures` that define the input/output behavior of each step, and a `Module` that composes these signatures into a coherent workflow.

This single module will replace the distributed logic currently found in `planner_agent.py` and `orchestrator.py`.

### Core DSPy Signatures

The following signatures define the contracts for our AI tasks:

```python
import dspy

class MarketResearchSignature(dspy.Signature):
    """
    Conducts market research for a given topic to identify potential opportunities.
    """
    topic = dspy.InputField(desc="The high-level topic for market research.")
    market_research_report = dspy.OutputField(desc="A detailed report on market trends, customer needs, and potential opportunities.")

class CompetitiveAnalysisSignature(dspy.Signature):
    """
    Analyzes the competitive landscape based on a market research report.
    """
    market_research_report = dspy.InputField(desc="The market research report to analyze.")
    competitive_analysis = dspy.OutputField(desc="An analysis of key competitors, their strengths, weaknesses, and market positioning.")

class SynthesisSignature(dspy.Signature):
    """
    Synthesizes market research and competitive analysis into a concrete, actionable AI opportunity.
    """
    market_research_report = dspy.InputField(desc="The market research report.")
    competitive_analysis = dspy.InputField(desc="The competitive analysis report.")
    ai_opportunity = dspy.OutputField(desc="A specific, well-defined AI opportunity, including a proposed solution and target user.")
```

### Main Opportunity Analysis Pipeline

The `OpportunityAnalysisPipeline` module composes the signatures into a declarative pipeline. The flow of data is handled automatically by DSPy based on the signature definitions.

```python
import dspy

# Assume Signatures from above are in the same file

class OpportunityAnalysisPipeline(dspy.Module):
    """
    A declarative pipeline for identifying AI opportunities.
    """
    def __init__(self):
        super().__init__()
        self.market_research = dspy.Predict(MarketResearchSignature)
        self.competitive_analysis = dspy.Predict(CompetitiveAnalysisSignature)
        self.synthesis = dspy.Predict(SynthesisSignature)

    def forward(self, topic):
        # 1. Conduct market research
        research = self.market_research(topic=topic)

        # 2. Perform competitive analysis
        analysis = self.competitive_analysis(market_research_report=research.market_research_report)

        # 3. Synthesize the final opportunity
        opportunity = self.synthesis(
            market_research_report=research.market_research_report,
            competitive_analysis=analysis.competitive_analysis
        )

        return opportunity
```

## 3. Implementation Steps

### Step 1: Create Core DSPy Components

The first step is to create the new file `agents/dspy_modules.py` and populate it with the `Signatures` and the `OpportunityAnalysisPipeline` module defined in the section above. This centralizes the core logic of the agent workflow into a single, manageable location.

### Step 2: Refactor the Orchestrator

Next, we will refactor `agents/orchestrator.py` to use our new DSPy pipeline. The complex, multi-step `trigger_dynamic_workflow` method will be replaced with a simple initialization of the DSPy environment and a single call to our pipeline.

**Simplified `agents/orchestrator.py`:**

```python
import dspy
from .dspy_modules import OpportunityAnalysisPipeline

class Orchestrator:
    def __init__(self, openai_api_key):
        # Configure DSPy settings
        self.turbo = dspy.OpenAI(model='gpt-3.5-turbo', api_key=openai_api_key)
        dspy.settings.configure(lm=self.turbo)

        # Initialize the declarative pipeline
        self.pipeline = OpportunityAnalysisPipeline()

    def analyze_opportunity(self, topic):
        """
        Triggers the self-optimizing DSPy pipeline to analyze a topic.
        """
        print(f"Starting DSPy pipeline for topic: {topic}...")

        # Execute the pipeline with a single call
        final_opportunity = self.pipeline(topic=topic)

        print("DSPy pipeline finished.")
        print("\n--- Generated AI Opportunity ---")
        print(final_opportunity.ai_opportunity)

        return final_opportunity.ai_opportunity

# Example usage:
# if __name__ == "__main__":
#     import os
#     orchestrator = Orchestrator(openai_api_key=os.getenv("OPENAI_API_KEY"))
#     orchestrator.analyze_opportunity("AI-powered code review assistants")
```

### Step 3: Optimization (Future Work)

The true power of DSPy lies in its ability to optimize pipelines. Once the initial refactoring is complete, the next phase is to compile the `OpportunityAnalysisPipeline` for production. This involves:

1.  **Creating a Training Set**: We will need to build a small dataset (`trainset`) of example inputs and desired outputs. Each example would be a `dspy.Example` containing a `topic` and the ideal `ai_opportunity`.
2.  **Defining an Evaluation Metric**: A custom metric function (`metric`) will be created to score the quality of the pipeline's output against the gold-standard examples in our training set.
3.  **Compiling the Pipeline**: We will use a `dspy.teleprompt` optimizer, such as `BootstrapFewShot`, to "compile" the pipeline. The optimizer will explore different few-shot prompt variations for each step, test them against the training data using our metric, and bake the best-performing prompts directly into the pipeline.

**Conceptual Optimization Code:**

```python
from dspy.teleprompt import BootstrapFewShot

# 1. Assume trainset is a list of dspy.Example objects
# trainset = [dspy.Example(topic=..., ai_opportunity=...).with_inputs('topic')]

# 2. Assume validation_metric is a function: (example, prediction, trace) -> bool
# def validation_metric(example, pred, trace=None):
#     # Logic to check if pred.ai_opportunity is a high-quality output
#     return "solution" in pred.ai_opportunity.lower() and "target user" in pred.ai_opportunity.lower()

# 3. Configure the teleprompter
teleprompter = BootstrapFewShot(metric=validation_metric)

# 4. Compile the pipeline
compiled_pipeline = teleprompter.compile(OpportunityAnalysisPipeline(), trainset=trainset)

# The compiled_pipeline now has optimized few-shot prompts and is ready for production
```

## 4. Benefits Summary

This refactoring will deliver significant advantages:

*   **Increased Reliability**: The compiled pipeline is more robust and less prone to errors from slight variations in LLM outputs.
*   **Simplified Codebase**: The logic is consolidated, declarative, and easier to understand and maintain. The complexity of manual prompt-chaining is eliminated.
*   **Improved Performance**: Optimization can lead to higher-quality outputs, reduced latency, and lower operational costs.
*   **Future-Proofing**: The architecture is modular. We can easily experiment with new models or add/modify steps in the pipeline without a complete rewrite.