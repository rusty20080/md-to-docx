# app.py - Main Python backend
from flask import Flask, render_template, request, jsonify, send_file
import os
import tempfile
import subprocess
import uuid

app = Flask(__name__)

# Global state for conversion tracking (single source of truth)
current_conversion = {
    "status": "idle",
    "error": None,
    "input_path": None,
    "output_path": None
}

def convert_markdown_to_word(input_path, output_path):
    """Convert Markdown to Word using pandoc (single source of truth)"""
    try:
        # Use subprocess to call pandoc - this leverages your existing installation
        result = subprocess.run([
            "pandoc", 
            input_path, 
            "-o", output_path,
            "--from=markdown",
            "--to=docx"  # Word document format
        ], capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            raise Exception(f"pandoc conversion failed: {result.stderr}")
            
        return True
    
    except Exception as e:
        current_conversion["error"] = str(e)
        return False

@app.route('/')
def index():
    """Serve the HTML front-end"""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    """Handle file upload and conversion"""
    if 'markdown_file' not in request.files:
        current_conversion.update({
            "status": "error",
            "error": "No file uploaded"
        })
        return jsonify(current_conversion), 400

    file = request.files['markdown_file']
    
    # Validate file extension
    if not file.filename.lower().endswith('.md'):
        current_conversion.update({
            "status": "error",
            "error": "Only .md files are allowed"
        })
        return jsonify(current_conversion), 400

    try:
        # Create temporary files (cleaned up automatically)
        input_fd, input_path = tempfile.mkstemp(suffix='.md')
        output_fd, output_path = tempfile.mkstemp(suffix='.docx')
        
        # Write uploaded file to temporary input path
        with os.fdopen(input_fd, 'wb') as f:
            f.write(file.read())

        # Update state and start conversion
        current_conversion.update({
            "status": "processing",
            "input_path": input_path,
            "output_path": output_path,
            "error": None
        })

        # Perform conversion (uses your existing pandoc)
        success = convert_markdown_to_word(input_path, output_path)
        
        if success:
            current_conversion["status"] = "completed"
            return jsonify(current_conversion), 200
        else:
            current_conversion["status"] = "error"
            return jsonify(current_conversion), 500

    except Exception as e:
        current_conversion.update({
            "status": "error", 
            "error": f"Conversion failed: {str(e)}"
        })
        return jsonify(current_conversion), 500

@app.route('/download/<conversion_id>', methods=['GET'])
def download(conversion_id):
    """Serve converted document for download"""
    try:
        # In a real app, you'd use conversion_id to look up the file
        # For simplicity, we're using our single conversion state
        if current_conversion["status"] != "completed":
            return jsonify({"error": "No completed conversion available"}), 404

        return send_file(
            current_conversion["output_path"],
            as_attachment=True,
            download_name='converted_document.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
