#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "llm",
#   "llm-mlx",
# ]
# ///

#!/usr/bin/env python3
"""
HTTP server that forwards all requests to an LLM for creative responses.
Run with uv or `pip install llm llm-mlx`.
Install model via `llm mlx download-model mlx-community/gemma-3-12b-it-qat-3bit`.
"""

import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import llm

# Configuration
PORT = 3000
MODEL_NAME = "mlx-community/gemma-3-12b-it-qat-3bit"

# Global model instance to keep in memory
MODEL_INSTANCE = None

def remove_thinking_tags(text):
    """Remove <think>...</think> sections from the response"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

class LLMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request()
    
    def do_POST(self):
        self.handle_request()
    
    def do_PUT(self):
        self.handle_request()
    
    def do_DELETE(self):
        self.handle_request()
    
    def do_PATCH(self):
        self.handle_request()
    
    def do_HEAD(self):
        self.handle_request()
    
    def do_OPTIONS(self):
        self.handle_request()

    def handle_request(self):
        try:
            # Get request details
            method = self.command
            path = self.path
            headers = dict(self.headers)
            
            # Read body if present
            content_length = int(headers.get('Content-Length', 0))
            body = ""
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
            
            # Format raw HTTP request for LLM
            raw_http_request = f"{method} {path} HTTP/1.1\r\n"
            for header_name, header_value in headers.items():
                raw_http_request += f"{header_name}: {header_value}\r\n"
            raw_http_request += "\r\n"
            if body:
                raw_http_request += body
            
            # Prepare prompt for LLM
            prompt = f"""You are an HTTP server responding to requests. Output ONLY a valid HTTP response with headers and body. No explanations, no commentary, just the raw HTTP response. NO MARKDOWN. You are speaking the WIRE protocol. No content-length; you'll get it wrong. Also no ``` before and after your output!

For API paths (like /api/, /users, /login, etc.), respond with JSON.
For regular paths, respond with HTML pages.
Make the content plausible and nice based on the request.

NO MARKDOWN! NO CONTENT LENGTH header!!!!! No ``` ANYWHERE BEFORE OR AFTER YOUR OUTPUT!
HTTP request starts after the separator:
--- REQUEST ---
{raw_http_request}

Your response is: """
            
            # Get LLM response using cached model instance with streaming
            global MODEL_INSTANCE
            print(f"\n=== Generating response for {method} {path} ===")
            
            # Stream the response and capture it
            full_response = ""
            for chunk in MODEL_INSTANCE.prompt(prompt, stream=True):
                chunk_text = str(chunk)
                print(chunk_text, end='', flush=True)
                full_response += chunk_text
            
            print("\n=== End of generation ===\n")
            llm_response = full_response
            
            # Remove thinking tags if present
            llm_response = remove_thinking_tags(llm_response)
            
            # Parse the LLM response as raw HTTP response
            # Split headers and body
            if '\r\n\r\n' in llm_response:
                headers_part, body_part = llm_response.split('\r\n\r\n', 1)
            elif '\n\n' in llm_response:
                headers_part, body_part = llm_response.split('\n\n', 1)
            else:
                # If no clear separation, treat it all as body with default headers
                headers_part = ""
                body_part = llm_response
            
            # Send status line
            self.send_response(200)
            
            # Parse and send custom headers from LLM
            if headers_part:
                for line in headers_part.split('\n'):
                    line = line.strip()
                    if ':' in line and not line.startswith('HTTP/'):
                        key, value = line.split(':', 1)
                        self.send_header(key.strip(), value.strip())
            
            # Add default headers if not provided
            if 'content-type' not in [h.lower() for h in headers_part.split('\n') if ':' in h]:
                self.send_header('Content-Type', 'text/html; charset=utf-8')
            
            self.send_header('Server', 'LLM-Powered-Server/1.0')
            self.end_headers()
            
            # Send body
            self.wfile.write(body_part.encode('utf-8'))
            
        except Exception as e:
            # Handle errors gracefully
            error_message = f"Error processing request: {str(e)}"
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(error_message)))
            self.end_headers()
            self.wfile.write(error_message.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Custom logging to show what's happening"""
        print(f"[{self.address_string()}] {format % args}")

def main():
    global MODEL_INSTANCE
    
    # Initialize and cache the model instance
    try:
        MODEL_INSTANCE = llm.get_model(MODEL_NAME)
        print(f"Model loaded and cached: {MODEL_NAME}")
    except Exception as e:
        print(f"Error loading model '{MODEL_NAME}': {e}")
        print("Available models:")
        for model in llm.get_models():
            print(f"  - {model.model_id}")
        return
    
    # Start server
    server = HTTPServer(('localhost', PORT), LLMHandler)
    print(f"Starting LLM HTTP server on http://localhost:{PORT}")
    print(f"Using model: {MODEL_NAME}")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()

if __name__ == "__main__":
    main()