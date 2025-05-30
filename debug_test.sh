#!/bin/bash
# Comprehensive debug script for Reddit Viewer

echo "========================================"
echo "Reddit Viewer Debug Test"
echo "========================================"

# Test 1: Python availability
echo "1. Testing Python..."
PYTHON_PATHS=("/usr/local/bin/python3.11" "/usr/local/bin/python3" "/opt/local/bin/python3.11" "/opt/local/bin/python3" "/usr/bin/python3")
PYTHON_FOUND=""

for path in "${PYTHON_PATHS[@]}"; do
    if [ -f "$path" ]; then
        echo "   Found Python: $path"
        PYTHON_FOUND="$path"
        break
    fi
done

if [ -z "$PYTHON_FOUND" ]; then
    if command -v python3 &> /dev/null; then
        PYTHON_FOUND="python3"
        echo "   Found Python in PATH: $(which python3)"
    else
        echo "   ERROR: No Python 3 found!"
        exit 1
    fi
fi

echo "   Using: $PYTHON_FOUND"
$PYTHON_FOUND --version

# Test 2: Script availability
echo ""
echo "2. Testing script availability..."
if [ -f "reddit_fetcher.py" ]; then
    echo "   ✓ reddit_fetcher.py found"
else
    echo "   ✗ reddit_fetcher.py NOT found"
    exit 1
fi

if [ -f "reddit_fetcher_simple.py" ]; then
    echo "   ✓ reddit_fetcher_simple.py found"
else
    echo "   ✗ reddit_fetcher_simple.py NOT found"
fi

# Test 3: Network connectivity
echo ""
echo "3. Testing network connectivity..."
if curl -s --max-time 5 "https://old.reddit.com/r/test.json" > /dev/null; then
    echo "   ✓ Can reach Reddit"
else
    echo "   ✗ Cannot reach Reddit"
    echo "   Check your internet connection"
fi

# Test 4: Simple script test
echo ""
echo "4. Testing simple script (no images)..."
if [ -f "reddit_fetcher_simple.py" ]; then
    echo "   Running: $PYTHON_FOUND reddit_fetcher_simple.py programming hot 3"
    
    OUTPUT=$($PYTHON_FOUND reddit_fetcher_simple.py programming hot 3 2>&1)
    EXIT_CODE=$?
    
    echo "   Exit code: $EXIT_CODE"
    
    if [ $EXIT_CODE -eq 0 ]; then
        if echo "$OUTPUT" | grep -q '"success".*true'; then
            POST_COUNT=$(echo "$OUTPUT" | grep -o '"title"' | wc -l | tr -d ' ')
            echo "   ✓ Simple script works! Found $POST_COUNT posts"
        else
            echo "   ✗ Script ran but failed to get data"
            echo "   Output: $OUTPUT"
        fi
    else
        echo "   ✗ Simple script failed"
        echo "   Output: $OUTPUT"
    fi
else
    echo "   Skipping (simple script not found)"
fi

# Test 5: Full script test with timeout
echo ""
echo "5. Testing full script (with images, 10 second timeout)..."
echo "   Running: timeout 10s $PYTHON_FOUND reddit_fetcher.py programming hot 3"

# Use timeout if available, otherwise just run normally
if command -v timeout &> /dev/null; then
    OUTPUT=$(timeout 10s $PYTHON_FOUND reddit_fetcher.py programming hot 3 2>&1)
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 124 ]; then
        echo "   ⚠ Script timed out after 10 seconds"
        echo "   This suggests the image download is taking too long"
    elif [ $EXIT_CODE -eq 0 ]; then
        if echo "$OUTPUT" | grep -q '"success".*true'; then
            POST_COUNT=$(echo "$OUTPUT" | grep -o '"title"' | wc -l | tr -d ' ')
            echo "   ✓ Full script works! Found $POST_COUNT posts"
            
            # Check for local image paths
            if echo "$OUTPUT" | grep -q '/.reddit_viewer_cache/'; then
                echo "   ✓ Found cached images"
            elif echo "$OUTPUT" | grep -q '"thumbnail".*"http'; then
                echo "   ⚠ Images not cached (still URLs)"
            fi
        else
            echo "   ✗ Script ran but failed to get data"
            echo "   First 500 chars of output:"
            echo "$OUTPUT" | head -c 500
        fi
    else
        echo "   ✗ Full script failed with exit code $EXIT_CODE"
        echo "   Output: $OUTPUT"
    fi
else
    echo "   timeout command not available, running without limit..."
    OUTPUT=$($PYTHON_FOUND reddit_fetcher.py programming hot 3 2>&1)
    EXIT_CODE=$?
    echo "   Exit code: $EXIT_CODE"
    
    if [ $EXIT_CODE -eq 0 ]; then
        if echo "$OUTPUT" | grep -q '"success".*true'; then
            echo "   ✓ Full script works!"
        else
            echo "   ✗ Script failed to get data"
        fi
    else
        echo "   ✗ Script failed"
    fi
fi

# Test 6: Cache directory
echo ""
echo "6. Checking cache directory..."
HOME_CACHE="$HOME/.reddit_viewer_cache"
LOCAL_CACHE="./image_cache"

if [ -d "$HOME_CACHE" ]; then
    CACHE_COUNT=$(ls -1 "$HOME_CACHE" 2>/dev/null | wc -l | tr -d ' ')
    echo "   ✓ Home cache exists: $HOME_CACHE ($CACHE_COUNT files)"
    
    if [ $CACHE_COUNT -gt 0 ]; then
        echo "   Sample files:"
        ls -la "$HOME_CACHE" | head -3 | tail -2
    fi
elif [ -d "$LOCAL_CACHE" ]; then
    CACHE_COUNT=$(ls -1 "$LOCAL_CACHE" 2>/dev/null | wc -l | tr -d ' ')
    echo "   ✓ Local cache exists: $LOCAL_CACHE ($CACHE_COUNT files)"
else
    echo "   ⚠ No cache directories found (will be created on first run)"
fi

# Test 7: App bundle test
echo ""
echo "7. Testing app bundle..."
if [ -d "RedditViewer.app" ]; then
    echo "   ✓ App bundle exists"
    
    BUNDLE_SCRIPT="RedditViewer.app/Contents/Resources/reddit_fetcher.py"
    if [ -f "$BUNDLE_SCRIPT" ]; then
        echo "   ✓ Script found in bundle"
    else
        echo "   ✗ Script NOT found in bundle"
        echo "   Expected: $BUNDLE_SCRIPT"
    fi
    
    BUNDLE_EXEC="RedditViewer.app/Contents/MacOS/RedditViewer"
    if [ -f "$BUNDLE_EXEC" ]; then
        echo "   ✓ Executable found in bundle"
    else
        echo "   ✗ Executable NOT found in bundle"
    fi
else
    echo "   ⚠ App bundle not found (run 'make' to build)"
fi

# Test 8: JSON validation
echo ""
echo "8. Testing JSON output validity..."
JSON_OUTPUT=$($PYTHON_FOUND reddit_fetcher.py programming hot 2 2>/dev/null)

if [ -n "$JSON_OUTPUT" ]; then
    # Try to validate JSON with python
    if echo "$JSON_OUTPUT" | $PYTHON_FOUND -m json.tool > /dev/null 2>&1; then
        echo "   ✓ JSON output is valid"
        
        # Check structure
        if echo "$JSON_OUTPUT" | grep -q '"success"'; then
            echo "   ✓ Has 'success' field"
        else
            echo "   ✗ Missing 'success' field"
        fi
        
        if echo "$JSON_OUTPUT" | grep -q '"posts"'; then
            echo "   ✓ Has 'posts' field"
        else
            echo "   ✗ Missing 'posts' field"
        fi
    else
        echo "   ✗ JSON output is invalid"
        echo "   First 200 chars: ${JSON_OUTPUT:0:200}"
    fi
else
    echo "   ✗ No JSON output received"
fi

echo ""
echo "========================================"
echo "Debug test completed!"
echo ""

# Recommendations
echo "RECOMMENDATIONS:"
echo "=================="

if [ -f "reddit_fetcher_simple.py" ]; then
    echo "1. If simple script works but full script times out:"
    echo "   → The issue is with image downloading"
    echo "   → Try reducing the number of posts or timeout values"
else
    echo "1. Create the simple script to test basic functionality first"
fi

echo ""
echo "2. To build and test the app:"
echo "   → make clean && make"
echo "   → make debug    (shows console output)"
echo ""

echo "3. If the app still times out:"
echo "   → Check Console.app for detailed error messages"
echo "   → Look for the '=== PYTHON SCRIPT EXECUTION START ===' messages"
echo "   → The detailed logs will show exactly where it fails"
