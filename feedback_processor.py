import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

class FeedbackProcessor:
    def __init__(self, db_path="feedback.db"):
        self.db_path = Path(db_path)
        
    def get_feedback_summary(self, days_back=30):
        """Get summary of feedback for the specified time period"""
        conn = sqlite3.connect(str(self.db_path))
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Query feedback data
        query = """
            SELECT 
                term,
                original_suggestion,
                COUNT(*) as total_responses,
                SUM(CASE WHEN is_helpful = 1 THEN 1 ELSE 0 END) as helpful_count,
                AVG(CASE WHEN is_helpful = 1 THEN 1 ELSE 0 END) as helpful_ratio
            FROM feedback
            WHERE timestamp >= ?
            GROUP BY term, original_suggestion
            ORDER BY helpful_ratio DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(start_date,))
        conn.close()
        
        return df
    
    def get_context_analysis(self, term):
        """Analyze contexts where a term appears"""
        conn = sqlite3.connect(str(self.db_path))
        
        query = """
            SELECT context, is_helpful
            FROM feedback
            WHERE term = ?
        """
        
        df = pd.read_sql_query(query, conn, params=(term,))
        conn.close()
        
        return df
    
    def generate_improvement_report(self, min_responses=5):
        """Generate a report of potential improvements based on feedback"""
        df = self.get_feedback_summary()
        
        # Filter for terms with sufficient feedback
        df_filtered = df[df['total_responses'] >= min_responses]
        
        report = {
            "needs_improvement": [],
            "successful_suggestions": [],
            "improvement_opportunities": []
        }
        
        for _, row in df_filtered.iterrows():
            if row['helpful_ratio'] < 0.25:
                report["needs_improvement"].append({
                    "term": row['term'],
                    "current_suggestion": row['original_suggestion'],
                    "helpful_ratio": row['helpful_ratio'],
                    "total_responses": row['total_responses']
                })
            elif row['helpful_ratio'] > 0.5:
                report["successful_suggestions"].append({
                    "term": row['term'],
                    "suggestion": row['original_suggestion'],
                    "helpful_ratio": row['helpful_ratio'],
                    "total_responses": row['total_responses']
                })
        
        return report

def print_improvement_report():
    """Print a formatted improvement report"""
    processor = FeedbackProcessor()
    report = processor.generate_improvement_report()
    
    print("Bias Detection Model Improvement Report")
    print("=" * 50)
    
    print("\nTerms Needing Improvement:")
    for item in report["needs_improvement"]:
        print(f"\n- Term: {item['term']}")
        print(f"  Current suggestion: {item['current_suggestion']}")
        print(f"  Helpful ratio: {item['helpful_ratio']:.2%}")
        print(f"  Total responses: {item['total_responses']}")
        
        # Get context analysis
        context_df = processor.get_context_analysis(item['term'])
        print("\n  Context Analysis:")
        print(f"  - Total contexts analyzed: {len(context_df)}")
        print(f"  - Helpful in: {(context_df['is_helpful'] == 1).sum()} contexts")
    
    print("\nSuccessful Suggestions:")
    for item in report["successful_suggestions"]:
        print(f"\n- Term: {item['term']}")
        print(f"  Suggestion: {item['suggestion']}")
        print(f"  Helpful ratio: {item['helpful_ratio']:.2%}")
        print(f"  Total responses: {item['total_responses']}")

# Example usage
if __name__ == "__main__":
    print_improvement_report()