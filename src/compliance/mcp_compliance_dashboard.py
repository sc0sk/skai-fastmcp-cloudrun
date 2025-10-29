#!/usr/bin/env python3
"""
Phase 3: MCP Best Practices Compliance Dashboard

Automated compliance scoring system that:
✅ Measures tool documentation quality
✅ Tracks best practices adherence
✅ Generates improvement recommendations
✅ Produces compliance reports
✅ Enables tracking over time
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict


@dataclass
class ComplianceMetric:
    """Single compliance metric"""
    name: str
    category: str
    weight: float  # Importance weight (0-1)
    score: float  # Achieved score (0-1)
    status: str  # "PASS", "WARN", "FAIL"
    evidence: str  # Supporting evidence/details
    recommendation: str  # Improvement suggestion


class MCPComplianceDashboard:
    """MCP Best Practices Compliance Scoring System"""

    # MCP Best Practices Checklist
    COMPLIANCE_CATEGORIES = {
        "Documentation": {
            "weight": 0.3,
            "metrics": {
                "description_quality": 0.2,
                "returns_documentation": 0.4,
                "error_documentation": 0.2,
                "examples": 0.2
            }
        },
        "Error Handling": {
            "weight": 0.25,
            "metrics": {
                "exception_types": 0.3,
                "error_messages": 0.4,
                "graceful_degradation": 0.3
            }
        },
        "Performance": {
            "weight": 0.15,
            "metrics": {
                "latency": 0.4,
                "response_size": 0.3,
                "timeout_handling": 0.3
            }
        },
        "Data Quality": {
            "weight": 0.15,
            "metrics": {
                "structure_validation": 0.4,
                "field_completeness": 0.3,
                "type_consistency": 0.3
            }
        },
        "Integration": {
            "weight": 0.15,
            "metrics": {
                "async_support": 0.4,
                "annotations": 0.3,
                "parameter_validation": 0.3
            }
        }
    }

    def __init__(self):
        self.metrics: List[ComplianceMetric] = []
        self.report_timestamp = datetime.now()

    def check_documentation_quality(self, docstring: str) -> ComplianceMetric:
        """Check documentation quality"""
        if not docstring:
            return ComplianceMetric(
                name="Documentation Quality",
                category="Documentation",
                weight=0.2,
                score=0.0,
                status="FAIL",
                evidence="No docstring found",
                recommendation="Add comprehensive docstring with Use/Don't use sections"
            )

        score = 0.0
        evidence = []

        # Check for key sections
        sections = {
            "Use this when": 0.15,
            "Do not use": 0.15,
            "Parameters": 0.2,
            "Returns": 0.25,
            "Error Conditions": 0.15,
            "Edge Cases": 0.1,
        }

        found_sections = []
        for section, weight in sections.items():
            if section.lower() in docstring.lower():
                score += weight
                found_sections.append(section)
                evidence.append(f"✓ Has {section}")
            else:
                evidence.append(f"✗ Missing {section}")

        status = "PASS" if score >= 0.85 else "WARN" if score >= 0.6 else "FAIL"

        return ComplianceMetric(
            name="Documentation Quality",
            category="Documentation",
            weight=0.2,
            score=score,
            status=status,
            evidence="; ".join(evidence),
            recommendation=(
                f"Found {len(found_sections)}/6 key sections. "
                f"Add missing: {', '.join(set(sections.keys()) - set(found_sections))}"
            )
        )

    def check_returns_documentation(self, docstring: str) -> ComplianceMetric:
        """Check for detailed Returns section"""
        if not docstring:
            return ComplianceMetric(
                name="Returns Documentation",
                category="Documentation",
                weight=0.4,
                score=0.0,
                status="FAIL",
                evidence="No docstring",
                recommendation="Add Returns section with response schema"
            )

        score = 0.0
        evidence = []

        if "Returns:" in docstring or "returns:" in docstring.lower():
            score += 0.3
            evidence.append("✓ Has Returns section")

            # Check for schema details
            returns_section = docstring.split("Returns:")[1] if "Returns:" in docstring else docstring.split("returns:")[1]
            
            if "{" in returns_section and "}" in returns_section:
                score += 0.3
                evidence.append("✓ Has response schema")
            else:
                evidence.append("✗ Missing response schema")

            if "Error" in returns_section or "error" in returns_section:
                score += 0.2
                evidence.append("✓ Documents error responses")
            else:
                evidence.append("✗ Missing error response docs")

            if "Example" in returns_section:
                score += 0.2
                evidence.append("✓ Has example response")
            else:
                evidence.append("✗ Missing example response")
        else:
            evidence.append("✗ No Returns section found")

        status = "PASS" if score >= 0.8 else "WARN" if score >= 0.5 else "FAIL"

        return ComplianceMetric(
            name="Returns Documentation",
            category="Documentation",
            weight=0.4,
            score=score,
            status=status,
            evidence="; ".join(evidence),
            recommendation="Ensure Returns section includes: schema, error cases, example response"
        )

    def check_error_documentation(self, docstring: str) -> ComplianceMetric:
        """Check for error condition documentation"""
        if not docstring:
            return ComplianceMetric(
                name="Error Documentation",
                category="Documentation",
                weight=0.2,
                score=0.0,
                status="FAIL",
                evidence="No docstring",
                recommendation="Add Error Conditions section"
            )

        score = 0.0
        evidence = []

        if "Error" in docstring:
            score += 0.4
            evidence.append("✓ Has error documentation")

            # Check for specific error types
            error_types = ["ValueError", "TypeError", "ConnectionError", "RuntimeError", "TimeoutError"]
            found_errors = sum(1 for et in error_types if et in docstring)
            
            if found_errors >= 2:
                score += 0.4
                evidence.append(f"✓ Documents {found_errors} error types")
            elif found_errors >= 1:
                score += 0.2
                evidence.append(f"✓ Documents {found_errors} error type")
            else:
                evidence.append("✗ No specific error types documented")

            if "Edge Case" in docstring or "edge case" in docstring.lower():
                score += 0.2
                evidence.append("✓ Documents edge cases")
            else:
                evidence.append("✗ Missing edge case documentation")
        else:
            evidence.append("✗ No error documentation section")

        status = "PASS" if score >= 0.8 else "WARN" if score >= 0.5 else "FAIL"

        return ComplianceMetric(
            name="Error Documentation",
            category="Documentation",
            weight=0.2,
            score=score,
            status=status,
            evidence="; ".join(evidence),
            recommendation="Document specific error types, messages, and handling approaches"
        )

    def check_async_support(self, is_async: bool, function_name: str) -> ComplianceMetric:
        """Check for async/await support"""
        if is_async:
            return ComplianceMetric(
                name="Async Support",
                category="Integration",
                weight=0.4,
                score=1.0,
                status="PASS",
                evidence="✓ Function is properly async",
                recommendation="Maintain async support for FastMCP compatibility"
            )
        else:
            return ComplianceMetric(
                name="Async Support",
                category="Integration",
                weight=0.4,
                score=0.0,
                status="FAIL",
                evidence="✗ Function is synchronous",
                recommendation=f"Convert {function_name} to async function for MCP compatibility"
            )

    def check_parameter_validation(self, docstring: str) -> ComplianceMetric:
        """Check for parameter validation documentation"""
        if not docstring:
            return ComplianceMetric(
                name="Parameter Validation",
                category="Integration",
                weight=0.3,
                score=0.0,
                status="FAIL",
                evidence="No docstring",
                recommendation="Add parameter validation documentation"
            )

        score = 0.0
        evidence = []

        if "Parameters" in docstring or "parameters:" in docstring.lower():
            score += 0.3
            evidence.append("✓ Has Parameters section")

            # Check for type hints
            if ":" in docstring and ("str" in docstring or "int" in docstring or "bool" in docstring):
                score += 0.3
                evidence.append("✓ Documents parameter types")
            else:
                evidence.append("✗ Missing parameter types")

            # Check for constraints
            if "required" in docstring.lower() or "optional" in docstring.lower():
                score += 0.2
                evidence.append("✓ Documents required/optional")
            else:
                evidence.append("✗ Missing required/optional indicators")

            if "default" in docstring.lower() or "range" in docstring.lower():
                score += 0.2
                evidence.append("✓ Documents defaults/constraints")
            else:
                evidence.append("✗ Missing defaults/constraints")
        else:
            evidence.append("✗ No Parameters section")

        status = "PASS" if score >= 0.8 else "WARN" if score >= 0.5 else "FAIL"

        return ComplianceMetric(
            name="Parameter Validation",
            category="Integration",
            weight=0.3,
            score=score,
            status=status,
            evidence="; ".join(evidence),
            recommendation="Ensure all parameters are documented with types, defaults, and constraints"
        )

    def generate_compliance_score(self, metrics: List[ComplianceMetric]) -> float:
        """Calculate overall compliance score (0-1)"""
        if not metrics:
            return 0.0

        total_weighted_score = 0.0
        total_weight = 0.0

        for metric in metrics:
            total_weighted_score += metric.score * metric.weight
            total_weight += metric.weight

        return total_weighted_score / total_weight if total_weight > 0 else 0.0

    def generate_report(self, tool_name: str, docstring: str, is_async: bool = True) -> Dict[str, Any]:
        """Generate compliance report for a single tool"""
        metrics = []

        # Documentation checks
        metrics.append(self.check_documentation_quality(docstring))
        metrics.append(self.check_returns_documentation(docstring))
        metrics.append(self.check_error_documentation(docstring))

        # Integration checks
        metrics.append(self.check_async_support(is_async, tool_name))
        metrics.append(self.check_parameter_validation(docstring))

        # Calculate scores
        compliance_score = self.generate_compliance_score(metrics)
        
        # Categorize metrics by category
        metrics_by_category = {}
        for metric in metrics:
            if metric.category not in metrics_by_category:
                metrics_by_category[metric.category] = []
            metrics_by_category[metric.category].append(metric)

        # Calculate category scores
        category_scores = {}
        for category, cat_metrics in metrics_by_category.items():
            cat_score = self.generate_compliance_score(cat_metrics)
            category_scores[category] = cat_score

        # Grade assessment
        if compliance_score >= 0.9:
            grade = "EXCELLENT"
            assessment = "Tool meets all MCP best practices"
        elif compliance_score >= 0.8:
            grade = "VERY GOOD"
            assessment = "Tool meets most best practices with minor gaps"
        elif compliance_score >= 0.7:
            grade = "GOOD"
            assessment = "Tool meets key best practices but needs improvements"
        elif compliance_score >= 0.6:
            grade = "FAIR"
            assessment = "Tool has significant best practices gaps"
        else:
            grade = "POOR"
            assessment = "Tool does not meet MCP best practices"

        # Generate recommendations
        failing_metrics = [m for m in metrics if m.status in ["FAIL", "WARN"]]
        recommendations = [m.recommendation for m in failing_metrics]

        return {
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "compliance_score": compliance_score,
            "grade": grade,
            "assessment": assessment,
            "category_scores": category_scores,
            "metrics": [asdict(m) for m in metrics],
            "recommendations": recommendations,
            "passing_metrics": len([m for m in metrics if m.status == "PASS"]),
            "total_metrics": len(metrics)
        }

    def generate_dashboard_html(self, reports: List[Dict[str, Any]]) -> str:
        """Generate HTML dashboard for compliance reports"""
        html = """
        <html>
        <head>
            <title>MCP Compliance Dashboard - Phase 3</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .dashboard { max-width: 1200px; margin: 0 auto; }
                .header { background: #003366; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .header h1 { margin: 0; }
                .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .card.excellent { border-left: 4px solid #4CAF50; }
                .card.very_good { border-left: 4px solid #8BC34A; }
                .card.good { border-left: 4px solid #FFC107; }
                .card.fair { border-left: 4px solid #FF9800; }
                .card.poor { border-left: 4px solid #f44336; }
                .score { font-size: 32px; font-weight: bold; color: #003366; }
                .grade { font-size: 18px; color: #666; }
                .metrics { margin-top: 10px; }
                .metric { padding: 8px; font-size: 14px; }
                .metric.pass { color: #4CAF50; }
                .metric.warn { color: #FF9800; }
                .metric.fail { color: #f44336; }
                .recommendations { background: #FFF8DC; padding: 15px; border-left: 4px solid #FFC107; margin-top: 10px; }
                .footer { text-align: center; margin-top: 30px; color: #999; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="dashboard">
                <div class="header">
                    <h1>🎯 MCP Best Practices Compliance Dashboard</h1>
                    <p>Feature 018: Phase 3 - Automated Compliance Scoring</p>
                </div>
        """

        for report in reports:
            grade_class = report["grade"].lower().replace(" ", "_")
            html += f"""
                <div class="card {grade_class}">
                    <h2>{report["tool_name"]}</h2>
                    <div class="score">{report["compliance_score"]:.2%}</div>
                    <div class="grade">{report["grade"]} - {report["assessment"]}</div>
                    
                    <div class="metrics">
                        <strong>Category Scores:</strong>
            """
            for category, score in report["category_scores"].items():
                html += f"<div class=\"metric\">• {category}: {score:.0%}</div>"

            html += f"""
                    </div>
                    
                    <div class="metrics">
                        <strong>Metrics: {report["passing_metrics"]}/{report["total_metrics"]} Passing</strong>
            """
            for metric in report["metrics"]:
                status_class = metric["status"].lower()
                html += f'<div class="metric {status_class}">• {metric["name"]}: {status_class}</div>'

            html += """
                    </div>
            """
            
            if report["recommendations"]:
                html += """
                    <div class="recommendations">
                        <strong>🔧 Recommendations:</strong>
                """
                for rec in report["recommendations"]:
                    html += f"<div>• {rec}</div>"
                html += """
                    </div>
                """

            html += """
                </div>
            """

        html += """
                <div class="footer">
                    <p>MCP Compliance Dashboard | Feature 018 Phase 3 | Generated automatically</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html


def main():
    """Generate compliance dashboard for MCP tools"""
    import sys
    sys.path.insert(0, '/home/user/skai-fastmcp-cloudrun/src')

    from tools.search import search_hansard_speeches
    from tools.fetch import fetch_hansard_speech

    dashboard = MCPComplianceDashboard()

    # Get tool information
    tools = [
        (search_hansard_speeches, "search_hansard_speeches", True),
        (fetch_hansard_speech, "fetch_hansard_speech", True),
    ]

    reports = []
    for tool_func, tool_name, is_async in tools:
        docstring = tool_func.__doc__ or ""
        report = dashboard.generate_report(tool_name, docstring, is_async)
        reports.append(report)

    # Print text summary
    print("=" * 70)
    print("🎯 MCP COMPLIANCE DASHBOARD - PHASE 3")
    print("=" * 70)

    for report in reports:
        print(f"\n📋 {report['tool_name']}")
        print(f"   Score: {report['compliance_score']:.2%}")
        print(f"   Grade: {report['grade']}")
        print(f"   Assessment: {report['assessment']}")
        print(f"   Metrics: {report['passing_metrics']}/{report['total_metrics']} passing")

        if report["recommendations"]:
            print(f"   Recommendations:")
            for rec in report["recommendations"]:
                print(f"      • {rec}")

    # Save JSON report
    with open('/home/user/skai-fastmcp-cloudrun/compliance_report.json', 'w') as f:
        json.dump(reports, f, indent=2)
    print(f"\n✅ JSON report saved to compliance_report.json")

    # Save HTML report
    html_content = dashboard.generate_dashboard_html(reports)
    with open('/home/user/skai-fastmcp-cloudrun/COMPLIANCE_DASHBOARD.html', 'w') as f:
        f.write(html_content)
    print(f"✅ HTML dashboard saved to COMPLIANCE_DASHBOARD.html")

    return reports


if __name__ == "__main__":
    reports = main()
