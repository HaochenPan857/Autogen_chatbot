import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

from src.agents.scoring_agent import ScoringAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Example of using the scoring agent to score a sustainability report"""
    
    # Path to your sustainability report
    # Replace this with the path to your actual report
    report_path = input("Enter the path to your sustainability report PDF or TXT file: ")
    
    if not os.path.exists(report_path):
        print(f"Error: File not found at {report_path}")
        return
    
    print(f"Scoring document: {os.path.basename(report_path)}")
    
    # Initialize the scoring agent
    agent = ScoringAgent()
    
    # Score the document
    result = agent.score_document(report_path)
    
    # Print the results
    print("\n" + "="*80)
    print("SCORING RESULTS")
    print("="*80)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"File: {result['file_name']}")
        print(f"Timestamp: {result['timestamp']}")
        print("\nDetailed Scoring:")
        print("-"*80)
        print(result['scoring_result'])
    
    print("="*80)

if __name__ == "__main__":
    main()
