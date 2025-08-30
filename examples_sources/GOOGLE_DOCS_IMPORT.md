# Extracting Text from Old Google Docs (10+ Years Old)

This guide covers methods to extract text content from Google Docs created more than 10 years ago (before 2015).

## Method 1: Google Takeout (Recommended)

### Step 1: Export Your Google Drive Data
1. Go to [Google Takeout](https://takeout.google.com)
2. Click "Deselect all"
3. Scroll down and select only "Drive"
4. Click the dropdown and choose:
   - **Format**: Select formats for different file types
   - **For Google Docs**: Choose "Open Document Format (.odt)" or "Microsoft Word (.docx)"
   - **Include all files**: Yes
5. Click "Next step"
6. Configure delivery:
   - **Delivery method**: Send download link via email (recommended)
   - **Frequency**: Export once
   - **File type & size**: .zip, 2GB (or larger if needed)
7. Click "Create export"
8. Wait for Google to prepare your archive (can take hours to days)
9. Download the zip file when you receive the email notification

### Step 2: Filter and Extract Text from Exported Documents

#### Option A: Python Script with Date Filtering
```python
import os
import zipfile
from datetime import datetime
from pathlib import Path
import docx
from odf import text, teletype
from odf.opendocument import load
import mimetypes

def extract_old_google_docs(takeout_zip_path, output_file, cutoff_year=2015):
    """
    Extract text from Google Docs older than cutoff_year
    """
    temp_dir = "temp_extraction"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Extract the zip file
    with zipfile.ZipFile(takeout_zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    drive_path = os.path.join(temp_dir, "Takeout", "Drive")
    
    with open(output_file, 'w', encoding='utf-8') as out_file:
        process_directory(drive_path, out_file, cutoff_year)
    
    # Clean up temp directory
    import shutil
    shutil.rmtree(temp_dir)

def process_directory(directory, output_file, cutoff_year):
    """
    Recursively process all documents in directory
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # Get file modification time as proxy for creation date
                mod_time = os.path.getmtime(file_path)
                file_date = datetime.fromtimestamp(mod_time)
                
                # Filter to documents older than cutoff year
                if file_date.year >= cutoff_year:
                    continue
                
                # Process supported document types
                text_content = extract_text_from_file(file_path)
                if text_content:
                    output_file.write(f"\n{'='*60}\n")
                    output_file.write(f"File: {file}\n")
                    output_file.write(f"Path: {file_path}\n")
                    output_file.write(f"Date: {file_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    output_file.write(f"{'='*60}\n\n")
                    output_file.write(text_content)
                    output_file.write("\n\n")
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

def extract_text_from_file(file_path):
    """
    Extract text based on file type
    """
    file_extension = Path(file_path).suffix.lower()
    
    try:
        if file_extension == '.docx':
            return extract_from_docx(file_path)
        elif file_extension == '.odt':
            return extract_from_odt(file_path)
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            return None
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return None

def extract_from_docx(file_path):
    """Extract text from DOCX file"""
    doc = docx.Document(file_path)
    text_content = []
    
    for paragraph in doc.paragraphs:
        text_content.append(paragraph.text)
    
    return '\n'.join(text_content)

def extract_from_odt(file_path):
    """Extract text from ODT file"""
    doc = load(file_path)
    text_content = []
    
    for paragraph in doc.getElementsByType(text.P):
        text_content.append(teletype.extractText(paragraph))
    
    return '\n'.join(text_content)

# Usage example
if __name__ == "__main__":
    # Extract Google Docs created before 2015 (10+ years ago)
    extract_old_google_docs(
        takeout_zip_path="takeout-20241201T120000Z-001.zip",
        output_file="old_google_docs_text.txt",
        cutoff_year=2015
    )
```

#### Required Python Libraries:
```bash
pip install python-docx odfpy
```

## Method 2: Google Drive API (Advanced)

### Step 1: Set Up API Access
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create credentials (Service Account or OAuth 2.0)
5. Download the credentials JSON file

### Step 2: Python Script Using API
```python
import io
import pickle
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

# Scopes needed
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_drive_api():
    """Authenticate and return Drive API service"""
    creds = None
    
    # Load existing token
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)

def find_old_google_docs(service, cutoff_date):
    """Find Google Docs created before cutoff_date"""
    query = f"mimeType='application/vnd.google-apps.document' and createdTime<'{cutoff_date.isoformat()}'"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, createdTime, modifiedTime)",
        pageSize=1000
    ).execute()
    
    return results.get('files', [])

def export_google_doc_text(service, file_id):
    """Export Google Doc as plain text"""
    request = service.files().export_media(
        fileId=file_id,
        mimeType='text/plain'
    )
    
    file_io = io.BytesIO()
    downloader = MediaIoBaseDownload(file_io, request)
    done = False
    
    while done is False:
        status, done = downloader.next_chunk()
    
    return file_io.getvalue().decode('utf-8', errors='ignore')

def extract_old_docs_via_api(output_file, cutoff_year=2015):
    """Main function to extract old Google Docs via API"""
    service = authenticate_drive_api()
    cutoff_date = datetime(cutoff_year, 1, 1)
    
    # Find old documents
    old_docs = find_old_google_docs(service, cutoff_date)
    print(f"Found {len(old_docs)} documents from before {cutoff_year}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for doc in old_docs:
            try:
                f.write(f"\n{'='*60}\n")
                f.write(f"Document: {doc['name']}\n")
                f.write(f"Created: {doc['createdTime']}\n")
                f.write(f"Modified: {doc['modifiedTime']}\n")
                f.write(f"ID: {doc['id']}\n")
                f.write(f"{'='*60}\n\n")
                
                # Export and write content
                content = export_google_doc_text(service, doc['id'])
                f.write(content)
                f.write("\n\n")
                
                print(f"Processed: {doc['name']}")
                
            except Exception as e:
                print(f"Error processing {doc['name']}: {e}")
                continue

# Usage
if __name__ == "__main__":
    extract_old_docs_via_api("old_google_docs_api.txt", 2015)
```

#### Required Libraries for API Method:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Method 3: Manual Google Drive Search and Export

### Step 1: Advanced Search in Google Drive
1. Go to [Google Drive](https://drive.google.com)
2. Click the search box
3. Use advanced search operators:
   - `type:document before:2015-01-01`: Google Docs created before 2015
   - `type:document after:2010-01-01 before:2015-01-01`: Docs from 2010-2014
4. Review results and note which documents are 10+ years old

### Step 2: Bulk Export
1. Select multiple old documents (Ctrl/Cmd + click)
2. Right-click and choose "Download"
3. Google will convert them to your default format (usually .docx)
4. Extract text using the Python script above

### Advanced Search Operators:
- `type:document`: Only Google Docs
- `before:YYYY-MM-DD`: Created before specific date
- `after:YYYY-MM-DD`: Created after specific date
- `owner:me`: Documents you own
- `"exact phrase"`: Search for exact text within documents

## Method 4: Google Apps Script (Automated)

### Create Apps Script:
```javascript
function exportOldGoogleDocs() {
  const cutoffDate = new Date('2015-01-01');
  const folder = DriveApp.getRootFolder();
  const files = DriveApp.searchFiles('type = "application/vnd.google-apps.document"');
  
  let allText = '';
  
  while (files.hasNext()) {
    const file = files.next();
    const createdDate = file.getDateCreated();
    
    if (createdDate < cutoffDate) {
      try {
        const docId = file.getId();
        const doc = DocumentApp.openById(docId);
        const content = doc.getBody().getText();
        
        allText += `\n${'='.repeat(60)}\n`;
        allText += `Document: ${file.getName()}\n`;
        allText += `Created: ${createdDate}\n`;
        allText += `ID: ${docId}\n`;
        allText += `${'='.repeat(60)}\n\n`;
        allText += content + '\n\n';
        
      } catch (error) {
        console.log(`Error processing ${file.getName()}: ${error}`);
      }
    }
  }
  
  // Create output document
  const outputDoc = DocumentApp.create('Old Google Docs Text Export');
  outputDoc.getBody().setText(allText);
  
  console.log('Export complete. Check for "Old Google Docs Text Export" in your Drive.');
}
```

### To Use Apps Script:
1. Go to [Google Apps Script](https://script.google.com)
2. Create new project
3. Paste the code above
4. Run the function (you'll need to authorize permissions)
5. Find the output document in your Google Drive

## Important Notes

### Date Filtering Considerations:
- **File creation vs modification**: Takeout may show last modified date, not original creation date
- **Google Docs history**: Original creation date is most accurate via API
- **10+ years**: As of 2024, this means documents from 2014 and earlier

### File Format Notes:
- **ODT format**: Better preserves formatting but requires odfpy library
- **DOCX format**: More universal but may lose some Google Docs features
- **Plain text export**: Via API gives cleanest text but loses all formatting

### Performance Tips:
- **Large exports**: Process in batches to avoid memory issues
- **API rate limits**: Add delays between API calls if hitting limits
- **Storage space**: Text files can be large; monitor disk space

## Troubleshooting

**Common Issues:**
- **Authentication errors**: Ensure API credentials are properly set up
- **Missing documents**: Check if documents are in shared drives or different accounts
- **Encoding issues**: Use `errors='ignore'` in file operations
- **API quota exceeded**: Implement exponential backoff and retry logic

**Date Filtering Problems:**
- If file dates seem wrong, use the API method for accurate creation dates
- Some very old documents may not have reliable creation timestamps
- Consider manual verification for critical date filtering

**Memory Issues:**
- Process large document collections in smaller batches
- Stream output to files rather than keeping all text in memory
- Use generators instead of loading all files at once