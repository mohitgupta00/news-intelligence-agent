# Remaining Tasks Implementation Plan

## 🎯 Priority Order for Completion

### **PHASE 1: Critical Robustness (30 min)**
**Task 7.4: Summary Expiration Logic**
- Add timestamp tracking to context summaries
- Reset summary after 10+ minutes of inactivity or topic drift detection
- Implement in `main_orchestrator.py._update_memory_with_summary()`

**Task 9.1-9.4: Error Handling**
- Wrap LLM calls in try-catch with specific error types
- Handle JSON parsing failures gracefully
- Add 10-second timeout to Groq calls
- Enhanced logging for debugging

### **PHASE 2: Demo Validation (45 min)**
**Task 10.1-10.5: Core Testing**
- Create test script for 4 demo scenarios
- Validate pronoun resolution accuracy
- Test confidence scoring and fallback activation
- Verify multi-entity conversation handling

### **PHASE 3: Production Polish (15 min)**
- Final UI tweaks for demo presentation
- Performance optimization checks
- Documentation updates

---

## 📝 Detailed Implementation Tasks

### **Task 7.4: Summary Expiration Logic**
**File:** `main_orchestrator.py`
**Effort:** 10 min
**Implementation:**
```python
def _should_reset_summary(self, memory: dict) -> bool:
    # Reset after 10 min inactivity or semantic drift
    last_update = memory.get('last_update', 0)
    if time.time() - last_update > 600:  # 10 minutes
        return True
    
    # Reset if context summary becomes too long (>100 chars)
    summary = memory.get('context_summary', '')
    if len(summary) > 100:
        return True
    
    return False
```

### **Task 9.1: Enhanced Error Handling**
**File:** `intelligent_router.py`
**Effort:** 15 min
**Implementation:**
- Wrap `resolve_intent_and_context()` in comprehensive try-catch
- Handle specific Groq API errors (rate limit, timeout, invalid response)
- Add structured logging with error types
- Graceful JSON parsing with validation

### **Task 9.2: Timeout & Retry Logic**
**File:** `intelligent_router.py`
**Effort:** 5 min
**Implementation:**
```python
# Add to Groq call
timeout=10,
max_retries=1
```

### **Task 10.1: Demo Test Script**
**File:** `test_demo_scenarios.py` (new)
**Effort:** 20 min
**Implementation:**
- 4 test scenarios from checklist
- Automated validation of resolution accuracy
- Confidence score verification
- Fallback activation testing

### **Task 10.2: Pronoun Resolution Validation**
**File:** `test_demo_scenarios.py`
**Effort:** 10 min
**Test Cases:**
```python
scenarios = [
    ("Trump latest news", "What about him?", "Trump"),
    ("Israel Iran war", "What about this?", "Israel Iran war"),
    ("Apple Google comparison", "Their AI ethics?", "Apple Google")
]
```

### **Task 10.3: Multi-Entity Conversation Test**
**File:** `test_demo_scenarios.py`
**Effort:** 10 min
**Test Flow:**
1. "Israel-Iran war updates"
2. "What is India's stance?"
3. "How about Pakistan?"
4. Verify context maintained across all 3 turns

### **Task 10.4: Semantic Drift Detection**
**File:** `test_demo_scenarios.py`
**Effort:** 5 min
**Test:**
- Start with news topic
- Switch to weather/recipe
- Verify `is_contextual_follow_up = False`

---

## 🚀 Execution Strategy

### **Immediate Actions (Next 30 min):**
1. Implement summary expiration logic
2. Add comprehensive error handling
3. Create basic test script

### **Validation Phase (Next 45 min):**
1. Run demo scenarios
2. Fix any resolution failures
3. Tune confidence thresholds if needed

### **Final Polish (Next 15 min):**
1. UI improvements
2. Performance checks
3. Update documentation

---

## 🎯 Success Criteria

### **Must Pass Tests:**
- [ ] "Trump" → "What about him?" resolves to "Trump"
- [ ] Multi-entity context maintained for 3+ turns
- [ ] Fallback activates when confidence < 0.7
- [ ] No crashes during error scenarios
- [ ] Response time < 6 seconds end-to-end

### **Demo Readiness Checklist:**
- [ ] All 4 demo scenarios work flawlessly
- [ ] UI shows clear query transformation
- [ ] Fallback safety prevents crashes
- [ ] Context summary updates correctly
- [ ] Confidence scoring is accurate

---

## 📊 Risk Mitigation

### **High Risk Areas:**
1. **LLM Hallucination** - Fallback safety at 0.7 threshold
2. **JSON Parsing Errors** - Comprehensive error handling
3. **Context Loss** - Summary expiration with reset logic
4. **Demo Failures** - Extensive testing of all scenarios

### **Contingency Plans:**
- If resolution fails → Use original query (already implemented)
- If LLM times out → Fallback to legacy router
- If confidence low → Automatic fallback (already implemented)

---

**Total Estimated Time:** 90 minutes
**Critical Path:** Error handling → Testing → Demo validation
**Success Metric:** Zero demo failures, >90% resolution accuracy