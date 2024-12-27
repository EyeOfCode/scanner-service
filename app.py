from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pyzbar.pyzbar import decode, ZBarSymbol
from PIL import Image
import cv2
import numpy as np
import io
import base64
import re

app = Flask(__name__, static_folder='static')
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/scan', methods=['POST'])
def scan_barcode():
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data received'}), 400

        # Extract base64 image data
        image_data = data['image']
        # Remove the data URL prefix if present
        if 'data:image' in image_data:
            image_data = re.sub('^data:image/.+;base64,', '', image_data)

        # Convert base64 to image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Process image with different methods
        processed_images = process_image(opencv_image)

        # Try to find barcodes in all processed versions
        all_barcodes = []
        for img in processed_images:
            barcodes = decode(img, symbols=[
                ZBarSymbol.CODE128,
                ZBarSymbol.CODE39,
                ZBarSymbol.EAN13,
                ZBarSymbol.QRCODE,
                ZBarSymbol.EAN8
            ])
            
            for barcode in barcodes:
                result = {
                    'type': barcode.type,
                    'data': barcode.data.decode('utf-8'),
                    'rect': {
                        'left': barcode.rect.left,
                        'top': barcode.rect.top,
                        'width': barcode.rect.width,
                        'height': barcode.rect.height
                    }
                }
                if result not in all_barcodes:
                    all_barcodes.append(result)

        return jsonify({
            'success': True,
            'barcodes': all_barcodes
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def process_image(image):
    """Process image with different methods to improve barcode detection"""
    results = []
    
    # Original grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    results.append(gray)
    
    # Threshold
    _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(threshold)
    
    # Adaptive threshold
    adaptive_threshold = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 91, 11
    )
    results.append(adaptive_threshold)
    
    # Blur and threshold
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, blurred_threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(blurred_threshold)
    
    return results

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)