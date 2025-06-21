import json
import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MetricsLoader:
    """Utility class to load sustainability metrics from reference JSON files"""
    
    @staticmethod
    def load_metrics_from_json(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load sustainability metrics and definitions from a JSON file
        
        Args:
            file_path: Path to the JSON file containing metrics
            
        Returns:
            Dictionary containing the metrics data or None if loading fails
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Metrics file not found: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                metrics_data = json.load(f)
                
            logger.info(f"Successfully loaded metrics from {file_path}")
            return metrics_data
        except Exception as e:
            logger.error(f"Error loading metrics from {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def format_metrics_for_prompt(metrics_data: Dict[str, Any]) -> str:
        """
        Format metrics data into a string suitable for inclusion in a prompt
        
        Args:
            metrics_data: Dictionary containing metrics data
            
        Returns:
            Formatted string with metrics and definitions
        """
        if not metrics_data:
            return "No metrics data available."
            
        try:
            # Extract the key containing the metrics list
            key = list(metrics_data.keys())[0]
            metrics_list = metrics_data.get(key, [])
            
            formatted_metrics = []
            for metric in metrics_list:
                term = metric.get("term", "")
                definition = metric.get("definition", "")
                if term and definition:
                    formatted_metrics.append(f"- {term}: {definition}")
            
            if formatted_metrics:
                return "SUSTAINABILITY METRICS AND DEFINITIONS:\n" + "\n\n".join(formatted_metrics)
            else:
                return "No valid metrics found in the data."
        except Exception as e:
            logger.error(f"Error formatting metrics for prompt: {str(e)}")
            return "Error formatting metrics data."
