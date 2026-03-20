"""
Comprehensive API Robustness Test Suite
Tests the news fetching system from multiple professional perspectives:
- Quality Analyst: Edge cases, failure modes, error handling
- Performance Engineer: Response times, concurrent load, resource usage  
- Security Analyst: Input validation, injection attacks, data sanitization
- Production Engineer: Reliability, fallback mechanisms, monitoring
"""

import asyncio
import time
import pytest
from unittest.mock import patch, Mock
from tools.fetch_news import fetch_news_with_fallback, _call_newsapi_async, _call_gnews_async, _call_newsdata_async

class TestAPIRobustness:
    """Comprehensive API robustness testing from professional perspectives."""
    
    @pytest.mark.asyncio
    async def test_edge_case_handling(self):
        """Quality Analyst perspective: Test edge cases and boundary conditions."""
        
        edge_cases = [
            # Input validation edge cases
            ("", "Empty string"),
            ("a", "Single character"),
            ("  ", "Whitespace only"),
            ("a" * 1000, "Very long query"),
            ("query\nwith\nnewlines", "Multiline input"),
            ("query\twith\ttabs", "Tab characters"),
            ("query with  multiple   spaces", "Multiple spaces"),
            
            # Special characters and encoding
            ("café résumé naïve", "Unicode characters"),
            ("query with 'quotes' and \"double quotes\"", "Quote characters"),
            ("query with & ampersand", "HTML entities"),
            ("query with <script>alert('xss')</script>", "XSS attempt"),
            ("'; DROP TABLE news; --", "SQL injection attempt"),
            ("../../../etc/passwd", "Path traversal attempt"),
            
            # Numeric and mixed content
            ("123456789", "Pure numbers"),
            ("query123", "Alphanumeric"),
            ("!@#$%^&*()", "Special characters only"),
            ("🚀🎯💡🔥", "Emoji only"),
            ("query 🚀 with emojis", "Mixed emoji content"),
        ]
        
        results = []
        for query, description in edge_cases:
            try:
                result, source = await fetch_news_with_fallback(query, n=3)
                
                # Validate response structure
                assert isinstance(result, str), f"Result must be string for: {description}"
                assert isinstance(source, str), f"Source must be string for: {description}"
                assert len(result) > 0, f"Result cannot be empty for: {description}"
                
                # Check for proper error handling
                is_validation_error = "validation_error" in source
                is_fallback = "fallback" in source
                has_helpful_message = any(word in result.lower() for word in ['try', 'search', 'provide', 'different'])
                
                success = True
                if len(query.strip()) < 2:
                    # Should be validation error
                    success = is_validation_error
                elif any(char in query for char in ['<', '>', ';', '--']):
                    # Potential security issues should be handled gracefully
                    success = is_validation_error or is_fallback or has_helpful_message
                else:
                    # Should either succeed or provide helpful fallback
                    success = not is_validation_error or has_helpful_message
                
                results.append({
                    'query': query[:50],
                    'description': description,
                    'success': success,
                    'source': source,
                    'result_length': len(result)
                })
                
            except Exception as e:
                results.append({
                    'query': query[:50],
                    'description': description,
                    'success': False,
                    'error': str(e)
                })
        
        # Analyze results
        total = len(results)
        successful = sum(1 for r in results if r['success'])
        
        print(f"\nEdge Case Analysis: {successful}/{total} ({successful/total*100:.1f}%) passed")
        for r in results:
            status = \"✅\" if r['success'] else \"❌\"
            print(f\"{status} {r['description']}: {r.get('source', r.get('error', 'Unknown'))}\")
        
        # Should handle at least 80% of edge cases gracefully
        assert successful / total >= 0.8, f\"Edge case handling too low: {successful/total:.2f} < 0.8\"
    
    @pytest.mark.asyncio
    async def test_performance_characteristics(self):
        """Performance Engineer perspective: Response times and resource usage."""
        
        performance_tests = [
            ("Tesla news", "Short query"),
            ("Apple vs Google artificial intelligence competition", "Medium query"),
            ("breaking news about international climate change summit discussions", "Long query"),
            ("AI", "Very short query"),
        ]
        
        results = []
        for query, description in performance_tests:
            times = []
            
            # Run multiple iterations for statistical significance
            for i in range(3):
                start_time = time.time()
                try:
                    result, source = await fetch_news_with_fallback(query, n=5)
                    response_time = time.time() - start_time
                    times.append(response_time)
                    
                    # Performance assertions
                    assert response_time < 30.0, f\"Response time too high: {response_time:.2f}s for {description}\"
                    
                except Exception as e:
                    times.append(30.0)  # Max penalty for errors
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)\n            \n            results.append({\n                'query': query,\n                'description': description,\n                'avg_time': avg_time,\n                'min_time': min_time,\n                'max_time': max_time,\n                'consistency': max_time - min_time  # Lower is better\n            })\n        \n        print(f"\nPerformance Analysis:")\n        for r in results:\n            print(f\"{r['description']:20} | Avg: {r['avg_time']:.2f}s | Range: {r['min_time']:.2f}-{r['max_time']:.2f}s\")\n        \n        # Performance requirements\n        overall_avg = sum(r['avg_time'] for r in results) / len(results)\n        assert overall_avg < 15.0, f\"Average response time too high: {overall_avg:.2f}s\"\n        \n        max_response_time = max(r['max_time'] for r in results)\n        assert max_response_time < 30.0, f\"Maximum response time too high: {max_response_time:.2f}s\"\n    \n    @pytest.mark.asyncio\n    async def test_concurrent_load_handling(self):\n        \"\"\"Production Engineer perspective: Concurrent request handling.\"\"\"\n        \n        queries = [\n            \"Tesla news\",\n            \"Apple earnings\", \n            \"Google AI\",\n            \"Microsoft cloud\",\n            \"Amazon retail\"\n        ]\n        \n        # Test concurrent execution\n        start_time = time.time()\n        \n        tasks = [fetch_news_with_fallback(query, n=3) for query in queries]\n        results = await asyncio.gather(*tasks, return_exceptions=True)\n        \n        total_time = time.time() - start_time\n        \n        # Analyze concurrent performance\n        successful_results = [r for r in results if not isinstance(r, Exception)]\n        failed_results = [r for r in results if isinstance(r, Exception)]\n        \n        success_rate = len(successful_results) / len(results)\n        \n        print(f"\nConcurrent Load Analysis:")\n        print(f\"Total time: {total_time:.2f}s for {len(queries)} concurrent requests\")\n        print(f\"Success rate: {len(successful_results)}/{len(results)} ({success_rate*100:.1f}%)\")\n        print(f\"Average per request: {total_time/len(queries):.2f}s\")\n        \n        # Concurrent performance requirements\n        assert success_rate >= 0.8, f\"Concurrent success rate too low: {success_rate:.2f} < 0.8\"\n        assert total_time < 45.0, f\"Concurrent execution too slow: {total_time:.2f}s\"\n    \n    @pytest.mark.asyncio\n    async def test_api_failure_resilience(self):\n        \"\"\"Production Engineer perspective: API failure handling and fallbacks.\"\"\"\n        \n        # Test with mocked API failures\n        test_query = \"Tesla news\"\n        \n        # Test 1: All APIs fail\n        with patch('tools.fetch_news._call_newsapi_async', return_value=None), \\\n             patch('tools.fetch_news._call_gnews_async', return_value=None), \\\n             patch('tools.fetch_news._call_newsdata_async', return_value=None):\n            \n            result, source = await fetch_news_with_fallback(test_query)\n            \n            # Should provide helpful fallback message\n            assert \"fallback\" in source, \"Should indicate fallback when all APIs fail\"\n            assert len(result) > 50, \"Fallback message should be informative\"\n            assert any(word in result.lower() for word in ['try', 'search', 'different']), \\\n                   \"Fallback should provide helpful suggestions\"\n        \n        # Test 2: Partial API failures\n        with patch('tools.fetch_news._call_newsapi_async', return_value=None), \\\n             patch('tools.fetch_news._call_gnews_async', return_value=\"GNews result: Sample news content\"):\n            \n            result, source = await fetch_news_with_fallback(test_query)\n            \n            # Should succeed with working API\n            assert \"gnews\" in source, \"Should use working API when others fail\"\n            assert \"Sample news content\" in result, \"Should return content from working API\"\n        \n        print(\"✅ API failure resilience tests passed\")\n    \n    @pytest.mark.asyncio\n    async def test_source_diversity_and_routing(self):\n        \"\"\"System Architect perspective: Source selection and diversity.\"\"\"\n        \n        routing_tests = [\n            (\"breaking Tesla news\", [\"gnews\", \"newsdata\"]),  # Real-time sources\n            (\"Apple earnings report\", [\"newsdata\"]),          # Business source\n            (\"global climate summit\", [\"gnews\"]),             # International source\n            (\"Biden election news\", [\"newsapi\"]),             # US politics source\n        ]\n        \n        source_usage = {}\n        \n        for query, expected_sources in routing_tests:\n            result, source = await fetch_news_with_fallback(query, n=3)\n            \n            actual_source = source.split('_')[0].split(' ')[0]  # Extract base source name\n            source_usage[actual_source] = source_usage.get(actual_source, 0) + 1\n            \n            # Check if routing logic is working\n            if not any(exp in source for exp in expected_sources) and \"fallback\" not in source:\n                print(f\"⚠️  Unexpected routing: '{query}' -> {source} (expected: {expected_sources})\")\n        \n        print(f"\nSource Diversity Analysis:")\n        for source, count in source_usage.items():\n            print(f\"{source}: {count} requests\")\n        \n        # Should use multiple sources for diversity\n        unique_sources = len([s for s in source_usage.keys() if s not in ['fallback', 'validation']])\n        assert unique_sources >= 2, f\"Insufficient source diversity: {unique_sources} < 2\"\n    \n    @pytest.mark.asyncio\n    async def test_data_quality_and_validation(self):\n        \"\"\"Quality Analyst perspective: Output quality and data validation.\"\"\"\n        \n        quality_tests = [\n            \"Tesla stock news\",\n            \"Apple iPhone release\",\n            \"Google search algorithm\"\n        ]\n        \n        for query in quality_tests:\n            result, source = await fetch_news_with_fallback(query, n=3)\n            \n            # Data quality checks\n            assert isinstance(result, str), \"Result must be string\"\n            assert len(result.strip()) > 0, \"Result cannot be empty\"\n            \n            if \"fallback\" not in source and \"validation\" not in source:\n                # For successful API calls, check content quality\n                assert \":\" in result, \"News articles should have title:content format\"\n                \n                # Check for reasonable content length\n                assert len(result) > 30, f\"Content too short: {len(result)} chars\"\n                \n                # Check for potential data corruption\n                assert not result.startswith(\"Error\"), \"Should not return raw error messages\"\n                assert \"<script>\" not in result, \"Should not contain script tags\"\n                assert \"null\" not in result.lower(), \"Should not contain null values\"\n        \n        print(\"✅ Data quality validation tests passed\")\n\nif __name__ == \"__main__\":\n    # Run comprehensive test suite\n    pytest.main([__file__, \"-v\", \"-s\", \"--tb=short\"])