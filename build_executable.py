import PyInstaller.__main__
import os
import shutil

def build():
    print("Building OptionAuditor executable...")

    # Define build options
    options = [
        'webapp/app.py',  # Entry point
        '--name=OptionAuditor',
        '--onefile',
        '--noconsole',  # Hide console window (remove for debugging)
        '--add-data=webapp/templates:webapp/templates',
        '--add-data=webapp/static:webapp/static',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=yfinance',
        '--hidden-import=boto3',
        '--hidden-import=flask',
        # Add other hidden imports if necessary
    ]

    # Clean previous builds
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    try:
        PyInstaller.__main__.run(options)
        print("Build successful! Executable is in 'dist/' folder.")
    except Exception as e:
        print(f"Build failed: {e}")

if __name__ == "__main__":
    build()
