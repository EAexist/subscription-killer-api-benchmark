#!/usr/bin/env python3
"""
Unit tests for MessageSelector chunk-based distribution with company_id constraints.
"""

import pytest
from unittest.mock import Mock
from services.message_selector import MessageSelector


class TestMessageSelector:
    """Test cases for MessageSelector chunk planning and selection."""

    def test_basic_chunk_creation(self):
        """Test basic chunk creation with configurable companies per chunk."""
        # Create mock samples with 5 companies, 10 samples each
        samples = []
        for company_id in range(5):
            for i in range(10):
                sample = Mock()
                sample.company_id = company_id
                
                # Mock the to_raw_gmail_message chain
                raw_message = Mock()
                raw_message.id = f"msg_{company_id}_{i}"
                raw_message.snippet = f"snippet_{i}"
                raw_message.get_header.return_value = f"Company {company_id} <company{company_id}@example.com>"
                sample.to_raw_gmail_message.return_value = raw_message
                
                samples.append(sample)
        
        # Test with chunk_size=5, companies_per_chunk=5 (1 sample per company)
        selector = MessageSelector(samples, chunk_size=5, companies_per_chunk=5, random_seed=42)
        
        # Should create 10 chunks (10 samples per company ÷ 1 per chunk)
        assert len(selector._chunks) == 10
        
        # Each chunk should have exactly 5 different companies
        for chunk in selector._chunks:
            company_ids = [sample.company_id for sample in chunk]
            assert len(set(company_ids)) == 5
            assert len(chunk) == 5

    def test_companies_per_chunk_configuration(self):
        """Test chunk creation with different companies_per_chunk values."""
        samples = []
        for company_id in range(8):
            for i in range(20):
                sample = Mock()
                sample.company_id = company_id
                
                # Mock the to_raw_gmail_message chain
                raw_message = Mock()
                raw_message.id = f"msg_{company_id}_{i}"
                raw_message.snippet = f"snippet_{i}"
                raw_message.get_header.return_value = f"Company {company_id} <company{company_id}@example.com>"
                sample.to_raw_gmail_message.return_value = raw_message
                
                samples.append(sample)
        
        # Test with companies_per_chunk=3
        selector = MessageSelector(samples, chunk_size=6, companies_per_chunk=3, random_seed=42)
        
        # Each chunk should have exactly 3 different companies
        for chunk in selector._chunks:
            company_ids = [sample.company_id for sample in chunk]
            assert len(set(company_ids)) == 3
            assert len(chunk) == 6

    def test_chunk_size_divisible_by_5(self):
        """Test chunk creation when chunk_size is divisible by companies_per_chunk."""
        samples = []
        for company_id in range(10):
            for i in range(20):
                sample = Mock()
                sample.company_id = company_id
                
                # Mock the to_raw_gmail_message chain
                raw_message = Mock()
                raw_message.id = f"msg_{company_id}_{i}"
                raw_message.snippet = f"snippet_{i}"
                raw_message.get_header.return_value = f"Company {company_id} <company{company_id}@example.com>"
                sample.to_raw_gmail_message.return_value = raw_message
                
                samples.append(sample)
        
        # Test with chunk_size=10, companies_per_chunk=5 (flexible distribution)
        selector = MessageSelector(samples, chunk_size=10, companies_per_chunk=5, random_seed=42)
        
        # Should create 20 chunks (200 total samples ÷ 10 chunk_size)
        assert len(selector._chunks) == 20
        
        # Each chunk should have exactly 5 different companies
        for chunk in selector._chunks:
            company_ids = [sample.company_id for sample in chunk]
            assert len(set(company_ids)) == 5
            assert len(chunk) == 10

    def test_chunk_size_with_remainder(self):
        """Test chunk creation when chunk_size has remainder when divided by companies_per_chunk."""
        samples = []
        for company_id in range(8):
            for i in range(25):
                sample = Mock()
                sample.company_id = company_id
                
                # Mock the to_raw_gmail_message chain
                raw_message = Mock()
                raw_message.id = f"msg_{company_id}_{i}"
                raw_message.snippet = f"snippet_{i}"
                raw_message.get_header.return_value = f"Company {company_id} <company{company_id}@example.com>"
                sample.to_raw_gmail_message.return_value = raw_message
                
                samples.append(sample)
        
        # Test with chunk_size=7, companies_per_chunk=5 (flexible distribution)
        selector = MessageSelector(samples, chunk_size=7, companies_per_chunk=5, random_seed=42)
        
        # Should create 28 chunks (200 total samples ÷ 7 chunk_size = 28 with 4 leftover)
        assert len(selector._chunks) == 28
        
        # Each chunk should have exactly 5 different companies
        for chunk in selector._chunks:
            company_ids = [sample.company_id for sample in chunk]
            assert len(set(company_ids)) == 5
            assert len(chunk) == 7

    def test_insufficient_companies(self):
        """Test error when fewer than companies_per_chunk companies are available."""
        samples = []
        for company_id in range(3):  # Only 3 companies
            for i in range(10):
                sample = Mock()
                sample.company_id = company_id
                
                # Mock the to_raw_gmail_message chain
                raw_message = Mock()
                raw_message.id = f"msg_{company_id}_{i}"
                raw_message.snippet = f"snippet_{i}"
                raw_message.get_header.return_value = f"Company {company_id} <company{company_id}@example.com>"
                sample.to_raw_gmail_message.return_value = raw_message
                
                samples.append(sample)
        
        # Should raise ValueError when companies_per_chunk=5 but only 3 available
        with pytest.raises(ValueError, match="Need 5 companies, found 3"):
            MessageSelector(samples, chunk_size=5, companies_per_chunk=5)

    def test_select_messages_until_exhaustion(self):
        """Test selecting messages until all chunks are exhausted."""
        samples = []
        for company_id in range(5):
            for i in range(4):
                sample = Mock()
                sample.company_id = company_id
                
                # Mock the to_raw_gmail_message chain
                raw_message = Mock()
                raw_message.id = f"msg_{company_id}_{i}"
                raw_message.snippet = f"snippet_{i}"
                raw_message.get_header.return_value = f"Company {company_id} <company{company_id}@example.com>"
                sample.to_raw_gmail_message.return_value = raw_message
                
                samples.append(sample)
        
        selector = MessageSelector(samples, chunk_size=5, companies_per_chunk=5, random_seed=42)
        
        # Should be able to select 4 chunks
        for _ in range(4):
            messages = selector.select_messages()
            assert len(messages) == 5
        
        # Should raise ValueError on 5th attempt
        with pytest.raises(ValueError, match="All chunks have been exhausted"):
            selector.select_messages()

    def test_random_seed_reproducibility(self):
        """Test that random seed produces reproducible results."""
        samples = []
        for company_id in range(5):
            for i in range(20):
                sample = Mock()
                sample.company_id = company_id
                
                # Mock the to_raw_gmail_message chain
                raw_message = Mock()
                raw_message.id = f"msg_{company_id}_{i}"
                raw_message.snippet = f"snippet_{i}"
                raw_message.get_header.return_value = f"Company {company_id} <company{company_id}@example.com>"
                sample.to_raw_gmail_message.return_value = raw_message
                
                samples.append(sample)
        
        # Create two selectors with same seed and companies_per_chunk
        selector1 = MessageSelector(samples, chunk_size=5, companies_per_chunk=5, random_seed=42)
        selector2 = MessageSelector(samples, chunk_size=5, companies_per_chunk=5, random_seed=42)
        
        # Should produce same chunks
        assert len(selector1._chunks) == len(selector2._chunks)
        
        # First chunks should have same company distribution
        chunk1_companies = {sample.company_id for sample in selector1._chunks[0]}
        chunk2_companies = {sample.company_id for sample in selector2._chunks[0]}
        assert chunk1_companies == chunk2_companies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
