#!/usr/bin/env python3
"""
Property deduplication system to avoid re-scraping known properties
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import asyncio

console = Console()

class PropertyDeduplicationDB:
    """SQLite-based property deduplication and tracking system"""
    
    def __init__(self, db_path: str = "property_dedup.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the deduplication database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scraped_properties (
                    uid TEXT PRIMARY KEY,
                    portal TEXT NOT NULL,
                    property_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    url_hash TEXT NOT NULL,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    last_scraped TIMESTAMP,
                    scrape_count INTEGER DEFAULT 0,
                    price TEXT,
                    address TEXT,
                    bedrooms INTEGER,
                    status TEXT DEFAULT 'active',
                    metadata TEXT,
                    UNIQUE(portal, property_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_uid TEXT NOT NULL,
                    price TEXT NOT NULL,
                    recorded_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (property_uid) REFERENCES scraped_properties (uid)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_portal_property 
                ON scraped_properties(portal, property_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_scraped 
                ON scraped_properties(last_scraped)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_url_hash 
                ON scraped_properties(url_hash)
            """)
    
    def generate_uid(self, portal: str, property_id: str) -> str:
        """Generate unique identifier for a property"""
        return f"{portal}:{property_id}"
    
    def generate_url_hash(self, url: str) -> str:
        """Generate hash for URL to detect duplicates across different URL formats"""
        # Normalize URL by removing query parameters that don't affect content
        import re
        
        # Extract core property identifier from URL
        if 'rightmove.co.uk/properties/' in url:
            match = re.search(r'/properties/(\d+)', url)
            if match:
                return f"rightmove:{match.group(1)}"
        elif 'zoopla.co.uk' in url:
            # Handle various Zoopla URL patterns
            for pattern in [r'/details/(\d+)', r'/rental/(\d+)', r'/property/(\d+)']:
                match = re.search(pattern, url)
                if match:
                    return f"zoopla:{match.group(1)}"
        
        # Fallback to URL hash
        return hashlib.md5(url.encode()).hexdigest()
    
    def should_scrape_property(
        self, 
        portal: str, 
        property_id: str, 
        url: str,
        max_age_hours: int = 24,
        force_rescrape: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if a property should be scraped
        Returns (should_scrape, reason)
        """
        uid = self.generate_uid(portal, property_id)
        url_hash = self.generate_url_hash(url)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Check if property exists
            result = conn.execute("""
                SELECT uid, last_scraped, scrape_count, status, url, url_hash
                FROM scraped_properties 
                WHERE uid = ? OR url_hash = ?
            """, (uid, url_hash)).fetchone()
            
            if not result:
                return True, "new_property"
            
            if force_rescrape:
                return True, "forced_rescrape"
            
            # Check if property was recently scraped
            if result['last_scraped']:
                last_scraped = datetime.fromisoformat(result['last_scraped'])
                age_hours = (datetime.now() - last_scraped).total_seconds() / 3600
                
                if age_hours < max_age_hours:
                    return False, f"recently_scraped_{age_hours:.1f}h_ago"
            
            # Check if property is marked as inactive
            if result['status'] == 'inactive':
                return False, "property_inactive"
            
            # Check if too many recent scrapes (rate limiting)
            if result['scrape_count'] > 10:
                return False, "too_many_scrapes"
            
            return True, "ready_for_rescrape"
    
    def record_property_attempt(
        self, 
        portal: str, 
        property_id: str, 
        url: str,
        success: bool = True,
        extracted_data: Optional[Dict] = None
    ):
        """Record a property scraping attempt"""
        uid = self.generate_uid(portal, property_id)
        url_hash = self.generate_url_hash(url)
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if property exists
            existing = conn.execute("""
                SELECT uid, first_seen, scrape_count, price 
                FROM scraped_properties WHERE uid = ?
            """, (uid,)).fetchone()
            
            if existing:
                # Update existing property
                new_scrape_count = existing[2] + 1
                
                # Prepare update data
                update_data = {
                    'last_seen': now,
                    'scrape_count': new_scrape_count,
                    'url': url,
                    'url_hash': url_hash
                }
                
                if success:
                    update_data['last_scraped'] = now
                    update_data['status'] = 'active'
                    
                    if extracted_data:
                        if 'price' in extracted_data and extracted_data['price']:
                            update_data['price'] = extracted_data['price']
                        if 'address' in extracted_data and extracted_data['address']:
                            update_data['address'] = extracted_data['address']
                        if 'bedrooms' in extracted_data and extracted_data['bedrooms']:
                            update_data['bedrooms'] = extracted_data['bedrooms']
                        update_data['metadata'] = json.dumps(extracted_data)
                
                # Build dynamic UPDATE query
                set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
                values = list(update_data.values()) + [uid]
                
                conn.execute(f"""
                    UPDATE scraped_properties 
                    SET {set_clause}
                    WHERE uid = ?
                """, values)
                
                # Record price change if applicable
                if (success and extracted_data and 'price' in extracted_data and 
                    extracted_data['price'] and extracted_data['price'] != existing[3]):
                    conn.execute("""
                        INSERT INTO price_history (property_uid, price, recorded_at)
                        VALUES (?, ?, ?)
                    """, (uid, extracted_data['price'], now))
                
            else:
                # Insert new property
                insert_data = {
                    'uid': uid,
                    'portal': portal,
                    'property_id': property_id,
                    'url': url,
                    'url_hash': url_hash,
                    'first_seen': now,
                    'last_seen': now,
                    'scrape_count': 1,
                    'status': 'active' if success else 'unknown'
                }
                
                if success:
                    insert_data['last_scraped'] = now
                    
                    if extracted_data:
                        if 'price' in extracted_data and extracted_data['price']:
                            insert_data['price'] = extracted_data['price']
                        if 'address' in extracted_data and extracted_data['address']:
                            insert_data['address'] = extracted_data['address']
                        if 'bedrooms' in extracted_data and extracted_data['bedrooms']:
                            insert_data['bedrooms'] = extracted_data['bedrooms']
                        insert_data['metadata'] = json.dumps(extracted_data)
                
                # Build dynamic INSERT query
                columns = ', '.join(insert_data.keys())
                placeholders = ', '.join(['?' for _ in insert_data])
                values = list(insert_data.values())
                
                conn.execute(f"""
                    INSERT INTO scraped_properties ({columns})
                    VALUES ({placeholders})
                """, values)
    
    def get_properties_to_scrape(
        self, 
        property_urls: List[str],
        max_age_hours: int = 24,
        force_rescrape: bool = False
    ) -> Tuple[List[str], List[str]]:
        """
        Filter property URLs to only include those that need scraping
        Returns (urls_to_scrape, skipped_urls)
        """
        urls_to_scrape = []
        skipped_urls = []
        
        for url in property_urls:
            # Extract portal and property ID from URL
            portal = None
            property_id = None
            
            if 'rightmove.co.uk/properties/' in url:
                import re
                match = re.search(r'/properties/(\d+)', url)
                if match:
                    portal = 'rightmove'
                    property_id = match.group(1)
            elif 'zoopla.co.uk' in url:
                import re
                for pattern in [r'/details/(\d+)', r'/rental/(\d+)', r'/property/(\d+)']:
                    match = re.search(pattern, url)
                    if match:
                        portal = 'zoopla'
                        property_id = match.group(1)
                        break
            
            if portal and property_id:
                should_scrape, reason = self.should_scrape_property(
                    portal, property_id, url, max_age_hours, force_rescrape
                )
                
                if should_scrape:
                    urls_to_scrape.append(url)
                else:
                    skipped_urls.append(url)
            else:
                # Unknown URL format, scrape anyway
                urls_to_scrape.append(url)
        
        return urls_to_scrape, skipped_urls
    
    def get_statistics(self) -> Dict:
        """Get deduplication statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total properties by portal
            portal_counts = conn.execute("""
                SELECT portal, COUNT(*) as count, COUNT(last_scraped) as scraped_count
                FROM scraped_properties 
                GROUP BY portal
            """).fetchall()
            
            stats['by_portal'] = {row[0]: {'total': row[1], 'scraped': row[2]} for row in portal_counts}
            
            # Overall statistics
            total_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_properties,
                    COUNT(last_scraped) as scraped_properties,
                    SUM(scrape_count) as total_scrape_attempts,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_properties
                FROM scraped_properties
            """).fetchone()
            
            stats['overall'] = {
                'total_properties': total_stats[0],
                'scraped_properties': total_stats[1], 
                'total_scrape_attempts': total_stats[2],
                'active_properties': total_stats[3]
            }
            
            # Recent activity
            last_24h = conn.execute("""
                SELECT COUNT(*) 
                FROM scraped_properties 
                WHERE last_scraped > datetime('now', '-24 hours')
            """).fetchone()[0]
            
            stats['recent_activity'] = {
                'scraped_last_24h': last_24h
            }
            
            return stats

def test_deduplication_system():
    """Test the deduplication system"""
    console.print(Panel.fit(
        "[bold blue]Property Deduplication System Test[/bold blue]",
        title="Dedup Test"
    ))
    
    # Initialize deduplication system
    dedup = PropertyDeduplicationDB("test_dedup.db")
    
    # Sample property URLs
    test_urls = [
        "https://www.rightmove.co.uk/properties/164209706",
        "https://www.rightmove.co.uk/properties/164244281", 
        "https://www.rightmove.co.uk/properties/164223689",
        "https://www.zoopla.co.uk/to-rent/details/70186875",
        "https://www.zoopla.co.uk/rental/70000000",
        # Duplicate URLs in different formats
        "https://www.rightmove.co.uk/properties/164209706?channel=RES_LET",
        "https://www.rightmove.co.uk/properties/164244281#/?channel=RES_LET"
    ]
    
    console.print(f"\n[bold]1. Initial filtering (should scrape all new properties)[/bold]")
    
    # First pass - all should be new
    to_scrape, skipped = dedup.get_properties_to_scrape(test_urls)
    console.print(f"  • To scrape: {len(to_scrape)}")
    console.print(f"  • Skipped: {len(skipped)}")
    
    # Simulate scraping some properties
    console.print(f"\n[bold]2. Simulating scraping results[/bold]")
    
    sample_results = [
        {
            'url': "https://www.rightmove.co.uk/properties/164209706",
            'success': True,
            'data': {'price': '£2,385 pcm', 'address': 'Grosvenor Road, London', 'bedrooms': 1}
        },
        {
            'url': "https://www.rightmove.co.uk/properties/164244281",
            'success': True,
            'data': {'price': '£3,332 pcm', 'address': 'Beatty House, London', 'bedrooms': 2}
        },
        {
            'url': "https://www.zoopla.co.uk/to-rent/details/70186875",
            'success': False,
            'data': None
        }
    ]
    
    for result in sample_results:
        url = result['url']
        if 'rightmove' in url:
            import re
            match = re.search(r'/properties/(\d+)', url)
            if match:
                dedup.record_property_attempt(
                    'rightmove', match.group(1), url,
                    result['success'], result['data']
                )
        elif 'zoopla' in url:
            import re
            match = re.search(r'/details/(\d+)', url)
            if match:
                dedup.record_property_attempt(
                    'zoopla', match.group(1), url,
                    result['success'], result['data']
                )
        
        status = "✅ Success" if result['success'] else "❌ Failed"
        console.print(f"  • {url}: {status}")
    
    console.print(f"\n[bold]3. Second pass filtering (should skip recent ones)[/bold]")
    
    # Second pass - recently scraped should be skipped
    to_scrape_2, skipped_2 = dedup.get_properties_to_scrape(test_urls, max_age_hours=24)
    console.print(f"  • To scrape: {len(to_scrape_2)}")
    console.print(f"  • Skipped: {len(skipped_2)}")
    
    for url in skipped_2:
        console.print(f"    - Skipped: {url}")
    
    console.print(f"\n[bold]4. Force rescrape test[/bold]")
    
    # Force rescrape
    to_scrape_3, skipped_3 = dedup.get_properties_to_scrape(test_urls, force_rescrape=True)
    console.print(f"  • To scrape (forced): {len(to_scrape_3)}")
    console.print(f"  • Skipped (forced): {len(skipped_3)}")
    
    # Display statistics
    console.print(f"\n[bold]5. Database Statistics[/bold]")
    
    stats = dedup.get_statistics()
    
    # Portal statistics table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Portal", style="bold")
    table.add_column("Total Properties", justify="center")
    table.add_column("Successfully Scraped", justify="center")
    table.add_column("Success Rate", justify="center")
    
    for portal, data in stats['by_portal'].items():
        success_rate = f"{data['scraped']/data['total']*100:.0f}%" if data['total'] > 0 else "0%"
        table.add_row(
            portal.title(),
            str(data['total']),
            str(data['scraped']),
            success_rate
        )
    
    console.print(table)
    
    # Overall statistics
    overall = stats['overall']
    console.print(f"\n[cyan]Overall Statistics:[/cyan]")
    console.print(f"  • Total properties tracked: {overall['total_properties']}")
    console.print(f"  • Successfully scraped: {overall['scraped_properties']}")
    console.print(f"  • Total scrape attempts: {overall['total_scrape_attempts']}")
    console.print(f"  • Active properties: {overall['active_properties']}")
    console.print(f"  • Scraped in last 24h: {stats['recent_activity']['scraped_last_24h']}")
    
    console.print(f"\n[bold green]✅ Deduplication system test complete![/bold green]")
    console.print(f"Database saved to: test_dedup.db")

if __name__ == "__main__":
    test_deduplication_system()