# Sports Legends Setup Instructions

Follow these simple steps to make the channel live and run it:

## 1. Setup YouTube Credentials (Required for uploads only)
If you want the pipeline to automatically upload videos to YouTube:
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **YouTube Data API v3**.
3. Create an **OAuth 2.0 Client ID** (select "Desktop app").
4. Download the JSON credentials file.
5. Save it in this directory as `client_secret.json` (or any name containing `client_secret.json`).

## 2. Generate Your Script Pool (Queue)
Run this command in the terminal to generate 100 high-retention scripts in one go:
```bash
python batch_generate.py sports --count 100
```

## 3. Run Video Generation Pipeline
To generate a new video and consume a script from the pool:
- **Local Render Only**:
  ```bash
  python run_channel.py sports
  ```
- **Render and Auto-Upload**:
  ```bash
  python run_channel.py sports --upload
  ```
