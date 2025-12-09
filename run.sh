#!/bin/bash
set -e

echo "🚀 Starting Trade Auditor Setup..."

# Frontend Setup
echo "📦 Installing Frontend Dependencies..."
cd frontend
npm install

echo "🏗️ Building Frontend..."
npm run build
cd ..

# Copy artifacts
echo "📂 Deploying Frontend to Backend..."
mkdir -p webapp/static/react_build
cp -r frontend/dist/* webapp/static/react_build/

# Backend Setup
echo "🐍 Installing Backend Dependencies..."
pip install -r requirements.txt

# Run App
echo "✅ Starting Web Application..."
echo "👉 Open http://127.0.0.1:5000 in your browser"
python -m webapp.app
