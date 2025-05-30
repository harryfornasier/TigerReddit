#!/usr/bin/env python3

import sys
import json
import urllib.request
import urllib.error
from urllib.parse import urlencode, urlparse
import re
import os
import hashlib
import time

def clean_image_url(url):
    """Properly clean image URLs by removing query parameters after file extension"""
    if not url:
        return url

    # Find the last occurrence of image extensions
    pattern = r'\.(jpe?g|png|gif|webp|bmp)(?=[\?&]|$)'
    match = re.search(pattern, url, re.IGNORECASE)

    if match:
        # Return URL up to and including the file extension
        end_pos = match.end()
        return url[:end_pos]

    return url

def is_image_url(url):
    """Check if URL points to an image"""
    if not url:
        return False
    # Direct image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    parsed = urlparse(url.lower())
    for ext in image_extensions:
        if parsed.path.endswith(ext):
            return True
    # Common image hosts
    image_hosts = ['i.redd.it', 'i.imgur.com', 'imgur.com', 'i.postimg.cc']
    if any(host in parsed.netloc for host in image_hosts):
        return True
    return False

def is_video_url(url):
    """Check if URL points to a video"""
    if not url:
        return False

    # Video extensions
    video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v']
    parsed = urlparse(url.lower())
    for ext in video_extensions:
        if parsed.path.endswith(ext):
            return True

    # Video hosts (including NSFW)
    video_hosts = [
        'v.redd.it', 'v.reddit.com', 'youtube.com', 'youtu.be',
        'streamable.com', 'gfycat.com', 'redgifs.com', 'imgur.com/a/',
        'clips.twitch.tv', 'vimeo.com'
    ]
    return any(host in url.lower() for host in video_hosts)

def is_article_url(url):
    """Check if URL points to an article/external link"""
    if not url:
        return False

    # Skip Reddit internal links
    if 'reddit.com' in url or 'redd.it' in url:
        return False

    # Skip direct media
    if is_image_url(url) or is_video_url(url):
        return False

    # Common article/news domains
    article_indicators = [
        '.com', '.org', '.net', '.edu', '.gov', '.co.uk', '.io',
        'news', 'blog', 'article', 'medium.com', 'substack.com'
    ]

    return any(indicator in url.lower() for indicator in article_indicators)

def get_content_type(post_data):
    """Determine the content type of a post"""
    url = post_data.get('url', '')
    is_self = post_data.get('is_self', False)

    if is_self:
        return 'self'  # Text post
    elif is_video_url(url):
        return 'video'
    elif is_image_url(url):
        return 'image'
    elif is_article_url(url):
        return 'article'
    else:
        return 'link'  # Generic link

def extract_video_thumbnail(post_data, url):
    """Try to extract video thumbnail"""
    # Reddit often provides thumbnails for videos
    thumbnail = post_data.get('thumbnail', '')
    if thumbnail and thumbnail.startswith('http') and thumbnail not in ['self', 'default', 'spoiler', 'nsfw']:
        return thumbnail

    # For redgifs, try to get thumbnail
    if 'redgifs.com' in url:
        try:
            # Redgifs thumbnail pattern: https://redgifs.com/watch/something -> https://thumbs2.redgifs.com/something-mobile.jpg
            if '/watch/' in url:
                video_id = url.split('/watch/')[-1].split('?')[0]
                return f"https://thumbs2.redgifs.com/{video_id}-mobile.jpg"
        except:
            pass

    # For YouTube, extract video ID and get thumbnail
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            youtube_regex = r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})'
            match = re.search(youtube_regex, url)
            if match:
                video_id = match.group(1)
                return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        except:
            pass

    return None

def extract_article_thumbnail(url):
    """Try to extract article thumbnail"""
    # This is basic - in a real implementation you might fetch the page and look for og:image
    # For now, just return None and let the UI show a generic article icon
    return None

def extract_gallery_images(post_data):
    """Extract all images from a Reddit gallery post"""
    images = []

    # Check for gallery in media_metadata
    if 'media_metadata' in post_data:
        media_metadata = post_data['media_metadata']
        for media_id, media_info in media_metadata.items():
            if 's' in media_info and 'u' in media_info['s']:
                # Get the full resolution image URL
                img_url = media_info['s']['u'].replace('&amp;', '&')
                # Convert preview URL to direct i.redd.it URL
                if 'preview.redd.it' in img_url:
                    # Extract the media ID and extension
                    if 'm' in media_info:
                        ext = media_info['m'].split('/')[-1]  # Gets 'jpg', 'png', etc.
                        direct_url = f"https://i.redd.it/{media_id}.{ext}"
                        images.append(direct_url)
                    else:
                        images.append(img_url)
                else:
                    images.append(img_url)

    return images

def extract_image_info(post_data):
    """Extract image/video/article information from a Reddit post"""
    image_info = {
        'has_image': False,
        'image_url': None,
        'thumbnail': None,
        'image_type': 'none',
        'content_type': 'none',
        'gallery_images': [],
        'is_video': False,
        'video_url': None,
        'is_article': False,
        'article_url': None,
        'is_nsfw': post_data.get('over_18', False)
    }

    url = post_data.get('url', '')
    content_type = get_content_type(post_data)
    image_info['content_type'] = content_type

    # Handle different content types
    if content_type == 'video':
        image_info['is_video'] = True
        image_info['video_url'] = url
        image_info['image_type'] = 'video'

        # Try to get video thumbnail
        video_thumb = extract_video_thumbnail(post_data, url)
        if video_thumb:
            image_info['thumbnail'] = video_thumb
            image_info['has_image'] = True

        return image_info

    elif content_type == 'article':
        image_info['is_article'] = True
        image_info['article_url'] = url
        image_info['image_type'] = 'article'

        # Try to get article thumbnail
        article_thumb = extract_article_thumbnail(url)
        if article_thumb:
            image_info['thumbnail'] = article_thumb
            image_info['has_image'] = True
        else:
            # Use Reddit's thumbnail if available
            thumbnail = post_data.get('thumbnail', '')
            if thumbnail and thumbnail.startswith('http') and thumbnail not in ['self', 'default', 'spoiler', 'nsfw']:
                image_info['thumbnail'] = thumbnail
                image_info['has_image'] = True

        return image_info

    # Handle Reddit gallery
    if ('reddit.com/gallery/' in url or post_data.get('is_gallery', False)) and 'media_metadata' in post_data:
        gallery_images = extract_gallery_images(post_data)
        if gallery_images:
            image_info['has_image'] = True
            image_info['image_url'] = gallery_images[0]  # First image as main
            image_info['gallery_images'] = gallery_images
            image_info['image_type'] = 'gallery'

            # Use Reddit's thumbnail if available
            thumbnail = post_data.get('thumbnail', '')
            if thumbnail and thumbnail.startswith('http') and thumbnail not in ['self', 'default', 'spoiler', 'nsfw']:
                image_info['thumbnail'] = thumbnail
            else:
                image_info['thumbnail'] = gallery_images[0]

            return image_info

    # Check if it's a direct image post
    if is_image_url(url):
        image_info['has_image'] = True
        image_info['image_url'] = clean_image_url(url)
        image_info['image_type'] = 'direct'
        # Use Reddit's thumbnail if available, otherwise use the image itself
        thumbnail = post_data.get('thumbnail', '')
        if thumbnail and thumbnail.startswith('http') and thumbnail not in ['self', 'default', 'spoiler', 'nsfw']:
            image_info['thumbnail'] = thumbnail
        else:
            image_info['thumbnail'] = clean_image_url(url)

    # Check for preview images (Reddit's image processing)
    elif 'preview' in post_data and 'images' in post_data['preview']:
        preview_images = post_data['preview']['images']
        if len(preview_images) > 0:
            image_info['has_image'] = True
            source = preview_images[0].get('source', {})
            if 'url' in source:
                image_info['image_url'] = source['url'].replace('&amp;', '&')
                image_info['image_type'] = 'preview'
                # Use smallest reasonable resolution for thumbnail
                resolutions = preview_images[0].get('resolutions', [])
                if resolutions:
                    # Find smallest resolution that's still reasonable
                    suitable_res = None
                    for res in resolutions:
                        if res.get('width', 0) >= 150:
                            suitable_res = res
                            break
                    if suitable_res:
                        image_info['thumbnail'] = suitable_res['url'].replace('&amp;', '&')
                    else:
                        image_info['thumbnail'] = resolutions[0]['url'].replace('&amp;', '&')
                else:
                    image_info['thumbnail'] = image_info['image_url']

    # Fallback to Reddit's thumbnail
    elif post_data.get('thumbnail', '') and post_data['thumbnail'].startswith('http'):
        thumbnail = post_data['thumbnail']
        if thumbnail not in ['self', 'default', 'spoiler', 'nsfw']:
            image_info['has_image'] = True
            image_info['thumbnail'] = thumbnail
            image_info['image_url'] = thumbnail
            image_info['image_type'] = 'thumbnail'

    return image_info

def download_gallery_to_desktop(gallery_images, post_title):
    """Download all images from a gallery to desktop"""
    if not gallery_images:
        return {'success': False, 'message': 'No gallery images found'}

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    # Create a folder for the gallery
    safe_title = re.sub(r'[^\w\s-]', '', post_title[:50]).strip().replace(' ', '_')
    gallery_folder = os.path.join(desktop_path, f"reddit_gallery_{safe_title}")

    counter = 1
    while os.path.exists(gallery_folder):
        gallery_folder = os.path.join(desktop_path, f"reddit_gallery_{safe_title}_{counter}")
        counter += 1

    try:
        os.makedirs(gallery_folder)
    except Exception as e:
        return {'success': False, 'message': f'Could not create folder: {e}'}

    downloaded_files = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_4) Reddit Viewer 1.0'
    }

    for i, img_url in enumerate(gallery_images, 1):
        try:
            cleaned_url = clean_image_url(img_url)
            parsed = urlparse(cleaned_url)
            filename = os.path.basename(parsed.path)

            if not filename or '.' not in filename:
                filename = f"image_{i}.jpg"

            filepath = os.path.join(gallery_folder, filename)

            request = urllib.request.Request(cleaned_url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)

            downloaded_files.append(filename)

        except Exception as e:
            print(f"DEBUG: Failed to download gallery image {i}: {e}", file=sys.stderr)
            continue

    return {
        'success': True,
        'folder': gallery_folder,
        'files': downloaded_files,
        'count': len(downloaded_files)
    }

def download_full_image_to_desktop(image_url, post_title=None):
    """Download full-sized image to desktop"""
    if not image_url or not image_url.startswith('http'):
        return {'success': False, 'path': ''}

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    # Clean URL and get filename
    cleaned_url = clean_image_url(image_url)
    parsed = urlparse(cleaned_url)
    filename = os.path.basename(parsed.path)

    if not filename or '.' not in filename:
        # Generate filename from URL hash or post title
        if post_title:
            safe_title = re.sub(r'[^\w\s-]', '', post_title[:30]).strip().replace(' ', '_')
            filename = f"reddit_{safe_title}.jpg"
        else:
            url_hash = hashlib.md5(cleaned_url.encode()).hexdigest()[:8]
            filename = f"reddit_image_{url_hash}.jpg"

    filepath = os.path.join(desktop_path, filename)

    # Avoid overwriting existing files
    counter = 1
    base_name, ext = os.path.splitext(filename)
    while os.path.exists(filepath):
        filename = f"{base_name}_{counter}{ext}"
        filepath = os.path.join(desktop_path, filename)
        counter += 1

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_4) Reddit Viewer 1.0'
        }

        request = urllib.request.Request(cleaned_url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            with open(filepath, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)

        return {'success': True, 'path': filepath, 'filename': filename}

    except Exception as e:
        print(f"DEBUG: Failed to download full image: {e}", file=sys.stderr)
        return {'success': False, 'path': '', 'error': str(e)}

def fetch_comments(permalink):
    """Fetch comments for a Reddit post - return raw Reddit API response"""
    # Clean up the permalink
    if not permalink.startswith('/'):
        permalink = '/' + permalink

    # Build the full URL
    url = f"https://reddit.com{permalink}"
    if not url.endswith('.json'):
        url += '.json'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_4) Reddit Viewer 1.0'
    }

    try:
        print(f"DEBUG: Fetching comments from: {url}", file=sys.stderr)
        sys.stderr.flush()

        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            raw_data = response.read().decode('utf-8')
            print(f"DEBUG: Raw response length: {len(raw_data)}", file=sys.stderr)

            # Parse to validate it's proper JSON
            data = json.loads(raw_data)

            print(f"DEBUG: Parsed data type: {type(data)}", file=sys.stderr)
            if isinstance(data, list):
                print(f"DEBUG: Array length: {len(data)}", file=sys.stderr)
                if len(data) >= 2:
                    print(f"DEBUG: Second element (comments) type: {type(data[1])}", file=sys.stderr)

            # Return the raw Reddit API response directly
            sys.stderr.flush()
            return data

    except urllib.error.HTTPError as e:
        print(f"DEBUG: HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        sys.stderr.flush()
        return {'success': False, 'error': f'HTTP {e.code}: {e.reason}'}
    except urllib.error.URLError as e:
        print(f"DEBUG: URL Error: {e.reason}", file=sys.stderr)
        sys.stderr.flush()
        return {'success': False, 'error': f'Network error: {e.reason}'}
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON decode error: {e}", file=sys.stderr)
        sys.stderr.flush()
        return {'success': False, 'error': f'Invalid JSON response'}
    except Exception as e:
        print(f"DEBUG: Unexpected error: {e}", file=sys.stderr)
        sys.stderr.flush()
        return {'success': False, 'error': str(e)}

def fetch_reddit_data_with_pagination(subreddit="all", sort="hot", limit=25, after=None, before=None):
    """Fetch Reddit data with pagination support and enhanced content detection"""
    base_url = f"https://old.reddit.com/r/{subreddit}/.json"

    if sort in ['new', 'top', 'rising']:
        base_url = f"https://old.reddit.com/r/{subreddit}/{sort}/.json"

    params = {
        'limit': min(limit, 100),
        'raw_json': 1
    }

    if after:
        params['after'] = after
    elif before:
        params['before'] = before

    url = f"{base_url}?{urlencode(params)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_4) Reddit Viewer 1.0'
    }

    try:
        print(f"DEBUG: Fetching {url}", file=sys.stderr)
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))

        posts = []
        pagination_info = {
            'after': data['data'].get('after'),
            'before': data['data'].get('before')
        }

        for child in data['data']['children']:
            post = child['data']
            image_info = extract_image_info(post)

            post_data = {
                # Existing fields
                'title': post.get('title', ''),
                'author': post.get('author', '[deleted]'),
                'subreddit': post.get('subreddit', ''),
                'score': post.get('score', 0),
                'num_comments': post.get('num_comments', 0),
                'url': post.get('url', ''),
                'permalink': f"https://reddit.com{post.get('permalink', '')}",
                'is_self': post.get('is_self', False),
                'selftext': post.get('selftext', '')[:300] if post.get('is_self') else '',
                'created_utc': post.get('created_utc', 0),

                # Image/media fields
                'has_image': image_info['has_image'],
                'image_url': image_info['image_url'],
                'thumbnail': image_info['thumbnail'],
                'image_type': image_info['image_type'],

                # New enhanced fields
                'content_type': image_info['content_type'],
                'is_video': image_info['is_video'],
                'video_url': image_info['video_url'],
                'is_article': image_info['is_article'],
                'article_url': image_info['article_url'],
                'is_nsfw': image_info['is_nsfw']
            }
            posts.append(post_data)

        return {
            'success': True,
            'posts': posts,
            'pagination': pagination_info
        }

    except Exception as e:
        print(f"DEBUG: Error fetching Reddit data: {e}", file=sys.stderr)
        return {
            'success': False,
            'error': str(e),
            'posts': [],
            'pagination': {'after': None, 'before': None}
        }

def download_single_image(url):
    """Download a single image and return local path"""
    if not url or not url.startswith('http'):
        return ""

    # Set up cache directory - try to use a writable location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # If we're in an app bundle Resources folder, use a better cache location
    if 'Contents/Resources' in script_dir:
        # Use the user's cache directory instead
        home_dir = os.path.expanduser("~")
        cache_dir = os.path.join(home_dir, ".reddit_viewer_cache")
    else:
        # Use local directory for development
        cache_dir = os.path.join(script_dir, "image_cache")

    try:
        os.makedirs(cache_dir, exist_ok=True)
        print(f"DEBUG: Using cache directory: {cache_dir}", file=sys.stderr)
        sys.stderr.flush()
    except Exception as e:
        print(f"DEBUG: Could not create cache dir {cache_dir}: {e}", file=sys.stderr)
        # Fallback to temp directory
        import tempfile
        cache_dir = tempfile.gettempdir()
        print(f"DEBUG: Using temp directory: {cache_dir}", file=sys.stderr)
        sys.stderr.flush()

    # Create filename
    cleaned_url = clean_image_url(url)
    url_hash = hashlib.md5(cleaned_url.encode()).hexdigest()[:8]
    # Determine extension
    parsed = urlparse(cleaned_url.lower())
    path_parts = parsed.path.split('.')
    extension = 'jpg'
    if len(path_parts) > 1 and path_parts[-1] in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        extension = path_parts[-1]

    filename = f"reddit_{url_hash}.{extension}"
    filepath = os.path.join(cache_dir, filename)

    # Return existing file if cached
    if os.path.exists(filepath):
        return filepath

    # Download
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_4) Reddit Viewer 1.0'
        }

        request = urllib.request.Request(cleaned_url, headers=headers)
        with urllib.request.urlopen(request, timeout=5) as response: # Reduced timeout
            # Check size
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > 200 * 1024: # Reduced to 200KB limit
                print(f"DEBUG: Skipping large image ({content_length} bytes)", file=sys.stderr)
                return ""

            # Download
            with open(filepath, 'wb') as f:
                downloaded = 0
                max_download = 200 * 1024 # Reduced limit
                while downloaded < max_download:
                    chunk = response.read(4096) # Smaller chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

            if downloaded > 0:
                print(f"DEBUG: Downloaded {downloaded} bytes to {filename}", file=sys.stderr)
                sys.stderr.flush()
                return filepath
            else:
                return ""

    except Exception as e:
        print(f"DEBUG: Failed to download {url}: {e}", file=sys.stderr)
        sys.stderr.flush()
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        return ""

def download_thumbnails_for_posts(posts_data):
    """Download thumbnails for all posts and update their paths"""
    if not posts_data.get('success') or not posts_data.get('posts'):
        return posts_data

    posts_with_images = [post for post in posts_data['posts'] if post.get('has_image') and post.get('thumbnail')]
    total_images = len(posts_with_images)
    print(f"DEBUG: Starting thumbnail downloads for {total_images} posts with images (out of {len(posts_data['posts'])} total posts)", file=sys.stderr)
    sys.stderr.flush()

    if total_images == 0:
        print(f"DEBUG: No images to download, returning data immediately", file=sys.stderr)
        sys.stderr.flush()
        return posts_data

    downloaded_count = 0
    for i, post in enumerate(posts_data['posts']):
        if post.get('has_image') and post.get('thumbnail'):
            thumb_url = post['thumbnail']
            if thumb_url and thumb_url.startswith('http'):
                print(f"DEBUG: Downloading thumbnail {downloaded_count+1}/{total_images}: {thumb_url[:60]}...", file=sys.stderr)
                sys.stderr.flush()
                local_path = download_single_image(thumb_url)
                if local_path and os.path.exists(local_path):
                    post['thumbnail'] = local_path # Replace URL with local path
                    print(f"DEBUG: Success - saved as {os.path.basename(local_path)}", file=sys.stderr)
                    sys.stderr.flush()
                else:
                    print(f"DEBUG: Failed to download thumbnail {downloaded_count+1}/{total_images}", file=sys.stderr)
                    sys.stderr.flush()
                downloaded_count += 1
                # Add a small delay to be nice to servers
                if downloaded_count < total_images:
                    time.sleep(0.1)

    print(f"DEBUG: Thumbnail downloads completed ({downloaded_count}/{total_images} attempted)", file=sys.stderr)
    sys.stderr.flush()
    return posts_data

def main():
    try:
        if len(sys.argv) < 2:
            print(json.dumps({'success': False, 'error': 'No command specified'}))
            return

        command = sys.argv[1]

        if command == "download_full_image":
            image_url = sys.argv[2] if len(sys.argv) > 2 else ""
            post_title = sys.argv[3] if len(sys.argv) > 3 else None
            result = download_full_image_to_desktop(image_url, post_title)
            print(json.dumps(result))

        elif command == "download_gallery":
            gallery_urls = sys.argv[2].split(',') if len(sys.argv) > 2 else []
            post_title = sys.argv[3] if len(sys.argv) > 3 else "Gallery"
            result = download_gallery_to_desktop(gallery_urls, post_title)
            print(json.dumps(result))

        elif command == "fetch_comments":
            permalink = sys.argv[2] if len(sys.argv) > 2 else ""
            print(f"DEBUG: Comments fetch requested for: {permalink}", file=sys.stderr)
            sys.stderr.flush()
            result = fetch_comments(permalink)

            # For comments, output the raw JSON directly if it's a list (Reddit API format)
            if isinstance(result, list):
                # This is the raw Reddit API response - output it directly as JSON
                print(json.dumps(result, separators=(',', ':')))
            else:
                # This is an error response - output as normal
                print(json.dumps(result))

        else:
            # Regular Reddit data fetch
            subreddit = sys.argv[1] if len(sys.argv) > 1 else "all"
            sort = sys.argv[2] if len(sys.argv) > 2 else "hot"
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            after = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "None" else None
            before = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "None" else None

            result = fetch_reddit_data_with_pagination(subreddit, sort, limit, after, before)

            # Download thumbnails if successful
            if result['success'] and len(result['posts']) > 0:
                result = download_thumbnails_for_posts(result)

            print(json.dumps(result, separators=(',', ':')))

        sys.stdout.flush()
        sys.stderr.flush()

    except Exception as e:
        print(f"DEBUG: Script error: {e}", file=sys.stderr)
        sys.stderr.flush()
        error_result = {'success': False, 'error': str(e)}
        print(json.dumps(error_result))
        sys.stdout.flush()

if __name__ == "__main__":
    main()
