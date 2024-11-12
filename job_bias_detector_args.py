import google.generativeai as genai
from load_creds import load_creds
import json
from typing import Dict, Any, List
import os
from pathlib import Path
import asyncio
import argparse

class JobBiasDetector:
    def __init__(self):
        """Initialize the bias detector with Google API key."""
        creds = load_creds()
        genai.configure(credentials=creds)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.messages = []  # Store conversation history
        # Enhanced dictionary of biased terms with multiple discrimination categories
        self.bias_dict = {
            "young": {
                "categories": ["age discrimination", "direct discrimination"],
                "replacement": "motivated",
                "explanation": "Directly discriminates against older workers and violates age discrimination laws"
            },
            "energetic": {
                "categories": ["age discrimination", "indirect discrimination"],
                "replacement": "enthusiastic",
                "explanation": "Often used as coded language for age discrimination and may discourage older applicants"
            },
            "ninja": {
                "categories": ["unprofessional language", "cultural appropriation"],
                "replacement": "skilled professional",
                "explanation": "Uses casual language that may be inappropriate and culturally insensitive"
            },
            "crush targets": {
                "categories": ["aggressive language", "toxic culture"],
                "replacement": "achieve sales goals",
                "explanation": "Promotes aggressive behavior and may indicate toxic work environment"
            },
            "long hours": {
                "categories": ["work-life balance", "indirect discrimination"],
                "replacement": "flexible schedule based on project needs",
                "explanation": "May discriminate against caregivers and promote unhealthy work-life balance"
            }
        }
    
    def _create_initial_prompt(self) -> str:
        """Create the initial system prompt explaining the task."""
        bias_terms_json = json.dumps(self.bias_dict, indent=2)
        
        return f"""You are a job description analyzer specialized in detecting discriminatory language.
        You will analyze job descriptions using these predefined problematic terms and categories:
        
        {bias_terms_json}
        
        For each job description, provide analysis in this JSON format:
        {{
            "flagged_terms": [
                {{
                    "term": "exact problematic phrase",
                    "categories": ["list", "of", "discrimination", "categories"],
                    "context": "full sentence containing the term",
                    "explanation": "detailed explanation of why this is problematic",
                    "suggestion": "specific replacement text",
                    "severity": "number 1-5, where 5 is most severe",
                    "compounding_effects": "explanation of how this term combines with others"
                }}
            ],
            "discrimination_score": "number 0-10",
            "confidence_level": "number 0-1",
            "discrimination_categories": {{
                "age_discrimination": {{
                    "count": "number of instances",
                    "severity": "average severity 1-5",
                    "terms": ["list of terms"]
                }},
                "unprofessional_language": {{
                    "count": "number of instances",
                    "severity": "average severity 1-5",
                    "terms": ["list of terms"]
                }},
                "work_life_balance": {{
                    "count": "number of instances",
                    "severity": "average severity 1-5",
                    "terms": ["list of terms"]
                }},
                "aggressive_language": {{
                    "count": "number of instances",
                    "severity": "average severity 1-5",
                    "terms": ["list of terms"]
                }}
            }},
            "compounding_effects_summary": "explanation of how multiple biased terms interact",
            "overall_risk_assessment": "analysis of legal and ethical risks",
            "improved_description": "rewritten job description removing all biased language"
        }}"""

    def _create_analysis_prompt(self, job_description: str) -> str:
        """Create the prompt for analyzing a specific job description."""
        return f"""Analyze this job description for discriminatory language, considering all previous guidelines:

        Job Description:
        {job_description}

        Provide your analysis in the specified JSON format."""

    async def analyze_job_description(self, job_description: str) -> Dict[str, Any]:
        """Analyze a job description for bias and discrimination using conversation history."""
        try:
            # Start new conversation if this is the first analysis
            if not self.messages:
                initial_prompt = self._create_initial_prompt()
                self.messages = [
                    {'role': 'user', 'parts': [initial_prompt]}
                ]
                response = self.model.generate_content(self.messages)
                self.messages.append(response.candidates[0].content)

            # Add the job description analysis request
            analysis_prompt = self._create_analysis_prompt(job_description)
            self.messages.append({'role': 'user', 'parts': [analysis_prompt]})
            
            # Get the analysis
            response = self.model.generate_content(self.messages)
            
            # Add the response to conversation history
            self.messages.append(response.candidates[0].content)
            
            # Parse and return the analysis
            return response.text
            
        except Exception as e:
            return {
                "error": f"Analysis failed: {str(e)}",
                "flagged_terms": [],
                "discrimination_score": 0,
                "confidence_level": 0,
                "discrimination_categories": {
                    "age_discrimination": {"count": 0, "severity": 0, "terms": []},
                    "unprofessional_language": {"count": 0, "severity": 0, "terms": []},
                    "work_life_balance": {"count": 0, "severity": 0, "terms": []},
                    "aggressive_language": {"count": 0, "severity": 0, "terms": []}
                },
                "compounding_effects_summary": "Analysis failed",
                "overall_risk_assessment": "Analysis failed",
                "improved_description": job_description
            }

    async def analyze_multiple_descriptions(self, descriptions: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple job descriptions while maintaining conversation context."""
        results = []
        for description in descriptions:
            analysis = await self.analyze_job_description(description)
            results.append(analysis)
        return results

    def generate_report(self, analysis: Dict[str, Any], output_file: str = None) -> str:
        """Generate an enhanced report highlighting multiple discrimination types."""
        # Convert JSON string to dictionary if needed
        if isinstance(analysis, str):
            try:
                # Remove any leading/trailing whitespace and handle potential empty strings
                analysis = analysis.strip()
                if not analysis:
                    raise ValueError("Empty input string")
                # Try to parse the JSON string
                analysis = json.loads(analysis)
            except json.JSONDecodeError as e:
                # If the string is not valid JSON, try to strip any potential markdown code block syntax
                clean_str = analysis.replace('```json', '').replace('```', '').strip()
                try:
                    analysis = json.loads(clean_str)
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON input: {str(e)}")
            except Exception as e:
                raise ValueError(f"Error processing input: {str(e)}")

        report = f"""Job Description Bias Analysis Report
                {'='*80}

                OVERALL METRICS
                {'-'*40}
                Discrimination Score: {analysis.get('discrimination_score')}/10
                Confidence Level: {analysis.get('confidence_level')*100:.1f}%

                DISCRIMINATION CATEGORIES ANALYSIS
                {'-'*40}"""

        for category, details in analysis.get('discrimination_categories', {}).items():
            report += f"\n\n{category.replace('_', ' ').title()}:"
            report += f"\n  Instances: {details['count']}"
            report += f"\n  Average Severity: {details['severity']}/5"
            report += f"\n  Problematic Terms: {', '.join(details['terms'])}"

        report += f"\n\nDETAILED TERM ANALYSIS"
        report += f"\n{'-'*40}"

        for term in analysis.get('flagged_terms', []):
            report += f"\n\nFlagged Term: {term['term']}"
            report += f"\nCategories: {', '.join(term['categories'])}"
            report += f"\nContext: \"{term['context']}\""
            report += f"\nSeverity: {term['severity']}/5"
            report += f"\nExplanation: {term['explanation']}"
            report += f"\nCompounding Effects: {term['compounding_effects']}"
            report += f"\nSuggested Replacement: {term['suggestion']}"

        report += f"\n\nCOMPOUNDING EFFECTS SUMMARY"
        report += f"\n{'-'*40}"
        report += f"\n{analysis.get('compounding_effects_summary')}"

        report += f"\n\nRISK ASSESSMENT"
        report += f"\n{'-'*40}"
        report += f"\n{analysis.get('overall_risk_assessment')}"

        report += f"\n\nIMPROVED JOB DESCRIPTION"
        report += f"\n{'-'*40}"
        report += f"\n{analysis.get('improved_description')}"

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)

        return report

async def main():
    """
    Main function to analyze job descriptions for bias.
    Job descriptions can be provided either directly as arguments or through a file.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Analyze job descriptions for potential bias and discrimination.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python script.py "Job description 1" "Job description 2"
    python script.py -f job_descriptions.txt
    python script.py -o custom_output_dir "Job description 1"
        """)
    
    # Add arguments
    parser.add_argument('descriptions', nargs='*', help='Job descriptions to analyze (as quoted strings)')
    parser.add_argument('-f', '--file', type=str, help='File containing job descriptions (one per line)')
    parser.add_argument('-o', '--output-dir', type=str, default='bias_analysis_reports',
                       help='Directory to store analysis reports (default: bias_analysis_reports)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Get job descriptions from either command line arguments or file
    job_descriptions: List[str] = []
    
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                job_descriptions.extend(line.strip() for line in f if line.strip())
        except Exception as e:
            print(f"Error reading file {args.file}: {str(e)}")
            return
    
    # Add descriptions from command line arguments
    if args.descriptions:
        job_descriptions.extend(args.descriptions)
    
    # Check if we have any descriptions to analyze
    if not job_descriptions:
        parser.print_help()
        print("\nError: No job descriptions provided. Please provide descriptions either as arguments or through a file.")
        return
    
    # Initialize the detector
    detector = JobBiasDetector()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Analyze all descriptions
    try:
        analyses = await detector.analyze_multiple_descriptions(job_descriptions)
        
        # Generate reports for each analysis
        for i, analysis in enumerate(analyses, 1):
            output_file = output_dir / f"job_analysis_report_{i}.txt"
            report = detector.generate_report(analysis, str(output_file))
            print(f"\nAnalysis Report {i}:")
            print(report)
            print("\n" + "="*80 + "\n")
            
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return

if __name__ == "__main__":
    asyncio.run(main())