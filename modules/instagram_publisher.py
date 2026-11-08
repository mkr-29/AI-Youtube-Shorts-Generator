import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_VERSION = "v21.0"
BASE_GRAPH_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

class InstagramPublisher:
    """
    Publishes finished short videos directly to Instagram Reels using the
    official Meta Graph API (Content Publishing API).
    
    Supports:
    1. Direct Resumable Upload (Local MP4 file uploaded straight to Meta servers).
    2. Hosted Public URL (If video is stored on S3, GCS, or GitHub Release).
    """

    def __init__(self):
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN")
        self.account_id = os.getenv("INSTAGRAM_ACCOUNT_ID") or os.getenv("IG_ACCOUNT_ID")

        if not self.access_token or not self.account_id:
            raise RuntimeError(
                "INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID is not set in .env.\n"
                "To enable automatic Instagram posting:\n"
                "1. Switch Instagram account to a Professional/Creator account.\n"
                "2. Connect it to a Facebook Page.\n"
                "3. In Meta Developer Portal, grant 'instagram_content_publish' and add credentials to .env."
            )

    def publish_reel(self, video_path: str, caption: str, video_url: str = None, max_retries: int = 15) -> str:
        """
        Uploads and publishes a video to Instagram Reels.
        Returns the published Instagram Media Permalink or None.
        """
        if not os.path.exists(video_path) and not video_url:
            print(f"❌ Instagram upload skipped: {video_path} does not exist.")
            return None

        # Instagram captions truncate past 2200 chars
        caption = caption[:2200]
        print(f"📸 [Instagram] Preparing Reel upload: {caption[:50]}...")

        container_id = None

        # Option A: Direct local file upload via Resumable Upload API
        if os.path.exists(video_path) and not video_url:
            container_id = self._upload_resumable(video_path, caption)
        
        # Option B: Hosted public URL
        elif video_url:
            container_id = self._create_container_from_url(video_url, caption)

        if not container_id:
            print("❌ [Instagram] Failed to create media container.")
            return None

        # Wait for Meta to process the video
        print(f"⏳ [Instagram] Container created ({container_id}). Waiting for video encoding...")
        if not self._wait_for_container(container_id, max_retries=max_retries):
            print("❌ [Instagram] Video processing timed out or failed.")
            return None

        # Publish the container
        return self._publish_container(container_id)

    def _upload_resumable(self, video_path: str, caption: str) -> str:
        """Uploads a local video file using Meta's resumable container protocol."""
        file_size = os.path.getsize(video_path)
        init_url = f"{BASE_GRAPH_URL}/{self.account_id}/media"
        
        init_params = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": self.access_token
        }

        try:
            init_res = requests.post(init_url, data=init_params, timeout=30).json()
            if "id" not in init_res or "uri" not in init_res:
                print(f"❌ [Instagram] Resumable init failed: {init_res}")
                return None

            container_id = init_res["id"]
            upload_uri = init_res["uri"]

            print(f"📤 [Instagram] Uploading {file_size / (1024*1024):.2f} MB directly to Meta...")
            with open(video_path, "rb") as video_file:
                video_data = video_file.read()

            upload_headers = {
                "Authorization": f"OAuth {self.access_token}",
                "offset": "0",
                "file_size": str(file_size)
            }

            upload_res = requests.post(upload_uri, headers=upload_headers, data=video_data, timeout=120)
            if upload_res.status_code not in (200, 201):
                print(f"❌ [Instagram] Binary upload failed ({upload_res.status_code}): {upload_res.text}")
                return None

            return container_id

        except Exception as e:
            print(f"❌ [Instagram] Resumable upload error: {e}")
            return None

    def _create_container_from_url(self, video_url: str, caption: str) -> str:
        """Creates an Instagram Reel container using an existing public URL."""
        url = f"{BASE_GRAPH_URL}/{self.account_id}/media"
        params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.access_token
        }
        try:
            res = requests.post(url, data=params, timeout=30).json()
            return res.get("id")
        except Exception as e:
            print(f"❌ [Instagram] Container init error: {e}")
            return None

    def _wait_for_container(self, container_id: str, max_retries: int = 15) -> bool:
        """Polls container status until Meta finishes transcoding the video."""
        status_url = f"{BASE_GRAPH_URL}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self.access_token
        }

        for attempt in range(max_retries):
            time.sleep(5)
            try:
                res = requests.get(status_url, params=params, timeout=20).json()
                status = res.get("status_code")
                print(f"   📊 [Instagram] Encoding status: {status} (check {attempt+1}/{max_retries})")

                if status == "FINISHED":
                    return True
                elif status in ("ERROR", "EXPIRED"):
                    print(f"❌ [Instagram] Container status error: {res}")
                    return False
            except Exception as e:
                print(f"   ⚠️ [Instagram] Status check error: {e}")

        return False

    def _publish_container(self, container_id: str) -> str:
        """Publishes the transcoded container to the Instagram feed."""
        publish_url = f"{BASE_GRAPH_URL}/{self.account_id}/media_publish"
        params = {
            "creation_id": container_id,
            "access_token": self.access_token
        }

        try:
            res = requests.post(publish_url, data=params, timeout=30).json()
            media_id = res.get("id")
            if not media_id:
                print(f"❌ [Instagram] Publish failed: {res}")
                return None

            # Get permalink
            media_info_url = f"{BASE_GRAPH_URL}/{media_id}"
            info_params = {"fields": "permalink", "access_token": self.access_token}
            info_res = requests.get(media_info_url, params=info_params, timeout=20).json()
            permalink = info_res.get("permalink", f"https://instagram.com/reel/{media_id}")

            print(f"✅ [Instagram] Reel published successfully: {permalink}")
            return permalink

        except Exception as e:
            print(f"❌ [Instagram] Publish error: {e}")
            return None

