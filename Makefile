# Makefile for Reddit Viewer on Mac OS X Tiger
# Compatible with Xcode 2.5 and GCC 4.0

CC = gcc
CFLAGS = -arch ppc -mmacosx-version-min=10.4 -O2 -Wall -fobjc-exceptions
OBJC_FLAGS = -framework Cocoa -framework Foundation
APP_NAME = TigerReddit
BUNDLE_NAME = $(APP_NAME).app

# Source files
OBJC_SOURCES = RedditViewer.m
C_SOURCES = cJSON.c

# Object files
OBJC_OBJECTS = $(OBJC_SOURCES:.m=.o)
C_OBJECTS = $(C_SOURCES:.c=.o)
ALL_OBJECTS = $(OBJC_OBJECTS) $(C_OBJECTS)

# Default target
all: check-cjson check-ytdlp $(BUNDLE_NAME)

# Check if cJSON files exist
check-cjson:
	@if [ ! -f cJSON.c ] || [ ! -f cJSON.h ]; then \
		echo "ERROR: cJSON files not found!"; \
		echo "Please run: ./setup.sh"; \
		echo "Or download manually:"; \
		echo "  curl -o cJSON.c https://raw.githubusercontent.com/DaveGamble/cJSON/v1.7.15/cJSON.c"; \
		echo "  curl -o cJSON.h https://raw.githubusercontent.com/DaveGamble/cJSON/v1.7.15/cJSON.h"; \
		exit 1; \
	fi

# Check if yt-dlp exists and download if needed
check-ytdlp:
	@if [ ! -d yt-dlp-master ]; then \
		echo "yt-dlp not found, downloading..."; \
		curl -L -o yt-dlp-master.zip https://github.com/yt-dlp/yt-dlp/archive/master.zip; \
		unzip -q yt-dlp-master.zip; \
		rm yt-dlp-master.zip; \
		chmod +x yt-dlp-master/yt-dlp; \
		echo "yt-dlp downloaded and extracted"; \
	fi

# Build the application bundle
$(BUNDLE_NAME): $(ALL_OBJECTS)
	@echo "Creating application bundle..."
	@mkdir -p $(BUNDLE_NAME)/Contents/MacOS
	@mkdir -p $(BUNDLE_NAME)/Contents/Resources
	$(CC) $(CFLAGS) $(OBJC_FLAGS) -o $(BUNDLE_NAME)/Contents/MacOS/$(APP_NAME) $(ALL_OBJECTS)
	@echo "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" > $(BUNDLE_NAME)/Contents/Info.plist
	@echo "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "<plist version=\"1.0\">" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "<dict>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <key>CFBundleExecutable</key>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <string>$(APP_NAME)</string>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <key>CFBundleIdentifier</key>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <string>com.example.redditviewer</string>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <key>CFBundleName</key>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <string>$(APP_NAME)</string>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <key>CFBundlePackageType</key>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <string>APPL</string>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <key>CFBundleVersion</key>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <string>1.0</string>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <key>LSMinimumSystemVersion</key>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "    <string>10.4.0</string>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "</dict>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@echo "</plist>" >> $(BUNDLE_NAME)/Contents/Info.plist
	@cp reddit_fetcher.py $(BUNDLE_NAME)/Contents/Resources/
	@if [ -f reddit_fetcher_simple.py ]; then cp reddit_fetcher_simple.py $(BUNDLE_NAME)/Contents/Resources/; fi
	@if [ -f table_test.py ]; then cp table_test.py $(BUNDLE_NAME)/Contents/Resources/; fi
	@if [ -d yt-dlp-master ]; then \
		echo "Bundling yt-dlp..."; \
		cp -r yt-dlp-master $(BUNDLE_NAME)/Contents/Resources/; \
		chmod +x $(BUNDLE_NAME)/Contents/Resources/yt-dlp-master/yt-dlp; \
		echo "yt-dlp bundled successfully"; \
	fi
	@echo "Built $(BUNDLE_NAME) successfully!"

# Compile Objective-C files
%.o: %.m
	$(CC) $(CFLAGS) -c $< -o $@

# Compile C files
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean build artifacts
clean:
	rm -f $(ALL_OBJECTS)
	rm -rf $(BUNDLE_NAME)
	rm -rf image_cache

# Clean everything including downloaded dependencies
clean-all: clean
	rm -rf yt-dlp-master
	rm -f cJSON.c cJSON.h

# Install Python dependencies (if needed)
install-deps:
	@echo "Checking Python 3 installation..."
	@which python3 || echo "Warning: Python 3 not found. Please install Python 3.11 or later."
	@python3 --version 2>/dev/null || echo "Warning: Cannot run python3"

# Download yt-dlp manually if needed
download-ytdlp:
	@if [ ! -d yt-dlp-master ]; then \
		echo "Downloading yt-dlp..."; \
		curl -L -o yt-dlp-master.zip https://github.com/yt-dlp/yt-dlp/archive/master.zip; \
		unzip -q yt-dlp-master.zip; \
		rm yt-dlp-master.zip; \
		chmod +x yt-dlp-master/yt-dlp; \
		echo "yt-dlp downloaded successfully"; \
	else \
		echo "yt-dlp already exists"; \
	fi

# Test the Python script independently
test-python:
	python3 reddit_fetcher.py programming hot 5

# Test simple version
test-simple:
	@if [ -f reddit_fetcher_simple.py ]; then \
		python3 reddit_fetcher_simple.py programming hot 3; \
	else \
		echo "reddit_fetcher_simple.py not found"; \
	fi

# Test table data
test-table:
	@if [ -f table_test.py ]; then \
		python3 table_test.py; \
	else \
		echo "table_test.py not found"; \
	fi

# Run the application
run: $(BUNDLE_NAME)
	open $(BUNDLE_NAME)

# Debug - run from command line to see console output
debug: $(BUNDLE_NAME)
	$(BUNDLE_NAME)/Contents/MacOS/$(APP_NAME)

.PHONY: all clean clean-all install-deps test-python test-simple test-table run debug check-cjson check-ytdlp download-ytdlp
