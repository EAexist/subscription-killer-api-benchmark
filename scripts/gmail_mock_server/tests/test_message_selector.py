#!/usr/bin/env python3
"""
Unit tests for MessageSelector chunk-based distribution with company_id constraints.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List
from services.message_selector import MessageSelector
from datasets_shared.schema.models import EmailTemplate, EmailTextParameterSet


class TestMessageSelector:
    """Test cases for MessageSelector chunk planning and selection."""

    def _create_mock_templates(self, num_companies: int, event_types: List[str], templates_per_event: int = 2) -> List[Mock]:
        """Helper method to create mock templates with specified parameters."""
        templates = []
        for company_id in range(num_companies):
            for event_type in event_types:
                for i in range(templates_per_event):
                    template = Mock(spec=EmailTemplate)
                    template.company_id = str(company_id)  # company_id should be string
                    template.subscription_event_type = event_type  # use valid enum values
                    template.id = f"template_{company_id}_{event_type}_{i}"
                    template.subject = f"Subject {company_id} {event_type} {i}"
                    template.snippet = f"Snippet {company_id} {event_type} {i}"
                    templates.append(template)
        return templates

    def _create_mock_parameters(self, count: int) -> List[Mock]:
        """Helper method to create mock parameters."""
        parameters: List[EmailTextParameterSet] = [Mock(spec=EmailTextParameterSet) for _ in range(count)]
        for param in parameters:
            param.model_dump.return_value = {'name': 'Test User', 'company': 'Test Corp'}
        return parameters

    def test_basic_chunk_creation(self):
        """Test basic chunk creation with configurable companies per chunk."""
        # Create mock templates with 5 companies, multiple templates each
        event_types = ['SUBSCRIPTION_START', 'SUBSCRIPTION_CANCEL', 'MONTHLY_PAYMENT', 'ANNUAL_PAYMENT', 'NOT_A_SUBSCRIPTION_EMAIL']
        templates = self._create_mock_templates(5, event_types, templates_per_event=2)
        
        # Create mock parameters
        parameters = self._create_mock_parameters(100)
        
        # Test with chunk_size=5, companies_per_chunk=5, n_companies=5
        selector = MessageSelector(templates, parameters, chunk_size=5, companies_per_chunk=5, random_seed=42, n_companies=5)
        
        # Test chunk generation
        chunk = selector._generate_chunk()
        assert len(chunk) == 5
        
        # Each chunk should have exactly 5 different companies
        company_ids = [template.company_id for template in chunk]
        assert len(set(company_ids)) == 5

    @patch('datasets_shared.schema.models.Sample.to_raw_gmail_message')
    def test_parameter_exhaustion(self, mock_to_raw_gmail_message):
        """Test behavior when parameters are exhausted."""
        # Configure mock to return a mock RawGmailMessage
        mock_raw_message = Mock()
        mock_raw_message.id = "mock-id"
        mock_raw_message.get_header.return_value = "Test Sender <test@example.com>"
        mock_raw_message.snippet = "Test snippet"
        mock_to_raw_gmail_message.return_value = mock_raw_message
        
        event_types = ['SUBSCRIPTION_START', 'SUBSCRIPTION_CANCEL']
        templates = self._create_mock_templates(5, event_types, templates_per_event=2)
        
        # Create only 3 parameters (less than needed for one chunk of 5)
        parameters = self._create_mock_parameters(3)
        
        selector = MessageSelector(templates, parameters, chunk_size=5, companies_per_chunk=5, random_seed=42, n_companies=5)
        
        # Should return empty list when parameters are exhausted
        messages = selector.select_messages()
        assert len(messages) == 0

    @patch('datasets_shared.schema.models.Sample.to_raw_gmail_message')
    def test_gradual_parameter_exhaustion(self, mock_to_raw_gmail_message):
        """Test gradual exhaustion of parameters across multiple calls."""
        # Configure mock to return a mock RawGmailMessage
        mock_raw_message = Mock()
        mock_raw_message.id = "mock-id"
        mock_raw_message.get_header.return_value = "Test Sender <test@example.com>"
        mock_raw_message.snippet = "Test snippet"
        mock_to_raw_gmail_message.return_value = mock_raw_message
        
        event_types = ['SUBSCRIPTION_START', 'SUBSCRIPTION_CANCEL']
        templates = self._create_mock_templates(3, event_types, templates_per_event=2)
        
        # Create exactly 7 parameters (enough for 1 full chunk of 3, then partial, then exhausted)
        parameters = self._create_mock_parameters(7)
        
        selector = MessageSelector(templates, parameters, chunk_size=3, companies_per_chunk=3, random_seed=42, n_companies=3)
        
        # First call should succeed with 3 messages
        messages1 = selector.select_messages()
        assert len(messages1) == 3
        
        # Second call should succeed with 3 messages  
        messages2 = selector.select_messages()
        assert len(messages2) == 3
        
        # Third call should have only 1 parameter left, but need 3, so return empty
        messages3 = selector.select_messages()
        assert len(messages3) == 0

    def test_companies_per_chunk_configuration(self):
        """Test chunk creation with different companies_per_chunk values."""
        event_types = ['SUBSCRIPTION_START', 'SUBSCRIPTION_CANCEL']
        templates = self._create_mock_templates(8, event_types, templates_per_event=3)
        
        # Create mock parameters
        parameters = self._create_mock_parameters(100)
        
        # Test with companies_per_chunk=3, n_companies=8
        selector = MessageSelector(templates, parameters, companies_per_chunk=3, chunk_size=6, random_seed=42, n_companies=8)
        
        # Generate multiple chunks and test each
        for _ in range(5):  # Test 5 chunks
            chunk = selector._generate_chunk()
            company_ids = [template.company_id for template in chunk]
            assert len(set(company_ids)) == 3
            assert len(chunk) == 6

    def test_chunk_size_divisible_by_5(self):
        """Test chunk creation when chunk_size is divisible by companies_per_chunk."""
        event_types = ['SUBSCRIPTION_START', 'MONTHLY_PAYMENT']
        templates = self._create_mock_templates(10, event_types, templates_per_event=5)
        
        # Create mock parameters
        parameters = self._create_mock_parameters(200)
        
        # Test with chunk_size=10, companies_per_chunk=5, n_companies=10
        selector = MessageSelector(templates, parameters, companies_per_chunk=5, chunk_size=10, random_seed=42, n_companies=10)
        
        # Test multiple chunks
        for _ in range(10):  # Test 10 chunks
            chunk = selector._generate_chunk()
            company_ids = [template.company_id for template in chunk]
            assert len(set(company_ids)) == 5
            assert len(chunk) == 10

    def test_random_seed_reproducibility(self):
        """Test that random seed produces reproducible results."""
        event_types = ['SUBSCRIPTION_START', 'SUBSCRIPTION_CANCEL']
        templates = self._create_mock_templates(5, event_types, templates_per_event=3)
        
        # Create mock parameters
        parameters1 = self._create_mock_parameters(50)
        parameters2 = self._create_mock_parameters(50)
        
        # Create two selectors with same seed
        selector1 = MessageSelector(templates, parameters1, companies_per_chunk=5, random_seed=42, n_companies=5)
        selector2 = MessageSelector(templates, parameters2, companies_per_chunk=5, random_seed=42, n_companies=5)
        
        # Generate chunks and compare company distributions
        chunk1 = selector1._generate_chunk()
        chunk2 = selector2._generate_chunk()
        
        # Should have same company distribution (though template selection may vary due to random.choices)
        chunk1_companies = {template.company_id for template in chunk1}
        chunk2_companies = {template.company_id for template in chunk2}
        assert chunk1_companies == chunk2_companies
        assert len(chunk1) == len(chunk2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
