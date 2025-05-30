#!/usr/bin/env python3
# Simple test data generator for debugging table display issues

import json
import sys

def generate_test_data():
    """Generate simple test data to verify table display works"""
    
    posts = []
    
    for i in range(5):
        post = {
            'title': f'Test Post {i+1} - This is a test post for debugging the table display',
            'author': f'test_user_{i+1}',
            'subreddit': 'test',
            'score': (i+1) * 10,
            'num_comments': i + 2,
            'url': f'https://example.com/post{i+1}',
            'permalink': f'https://reddit.com/r/test/comments/test{i+1}',
            'is_self': False,
            'selftext': '',
            'created_utc': 1234567890,
            'has_image': False,
            'image_url': None,
            'thumbnail': None,
            'image_type': 'none'
        }
        posts.append(post)
    
    result = {
        'success': True,
        'posts': posts
    }
    
    return result

def main():
    print("DEBUG: Generating test data...", file=sys.stderr)
    sys.stderr.flush()
    
    result = generate_test_data()
    
    print("DEBUG: Generated test data with {} posts".format(len(result['posts'])), file=sys.stderr)
    sys.stderr.flush()
    
    json_output = json.dumps(result)
    print(json_output)
    sys.stdout.flush()
    
    print("DEBUG: Test data output complete", file=sys.stderr)
    sys.stderr.flush()

if __name__ == "__main__":
    main()
