from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import tempfile
import mutagen
from mutagen.id3 import ID3, APIC
import pathlib
import urllib
import requests
import boto3.dynamodb.types
from decimal import Decimal
import hashlib
import base64
from mutagen.flac import Picture
import time
from boto3.dynamodb.conditions import Key

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# Constants
S3_GENERATED_FOLDER = 'generated/'

# Configure AWS S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

# Configure DynamoDB client
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
RATINGS_TABLE = dynamodb.Table('RatingList')

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

def format_duration(seconds):
    """Handle None and float values properly"""
    try:
        seconds = float(seconds)
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    except:
        return "0:00"

# Update the cover path handling
def get_cover_path(audio, key):
    """Extract and save cover art, return path to cover image"""
    cover_dir = os.path.join(app.static_folder, 'assets')
    os.makedirs(cover_dir, exist_ok=True)
    default_cover = '/static/assets/song-1.png'  # Corrected static path
    
    try:
        if not audio or not hasattr(audio, 'tags'):
            return default_cover

        # Handle different cover art types
        cover = None
        # ... [keep your existing cover extraction logic] ...

        if cover:
            file_hash = hashlib.md5(key.encode()).hexdigest()
            cover_filename = f"cover-{file_hash}.jpg"
            cover_path = os.path.join(cover_dir, cover_filename)
            
            if not os.path.exists(cover_path):
                with open(cover_path, 'wb') as f:
                    f.write(cover)
            return f"/static/assets/{cover_filename}"  # Corrected path
    
    except Exception as e:
        print(f"Cover art error: {str(e)}")
    
    return default_cover

# Temporarily add this test route
@app.route('/test-file')
def test_file():
    key = "Super_Mario_Bros_MainTheme.mp3"  # Use one of your actual filenames
    try:
        # Direct download test
        obj = s3_client.get_object(Bucket=os.getenv('S3_BUCKET_NAME'), Key=key)
        return f"File exists! Size: {obj['ContentLength']} bytes"
    except ClientError as e:
        return f"Access denied: {e.response['Error']['Code']}", 403
    except Exception as e:
        return str(e), 500

@app.route('/api/rate-song', methods=['POST'])
def rate_song():
    try:
        data = request.json
        print("Received rating data:", data)  # Add logging
        
        # Validate required fields
        if not all(key in data for key in ['arousal', 'valence', 'overall', 'song_id']):
            return jsonify({'error': 'Missing required fields'}), 400

        song_id = data['song_id']
        
        # Validate ratings
        if not (1 <= data['arousal'] <= 10) or \
           not (1 <= data['valence'] <= 10) or \
           not (1 <= data['overall'] <= 5):
            return jsonify({'error': 'Invalid rating values'}), 400

        # Convert values to Decimal
        arousal = Decimal(str(data['arousal']))
        valence = Decimal(str(data['valence']))
        overall = Decimal(str(data['overall']))
        
        # Simplified update expression
        response = RATINGS_TABLE.update_item(
            Key={'song_id': song_id},
            UpdateExpression="""
            ADD 
                total_arousal :a,
                total_valence :v,
                total_overall :o,
                rating_count :c
            """,
            ExpressionAttributeValues={
                ':a': arousal,
                ':v': valence,
                ':o': overall,
                ':c': Decimal('1')
            },
            ReturnValues="UPDATED_NEW"
        )
        
        print("DynamoDB response:", response)  # Add logging
        return jsonify({
            'message': 'Rating updated successfully',
            'new_values': response.get('Attributes')
        }), 200

    except ClientError as e:
        error_msg = f"DynamoDB Error ({e.response['Error']['Code']}): {e.response['Error']['Message']}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Modified /api/local-music endpoint
@app.route('/api/local-music', methods=['GET'])
def get_local_music():
    try:
        bucket = os.getenv('S3_BUCKET_NAME')
        print(f"Attempting to list objects in bucket: {bucket}")
        
        response = s3_client.list_objects_v2(Bucket=bucket)
        print(f"Found {len(response.get('Contents', []))} objects")
        
        music_files = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            print(f"Processing object: {key}")
            
            ext = pathlib.Path(key).suffix.lower()
            if ext not in ['.mp3', '.wav', '.ogg']:
                print(f"Skipping non-audio file: {key}")
                continue
            
            music_files.append({
                's3_key': key,
                'title': pathlib.Path(key).stem.replace('_', ' '),
                'file': s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=3600
                )
            })
        
        print(f"Returning {len(music_files)} music files")
        return jsonify(music_files)
    
    except ClientError as e:
        print(f"S3 Error: {str(e)}")
        return jsonify({'error': 'Failed to fetch music list'}), 500
    
# New metadata endpoint
@app.route('/api/song-details', methods=['POST'])
def get_song_details():
    try:
        data = request.json
        key = data['s3_key']
        bucket = os.getenv('S3_BUCKET_NAME')
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            s3_client.download_fileobj(bucket, key, tmp_file)
            tmp_path = tmp_file.name
        
        audio = mutagen.File(tmp_path, easy=True)
        os.remove(tmp_path)
        
        return jsonify({
            'duration': format_duration(audio.info.length if audio else 0),
            'artist': getattr(audio.tags, 'artist', ['Unknown Artist'])[0] if audio else "Unknown Artist",
            'album': getattr(audio.tags, 'album', ['Unknown Album'])[0] if audio else "Unknown Album",
            'cover': get_cover_path(audio, key)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add this route in server.py
@app.route('/api/generate-music', methods=['POST'])
def generate_music():
    try:
        # After load_dotenv()
        # print("COLAB_API_URL:", os.getenv('COLAB_API_URL'))  # Should show the new URL
        # colab_url = os.getenv('COLAB_API_URL') + '/generate'
        colab_url = "https://6004-34-87-59-188.ngrok-free.app/generate"
        print(f"Forwarding request to Colab URL: {colab_url}")  # Log the URL
        
        response = requests.post(
            colab_url,
            json=request.json,
            timeout=300
        )
        print(f"Colab response status: {response.status_code}")  # Log response status
        print(f"Colab response content: {response.text}")  # Log response content
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        return jsonify({'error': 'Generation failed'}), 500
        
    except Exception as e:
        print(f"Generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/generated-music', methods=['GET'])
def get_generated_music():
    try:
        bucket = os.getenv('S3_BUCKET_NAME')
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=S3_GENERATED_FOLDER
        )
        # Sort files by last modified date (newest first)
        objects = sorted(response.get('Contents', []), 
                       key=lambda x: x['LastModified'], 
                       reverse=True)
        
        music_files = []
        
        for index, obj in enumerate(objects):
            key = obj['Key']
            if key.endswith('/'): continue

            ext = pathlib.Path(key).suffix.lower()
            if ext not in ['.mp3', '.wav', '.ogg']:
                continue

            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                    temp_file_path = temp_file.name
                    s3_client.download_fileobj(bucket, key, temp_file)

                audio = mutagen.File(temp_file_path, easy=True) or type('', (), {})()
                filename = os.path.basename(key)
                title = pathlib.Path(filename).stem.replace('_', ' ')
                duration = getattr(audio.info, 'length', 0)
                
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=3600
                )

                music_files.append({
                    'id': index + 1,
                    'title': title,
                    'artist': getattr(audio.tags, 'artist', ['AI Generated'])[0] if hasattr(audio, 'tags') else "AI Generated",
                    'album': getattr(audio.tags, 'album', ['Generated'])[0] if hasattr(audio, 'tags') else "Generated",
                    'duration': format_duration(duration),
                    'cover': get_cover_path(audio, key),
                    'file': url
                })
                
            except Exception as e:
                filename = os.path.basename(key)
                title = pathlib.Path(filename).stem.replace('_', ' ')
                music_files.append({
                    'id': index + 1,
                    'title': title,
                    'artist': "AI Generated",
                    'album': "Generated",
                    'duration': "0:00",
                    'cover': "/assets/song-1.png",
                    'file': f"https://{bucket}.s3.amazonaws.com/{urllib.parse.quote(key)}"
                })
                
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    try: os.remove(temp_file_path)
                    except: pass

        return jsonify(music_files)
    
    except ClientError as e:
        return jsonify({'error': 'Failed to fetch generated music'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

FAVOURITES_TABLE = dynamodb.Table('Favourites')

# Add new endpoints
@app.route('/api/toggle-favorite', methods=['POST'])
def toggle_favorite():
    try:
        data = request.json
        user_id = data['user_id']
        s3_key = data['s3_key']
        
        # Check current state
        response = FAVOURITES_TABLE.get_item(
            Key={'user_id': user_id, 's3_key': s3_key}
        )
        
        if 'Item' in response:
            # Unlike
            FAVOURITES_TABLE.delete_item(
                Key={'user_id': user_id, 's3_key': s3_key}
            )
            return jsonify({'liked': False})
        else:
            # Like
            FAVOURITES_TABLE.put_item(Item={
                'user_id': user_id,
                's3_key': s3_key,
                'timestamp': Decimal(str(time.time()))
            })
            return jsonify({'liked': True})

    except ClientError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/favourites')
def get_favourites():
    try:
        user_id = request.args.get('user_id')
        response = FAVOURITES_TABLE.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        
        favourites = []
        for item in response.get('Items', []):
            key = item['s3_key']
            try:
                # Generate presigned URL like in other endpoints
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': os.getenv('S3_BUCKET_NAME'),
                        'Key': key
                    },
                    ExpiresIn=3600
                )
                
                favourites.append({
                    's3_key': key,
                    'title': pathlib.Path(key).stem.replace('_', ' '),
                    'file': url,
                    'liked': True
                })
                
            except ClientError as e:
                print(f"Skipping invalid key {key}: {str(e)}")
                continue  # Skip invalid entries

        return jsonify(favourites)
    
    except ClientError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=3000)