#!/usr/bin/env python3
"""
🧬 IGVer Agent Web Interface
Simple web UI for user-friendly genomic analysis
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import webbrowser
import threading
from dataclasses import asdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from flask import Flask, render_template_string, request, jsonify, send_file, session
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not installed. Install with: pip install flask flask-cors")
    sys.exit(1)

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig
from test_config import get_singularity_image

# Create Flask app
app = Flask(__name__)
app.secret_key = 'igver-agent-secret-key-change-in-production'
CORS(app)

# Global agent instance
agent_instance = None
current_job = {'status': 'idle', 'progress': 0, 'message': ''}

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🧬 IGVer Genomic AI Agent</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }
        
        .section h2 .icon {
            margin-right: 10px;
            font-size: 1.5em;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #4facfe;
        }
        
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        .file-input-wrapper {
            position: relative;
            display: inline-block;
            width: 100%;
        }
        
        .file-input-wrapper input[type=file] {
            position: absolute;
            left: -9999px;
        }
        
        .file-input-label {
            display: block;
            padding: 12px;
            background: white;
            border: 2px dashed #4facfe;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .file-input-label:hover {
            background: #f0f8ff;
        }
        
        .btn {
            padding: 12px 30px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .progress-container {
            display: none;
            margin: 20px 0;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        
        .results {
            display: none;
            margin-top: 30px;
        }
        
        .result-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .result-card h3 {
            color: #333;
            margin-bottom: 15px;
        }
        
        .screenshot-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .screenshot-item {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.3s;
        }
        
        .screenshot-item:hover {
            transform: scale(1.05);
        }
        
        .screenshot-item img {
            width: 100%;
            height: 150px;
            object-fit: cover;
        }
        
        .screenshot-item .label {
            padding: 8px;
            background: #f8f9fa;
            font-size: 0.9em;
            text-align: center;
        }
        
        .tag {
            display: inline-block;
            padding: 4px 12px;
            background: #e3f2fd;
            color: #1976d2;
            border-radius: 15px;
            font-size: 0.9em;
            margin: 2px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-success { background: #4caf50; }
        .status-error { background: #f44336; }
        .status-warning { background: #ff9800; }
        .status-info { background: #2196f3; }
        
        .help-text {
            color: #777;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .quick-actions {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .quick-action {
            flex: 1;
            padding: 15px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .quick-action:hover {
            border-color: #4facfe;
            background: #f0f8ff;
        }
        
        .quick-action .icon {
            font-size: 2em;
            margin-bottom: 8px;
        }
        
        @media (max-width: 768px) {
            .container {
                border-radius: 0;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
            
            .quick-actions {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧬 IGVer Genomic AI Agent</h1>
            <p>Automated IGV visualization with AI-powered analysis</p>
        </div>
        
        <div class="content">
            <!-- Quick Actions -->
            <div class="quick-actions">
                <div class="quick-action" onclick="loadExample('cancer')">
                    <div class="icon">🎗️</div>
                    <div>Cancer Genes</div>
                </div>
                <div class="quick-action" onclick="loadExample('qc')">
                    <div class="icon">✅</div>
                    <div>QC Regions</div>
                </div>
                <div class="quick-action" onclick="loadExample('test')">
                    <div class="icon">🧪</div>
                    <div>Test Data</div>
                </div>
            </div>
            
            <!-- Input Form -->
            <form id="analysisForm">
                <!-- BAM Files Section -->
                <div class="section">
                    <h2><span class="icon">📁</span> BAM Files</h2>
                    
                    <div class="form-group">
                        <label for="bamInput">BAM File Paths</label>
                        <textarea id="bamInput" name="bam_files" placeholder="Enter BAM file paths, one per line&#10;Example:&#10;/path/to/sample1.bam&#10;/path/to/sample2.bam"></textarea>
                        <div class="help-text">Enter full paths to BAM files, or use test data</div>
                    </div>
                </div>
                
                <!-- Regions Section -->
                <div class="section">
                    <h2><span class="icon">🎯</span> Genomic Regions</h2>
                    
                    <div class="form-group">
                        <label for="regionsInput">Regions</label>
                        <textarea id="regionsInput" name="regions" placeholder="Enter regions, one per line&#10;Example:&#10;chr17:43044295-43045802&#10;chr13:32315086-32400266"></textarea>
                        <div class="help-text">Format: chr:start-end (optionally add tags with space)</div>
                    </div>
                </div>
                
                <!-- Configuration Section -->
                <div class="section">
                    <h2><span class="icon">⚙️</span> Configuration</h2>
                    
                    <div class="form-group">
                        <label for="genomeSelect">Reference Genome</label>
                        <select id="genomeSelect" name="genome">
                            <option value="hg38">hg38 (GRCh38)</option>
                            <option value="hg19">hg19 (GRCh37)</option>
                            <option value="mm10">mm10 (Mouse)</option>
                            <option value="mm39">mm39 (Mouse)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="aiProvider">AI Provider</label>
                        <select id="aiProvider" name="ai_provider">
                            <option value="mock">Mock (No API needed)</option>
                            <option value="openai">OpenAI GPT-4</option>
                            <option value="anthropic">Anthropic Claude</option>
                        </select>
                        <div class="help-text">Requires API key for OpenAI/Anthropic</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="contextInput">Analysis Context (Optional)</label>
                        <textarea id="contextInput" name="context" placeholder="E.g., Looking for somatic mutations in cancer genes"></textarea>
                    </div>
                </div>
                
                <!-- Submit Button -->
                <div style="text-align: center;">
                    <button type="submit" class="btn" id="submitBtn">
                        🚀 Start Analysis
                    </button>
                </div>
            </form>
            
            <!-- Progress Section -->
            <div class="progress-container" id="progressContainer">
                <h3>Analysis Progress</h3>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%">0%</div>
                </div>
                <p id="progressMessage" style="margin-top: 10px; text-align: center;">Initializing...</p>
            </div>
            
            <!-- Results Section -->
            <div class="results" id="results">
                <h2>📊 Analysis Results</h2>
                <div id="resultsContent"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Form submission
        document.getElementById('analysisForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(e.target);
            const data = {};
            formData.forEach((value, key) => {
                data[key] = value;
            });
            
            // Parse text areas
            data.bam_files = data.bam_files.split('\\n').filter(x => x.trim());
            data.regions = data.regions.split('\\n').filter(x => x.trim());
            
            // Show progress
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('submitBtn').disabled = true;
            
            try {
                // Start analysis
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Poll for progress
                    pollProgress(result.job_id);
                } else {
                    showError(result.error);
                }
            } catch (error) {
                showError(error.toString());
            }
        });
        
        // Poll for progress
        async function pollProgress(jobId) {
            const interval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/status/${jobId}`);
                    const status = await response.json();
                    
                    // Update progress bar
                    document.getElementById('progressFill').style.width = status.progress + '%';
                    document.getElementById('progressFill').textContent = status.progress + '%';
                    document.getElementById('progressMessage').textContent = status.message;
                    
                    if (status.status === 'completed') {
                        clearInterval(interval);
                        showResults(status.results);
                    } else if (status.status === 'error') {
                        clearInterval(interval);
                        showError(status.error);
                    }
                } catch (error) {
                    clearInterval(interval);
                    showError(error.toString());
                }
            }, 1000);
        }
        
        // Show results
        function showResults(results) {
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('results').style.display = 'block';
            document.getElementById('submitBtn').disabled = false;
            
            let html = `
                <div class="result-card">
                    <h3>Summary</h3>
                    <p><span class="status-indicator status-success"></span>Analysis Complete</p>
                    <p>Total Regions: ${results.summary.total_regions}</p>
                    <p>Screenshots Generated: ${results.summary.screenshots_generated}</p>
                    <p>Success Rate: ${results.summary.success_rate}</p>
                </div>
            `;
            
            // Screenshots
            if (results.screenshots && Object.keys(results.screenshots).length > 0) {
                html += `
                    <div class="result-card">
                        <h3>📸 Screenshots</h3>
                        <div class="screenshot-grid">
                `;
                
                for (const [region, path] of Object.entries(results.screenshots)) {
                    html += `
                        <div class="screenshot-item" onclick="viewScreenshot('${path}')">
                            <img src="/api/screenshot?path=${encodeURIComponent(path)}" alt="${region}">
                            <div class="label">${region}</div>
                        </div>
                    `;
                }
                
                html += '</div></div>';
            }
            
            // AI Analysis
            if (results.ai_analyses && Object.keys(results.ai_analyses).length > 0) {
                html += '<div class="result-card"><h3>🤖 AI Analysis</h3>';
                
                for (const [region, analysis] of Object.entries(results.ai_analyses)) {
                    if (analysis.analysis) {
                        html += `
                            <div style="margin-bottom: 20px;">
                                <h4>${region}</h4>
                                <p style="white-space: pre-wrap;">${analysis.analysis.substring(0, 500)}...</p>
                            </div>
                        `;
                    }
                }
                
                html += '</div>';
            }
            
            // Download links
            if (results.report_path) {
                html += `
                    <div class="result-card">
                        <h3>📥 Downloads</h3>
                        <a href="/api/download?path=${encodeURIComponent(results.report_path)}" class="btn btn-secondary">
                            Download JSON Report
                        </a>
                        ${results.html_report ? `
                            <a href="/api/download?path=${encodeURIComponent(results.html_report)}" class="btn btn-secondary" style="margin-left: 10px;">
                                Download HTML Report
                            </a>
                        ` : ''}
                    </div>
                `;
            }
            
            document.getElementById('resultsContent').innerHTML = html;
        }
        
        // Show error
        function showError(error) {
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('submitBtn').disabled = false;
            alert('Error: ' + error);
        }
        
        // Load example data
        function loadExample(type) {
            const examples = {
                cancer: {
                    regions: 'chr17:43044295-43045802 BRCA1\\nchr13:32315086-32400266 BRCA2\\nchr17:7571720-7579721 TP53',
                    context: 'Cancer gene panel analysis for hereditary cancer risk assessment'
                },
                qc: {
                    regions: 'chr1:1000000-1010000 standard\\nchr19:58858172-58864865 high_gc\\nchr4:1000000-1010000 low_gc',
                    context: 'Quality control analysis for sequencing coverage and uniformity'
                },
                test: {
                    bam: 'test/test_normal.bam\\ntest/test_tumor.bam',
                    regions: 'chr8:32534767-32536767 test1\\nchr19:11137898-11139898 test2',
                    context: 'Test analysis with sample data'
                }
            };
            
            const example = examples[type];
            if (example.bam) document.getElementById('bamInput').value = example.bam;
            if (example.regions) document.getElementById('regionsInput').value = example.regions;
            if (example.context) document.getElementById('contextInput').value = example.context;
        }
        
        // View screenshot
        function viewScreenshot(path) {
            window.open(`/api/screenshot?path=${encodeURIComponent(path)}`, '_blank');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Start analysis job"""
    global agent_instance, current_job
    
    try:
        data = request.json
        
        # Initialize agent if needed
        if not agent_instance:
            config = AnalysisConfig(
                genome=data.get('genome', 'hg38'),
                output_format='png',
                remove_png=False
            )
            
            agent_instance = GenomicAIAgent(
                singularity_image=get_singularity_image(),
                output_base_dir='test_results/web_ui',
                config=config,
                ai_provider=data.get('ai_provider', 'mock')
            )
        
        # Start analysis in background
        job_id = f"job_{int(time.time())}"
        current_job = {
            'status': 'running',
            'progress': 0,
            'message': 'Starting analysis...',
            'job_id': job_id
        }
        
        # Run in thread
        thread = threading.Thread(
            target=run_analysis_thread,
            args=(data, job_id)
        )
        thread.start()
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get job status"""
    return jsonify(current_job)

@app.route('/api/screenshot')
def get_screenshot():
    """Serve screenshot file"""
    path = request.args.get('path')
    if path and Path(path).exists():
        return send_file(path, mimetype='image/png')
    return "File not found", 404

@app.route('/api/download')
def download_file():
    """Download report file"""
    path = request.args.get('path')
    if path and Path(path).exists():
        return send_file(path, as_attachment=True)
    return "File not found", 404

def run_analysis_thread(data, job_id):
    """Run analysis in background thread"""
    global current_job
    
    try:
        # Update progress
        current_job['progress'] = 20
        current_job['message'] = 'Preparing input files...'
        
        # Parse regions and tags
        regions = []
        tags = []
        for region_line in data.get('regions', []):
            parts = region_line.split()
            regions.append(parts[0])
            tags.append(parts[1] if len(parts) > 1 else None)
        
        # Update progress
        current_job['progress'] = 40
        current_job['message'] = 'Generating screenshots...'
        
        # Run analysis
        results = agent_instance.comprehensive_analysis(
            bam_files=data.get('bam_files', []),
            regions=regions,
            region_tags=tags if any(tags) else None,
            session_name=f"web_{job_id}",
            context=data.get('context', ''),
            ai_analysis=(data.get('ai_provider') != 'mock'),
            save_report=True
        )
        
        # Update progress
        current_job['progress'] = 100
        current_job['message'] = 'Analysis complete!'
        current_job['status'] = 'completed'
        current_job['results'] = results
        
    except Exception as e:
        current_job['status'] = 'error'
        current_job['error'] = str(e)
        current_job['message'] = f'Error: {e}'

def main():
    """Run the web server"""
    print("🧬 IGVer Agent Web Interface")
    print("=" * 40)
    print(f"Starting web server at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    # Auto-open browser
    def open_browser():
        time.sleep(1)
        webbrowser.open('http://localhost:5000')
    
    threading.Thread(target=open_browser).start()
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    if not FLASK_AVAILABLE:
        print("Flask is required for web interface")
        print("Install with: pip install flask flask-cors")
        sys.exit(1)
    
    main()