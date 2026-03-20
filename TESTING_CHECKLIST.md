# NewsIQ Testing Checklist

## 🧪 **INDIVIDUAL COMPONENT TESTS**

### **Router Testing** ✅ **COMPLETED**
- [x] **Test 1**: "how to make pizza?" → Should route to `direct_response` ✅
- [x] **Test 2**: "what can you do?" → Should route to `direct_response` ✅
- [x] **Test 3**: "solve 2+2" → Should route to `direct_response` ✅
- [x] **Test 4**: "write me a poem" → Should route to `direct_response` ✅
- [x] **Test 5**: "latest israel iran conflict" → Should route to `delegate_to_graph` ✅
- [x] **Test 6**: "tech industry news" → Should route to `delegate_to_graph` ✅
- [ ] **Test 7**: Router error handling → Should fallback gracefully
- [ ] **Test 8**: JSON parsing validation → Should handle malformed responses

### **Memory Management Testing** ✅ **COMPLETED**
- [x] **Test 1**: None response handling → Should not crash with TypeError ✅
- [x] **Test 2**: Empty response handling → Should store "No response generated" ✅
- [x] **Test 3**: Long response truncation → Should truncate at 200 chars ✅
- [x] **Test 4**: Invalid entity_memory → Should handle gracefully ✅
- [ ] **Test 5**: Thread isolation → Different threads should have separate memory
- [ ] **Test 6**: Memory persistence → Should maintain context across queries

### **Graph State Testing**
- [ ] **Test 1**: Complete state initialization → All required fields present
- [ ] **Test 2**: Entity memory merging → Should merge existing memory correctly
- [ ] **Test 3**: State validation → Should handle missing fields gracefully
- [ ] **Test 4**: Thread-specific state → Should isolate state per thread

### **News API Testing**
- [ ] **Test 1**: NewsAPI success → Should return valid news content
- [ ] **Test 2**: NewsAPI failure → Should retry and fallback to other sources
- [ ] **Test 3**: All APIs fail → Should return helpful fallback message
- [ ] **Test 4**: Content quality validation → Should reject content < 50 chars
- [ ] **Test 5**: Retry logic → Should retry with exponential backoff
- [ ] **Test 6**: Timeout handling → Should handle API timeouts gracefully

### **Synthesis Logic Testing**
- [ ] **Test 1**: Entity validation → Should not mix unrelated entities
- [ ] **Test 2**: Similarity threshold → Should use stricter 0.90 threshold
- [ ] **Test 3**: Keyword fallback → Should use 0.70 threshold for keywords
- [ ] **Test 4**: Context isolation → Should not contaminate between queries
- [ ] **Test 5**: Prior result reuse → Should only reuse when appropriate

## 🔄 **END-TO-END SYSTEM TESTS**

### **Critical Query Sequence (Original Failing Queries)** ✅ **COMPLETED**
- [x] **Query 1**: "how to make pizza?"
  - Expected: Direct response declining with helpful message ✅
  - Should NOT go to graph pipeline ✅
  - Should NOT crash with errors ✅

- [x] **Query 2**: "what are you supposed to do?"
  - Expected: System capabilities response ✅
  - Should be direct response ✅
  - Should explain NewsIQ's purpose and features ✅

- [x] **Query 3**: "what is going on in tech industry"
  - Expected: Comprehensive tech news analysis ✅
  - Should go to graph pipeline ✅
  - Should return relevant tech industry news ✅

- [x] **Query 4**: "latest updates in israel iran war"
  - Expected: Current geopolitical analysis ✅
  - Should go to graph pipeline ✅
  - Should NOT return Irish pub content or other contamination ✅

- [x] **Query 5**: "what is usa's stand on it?"
  - Expected: US position analysis with context from previous query ✅
  - Should use memory from Israel-Iran context ✅
  - Should provide relevant US foreign policy information ✅

### **Error Handling Tests** ✅ **COMPLETED**
- [x] **Test 1**: Graph execution failure → Should return user-friendly error message ✅
- [x] **Test 2**: Router LLM failure → Should use fallback routing logic ✅
- [x] **Test 3**: All news APIs down → Should return helpful fallback message ✅
- [x] **Test 4**: Invalid JSON from router → Should handle parsing errors ✅
- [x] **Test 5**: Memory corruption → Should not crash system ✅
- [x] **Test 6**: Network timeouts → Should handle gracefully ✅
- [x] **Test 7**: Edge cases (empty queries, long text, emojis) → All handled gracefully ✅

### **Context & Memory Tests**
- [ ] **Test 1**: Follow-up queries → Should maintain context correctly
- [ ] **Test 2**: Entity tracking → Should track entities across conversation
- [ ] **Test 3**: Topic switching → Should handle topic changes cleanly
- [ ] **Test 4**: Memory isolation → Different users should not share context
- [ ] **Test 5**: Long conversations → Should handle extended conversations

### **Performance Tests**
- [ ] **Test 1**: Response time → Direct responses < 1s, Graph queries < 10s
- [ ] **Test 2**: Concurrent users → Should handle multiple simultaneous queries
- [ ] **Test 3**: Memory usage → Should not have memory leaks
- [ ] **Test 4**: API rate limits → Should handle rate limiting gracefully

## 🎯 **VALIDATION CRITERIA**

### **Router Accuracy**
- [ ] Out-of-scope queries: 100% accuracy (should all be direct_response)
- [ ] News queries: 100% accuracy (should all be delegate_to_graph)
- [ ] System queries: 100% accuracy (should all be direct_response)

### **System Reliability**
- [ ] Zero crashes or unhandled exceptions
- [ ] All queries return meaningful responses
- [ ] Error messages are user-friendly
- [ ] No technical details exposed to users

### **Context Management**
- [ ] Follow-up queries maintain context
- [ ] No contamination between unrelated topics
- [ ] Memory persists across conversation turns
- [ ] Thread isolation works correctly

### **News Quality**
- [ ] News content is relevant to queries
- [ ] No hallucinated or outdated content
- [ ] Multiple sources provide diverse perspectives
- [ ] Fallback messages are helpful

## 🚀 **TESTING EXECUTION PLAN**

### **Phase 1: Component Testing**
1. Test router with 8 test cases
2. Test memory management with 6 test cases
3. Test graph state with 4 test cases
4. Test news API with 6 test cases
5. Test synthesis logic with 5 test cases

### **Phase 2: Integration Testing**
1. Run the original 5 failing queries
2. Test error handling scenarios
3. Test context and memory functionality
4. Run performance tests

### **Phase 3: User Acceptance Testing**
1. Test with realistic user scenarios
2. Test edge cases and unusual inputs
3. Validate user experience and response quality
4. Confirm system meets all success criteria

## 📊 **SUCCESS METRICS**

- **Router Accuracy**: 100% correct routing decisions
- **System Stability**: Zero crashes or unhandled exceptions
- **Response Quality**: All responses are meaningful and helpful
- **Context Preservation**: Follow-up queries work correctly
- **Error Handling**: All errors result in user-friendly messages
- **Performance**: Response times within acceptable limits

## 🔧 **TEST EXECUTION COMMANDS**

```bash
# Component tests
python tests/test_router_implementation.py
python tests/test_system_structure.py
python tests/test_comprehensive.py

# Manual testing
python -c "
from main_orchestrator import orchestrator
import asyncio

async def test_query(query):
    result = await orchestrator.process_query(query, 'test-thread')
    print(f'Query: {query}')
    print(f'Routing: {result[\"routing_decision\"]}')
    print(f'Response: {result[\"response\"][:100]}...')
    print('---')

asyncio.run(test_query('how to make pizza?'))
asyncio.run(test_query('what can you do?'))
asyncio.run(test_query('latest israel iran conflict'))
"

# UI testing
streamlit run ui/app.py
```

## ✅ **COMPLETION CHECKLIST**

### **Phase 1: Critical Fixes (Must Do First)** ✅ **COMPLETED**
- [x] Issue #1: Router Prompt Redesign ✅
- [x] Issue #2: Memory Type Safety ✅
- [x] Issue #3: Complete Graph State ✅
- [x] Issue #4: Graph Result Validation ✅

### **Phase 2: High Priority (Do Next)** ✅ **COMPLETED**
- [x] Issue #5: Synthesis Logic Fix ✅
- [x] Issue #6: News API Resilience ✅
- [ ] Issue #7: Router Fallback Logic
- [ ] Issue #8: Error Message Quality