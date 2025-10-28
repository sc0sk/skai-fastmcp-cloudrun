#!/usr/bin/env python3
"""
Comprehensive MCP Best Practices Evaluation
Tests MCP tools against the complete best practices checklist
"""
import json
import sys
import time
from typing import Dict, List
from dataclasses import dataclass

# Import tools directly for testing
sys.path.insert(0, '/home/user/skai-fastmcp-cloudrun/src')

from tools.search import search_hansard_speeches
from tools.fetch import fetch_hansard_speech


@dataclass
class BestPracticeResult:
    criterion: str
    status: str  # "PASS", "FAIL", "PARTIAL"
    details: str
    score: float  # 0.0 to 1.0


class MCPBestPracticesEvaluator:
    """Comprehensive MCP Best Practices Evaluator"""
    
    def __init__(self):
        self.results: List[BestPracticeResult] = []
        
    def evaluate_tool_annotations(self, tool_func) -> BestPracticeResult:
        """Check if tool has proper FastMCP annotations"""
        try:
            # Check for FastMCP annotations
            has_annotations = hasattr(tool_func, '__annotations__')
            has_description = tool_func.__doc__ is not None
            
            # Check for readOnlyHint in the function's tool annotation
            annotation_score = 0.0
            details = []
            
            if has_annotations:
                annotation_score += 0.3
                details.append("✓ Has type annotations")
            else:
                details.append("✗ Missing type annotations")
                
            if has_description and len(tool_func.__doc__.strip()) > 20:
                annotation_score += 0.4
                details.append("✓ Has comprehensive docstring")
            else:
                details.append("✗ Missing or inadequate docstring")
                
            # Check if function is properly decorated (FastMCP style)
            if hasattr(tool_func, '_mcp_tool_info'):
                annotation_score += 0.3
                details.append("✓ Has MCP tool decoration")
            else:
                details.append("? Unknown MCP decoration status")
                
            status = "PASS" if annotation_score >= 0.7 else "PARTIAL" if annotation_score >= 0.4 else "FAIL"
            
            return BestPracticeResult(
                criterion="Tool Annotations",
                status=status,
                details="; ".join(details),
                score=annotation_score
            )
        except Exception as e:
            return BestPracticeResult(
                criterion="Tool Annotations",
                status="FAIL",
                details=f"Error evaluating annotations: {e}",
                score=0.0
            )
    
    def evaluate_docstring_quality(self, tool_func) -> BestPracticeResult:
        """Evaluate docstring quality against MCP best practices"""
        docstring = tool_func.__doc__ or ""
        
        score = 0.0
        details = []
        
        # Check for key phrases from MCP best practices
        required_phrases = [
            ("Use this when", "Usage guidance"),
            ("Do not use", "Anti-pattern guidance"),
            ("Returns", "Return value description"),
        ]
        
        for phrase, description in required_phrases:
            if phrase.lower() in docstring.lower():
                score += 0.25
                details.append(f"✓ Has {description}")
            else:
                details.append(f"✗ Missing {description}")
        
        # Check overall length and detail
        if len(docstring) > 100:
            score += 0.25
            details.append("✓ Comprehensive length")
        else:
            details.append("✗ Too brief")
            
        status = "PASS" if score >= 0.75 else "PARTIAL" if score >= 0.5 else "FAIL"
        
        return BestPracticeResult(
            criterion="Docstring Quality",
            status=status,
            details="; ".join(details),
            score=score
        )
    
    def evaluate_error_handling(self, tool_func, test_inputs: List[Dict]) -> BestPracticeResult:
        """Test error handling with invalid inputs"""
        score = 0.0
        details = []
        
        for i, invalid_input in enumerate(test_inputs):
            try:
                result = tool_func(**invalid_input)
                # If no exception, check if error is handled gracefully
                if isinstance(result, dict) and 'error' in result:
                    score += 0.5 / len(test_inputs)
                    details.append(f"✓ Test {i+1}: Graceful error handling")
                else:
                    details.append(f"? Test {i+1}: No error for invalid input")
            except Exception as e:
                # Exception is caught - check if it's informative
                if len(str(e)) > 10:
                    score += 0.5 / len(test_inputs)
                    details.append(f"✓ Test {i+1}: Informative exception")
                else:
                    details.append(f"✗ Test {i+1}: Uninformative exception")
        
        status = "PASS" if score >= 0.7 else "PARTIAL" if score >= 0.4 else "FAIL"
        
        return BestPracticeResult(
            criterion="Error Handling",
            status=status,
            details="; ".join(details),
            score=score
        )
    
    def evaluate_performance(self, tool_func, test_input: Dict) -> BestPracticeResult:
        """Evaluate tool performance"""
        try:
            start_time = time.time()
            result = tool_func(**test_input)
            execution_time = time.time() - start_time
            
            score = 0.0
            details = []
            
            # Performance thresholds
            if execution_time < 1.0:
                score += 0.4
                details.append(f"✓ Fast execution ({execution_time:.3f}s)")
            elif execution_time < 3.0:
                score += 0.2
                details.append(f"~ Acceptable execution ({execution_time:.3f}s)")
            else:
                details.append(f"✗ Slow execution ({execution_time:.3f}s)")
            
            # Response structure
            if isinstance(result, (dict, list)):
                score += 0.3
                details.append("✓ Structured response")
            else:
                details.append("✗ Unstructured response")
                
            # Response size reasonableness
            result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
            if 100 < len(result_str) < 50000:
                score += 0.3
                details.append(f"✓ Reasonable response size ({len(result_str)} chars)")
            else:
                details.append(f"? Response size: {len(result_str)} chars")
                
            status = "PASS" if score >= 0.7 else "PARTIAL" if score >= 0.4 else "FAIL"
            
            return BestPracticeResult(
                criterion="Performance",
                status=status,
                details="; ".join(details),
                score=score
            )
        except Exception as e:
            return BestPracticeResult(
                criterion="Performance",
                status="FAIL",
                details=f"Performance test failed: {e}",
                score=0.0
            )
    
    def evaluate_data_quality(self, tool_func, test_input: Dict) -> BestPracticeResult:
        """Evaluate output data quality"""
        try:
            result = tool_func(**test_input)
            
            score = 0.0
            details = []
            
            if isinstance(result, dict):
                # Check for required fields
                if 'results' in result or 'speech' in result or 'data' in result:
                    score += 0.3
                    details.append("✓ Has primary data field")
                else:
                    details.append("✗ Missing primary data field")
                
                # Check for metadata
                if any(key in result for key in ['metadata', 'count', 'total', 'timestamp']):
                    score += 0.3
                    details.append("✓ Includes metadata")
                else:
                    details.append("✗ Missing metadata")
                    
                # Check for non-empty results
                if result:
                    score += 0.4
                    details.append("✓ Non-empty response")
                else:
                    details.append("✗ Empty response")
            
            elif isinstance(result, list):
                if result:
                    score += 0.5
                    details.append(f"✓ List with {len(result)} items")
                else:
                    details.append("✗ Empty list")
                    
                if len(result) > 0 and isinstance(result[0], dict):
                    score += 0.5
                    details.append("✓ Structured list items")
            else:
                details.append("? Non-standard response format")
                
            status = "PASS" if score >= 0.7 else "PARTIAL" if score >= 0.4 else "FAIL"
            
            return BestPracticeResult(
                criterion="Data Quality",
                status=status,
                details="; ".join(details),
                score=score
            )
        except Exception as e:
            return BestPracticeResult(
                criterion="Data Quality",
                status="FAIL",
                details=f"Data quality test failed: {e}",
                score=0.0
            )

def run_comprehensive_evaluation():
    """Run comprehensive MCP best practices evaluation"""
    print("🔍 Starting Comprehensive MCP Best Practices Evaluation")
    print("=" * 60)
    
    evaluator = MCPBestPracticesEvaluator()
    
    # Test configurations
    tools_to_test = [
        {
            'name': 'search_hansard_speeches',
            'func': search_hansard_speeches,
            'valid_input': {'query': 'climate change', 'limit': 3},
            'invalid_inputs': [
                {'query': '', 'limit': -1},
                {'query': None},
                {'limit': 'invalid'}
            ]
        },
        {
            'name': 'fetch_hansard_speech',
            'func': fetch_hansard_speech,
            'valid_input': {'speech_id': 'd9c697e9-e13d-4769-9fbe-ce6cb18f4700'},
            'invalid_inputs': [
                {'speech_id': ''},
                {'speech_id': 'invalid-uuid'},
                {'speech_id': None}
            ]
        }
    ]
    
    all_results = []
    
    for tool_config in tools_to_test:
        print(f"\n📋 Evaluating: {tool_config['name']}")
        print("-" * 40)
        
        tool_results = []
        
        # 1. Tool Annotations
        result = evaluator.evaluate_tool_annotations(tool_config['func'])
        tool_results.append(result)
        print(f"  {result.status:8} | {result.criterion:20} | {result.details}")
        
        # 2. Docstring Quality
        result = evaluator.evaluate_docstring_quality(tool_config['func'])
        tool_results.append(result)
        print(f"  {result.status:8} | {result.criterion:20} | {result.details}")
        
        # 3. Error Handling
        result = evaluator.evaluate_error_handling(tool_config['func'], tool_config['invalid_inputs'])
        tool_results.append(result)
        print(f"  {result.status:8} | {result.criterion:20} | {result.details}")
        
        # 4. Performance
        result = evaluator.evaluate_performance(tool_config['func'], tool_config['valid_input'])
        tool_results.append(result)
        print(f"  {result.status:8} | {result.criterion:20} | {result.details}")
        
        # 5. Data Quality
        result = evaluator.evaluate_data_quality(tool_config['func'], tool_config['valid_input'])
        tool_results.append(result)
        print(f"  {result.status:8} | {result.criterion:20} | {result.details}")
        
        # Calculate tool score
        tool_score = sum(r.score for r in tool_results) / len(tool_results)
        print(f"  📊 Overall Tool Score: {tool_score:.2f}/1.00")
        
        all_results.extend(tool_results)
    
    # Overall summary
    print("\n" + "=" * 60)
    print("📊 OVERALL EVALUATION SUMMARY")
    print("=" * 60)
    
    total_score = sum(r.score for r in all_results) / len(all_results)
    pass_count = len([r for r in all_results if r.status == "PASS"])
    partial_count = len([r for r in all_results if r.status == "PARTIAL"])
    fail_count = len([r for r in all_results if r.status == "FAIL"])
    
    print(f"Overall Score: {total_score:.2f}/1.00")
    print(f"Results: {pass_count} PASS, {partial_count} PARTIAL, {fail_count} FAIL")
    
    if total_score >= 0.8:
        print("🎉 EXCELLENT: Tools meet MCP best practices standards")
    elif total_score >= 0.6:
        print("✅ GOOD: Tools meet most MCP best practices")
    elif total_score >= 0.4:
        print("⚠️  NEEDS IMPROVEMENT: Some best practices gaps")
    else:
        print("❌ POOR: Significant best practices violations")
    
    # Recommendations
    print("\n🔧 RECOMMENDATIONS:")
    for result in all_results:
        if result.status in ["FAIL", "PARTIAL"]:
            print(f"  • {result.criterion}: {result.details}")
    
    return {
        'total_score': total_score,
        'results': all_results,
        'summary': {
            'pass': pass_count,
            'partial': partial_count,
            'fail': fail_count
        }
    }

if __name__ == "__main__":
    evaluation_results = run_comprehensive_evaluation()