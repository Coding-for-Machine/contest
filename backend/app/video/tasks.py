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


def upload_to_minio(local_path: str, s3_key: str, content_type='application/octet-stream'):
    s3 = get_s3_client()
    s3.upload_file(local_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key, ExtraArgs={'ContentType': content_type})


def upload_folder_to_minio(local_dir: str, s3_prefix: str):
    s3 = get_s3_client()
    for filename in os.listdir(local_dir):
        local_file = os.path.join(local_dir, filename)
        s3_key = f"{s3_prefix}/{filename}"
        content_type = 'application/x-mpegURL' if filename.endswith('.m3u8') else 'video/mp2t'
        s3.upload_file(local_file, settings.AWS_STORAGE_BUCKET_NAME, s3_key, ExtraArgs={'ContentType': content_type})


@shared_task(bind=True, max_retries=3)
def convert_to_hls(self, movie_id: int):
    from .models import Video
    try:
        movie = Video.objects.get(id=movie_id)
        if not movie.video:
            return {'status': 'error', 'msg': 'Video fayl yo\'q'}

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path  = os.path.join(tmpdir, 'input.mp4')
            output_dir  = os.path.join(tmpdir, 'hls')
            output_m3u8 = os.path.join(output_dir, 'index.m3u8')
            os.makedirs(output_dir)

            self.update_state(state='PROGRESS', meta={'step': 'downloading'})
            download_from_minio(movie.video, input_path)

            # 🟢 AVTOMATIK DURATION & MP4_URL SHU YERDA TO'LDIRILADI (Model yukidan qutuldi)
            # ffprobe orqali sekundni aniqlaymiz
            duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
            duration_res = subprocess.run(duration_cmd, capture_output=True, text=True)
            
            duration_str = "00:00"
            if duration_res.returncode == 0 and duration_res.stdout.strip():
                total_seconds = float(duration_res.stdout.strip())
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                duration_str = f"{minutes:02d}:{seconds:02d}"

            self.update_state(state='PROGRESS', meta={'step': 'converting'})
            result = subprocess.run([
                'ffmpeg', '-i', input_path, '-codec:', 'copy', '-start_number', '0',
                '-hls_time', '10', '-hls_list_size', '0', '-f', 'hls', output_m3u8, '-y'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f'FFmpeg xato: {result.stderr}')

            self.update_state(state='PROGRESS', meta={'step': 'uploading'})
            s3_hls_prefix = f"media/movies/hls/{movie_id}"
            upload_folder_to_minio(output_dir, s3_hls_prefix)

        hls_url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{s3_hls_prefix}/index.m3u8"
        mp4_url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{movie.video.name}"
        
        # HLS, MP4_URL va Duration barchasini bitta so'rovda yangilaymiz
        Video.objects.filter(id=movie_id).update(hls_url=hls_url, mp4_url=mp4_url, duration=duration_str)

        return {'status': 'ok', 'hls_url': hls_url}

    except Video.DoesNotExist:
        return {'status': 'error', 'msg': 'Movie topilmadi'}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self, movie_id: int, time_sec: int = 2):
    from .models import Video
    try:
        movie = Video.objects.get(id=movie_id)
        if not movie.video:
            return {'status': 'error', 'msg': 'Video fayl yo\'q'}

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.mp4')
            thumb_path = os.path.join(tmpdir, 'thumbnail.jpg')

            download_from_minio(movie.video, input_path)

            result = subprocess.run([
                'ffmpeg', '-i', input_path, '-ss', str(time_sec), '-vframes', '1',
                '-strict', '-2', '-pix_fmt', 'yuvj420p', '-q:v', '2', thumb_path, '-y'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f'FFmpeg xato: {result.stderr}')

            s3_thumb_key = f"media/movies/thumbnails/thumb_{movie_id}.jpg"
            upload_to_minio(thumb_path, s3_thumb_key, content_type='image/jpeg')

        thumb_url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{s3_thumb_key}"
        Video.objects.filter(id=movie_id).update(thumbnail=thumb_url)

        return {'status': 'ok', 'thumbnail': thumb_url}

    except Video.DoesNotExist:
        return {'status': 'error', 'msg': 'Movie topilmadi'}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
