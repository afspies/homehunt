"""
Google Sheets API client for HomeHunt
Handles authentication and basic operations with Google Sheets
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rich.console import Console

from .models import GoogleSheetsConfig

console = Console()


class GoogleSheetsError(Exception):
    """Google Sheets operation error"""
    pass


class GoogleSheetsClient:
    """Client for Google Sheets API operations"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, config: GoogleSheetsConfig):
        """
        Initialize Google Sheets client
        
        Args:
            config: Google Sheets configuration
        """
        self.config = config
        self.service = None
        self.drive_service = None
        self._credentials = None
        
    def _get_credentials(self):
        """Get Google service account credentials"""
        if self._credentials:
            return self._credentials
            
        try:
            if self.config.service_account_file:
                # Load from file
                self._credentials = service_account.Credentials.from_service_account_file(
                    str(self.config.service_account_file),
                    scopes=self.SCOPES
                )
            elif self.config.service_account_info:
                # Load from dict
                self._credentials = service_account.Credentials.from_service_account_info(
                    self.config.service_account_info,
                    scopes=self.SCOPES
                )
            else:
                # Try application default credentials as fallback
                try:
                    from google.auth import default
                    self._credentials, _ = default(scopes=self.SCOPES)
                    console.print("[blue]Using application default credentials[/blue]")
                except Exception as e:
                    raise GoogleSheetsError(
                        "No service account credentials provided. "
                        "Either provide service_account_file/service_account_info "
                        "or run 'gcloud auth application-default login'"
                    )
                
            return self._credentials
            
        except Exception as e:
            raise GoogleSheetsError(f"Failed to load credentials: {e}")
    
    def _get_service(self):
        """Get Google Sheets service"""
        if not self.service:
            credentials = self._get_credentials()
            self.service = build('sheets', 'v4', credentials=credentials)
        return self.service
    
    def _get_drive_service(self):
        """Get Google Drive service for file operations"""
        if not self.drive_service:
            credentials = self._get_credentials()
            self.drive_service = build('drive', 'v3', credentials=credentials)
        return self.drive_service
    
    async def create_spreadsheet(self, title: str) -> str:
        """
        Create a new spreadsheet
        
        Args:
            title: Spreadsheet title
            
        Returns:
            Spreadsheet ID
        """
        try:
            service = self._get_service()
            
            spreadsheet_body = {
                'properties': {
                    'title': title
                }
            }
            
            # Run in thread pool to avoid blocking
            spreadsheet = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.spreadsheets().create(body=spreadsheet_body).execute()
            )
            
            spreadsheet_id = spreadsheet['spreadsheetId']
            console.print(f"[green]Created spreadsheet: {title} ({spreadsheet_id})[/green]")
            
            return spreadsheet_id
            
        except HttpError as e:
            raise GoogleSheetsError(f"Failed to create spreadsheet: {e}")
    
    async def get_spreadsheet_info(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get spreadsheet information
        
        Args:
            spreadsheet_id: Spreadsheet ID
            
        Returns:
            Spreadsheet metadata
        """
        try:
            service = self._get_service()
            
            spreadsheet = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            
            return spreadsheet
            
        except HttpError as e:
            if e.resp.status == 404:
                raise GoogleSheetsError(f"Spreadsheet not found: {spreadsheet_id}")
            raise GoogleSheetsError(f"Failed to get spreadsheet info: {e}")
    
    async def create_sheet(self, spreadsheet_id: str, sheet_name: str) -> int:
        """
        Create a new sheet in existing spreadsheet
        
        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_name: Name of the new sheet
            
        Returns:
            Sheet ID
        """
        try:
            service = self._get_service()
            
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id, 
                    body=body
                ).execute()
            )
            
            sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            console.print(f"[green]Created sheet: {sheet_name} (ID: {sheet_id})[/green]")
            
            return sheet_id
            
        except HttpError as e:
            if "already exists" in str(e):
                # Sheet already exists, get its ID
                info = await self.get_spreadsheet_info(spreadsheet_id)
                for sheet in info['sheets']:
                    if sheet['properties']['title'] == sheet_name:
                        return sheet['properties']['sheetId']
            raise GoogleSheetsError(f"Failed to create sheet: {e}")
    
    async def write_data(
        self, 
        spreadsheet_id: str, 
        sheet_name: str, 
        data: List[List[Any]],
        clear_existing: bool = False,
        include_headers: bool = True
    ) -> None:
        """
        Write data to a sheet
        
        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_name: Sheet name
            data: Data to write (list of rows)
            clear_existing: Whether to clear existing data
            include_headers: Whether first row contains headers
        """
        try:
            service = self._get_service()
            
            # Clear existing data if requested
            if clear_existing:
                await self.clear_sheet(spreadsheet_id, sheet_name)
            
            if not data:
                console.print("[yellow]No data to write[/yellow]")
                return
            
            # Determine range
            end_column_letter = self._number_to_column_letter(len(data[0]))
            range_name = f"{sheet_name}!A1:{end_column_letter}{len(data)}"
            
            # Prepare request body
            body = {
                'values': data
            }
            
            # Write data
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            )
            
            console.print(f"[green]Wrote {len(data)} rows to {sheet_name}[/green]")
            
            # Format headers if included
            if include_headers and data:
                await self._format_headers(spreadsheet_id, sheet_name, len(data[0]))
                
        except HttpError as e:
            raise GoogleSheetsError(f"Failed to write data: {e}")
    
    async def append_data(
        self, 
        spreadsheet_id: str, 
        sheet_name: str, 
        data: List[List[Any]]
    ) -> None:
        """
        Append data to existing sheet
        
        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_name: Sheet name
            data: Data to append
        """
        try:
            service = self._get_service()
            
            if not data:
                return
            
            range_name = f"{sheet_name}!A:A"
            
            body = {
                'values': data
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()
            )
            
            console.print(f"[green]Appended {len(data)} rows to {sheet_name}[/green]")
            
        except HttpError as e:
            raise GoogleSheetsError(f"Failed to append data: {e}")
    
    async def clear_sheet(self, spreadsheet_id: str, sheet_name: str) -> None:
        """
        Clear all data from a sheet
        
        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_name: Sheet name
        """
        try:
            service = self._get_service()
            
            range_name = f"{sheet_name}!A:Z"
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
            )
            
            console.print(f"[blue]Cleared sheet: {sheet_name}[/blue]")
            
        except HttpError as e:
            raise GoogleSheetsError(f"Failed to clear sheet: {e}")
    
    async def share_spreadsheet(
        self, 
        spreadsheet_id: str, 
        email_addresses: List[str],
        role: str = "reader"
    ) -> None:
        """
        Share spreadsheet with email addresses
        
        Args:
            spreadsheet_id: Spreadsheet ID
            email_addresses: List of email addresses
            role: Permission role (reader/writer/commenter)
        """
        try:
            drive_service = self._get_drive_service()
            
            for email in email_addresses:
                permission = {
                    'type': 'user',
                    'role': role,
                    'emailAddress': email
                }
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: drive_service.permissions().create(
                        fileId=spreadsheet_id,
                        body=permission,
                        sendNotificationEmail=True
                    ).execute()
                )
                
                console.print(f"[green]Shared with {email} as {role}[/green]")
                
        except HttpError as e:
            raise GoogleSheetsError(f"Failed to share spreadsheet: {e}")
    
    async def _format_headers(
        self, 
        spreadsheet_id: str, 
        sheet_name: str, 
        num_columns: int
    ) -> None:
        """Format header row with bold text and background color"""
        try:
            service = self._get_service()
            
            # Get sheet ID
            info = await self.get_spreadsheet_info(spreadsheet_id)
            sheet_id = None
            for sheet in info['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            # Format headers
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': num_columns
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            },
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                }
            }]
            
            body = {'requests': requests}
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
            )
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not format headers: {e}[/yellow]")
    
    @staticmethod
    def _number_to_column_letter(n: int) -> str:
        """Convert column number to letter (1 -> A, 26 -> Z, 27 -> AA, etc.)"""
        result = ""
        while n > 0:
            n -= 1
            result = chr(n % 26 + ord('A')) + result
            n //= 26
        return result
    
    async def get_sheet_url(self, spreadsheet_id: str, sheet_name: Optional[str] = None) -> str:
        """
        Get URL for spreadsheet or specific sheet
        
        Args:
            spreadsheet_id: Spreadsheet ID
            sheet_name: Optional sheet name for direct link
            
        Returns:
            URL to spreadsheet or sheet
        """
        base_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        
        if sheet_name:
            # Get sheet ID for direct link
            try:
                info = await self.get_spreadsheet_info(spreadsheet_id)
                for sheet in info['sheets']:
                    if sheet['properties']['title'] == sheet_name:
                        sheet_id = sheet['properties']['sheetId']
                        return f"{base_url}#gid={sheet_id}"
            except Exception:
                pass
        
        return base_url