import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from IPython import __version__
import json
import asyncio
from datetime import datetime
import sqlite3
from pathlib import Path
import sys
import traceback
import io
from contextlib import redirect_stdout

class JobBiasAnalyzerUI:
    def __init__(self):
        """Initialize the UI with enhanced debug capture"""
        try:
            # Initialize database
            self._init_database()
            
            # Create UI components
            self.create_ui_components()
            
            # Store analysis results
            self.current_analysis = None
            
            # Enhanced debug output
            self.debug_output = widgets.Output(
                layout=widgets.Layout(
                    width='100%', 
                    border='1px solid #ff9999',
                    padding='10px',
                    margin='10px 0',
                    background_color='#fff8f8'
                )
            )
            
            # Debug status tracking
            self.has_error = False
            self.last_update_time = None
            
            # Main layout with debug visibility control
            self.main_container = widgets.VBox([
                widgets.HTML("<h2>Job Description Bias Analyzer</h2>"),
                widgets.HTML("<p>Paste your job description below and click 'Analyze' to check for potential bias.</p>"),
                self.input_area,
                widgets.HBox([
                    self.analyze_button,
                    self.debug_toggle,
                    self.auto_debug_toggle
                ]),
                self.debug_output,
                self.results_area,
                self.feedback_container
            ], layout=widgets.Layout(padding='20px'))
            
        except Exception as e:
            print(f"Initialization error: {str(e)}")
            traceback.print_exc()
    
    def _init_database(self):
        """Initialize SQLite database for feedback storage"""
        db_path = Path("feedback.db")
        self.conn = sqlite3.connect(str(db_path))
        self.cursor = self.conn.cursor()
        
        # Create tables if they don't exist
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
    
    def log_debug(self, message, level="INFO"):
        """Enhanced debug logging with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with self.debug_output:
            print(f"[{timestamp}] [{level}] {message}")
            
        self.last_update_time = datetime.now()
        
        # Auto-show debug output on errors or warnings
        if level in ["ERROR", "WARNING"] and self.auto_debug_toggle.value:
            self.debug_output.layout.display = 'block'
            self.has_error = True
    
    def on_analyze_click(self, b):
        """Handle analyze button click with enhanced debug capture"""
        description = self.input_area.value.strip()
        
        if not description:
            self.log_debug("Empty job description provided", "WARNING")
            with self.results_area:
                clear_output(wait=True)
                print("Please enter a job description to analyze.")
            return
        
        # Reset error state
        self.has_error = False
        
        # Clear previous outputs
        with self.debug_output:
            clear_output(wait=True)
        with self.results_area:
            clear_output(wait=True)
            print("Analyzing...")
        
        async def analyze():
            try:
                self.log_debug("Starting analysis")
                
                # Verify JobBiasDetector is imported and accessible
                if not hasattr(sys.modules[__name__], 'JobBiasDetector'):
                    self.log_debug("Attempting to import JobBiasDetector", "INFO")
                    # Add your import statement here
                    from job_bias_detector import JobBiasDetector
                
                # Create detector instance
                detector = JobBiasDetector()
                
                # Capture stdout during analysis
                stdout_capture = io.StringIO()
                with redirect_stdout(stdout_capture):
                    analysis = await detector.analyze_job_description(description)
                
                self.log_debug("Analysis completed successfully")
                
                # Log captured output
                self.log_debug("=== Analysis Details ===")
                self.log_debug(f"Input Length: {len(description)} characters")
                self.log_debug(f"Raw Output: {stdout_capture.getvalue()}")
                
                # Update UI with results
                self.current_analysis = analysis
                self.display_results(analysis)
                self.update_feedback_ui(analysis)
                
            except ImportError as e:
                self.log_debug(f"Import error: {str(e)}", "ERROR")
                self.log_debug(f"Current Python path: {sys.path}", "DEBUG")
                
            except Exception as e:
                self.log_debug(f"Analysis error: {str(e)}", "ERROR")
                self.log_debug(f"Traceback: {traceback.format_exc()}", "ERROR")
                self.log_debug(f"Current state - Description length: {len(description)}", "DEBUG")
                self.log_debug(f"Available modules: {list(sys.modules.keys())}", "DEBUG")
        
        # Create and run the async task with error handling
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(analyze())
            else:
                loop.run_until_complete(analyze())
        except Exception as e:
            self.log_debug(f"Async execution error: {str(e)}", "ERROR")
            self.log_debug(traceback.format_exc(), "ERROR")
    
    def create_ui_components(self):
        """Create all UI components with enhanced debug controls"""
        try:
            # Input area
            self.input_area = widgets.Textarea(
                placeholder='Paste your job description here...',
                layout=widgets.Layout(width='100%', height='150px')
            )
            
            # Analyze button
            self.analyze_button = widgets.Button(
                description='Analyze',
                button_style='primary',
                layout=widgets.Layout(width='200px')
            )
            self.analyze_button.on_click(self.on_analyze_click)
            
            # Results area
            self.results_area = widgets.Output(
                layout=widgets.Layout(width='100%', border='1px solid #ddd', padding='10px')
            )
            
            # Debug toggle button
            self.debug_toggle = widgets.ToggleButton(
                value=False,
                description='Show Debug Output',
                icon='bug'
            )
            
            # Auto-debug toggle
            self.auto_debug_toggle = widgets.ToggleButton(
                value=True,
                description='Auto-show Debug on Error',
                icon='warning',
                button_style='warning'
            )
            
            def toggle_debug(change):
                self.debug_output.layout.display = 'block' if change['new'] else 'none'
            
            self.debug_toggle.observe(toggle_debug, 'value')
            
            # Feedback container
            self.feedback_container = widgets.VBox([])
            

            
        except Exception as e:
            print(f"UI component creation error: {str(e)}")
            traceback.print_exc()
    
    def display_results(self, analysis):
        """Display analysis results with enhanced error handling"""
        try:
            with self.results_area:
                clear_output(wait=True)
                
                if isinstance(analysis, str):
                    try:
                        analysis = json.loads(analysis)
                    except json.JSONDecodeError:
                        self.log_debug("Failed to parse analysis JSON", "ERROR")
                        self.log_debug(f"Raw analysis: {analysis}", "DEBUG")
                        print("Error: Invalid analysis format")
                        return
                
                if "error" in analysis:
                    self.log_debug(f"Analysis returned error: {analysis['error']}", "ERROR")
                    print(f"Error: {analysis['error']}")
                    return
                
                self.log_debug("Displaying analysis results")
                print("Analysis Results:")
                print(f"Discrimination Score: {analysis.get('discrimination_score', 0)}/10")
                print("\nFlagged Terms:")
                
                for term in analysis.get('flagged_terms', []):
                    print(f"\n- Term: {term.get('term', '')}")
                    print(f"  Severity: {term.get('severity', 0)}/5")
                    print(f"  Suggestion: {term.get('suggestion', '')}")
                    print(f"  Explanation: {term.get('explanation', '')}")
                
        except Exception as e:
            self.log_debug(f"Display error: {str(e)}", "ERROR")
            self.log_debug(traceback.format_exc(), "ERROR")
                
    def display(self):
        """Display the UI with debug handling"""
        try:
            display(self.main_container)
            self.log_debug("UI initialized successfully")
        except Exception as e:
            print(f"Failed to display UI: {str(e)}")
            traceback.print_exc()
        
    def create_feedback_widget(self, term, suggestion):
        """Create feedback widget for a single term"""
        term_container = widgets.VBox([
            widgets.HTML(f"<b>Term:</b> {term}"),
            widgets.HTML(f"<b>Suggestion:</b> {suggestion}"),
            widgets.RadioButtons(
                options=['Helpful', 'Not Helpful'],
                description='Was this suggestion helpful?',
                layout=widgets.Layout(margin='10px 0')
            )
        ], layout=widgets.Layout(margin='10px 0', padding='10px', border='1px solid #eee'))
        
        return term_container
    
    def save_feedback(self, term, suggestion, is_helpful, context):
        """Save feedback to database"""
        self.cursor.execute("""
            INSERT INTO feedback (term, original_suggestion, is_helpful, timestamp, context)
            VALUES (?, ?, ?, ?, ?)
        """, (term, suggestion, is_helpful, datetime.now(), context))
        self.conn.commit()
    
    def update_feedback_ui(self, analysis):
        """Update feedback UI with new analysis results"""
        feedback_widgets = []
        
        for term_data in analysis.get('flagged_terms', []):
            term = term_data.get('term', '')
            suggestion = term_data.get('suggestion', '')
            
            # Create feedback widget
            feedback_widget = self.create_feedback_widget(term, suggestion)
            
            # Add callback for feedback
            def make_callback(t=term, s=suggestion):
                def callback(change):
                    if change['type'] == 'value':
                        is_helpful = change['new'] == 'Helpful'
                        self.save_feedback(t, s, is_helpful, self.input_area.value)
                return callback
            
            feedback_widget.children[-1].observe(make_callback(), names='value')
            feedback_widgets.append(feedback_widget)
        
        self.feedback_container.children = feedback_widgets
    
if __name__ == "__main__":
    # Usage example with enhanced debug output
    print("=== Environment Information ===")
    print(f"Python version: {sys.version}")
    print(f"IPython version: {__version__}")
    print(f"Working directory: {Path.cwd()}")
    print("\n=== Initializing UI ===")

    try:
        analyzer_ui = JobBiasAnalyzerUI()
        analyzer_ui.display()
    except Exception as e:
        print(f"Failed to initialize UI: {str(e)}")
        traceback.print_exc()