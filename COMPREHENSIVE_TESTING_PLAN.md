# NewsIQ Comprehensive Testing Plan

## 🎯 **TESTING PHILOSOPHY**
Test each component in isolation, integration scenarios, edge cases, failure modes, and performance under load. Think like an adversarial user trying to break the system.

## 📋 **TESTING CHECKLIST OVERVIEW**

### **✅ UNIT TESTS (Component Level)**
- [x] Router Decision Logic Tests
- [x] Query Contextualization Tests  
- [x] State Management Tests
- [x] Cache Logic Tests ✅ COMPLETED
- [x] Source Selection Tests ✅ PROFESSIONAL GRADE (83.3%)
- [x] Synthesis Fallback Tests ✅ PROFESSIONAL GRADE (100.0%)

### **✅ INTEGRATION TESTS (System Level)**
- [x] End-to-End Conversation Flow Tests ⚠️ PARTIAL (40.0%)
- [ ] Router-Graph Handoff Tests
- [ ] Memory Persistence Tests
- [ ] Multi-User Isolation Tests

### **✅ EDGE CASE TESTS (Adversarial)**
- [ ] Malformed Input Tests
- [ ] API Failure Simulation Tests
- [ ] Rate Limit Handling Tests
- [ ] Memory Corruption Tests

### **✅ PERFORMANCE TESTS (Load & Stress)**
- [ ] Concurrent User Tests
- [ ] Memory Leak Tests
- [ ] Response Time Tests
- [ ] Cache Efficiency Tests

---

## 🧪 **DETAILED TEST SPECIFICATIONS**

### **1. ROUTER DECISION LOGIC TESTS**
**File**: `test_router_comprehensive.py`

#### **1.1 Basic Routing Accuracy**
```python
def test_router_basic_decisions():
    """Test fundamental routing decisions"""
    test_cases = [
        # Direct response cases
        ("what can you do?", "direct_response"),
        ("how to make pizza", "direct_response"),
        ("solve 2+2", "direct_response"),
        ("write a poem", "direct_response"),
        
        # Graph delegation cases
        ("Tesla earnings news", "delegate_to_graph"),
        ("latest Ukraine updates", "delegate_to_graph"),
        ("Apple vs Google AI", "delegate_to_graph"),
        ("breaking news today", "delegate_to_graph"),
    ]
```

#### **1.2 Context Extraction Accuracy**
```python
def test_router_context_extraction():
    """Test entity and topic extraction"""
    test_cases = [
        ("Tesla stock news", ["Tesla"], "Stock News"),
        ("Israel Iran conflict", ["Israel", "Iran"], "Conflict"),
        ("Apple Google Microsoft AI", ["Apple", "Google", "Microsoft"], "AI"),
        ("Biden climate policy", ["Biden"], "Climate Policy"),
    ]
```

#### **1.3 Source Suggestion Logic**
```python
def test_router_source_suggestions():
    """Test intelligent source routing"""
    test_cases = [
        ("breaking Tesla news", ["newsapi"]),
        ("global climate impact", ["gnews"]),
        ("Apple earnings report", ["newsdata"]),
        ("international conflict", ["gnews", "newsapi"]),
    ]
```

#### **1.4 Fallback Robustness**
```python
def test_router_fallback_scenarios():
    """Test router failure handling"""
    # LLM timeout scenarios
    # Malformed JSON responses
    # Network failures
    # Invalid API keys
```

### **2. QUERY CONTEXTUALIZATION TESTS**
**File**: `test_query_contextualization.py`

#### **2.1 Pronoun Resolution**
```python
def test_pronoun_resolution():
    """Test pronoun and reference resolution"""
    conversation_scenarios = [
        # Scenario 1: War context
        [
            ("Israel Iran conflict", "Israel Iran conflict"),
            ("How is this affecting India?", "How is Israel Iran conflict affecting India?"),
            ("What about their economies?", "What about Israel Iran economies?"),
        ],
        
        # Scenario 2: Company context
        [
            ("Apple earnings report", "Apple earnings report"),
            ("What about their competition?", "What about Apple competition?"),
            ("Any updates on it?", "Any updates on Apple?"),
        ],
        
        # Scenario 3: Multi-entity context
        [
            ("Tesla vs Ford electric vehicles", "Tesla vs Ford electric vehicles"),
            ("How are they performing?", "How are Tesla Ford performing?"),
            ("Latest on their rivalry?", "Latest on Tesla Ford rivalry?"),
        ]
    ]
```

#### **2.2 Context Switching**
```python
def test_context_switching():
    """Test topic switching scenarios"""
    conversation_scenarios = [
        [
            ("Apple news", "Apple news"),
            ("Now tell me about Google", "Google news"),  # Context should switch
            ("What about their AI?", "What about Google AI?"),  # Should use new context
        ]
    ]
```

#### **2.3 Ambiguous Reference Handling**
```python
def test_ambiguous_references():
    """Test handling of unclear references"""
    test_cases = [
        ("What about it?", None, "What about it?"),  # No context - unchanged
        ("How are they doing?", [], "How are they doing?"),  # Empty context - unchanged
        ("This situation is complex", ["Apple", "Google"], "Apple Google situation is complex"),
    ]
```

#### **2.4 Fallback Strategy Testing**
```python
def test_contextualization_fallbacks():
    """Test 5-layer fallback strategy"""
    # Rule-based resolution
    # Entity memory fallback
    # LLM resolution
    # Keyword matching
    # Original query return
```

### **3. STATE MANAGEMENT TESTS**
**File**: `test_state_management.py`

#### **3.1 State Schema Validation**
```python
def test_state_schema_completeness():
    """Test all required state fields are present"""
    required_fields = [
        'user_query', 'resolved_query', 'active_entities',
        'search_queries', 'query_resolution', 'context_hints',
        'extracted_entities', 'conversation_history'
    ]
```

#### **3.2 Entity Tracking Across Turns**
```python
def test_entity_persistence():
    """Test entity tracking across conversation turns"""
    conversation_flow = [
        ("Apple earnings", ["Apple"]),
        ("What about Google?", ["Apple", "Google"]),
        ("Compare their AI strategies", ["Apple", "Google"]),
    ]
```

#### **3.3 Memory Isolation**
```python
def test_thread_isolation():
    """Test memory isolation between different threads"""
    # Thread A: Apple discussion
    # Thread B: Tesla discussion
    # Verify no cross-contamination
```

#### **3.4 State Corruption Handling**
```python
def test_malformed_state_handling():
    """Test handling of corrupted state"""
    # Missing required fields
    # Wrong data types
    # Circular references
    # Oversized state objects
```

### **4. CACHE LOGIC TESTS**
**File**: `test_cache_temporal_logic.py`

#### **4.1 Time-Sensitive Query Detection**
```python
def test_time_sensitive_detection():
    """Test detection of time-sensitive queries"""
    time_sensitive = [
        "latest Tesla news", "breaking Apple updates", 
        "today's market news", "recent developments",
        "this week's earnings", "yesterday's announcement"
    ]
    
    general_queries = [
        "Tesla company overview", "Apple history",
        "market analysis", "business strategy"
    ]
```

#### **4.2 Dynamic TTL Assignment**
```python
def test_dynamic_ttl():
    """Test TTL assignment based on query type"""
    test_cases = [
        ("latest news", 1800),  # 30 minutes
        ("breaking updates", 1800),  # 30 minutes
        ("company analysis", 3600),  # 60 minutes
        ("historical data", 3600),  # 60 minutes
    ]
```

#### **4.3 Temporal Score Adjustment**
```python
def test_temporal_scoring():
    """Test time decay in similarity scoring"""
    # High similarity, recent cache -> Use cache
    # High similarity, old cache -> Reject cache
    # Medium similarity, recent cache -> Use cache
    # Medium similarity, old cache -> Reject cache
```

#### **4.4 Cache Invalidation Edge Cases**
```python
def test_cache_edge_cases():
    """Test cache behavior in edge scenarios"""
    # System clock changes
    # Negative timestamps
    # Future timestamps
    # Cache corruption
```

### **5. SOURCE SELECTION TESTS**
**File**: `test_intelligent_routing.py`

#### **5.1 Pattern-Based Routing**
```python
def test_pattern_routing():
    """Test source selection based on query patterns"""
    test_cases = [
        ("breaking Tesla news", ["newsapi"]),
        ("global climate summit", ["gnews"]),
        ("Apple earnings financial", ["newsdata"]),
        ("international Ukraine crisis", ["gnews", "newsapi"]),
    ]
```

#### **5.2 Entity-Specific Routing**
```python
def test_entity_routing():
    """Test routing based on entity types"""
    test_cases = [
        ("Trump Biden election", ["newsapi"]),  # US politics
        ("China Russia relations", ["gnews"]),   # International
        ("Tesla Apple stock", ["newsdata"]),     # Business/Tech
    ]
```

#### **5.3 Intent-Based Optimization**
```python
def test_intent_optimization():
    """Test source preference based on intent"""
    test_cases = [
        ("compare", "Apple vs Google", ["newsdata"]),  # Business comparison
        ("sentiment", "public opinion", ["gnews"]),    # Global sentiment
        ("timeline", "event sequence", ["newsapi"]),   # Chronological
    ]
```

#### **5.4 Fallback Source Selection**
```python
def test_source_fallbacks():
    """Test fallback when preferred sources fail"""
    # Primary source fails -> Secondary source
    # All sources fail -> Graceful degradation
    # Invalid source configuration -> Default routing
```

### **6. SYNTHESIS FALLBACK TESTS**
**File**: `test_synthesis_contextual.py`

#### **6.1 Query Classification**
```python
def test_query_classification():
    """Test synthesis query type detection"""
    test_cases = [
        ("How does war affect economy?", "impact"),
        ("What's Biden's response?", "response"),
        ("Apple vs Google comparison", "comparison"),
        ("Tesla news updates", "generic"),
    ]
```

#### **6.2 Contextual Analysis Generation**
```python
def test_contextual_analysis():
    """Test contextual analysis when no direct results"""
    scenarios = [
        # Impact analysis
        ("Israel Iran war affecting India", ["Israel", "Iran", "India"], "economic, diplomatic impact analysis"),
        
        # Response analysis  
        ("Biden's stance on climate", ["Biden"], "typical response patterns"),
        
        # Comparison analysis
        ("Apple vs Google AI", ["Apple", "Google"], "comparison dimensions"),
    ]
```

#### **6.3 Meaningful Results Detection**
```python
def test_meaningful_results_detection():
    """Test detection of meaningful vs empty results"""
    meaningful_results = [
        "Apple reported strong quarterly earnings...",
        "Tesla announced new factory construction...",
    ]
    
    empty_results = [
        "No recent news found",
        "Try a different search term",
        "Please try again later",
    ]
```

#### **6.4 Search Suggestion Quality**
```python
def test_search_suggestions():
    """Test quality of alternative search suggestions"""
    test_cases = [
        ("Tesla Mars mission", ["Tesla", "SpaceX"], ["Tesla news", "SpaceX Mars"]),
        ("Apple quantum computing", ["Apple"], ["Apple technology", "Apple research"]),
    ]
```

---

## 🔗 **INTEGRATION TESTS**

### **7. END-TO-END CONVERSATION FLOW**
**File**: `test_e2e_conversations.py`

#### **7.1 Multi-Turn Conversations**
```python
def test_complete_conversation_flows():
    """Test realistic conversation scenarios"""
    scenarios = [
        # Business Analysis Flow
        [
            "Tell me about Apple's latest earnings",
            "How does this compare to Google?", 
            "What about their AI strategies?",
            "Any analyst reactions?"
        ],
        
        # Geopolitical Analysis Flow
        [
            "Latest on Israel Iran tensions",
            "How is this affecting oil prices?",
            "What's the US position?",
            "Any diplomatic efforts?"
        ],
        
        # Technology Trend Flow
        [
            "AI developments this week",
            "What about OpenAI specifically?",
            "How are competitors responding?",
            "Market implications?"
        ]
    ]
```

#### **7.2 Context Persistence Validation**
```python
def test_context_persistence():
    """Verify context maintained across conversation"""
    # Entity tracking
    # Topic continuity  
    # Memory updates
    # State consistency
```

### **8. ROUTER-GRAPH HANDOFF TESTS**
**File**: `test_router_graph_integration.py`

#### **8.1 Context Injection Verification**
```python
def test_context_injection():
    """Test router insights passed to graph"""
    # Router extracts entities -> Graph receives entities
    # Router suggests sources -> Graph uses sources
    # Router confidence -> Graph tracking
    # No duplicate analysis
```

#### **8.2 Performance Optimization Validation**
```python
def test_performance_optimization():
    """Test elimination of double-think"""
    # Measure LLM calls before/after
    # Verify 1-2 second latency reduction
    # Confirm single-pass context understanding
```

---

## ⚡ **EDGE CASE & STRESS TESTS**

### **9. MALFORMED INPUT TESTS**
**File**: `test_edge_cases.py`

#### **9.1 Input Validation**
```python
def test_malformed_inputs():
    """Test handling of invalid inputs"""
    edge_cases = [
        "",  # Empty query
        " " * 1000,  # Whitespace only
        "🚀🎯💡" * 100,  # Emoji spam
        "SELECT * FROM users",  # SQL injection attempt
        "<script>alert('xss')</script>",  # XSS attempt
        "A" * 10000,  # Extremely long query
        "\n\r\t\0",  # Control characters
        "query with\x00null bytes",  # Null bytes
    ]
```

#### **9.2 Unicode and Encoding**
```python
def test_unicode_handling():
    """Test international character handling"""
    test_cases = [
        "最新的苹果新闻",  # Chinese
        "أخبار تسلا الأخيرة",  # Arabic  
        "Последние новости Google",  # Russian
        "नवीनतम माइक्रोसॉफ्ट समाचार",  # Hindi
        "🇺🇸🇨🇳🇷🇺 trade war news",  # Flag emojis
    ]
```

### **10. API FAILURE SIMULATION**
**File**: `test_api_failures.py`

#### **10.1 Network Failures**
```python
def test_network_failures():
    """Test handling of network issues"""
    failure_scenarios = [
        "connection_timeout",
        "dns_resolution_failure", 
        "ssl_certificate_error",
        "connection_refused",
        "network_unreachable"
    ]
```

#### **10.2 API Response Failures**
```python
def test_api_response_failures():
    """Test handling of API errors"""
    error_scenarios = [
        (401, "unauthorized"),
        (403, "forbidden"), 
        (429, "rate_limited"),
        (500, "internal_server_error"),
        (503, "service_unavailable"),
        ("malformed_json", "invalid response"),
        ("empty_response", "no content"),
    ]
```

#### **10.3 Partial Failures**
```python
def test_partial_failures():
    """Test mixed success/failure scenarios"""
    # NewsAPI succeeds, GNews fails
    # All sources return empty results
    # Some sources timeout, others succeed
    # Corrupted response from one source
```

### **11. CONCURRENT USER TESTS**
**File**: `test_concurrent_users.py`

#### **11.1 Thread Safety**
```python
def test_thread_safety():
    """Test concurrent user handling"""
    # 10 users asking different questions simultaneously
    # Memory isolation verification
    # No race conditions in cache
    # State consistency under load
```

#### **11.2 Memory Isolation**
```python
def test_memory_isolation():
    """Test user memory separation"""
    # User A: Apple discussion
    # User B: Tesla discussion  
    # User C: Google discussion
    # Verify no cross-contamination
```

#### **11.3 Resource Contention**
```python
def test_resource_contention():
    """Test system behavior under resource pressure"""
    # High memory usage scenarios
    # CPU intensive operations
    # API rate limit scenarios
    # Cache overflow handling
```

---

## 📊 **PERFORMANCE & MONITORING TESTS**

### **12. RESPONSE TIME BENCHMARKS**
**File**: `test_performance_benchmarks.py`

#### **12.1 Response Time Targets**
```python
def test_response_time_targets():
    """Test response time requirements"""
    targets = {
        "direct_response": 0.5,  # 500ms
        "simple_news_query": 6.0,  # 6 seconds
        "complex_analysis": 10.0,  # 10 seconds
        "cached_response": 0.5,  # 500ms
    }
```

#### **12.2 Performance Regression**
```python
def test_performance_regression():
    """Test for performance degradation"""
    # Baseline measurements
    # Current performance comparison
    # Alert on >20% degradation
```

### **13. MEMORY LEAK TESTS**
**File**: `test_memory_management.py`

#### **13.1 Memory Growth Monitoring**
```python
def test_memory_leaks():
    """Test for memory leaks over time"""
    # Process 1000 queries
    # Monitor memory usage
    # Verify cleanup after conversations
    # Check for circular references
```

#### **13.2 Cache Size Management**
```python
def test_cache_size_limits():
    """Test cache size management"""
    # Fill cache to capacity
    # Verify LRU eviction
    # Test cache cleanup
    # Memory usage bounds
```

---

## 🎯 **QUALITY GATES**

### **PASS CRITERIA**
- **Unit Tests**: 95%+ pass rate
- **Integration Tests**: 90%+ pass rate  
- **Edge Case Tests**: 85%+ pass rate
- **Performance Tests**: Meet all targets
- **Memory Tests**: No leaks detected

### **CRITICAL FAILURES (MUST FIX)**
- System crashes or hangs
- Memory leaks or unbounded growth
- Security vulnerabilities
- Data corruption or cross-contamination
- Response time >2x targets

### **HIGH PRIORITY FAILURES**
- >10% test failures in any category
- Incorrect routing decisions
- Context loss in conversations
- Cache inconsistencies
- API failure handling issues

---

## 📝 **TEST EXECUTION STRATEGY**

### **AUTOMATED TESTING**
```bash
# Run all tests
python -m pytest tests/ -v --cov=. --cov-report=html

# Run specific test categories
python -m pytest tests/test_router_comprehensive.py -v
python -m pytest tests/test_query_contextualization.py -v
python -m pytest tests/test_e2e_conversations.py -v

# Performance benchmarks
python -m pytest tests/test_performance_benchmarks.py --benchmark-only

# Stress tests
python -m pytest tests/test_concurrent_users.py --stress-test
```

### **MANUAL TESTING SCENARIOS**
1. **Adversarial Testing**: Try to break the system
2. **User Journey Testing**: Realistic conversation flows
3. **Edge Case Exploration**: Unusual input combinations
4. **Performance Validation**: Real-world usage patterns

### **CONTINUOUS MONITORING**
- Response time tracking
- Error rate monitoring  
- Memory usage alerts
- Cache hit rate metrics
- User satisfaction feedback

This comprehensive testing plan ensures the NewsIQ system is production-ready, robust, and maintains high quality under all conditions.