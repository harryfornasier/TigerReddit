#!/usr/bin/env python3
#
# Simplified Reddit JSON fetcher for debugging
# This version focuses on getting text data working first
#

import sys
import json
import urllib.request
import urllib.error
from urllib.parse import urlencode

def fetch_reddit_data_simple(subreddit="all", sort="hot", limit=25):
    """Simple fetch - text only, no images"""
    
    # Build URL
    base_url = f"https://old.reddit.com/r/{subreddit}/.json"
    params = {
        'limit': min(limit, 25),
        'raw_json': 1
    }
    
    if sort in ['new', 'top', 'rising']:
        base_url = f"https://old.reddit.com/r/{subreddit}/{sort}/.json"
    
    url = f"{base_url}?{urlencode(params)}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_4) Reddit Viewer 1.0'
    }
    
    try:
        print(f"DEBUG: Fetching {url}", file=sys.stderr)
        sys.stderr.flush()
        
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            posts = []
            
            print(f"DEBUG: Processing {len(data['data']['children'])} posts", file=sys.stderr)
            sys.stderr.flush()
            
            for child in data['data']['children']:
                post = child['data']
                
                # Simple post data - no image processing for now
                post_data = {
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
                    'has_image': False,  # Simplified - no images for now
                    'image_url': None,
                    'thumbnail': None,
                    'image_type': 'none'
                }
                
                posts.append(post_data)
            
            print(f"DEBUG: Returning {len(posts)} posts", file=sys.stderr)
            sys.stderr.flush()
            return {'success': True, 'posts': posts}
            
    except Exception as e:
        print(f"DEBUG: Error: {str(e)}", file=sys.stderr)
        sys.stderr.flush()
        return {'success': False, 'error': str(e), 'posts': []}

def main():
    try:
        subreddit = sys.argv[1] if len(sys.argv) > 1 else "all"
        sort = sys.argv[2] if len(sys.argv) > 2 else "hot"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 25
        
        print(f"DEBUG: Simple fetch - r/{subreddit}, sort={sort}, limit={limit}", file=sys.stderr)
        sys.stderr.flush()
        
        result = fetch_reddit_data_simple(subreddit, sort, limit)
        
        print(f"DEBUG: Outputting JSON...", file=sys.stderr)
        sys.stderr.flush()
        
        json_output = json.dumps(result)
        print(json_output)
        sys.stdout.flush()
        
        print(f"DEBUG: Done.", file=sys.stderr)
        sys.stderr.flush()
        
    except Exception as e:
        error_result = {
            'success': False, 
            'error': f'Script error: {str(e)}',
            'posts': []
        }
        print(json.dumps(error_result))
        sys.stdout.flush()
        print(f"DEBUG: Error: {str(e)}", file=sys.stderr)
        sys.stderr.flush()

if __name__ == "__main__":
    main()
