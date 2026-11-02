#!/usr/bin/env bash
# comfyui-start skill runner
# Executes the desktop start script and reports status
SCRIPT="/home/jagones/Desktop/QUICK COMMANDS/start_comfy.sh"

if [ ! -x "$SCRIPT" ]; then
  echo "❌ start script not found or not executable: $SCRIPT"
  exit 1
fi

# Run the script in background
bash "$SCRIPT" &
PID=$!

# Wait a few seconds for the server to spin up
sleep 5

# Check if python process for ComfyUI is running
if pgrep -f "python.*main.py" > /dev/null; then
  echo "✅ ComfyUI started – open http://127.0.0.1:8188 in your browser."
else
  echo "⚠️ ComfyUI may not have started. Check logs with: cat /home/jagones/ComfyUI/comfyui.log"
fi
