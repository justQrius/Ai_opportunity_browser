import pytest
from unittest.mock import MagicMock, patch
from agents.orchestrator import Orchestrator

@patch('dspy.LM')
@patch('dspy.settings')
@patch('agents.orchestrator.OpportunityAnalysisPipeline')
def test_orchestrator_initialization(mock_pipeline, mock_settings, mock_openai):
    """
    Tests if the orchestrator initializes the DSPy environment and the pipeline correctly.
    """
    # Arrange
    api_key = "test_api_key"

    # Act
    orchestrator = Orchestrator(openai_api_key=api_key)

    # Assert
    mock_openai.assert_called_once_with("openai/gpt-3.5-turbo", api_key=api_key)
    mock_settings.configure.assert_called_once_with(lm=mock_openai.return_value)
    mock_pipeline.assert_called_once()
    assert orchestrator.pipeline is not None

@patch('dspy.LM')
@patch('dspy.settings')
@patch('agents.orchestrator.OpportunityAnalysisPipeline')
def test_analyze_opportunity(mock_pipeline, mock_settings, mock_openai):
    """
    Tests the main `analyze_opportunity` method to ensure it calls the DSPy pipeline.
    """
    # Arrange
    api_key = "test_api_key"
    orchestrator = Orchestrator(openai_api_key=api_key)
    
    # Mock the pipeline execution
    mock_pipeline_instance = mock_pipeline.return_value
    mock_pipeline_instance.return_value = MagicMock(ai_opportunity="Test opportunity")

    # Act
    topic = "AI-powered code review assistants"
    result = orchestrator.analyze_opportunity(topic)

    # Assert
    mock_pipeline_instance.assert_called_once_with(topic=topic)
    assert result == "Test opportunity"

