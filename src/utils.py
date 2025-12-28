"""
Utility functions for the Market Research Agent.
"""

import re
import json
from pathlib import Path
from typing import Optional, Any


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number to standard format.

    Args:
        phone: Phone number string

    Returns:
        Normalized phone number or None
    """
    if not phone:
        return None

    # Remove all non-numeric characters
    digits = re.sub(r'\D', '', phone)

    # Handle US phone numbers
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    return phone


def normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Normalize URL to include protocol.

    Args:
        url: URL string

    Returns:
        Normalized URL or None
    """
    if not url:
        return None

    url = url.strip()

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    return url


def safe_json_loads(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON with fallback.

    Args:
        text: JSON string
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Extract JSON object or array from text that may contain other content.

    Args:
        text: Text that might contain JSON

    Returns:
        Parsed JSON or None
    """
    text = text.strip()

    # Try direct parse first
    result = safe_json_loads(text)
    if result is not None:
        return result

    # Look for JSON array
    if '[' in text:
        start = text.find('[')
        # Find matching closing bracket
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char == '[':
                depth += 1
            elif char == ']':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break

    # Look for JSON object
    if '{' in text:
        start = text.find('{')
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break

    return None


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


# US States mapping
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
}


# Major cities by state (for fallback if manager doesn't generate enough cities)
MAJOR_CITIES = {
    "TX": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth", "El Paso", "Arlington", "Plano"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "San Jose", "Sacramento", "Fresno", "Oakland", "Long Beach"],
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale", "Tallahassee", "St. Petersburg", "Hialeah"],
    "NY": ["New York City", "Buffalo", "Rochester", "Albany", "Syracuse", "Yonkers"],
    "IL": ["Chicago", "Aurora", "Naperville", "Rockford", "Springfield", "Peoria"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Reading", "Erie", "Scranton"],
    "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton"],
    "GA": ["Atlanta", "Augusta", "Savannah", "Columbus", "Macon", "Athens"],
    "NC": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem", "Fayetteville"],
    "MI": ["Detroit", "Grand Rapids", "Warren", "Sterling Heights", "Ann Arbor", "Lansing"],
}


def get_major_cities(state: str) -> list[str]:
    """
    Get list of major cities for a state.

    Args:
        state: State abbreviation

    Returns:
        List of city names
    """
    return MAJOR_CITIES.get(state.upper(), [])
