import json
import asyncio
import sqlite3
from pathlib import Path
import sys
import traceback
from datetime import datetime
import textwrap
from typing import Optional, Dict, Any
import os

class JobBiasAnalyzerCLI:
    def __init__(self):
        """Initialize the CLI analyzer with database connection and debug settings"""
        self.debug_enabled = False
        self.current_analysis = None
        self._init_database()
        self.clear_screen()
        
    def _init_database(self):
        """Initialize SQLite database for feedback storage"""
        try:
            db_path = Path("feedback.db")
            self.conn = sqlite3.connect(str(db_path))
            self.cursor = self.conn.cursor()
            
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT,
                    original_suggestion TEXT,
                    is_helpful BOOLEAN,
                    timestamp DATETIME,
                    context TEXT
                )
            """)
            self.conn.commit()
            self.log_debug("Database initialized successfully")
        except Exception as e:
            self.log_debug(f"Database initialization error: {str(e)}", "ERROR")
            print("Warning: Feedback storage may not be available")

    def clear_screen(self):
        """Clear the terminal screen across platforms"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """Display the program header"""
        print("=" * 60)
        print("               Job Description Bias Analyzer")
        print("=" * 60)
        print()

    def log_debug(self, message: str, level: str = "INFO") -> None:
        """Log debug messages if debug mode is enabled"""
        if self.debug_enabled:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"\n[{timestamp}] [{level}] {message}")

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze job description text for bias"""
        try:
            # Import the detector here to handle potential import errors
            from job_bias_detector import JobBiasDetector
            detector = JobBiasDetector()
            return await detector.analyze_job_description(text)
        except ImportError:
            self.log_debug("Failed to import JobBiasDetector", "ERROR")
            return {"error": "Analysis module not found. Please ensure job_bias_detector.py is available."}
        except Exception as e:
            self.log_debug(f"Analysis error: {str(e)}", "ERROR")
            return {"error": f"Analysis failed: {str(e)}"}

    def display_results(self, analysis: Dict[str, Any]) -> None:
        """Display analysis results in a formatted way"""
        try:
            if "error" in analysis:
                print("\nError:", analysis["error"])
                return
            
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

            print("\nAnalysis Results:")
            print("-" * 40)
            print(f"Discrimination Score: {analysis.get('discrimination_score', 0)}/10")
            
            flagged_terms = analysis.get('flagged_terms', [])
            if flagged_terms:
                print("\nFlagged Terms:")
                for term in flagged_terms:
                    print("\n" + "-" * 40)
                    print(f"Term: {term.get('term', '')}")
                    print(f"Severity: {'●' * term.get('severity', 0)}{'○' * (5 - term.get('severity', 0))} ({term.get('severity', 0)}/5)")
                    print(f"Suggestion: {term.get('suggestion', '')}")
                    print("Explanation:")
                    # Wrap explanation text for better readability
                    explanation = term.get('explanation', '')
                    wrapped_explanation = textwrap.fill(explanation, width=60)
                    print(wrapped_explanation)
            else:
                print("\nNo biased terms detected.")

        except Exception as e:
            self.log_debug(f"Display error: {str(e)}", "ERROR")
            print("\nError displaying results. Check debug output for details.")

    def get_multiline_input(self) -> str:
        """Get multiline input from user with instructions"""
        print("\nEnter/paste your job description below.")
        print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) + Enter when finished.")
        print("Start typing:\n")
        
        contents = []
        while True:
            try:
                line = input()
                contents.append(line)
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nInput cancelled.")
                return ""
        
        return "\n".join(contents)

    def get_feedback(self) -> None:
        """Get user feedback on analysis results"""
        if not self.current_analysis or "error" in self.current_analysis:
            return

        print("\nWas this analysis helpful? (y/n/q to skip)")
        response = input("> ").lower()
        
        if response == 'q':
            return
        
        is_helpful = response.startswith('y')
        
        try:
            now = datetime.now().isoformat().replace(":", ".")
            # Store feedback for each flagged term
            for term in self.current_analysis.get('flagged_terms', []):
                self.cursor.execute("""
                    INSERT INTO feedback (term, original_suggestion, is_helpful, timestamp, context)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    term.get('term', ''),
                    term.get('suggestion', ''),
                    is_helpful,
                    now,
                    json.dumps(term)
                ))
            
            self.conn.commit()
            print("Thank you for your feedback!")
            
        except Exception as e:
            self.log_debug(f"Feedback storage error: {str(e)}", "ERROR")
            print("Failed to store feedback.")

    async def main_loop(self) -> None:
        """Main program loop"""
        while True:
            self.clear_screen()
            self.print_header()
            
            print("Options:")
            print("1. Analyze job description")
            print("2. Toggle debug mode", f"({'enabled' if self.debug_enabled else 'disabled'})")
            print("3. Clear screen")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ")
            
            if choice == '1':
                text = self.get_multiline_input()
                if text.strip():
                    print("\nAnalyzing...")
                    analysis = await self.analyze_text(text)

                    # Convert JSON string to dictionary if needed
                    if isinstance(analysis, str):
                        try:
                            # Remove any leading/trailing whitespace and handle potential empty strings
                            analysis = analysis.strip()
                            if not analysis:
                                raise ValueError("Empty input string")
                            # Try to parse the JSON string
                            self.current_analysis = json.loads(analysis)
                        except json.JSONDecodeError as e:
                            # If the string is not valid JSON, try to strip any potential markdown code block syntax
                            clean_str = analysis.replace('```json', '').replace('```', '').strip()
                            try:
                                self.current_analysis = json.loads(clean_str)
                            except json.JSONDecodeError:
                                raise ValueError(f"Invalid JSON input: {str(e)}")
                        except Exception as e:
                            raise ValueError(f"Error processing input: {str(e)}")

                    self.display_results(self.current_analysis)
                    self.get_feedback()
                    input("\nPress Enter to continue...")
                    
            elif choice == '2':
                self.debug_enabled = not self.debug_enabled
                print(f"\nDebug mode {'enabled' if self.debug_enabled else 'disabled'}.")
                input("Press Enter to continue...")
                
            elif choice == '3':
                continue
                
            elif choice == '4':
                print("\nThank you for using the Job Bias Analyzer!")
                break
            
            else:
                print("\nInvalid choice. Please try again.")
                input("Press Enter to continue...")

def main():
    """Main entry point with error handling"""
    try:
        print("Initializing Job Bias Analyzer...")
        analyzer = JobBiasAnalyzerCLI()
        asyncio.run(analyzer.main_loop())
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        traceback.print_exc()
    finally:
        try:
            analyzer.conn.close()
        except:
            pass

if __name__ == "__main__":
    main()