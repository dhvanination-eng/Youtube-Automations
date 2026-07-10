import os
import sys
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes needed for uploading videos
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubeDistributor:
    def __init__(self, secrets_dir):
        self.secrets_dir = Path(secrets_dir)
        
        # Search for any client secrets file matching common naming patterns
        secrets_patterns = ["client_secret*.json", "clientsecret*.json"]
        found_files = []
        for pattern in secrets_patterns:
            found_files.extend(list(self.secrets_dir.glob(pattern)))
            
        if found_files:
            self.client_secrets_file = found_files[0]
            print(f"[Distributor] Found client secret file: {self.client_secrets_file.name}")
        else:
            self.client_secrets_file = self.secrets_dir / "client_secret.json"
            
        self.token_file = self.secrets_dir / "token.json"
        self.youtube = None

    def authenticate(self):
        """Authenticates with YouTube API using OAuth 2.0 flow."""
        creds = None
        
        # Load existing token if it exists
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                print(f"[Distributor Warning] Failed to load saved token: {e}. Re-authenticating...")
                
        # If credentials are not valid or don't exist, trigger login flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("[Distributor] Refreshing expired YouTube API credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[Distributor Warning] Refresh failed: {e}. Requesting new auth...")
                    creds = None
            
            if not creds:
                if not self.client_secrets_file.exists():
                    print(f"[Distributor Error] client_secret.json not found at {self.client_secrets_file}!")
                    print("Please place your client_secret.json inside the shared_core directory.")
                    return False
                
                print("[Distributor] Starting YouTube OAuth flow. Please visit the URL printed below to log in...")
                try:
                    # Allow insecure local OAuth redirect
                    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secrets_file), SCOPES)
                    creds = flow.run_local_server(port=0, open_browser=False)
                except Exception as e:
                    print(f"[Distributor Error] OAuth authentication flow failed: {e}")
                    return False
            
            # Save the credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
        try:
            self.youtube = build('youtube', 'v3', credentials=creds)
            print("[Distributor] YouTube API Service built successfully.")
            return True
        except Exception as e:
            print(f"[Distributor Error] Failed to build YouTube API service: {e}")
            return False

    def upload_video(self, video_path, title, description="", tags=None, category_id="22"):
        """Uploads a video to YouTube."""
        if not self.youtube:
            print("[Distributor Error] YouTube service not authenticated.")
            return None
            
        if tags is None:
            tags = []
            
        try:
            print(f"[Distributor] Preparing upload for: {video_path}")
            
            body = {
                'snippet': {
                    'title': title[:100],
                    'description': description[:5000],
                    'tags': tags[:15],
                    'categoryId': str(category_id)
                },
                'status': {
                    'privacyStatus': 'public',  # Options: public, private, unlisted
                    'selfDeclaredMadeForKids': False
                }
            }
            
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            print("[Distributor] Uploading video to YouTube...")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"[Distributor] Upload progress: {progress}%")
            
            video_id = response.get('id')
            print(f"[Distributor] SUCCESS! Video uploaded successfully. Video ID: {video_id}")
            return video_id
            
        except Exception as e:
            print(f"[Distributor Error] YouTube video upload failed: {e}")
            return None
