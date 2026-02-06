#!/bin/bash
set -e

# Function to cleanup background processes
cleanup() {
    echo "🧹 Cleaning up..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
}

# Trap signals
trap cleanup EXIT INT TERM

echo "🚀 Setting up TradeGuardian E2E Environment..."

# 1. Frontend Build
echo "📦 Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# 2. Deploy Frontend
echo "📂 Deploying Frontend..."
mkdir -p webapp/static/react_build
cp -r frontend/dist/* webapp/static/react_build/

# 3. Start Backend
echo "🐍 Starting Backend..."
# Ensure backend deps are installed
pip install -r requirements.txt > /dev/null 2>&1

export FLASK_DEBUG=0
export PORT=5000
python -m webapp.app > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID $BACKEND_PID. Logs in backend.log"

# Wait for backend to be ready
echo "⏳ Waiting for Backend to be ready..."
# Loop for up to 30 seconds
for i in {1..30}; do
    if curl -s http://localhost:5000/health > /dev/null; then
        echo "✅ Backend is ready!"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start. Check backend.log:"
        cat backend.log
        exit 1
    fi
done

# 4. Run E2E Tests
echo "🧪 Running E2E Tests..."
cd e2e
npm install
# Ensure Playwright browsers are installed
npx playwright install chromium --with-deps
npm test

echo "✅ E2E Tests Passed!"
