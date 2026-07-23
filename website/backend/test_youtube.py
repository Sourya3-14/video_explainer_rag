from pathlib import Path
from app.controllers.chat_controller import download_youtube_video

url = 'https://youtu.be/3dhcmeOTZ_Q'
out = Path('tmp_test_download')
out.mkdir(exist_ok=True)
path, title = download_youtube_video(url, out)
print('TITLE', title)
print('PATH', path)
print('EXISTS', path.exists())
