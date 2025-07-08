"""
URL builders for Rightmove and Zoopla property searches
Converts SearchConfig into portal-specific search URLs
"""

import re
from typing import List
from urllib.parse import quote, urlencode

from homehunt.core.models import Portal, PropertyType

from .config import FurnishedType, LetType, SearchConfig, SortOrder


class RightmoveURLBuilder:
    """Build search URLs for Rightmove"""
    
    BASE_URL = "https://www.rightmove.co.uk/property-to-rent/find.html"
    
    # Property type mappings for Rightmove
    PROPERTY_TYPE_MAP = {
        PropertyType.FLAT: "flats",
        PropertyType.HOUSE: "houses",
        PropertyType.STUDIO: "flats",  # Studios are listed under flats
        PropertyType.BUNGALOW: "bungalows",
        PropertyType.MAISONETTE: "flats",  # Maisonettes are listed under flats
    }
    
    # Sort order mappings
    SORT_MAP = {
        SortOrder.PRICE_ASC: "1",
        SortOrder.PRICE_DESC: "2",
        SortOrder.DATE_DESC: "6",
        SortOrder.DATE_ASC: "10",
    }
    
    # Furnished status mappings
    FURNISHED_MAP = {
        FurnishedType.FURNISHED: "furnished",
        FurnishedType.UNFURNISHED: "unfurnished",
        FurnishedType.PART_FURNISHED: "partFurnished",
        FurnishedType.ANY: "",
    }
    
    @classmethod
    def build_url(cls, config: SearchConfig) -> str:
        """Build Rightmove search URL from config"""
        params = {}
        
        # Location - encode the location parameter
        params["searchLocation"] = config.location
        
        # Radius (convert miles to km)
        if config.radius:
            km_radius = round(float(config.radius) * 1.60934)
            params["radius"] = str(km_radius)
        
        # Price range
        if config.min_price is not None:
            params["minPrice"] = str(config.min_price)
        if config.max_price is not None:
            params["maxPrice"] = str(config.max_price)
        
        # Bedrooms
        if config.min_bedrooms is not None:
            params["minBedrooms"] = str(config.min_bedrooms)
        if config.max_bedrooms is not None:
            params["maxBedrooms"] = str(config.max_bedrooms)
        
        # Property types
        if config.property_types:
            # Rightmove uses multiple propertyTypes[] parameters
            for prop_type in config.property_types:
                if prop_type in cls.PROPERTY_TYPE_MAP:
                    if "propertyTypes" not in params:
                        params["propertyTypes"] = []
                    params["propertyTypes"].append(cls.PROPERTY_TYPE_MAP[prop_type])
        
        # Furnished status
        if config.furnished != FurnishedType.ANY:
            furnished_value = cls.FURNISHED_MAP.get(config.furnished)
            if furnished_value:
                params["furnishTypes"] = furnished_value
        
        # Additional features
        if config.parking:
            params["mustHave"] = params.get("mustHave", [])
            params["mustHave"].append("parking")
        
        if config.garden:
            params["mustHave"] = params.get("mustHave", [])
            params["mustHave"].append("garden")
        
        # Let type
        if config.let_type == LetType.SHORT_TERM:
            params["letType"] = "short-term"
        elif config.let_type == LetType.LONG_TERM:
            params["letType"] = "long-term"
        
        # Include let agreed
        if not config.include_let_agreed:
            params["includeLetAgreed"] = "false"
        
        # Pets allowed
        if config.pets_allowed:
            params["petsAllowed"] = "true"
        
        # Student friendly
        if config.student_friendly:
            params["keywords"] = params.get("keywords", [])
            params["keywords"].append("student")
        
        # DSS accepted
        if config.dss_accepted:
            params["dssWelcome"] = "true"
        
        # Keywords
        if config.keywords:
            params["keywords"] = params.get("keywords", [])
            params["keywords"].extend(config.keywords)
        
        # Sort order
        params["sortType"] = cls.SORT_MAP.get(config.sort_order, "6")
        
        # Number of results per page (Rightmove default is 24)
        params["resultsPerPage"] = "24"
        
        # Build the URL
        url_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                # Handle array parameters
                for item in value:
                    url_parts.append(f"{key}[]={quote(str(item))}")
            else:
                url_parts.append(f"{key}={quote(str(value))}")
        
        return f"{cls.BASE_URL}?{'&'.join(url_parts)}"
    
    @classmethod
    def get_pagination_urls(cls, base_url: str, total_results: int, page_size: int = 24) -> List[str]:
        """Generate pagination URLs for all pages"""
        urls = [base_url]
        
        if total_results > page_size:
            num_pages = (total_results + page_size - 1) // page_size
            for page in range(1, num_pages):
                offset = page * page_size
                # Add index parameter for pagination
                separator = "&" if "?" in base_url else "?"
                urls.append(f"{base_url}{separator}index={offset}")
        
        return urls


class ZooplaURLBuilder:
    """Build search URLs for Zoopla"""
    
    BASE_URL = "https://www.zoopla.co.uk/to-rent/property"
    
    # Property type mappings for Zoopla
    PROPERTY_TYPE_MAP = {
        PropertyType.FLAT: "flats",
        PropertyType.HOUSE: "houses",
        PropertyType.STUDIO: "studios",
        PropertyType.BUNGALOW: "bungalows",
        PropertyType.MAISONETTE: "flats",  # Maisonettes listed under flats
    }
    
    # Sort order mappings
    SORT_MAP = {
        SortOrder.PRICE_ASC: "rental_price_ascending",
        SortOrder.PRICE_DESC: "rental_price_descending",
        SortOrder.DATE_DESC: "most_recent",
        SortOrder.DATE_ASC: "oldest_first",
    }
    
    # Furnished status mappings
    FURNISHED_MAP = {
        FurnishedType.FURNISHED: "furnished",
        FurnishedType.UNFURNISHED: "unfurnished",
        FurnishedType.PART_FURNISHED: "part_furnished",
        FurnishedType.ANY: "",
    }
    
    @classmethod
    def build_url(cls, config: SearchConfig) -> str:
        """Build Zoopla search URL from config"""
        
        # Start with property type in URL path
        url_parts = [cls.BASE_URL]
        
        # Add property types to URL path
        if config.property_types:
            for prop_type in config.property_types:
                if prop_type in cls.PROPERTY_TYPE_MAP:
                    url_parts.append(cls.PROPERTY_TYPE_MAP[prop_type])
        
        # Add location to URL path
        # Clean location for URL (remove special characters)
        clean_location = re.sub(r'[^\w\s-]', '', config.location.lower())
        clean_location = re.sub(r'[-\s]+', '-', clean_location)
        url_parts.append(clean_location)
        
        base_path = "/".join(url_parts)
        
        # Build query parameters
        params = {}
        
        # Radius
        if config.radius:
            params["search_radius"] = str(float(config.radius))
        
        # Price range
        if config.min_price is not None:
            params["price_min"] = str(config.min_price)
        if config.max_price is not None:
            params["price_max"] = str(config.max_price)
        
        # Bedrooms
        if config.min_bedrooms is not None:
            params["beds_min"] = str(config.min_bedrooms)
        if config.max_bedrooms is not None:
            params["beds_max"] = str(config.max_bedrooms)
        
        # Furnished status
        if config.furnished != FurnishedType.ANY:
            furnished_value = cls.FURNISHED_MAP.get(config.furnished)
            if furnished_value:
                params["furnished_state"] = furnished_value
        
        # Additional features
        if config.parking:
            params["feature"] = params.get("feature", [])
            params["feature"].append("parking")
        
        if config.garden:
            params["feature"] = params.get("feature", [])
            params["feature"].append("garden")
        
        # Pets allowed
        if config.pets_allowed:
            params["pets_allowed"] = "yes"
        
        # Bills included
        if config.bills_included:
            params["bills_included"] = "yes"
        
        # DSS accepted
        if config.dss_accepted:
            params["accept_dss"] = "yes"
        
        # Student friendly
        if config.student_friendly:
            params["available_to"] = params.get("available_to", [])
            params["available_to"].append("students")
        
        # Available from date
        if config.available_from:
            # Zoopla uses YYYYMMDD format
            date_str = config.available_from.strftime("%Y%m%d")
            params["available_from"] = date_str
        
        # Keywords
        if config.keywords:
            params["keywords"] = " ".join(config.keywords)
        
        # Exclude keywords
        if config.exclude_keywords:
            params["exclude_keywords"] = " ".join(config.exclude_keywords)
        
        # Exclude shared ownership
        if config.exclude_shared:
            params["exclude_shared_ownership"] = "yes"
        
        # Sort order
        params["results_sort"] = cls.SORT_MAP.get(config.sort_order, "most_recent")
        
        # Results per page
        params["page_size"] = "25"
        
        # Build the final URL
        if params:
            # Handle list parameters properly
            query_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        query_parts.append(f"{key}={quote(str(item))}")
                else:
                    query_parts.append(f"{key}={quote(str(value))}")
            
            return f"{base_path}/?{'&'.join(query_parts)}"
        else:
            return f"{base_path}/"
    
    @classmethod
    def get_pagination_urls(cls, base_url: str, total_results: int, page_size: int = 25) -> List[str]:
        """Generate pagination URLs for all pages"""
        urls = [base_url]
        
        if total_results > page_size:
            num_pages = (total_results + page_size - 1) // page_size
            for page in range(2, num_pages + 1):  # Zoopla uses 1-based page numbers
                # Add pn parameter for pagination
                separator = "&" if "?" in base_url else "?"
                urls.append(f"{base_url}{separator}pn={page}")
        
        return urls


def build_search_urls(config: SearchConfig) -> dict[Portal, List[str]]:
    """
    Build search URLs for all requested portals
    
    Args:
        config: Search configuration
        
    Returns:
        Dictionary mapping Portal to list of search URLs
    """
    urls = {}
    
    if Portal.RIGHTMOVE in config.portals:
        rightmove_url = RightmoveURLBuilder.build_url(config)
        urls[Portal.RIGHTMOVE] = [rightmove_url]
    
    if Portal.ZOOPLA in config.portals:
        zoopla_url = ZooplaURLBuilder.build_url(config)
        urls[Portal.ZOOPLA] = [zoopla_url]
    
    return urls