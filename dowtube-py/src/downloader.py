import yt_dlp
import os

class YouTubeDownloader:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total_bytes > 0:
                percent = d.get('downloaded_bytes', 0) / total_bytes * 100
                if self.progress_callback:
                    self.progress_callback(percent)

    def download_video(self, url, quality, save_path):
        format_str = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'
        if quality == "Audio Only":
            format_str = 'bestaudio/best'

        ydl_opts = {
            'format': format_str,
            'progress_hooks': [self._progress_hook],
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4', 
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True, "Download concluído!"
        except Exception as e:
            return False, str(e)