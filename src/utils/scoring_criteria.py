import json
import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ScoringCriteria:
    """Utility class to load and manage sustainability report scoring criteria"""
    
    @staticmethod
    def load_criteria(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load scoring criteria from a JSON file
        
        Args:
            file_path: Path to the JSON file containing scoring criteria
            
        Returns:
            Dictionary containing the scoring criteria or None if loading fails
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Scoring criteria file not found: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                criteria_data = json.load(f)
                
            logger.info(f"Successfully loaded scoring criteria from {file_path}")
            return criteria_data
        except Exception as e:
            logger.error(f"Error loading scoring criteria from {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def get_categories(criteria_data: Dict[str, Any]) -> List[str]:
        """
        Get list of scoring categories from criteria data
        
        Args:
            criteria_data: Dictionary containing scoring criteria
            
        Returns:
            List of category names
        """
        if not criteria_data:
            return []
        
        return list(criteria_data.keys())
    
    @staticmethod
    def get_dimensions_for_category(criteria_data: Dict[str, Any], category: str) -> List[Dict[str, str]]:
        """
        Get dimensions for a specific category
        
        Args:
            criteria_data: Dictionary containing scoring criteria
            category: Category name to get dimensions for
            
        Returns:
            List of dimension dictionaries with 'dimension' and 'description' keys
        """
        if not criteria_data or category not in criteria_data:
            return []
        
        return criteria_data.get(category, {}).get("dimensions", [])
    
    @staticmethod
    def format_criteria_for_prompt(criteria_data: Dict[str, Any]) -> str:
        """
        Format scoring criteria into a string suitable for inclusion in a prompt
        
        Args:
            criteria_data: Dictionary containing scoring criteria
            
        Returns:
            Formatted string with categories and dimensions
        """
        if not criteria_data:
            return "No scoring criteria available."
        
        formatted_output = []
        
        for category, content in criteria_data.items():
            formatted_output.append(f"## {category}")
            
            for dimension in content.get("dimensions", []):
                dim_name = dimension.get("dimension", "")
                dim_desc = dimension.get("description", "")
                
                if dim_name and dim_desc:
                    # Remove content references from descriptions
                    desc_cleaned = dim_desc
                    while ":contentReference[" in desc_cleaned:
                        start_idx = desc_cleaned.find(":contentReference[")
                        end_idx = desc_cleaned.find("]", start_idx)
                        if end_idx > start_idx:
                            desc_cleaned = desc_cleaned[:start_idx] + desc_cleaned[end_idx+1:]
                        else:
                            break
                    
                    formatted_output.append(f"### {dim_name}")
                    formatted_output.append(f"{desc_cleaned}\n")
        
        return "\n".join(formatted_output)
