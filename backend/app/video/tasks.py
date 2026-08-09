import os
import subprocess
import tempfile

import boto3
from celery import shared_task
from django.conf import settings


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def download_from_minio(storage_field, local_path: str):
    with storage_field.open('rb') as remote_file:
        with open(local_path, 'wb') as local_file:
            local_file.write(remote_file.read())


def upload_folder_to_minio(local_dir: str, s3_prefix: str):
    s3 = get_s3_client()
    for root, _, files in os.walk(local_dir):
        for filename in files:
            local_file = os.path.join(root, filename)
            rel_path = os.path.relpath(local_file, local_dir)
            s3_key = f"{s3_prefix}/{rel_path}"

            if filename.endswith('.m3u8'):
                content_type = 'application/vnd.apple.mpegurl'
            elif filename.endswith('.ts'):
                content_type = 'video/mp2t'
            else:
                content_type = 'application/octet-stream'

            s3.upload_file(
                local_file,
                settings.AWS_STORAGE_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )


@shared_task(bind=True, max_retries=3)
def convert_to_hls(self, movie_id: str):
    from .models import Video

    try:
        movie = Video.objects.get(id=movie_id)

        if not movie.video:
            return {'status': 'error', 'msg': "Video fayl yo'q"}

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.mp4')
            output_dir = os.path.join(tmpdir, 'hls')
            output_m3u8 = os.path.join(output_dir, 'index.m3u8')

            os.makedirs(output_dir, exist_ok=True)

            # 1. Yuklab olish
            self.update_state(state='PROGRESS', meta={'step': 'downloading'})
            download_from_minio(movie.video, input_path)

            # 2. Davomiylik
            duration_cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            duration_res = subprocess.run(duration_cmd, capture_output=True, text=True)

            duration_str = "00:00"
            if duration_res.returncode == 0 and duration_res.stdout.strip():
                total_seconds = float(duration_res.stdout.strip())
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                duration_str = f"{minutes:02d}:{seconds:02d}"

            # 3. Konvertatsiya
            self.update_state(state='PROGRESS', meta={'step': 'converting'})

            result = subprocess.run([
                'ffmpeg',
                '-y',  # ✅ global option — boshida
                '-i', input_path,
                '-vcodec', 'libx264',
                '-acodec', 'aac',
                '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
                '-start_number', '0',
                '-hls_time', '10',
                '-hls_list_size', '0',
                '-f', 'hls',
                output_m3u8,
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f'FFmpeg xato: {result.stderr}')

            # 4. Upload
            self.update_state(state='PROGRESS', meta={'step': 'uploading'})
            s3_hls_prefix = f"media/movies/hls/{movie_id}"
            upload_folder_to_minio(output_dir, s3_hls_prefix)

        # 5. DB yangilash
        base_s3_url = settings.MINIO_ENDPOINT_PUBLIC.rstrip('/')
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        hls_url = f"{base_s3_url}/{bucket}/{s3_hls_prefix}/index.m3u8"

        Video.objects.filter(id=movie_id).update(hls_url=hls_url, duration=duration_str)

        return {'status': 'ok', 'hls_url': hls_url}

    except Video.DoesNotExist:
        return {'status': 'error', 'msg': 'Movie topilmadi'}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)