import io
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class GoogleDriveInterface:
    base_folder_location = Path(os.getenv("GOOGLE_DRIVE_SECRET_LOCATION", "/creds"))
    credential_file = Path("drive.json")
    token_file = Path("token.json")
    output_file_location = Path(os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_NAME", "/output"))
    creds = None
    service = None
    scopes = [
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self, *, credential_secret_folder_location = None):
        if credential_secret_folder_location:
            self.base_folder_location = credential_secret_folder_location
        token_file = Path(self.base_folder_location, self.token_file)
        credential_file = Path(self.base_folder_location, self.credential_file)
        if not credential_file.exists():
            print(credential_file)
            raise ValueError("Credential File is empty and needs to be provided")
        if token_file.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_file), self.scopes)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except RefreshError:
                    token_file.unlink()
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credential_file),
                    scopes=self.scopes
                )
                self.creds = flow.run_local_server(port=0)
                token_file.write_text(self.creds.to_json())
        self.service = build('drive', 'v3', credentials=self.creds)

    def get_file_list(self, *, file_name_to_retrieve: str = None, file_id_to_retrieve: str = None):
        page_token = None
        while True:
            response = self.service.files().list(
                q="mimeType='application/vnd.google-apps.folder'",
                spaces='drive',
                fields='nextPageToken, files(id, name, parents)',
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                if file_name_to_retrieve:
                    if file.get("name") == file_name_to_retrieve:
                        return file
                if file_id_to_retrieve:
                    if file.get("id") == file_id_to_retrieve:
                        return file
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break

    def _download_file(self, file_id: str):
        request = self.service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False

        while done is False:
            status, done = downloader.next_chunk()
            print(F'Download {int(status.progress() * 100)}.')

        return file.getvalue()

    def get_files_in_folder(
            self,
            *,
            output_file_location: Path = None,
            folder_name: str = None,
            folder_id: str = None,
            delete_files: bool = False
    ):
        page_token = None
        search_term = folder_name
        if not search_term:
            search_term = folder_id
        while True:
            response = self.service.files().list(
                q=f"'{search_term}' in parents",
                spaces='drive',
                fields='nextPageToken, files(id, name, parents)',
                pageToken=page_token
            ).execute()
            base_file = self.output_file_location
            if not base_file.exists():
                base_file.mkdir()

            for file in response.get('files', []):
                print(file)
                if output_file_location:
                    base_file = output_file_location
                if not base_file.exists():
                    base_file.mkdir(parents=True)
                output_file = Path(base_file, file.get('name'))
                output_file.write_bytes(self._download_file(file.get('id')))
                if delete_files:
                    self.service.files().delete(fileId=file.get('id')).execute()
                    print("File Deleted.")
            page_token = response.get('nextPageToken', None)
            if not page_token:
                break


if __name__ == '__main__':
    google_drive_secret_location = None
    if os.getenv('GOOGLE_DRIVE_SECRET_LOCATION'):
        google_drive_secret_location = os.getenv('GOOGLE_DRIVE_SECRET_LOCATION')
    drive = GoogleDriveInterface(credential_secret_folder_location=google_drive_secret_location)
    automation_folder = drive.get_file_list(file_name_to_retrieve=os.getenv("GOOGLE_DRIVE_PARENT_FOLDER_NAME", "Automation"))
    scanning_folder = drive.get_file_list(file_name_to_retrieve=os.getenv("GOOGLE_DRIVE_FOLDER__TO_DOWNLOAD_NAME", "Scanning"))
    print(automation_folder)
    print(scanning_folder)
    if automation_folder.get("id") not in scanning_folder.get("parents"):
        raise ValueError("Wrong Scanning Folder")
    drive.get_files_in_folder(folder_id=scanning_folder.get('id'), delete_files=True)

