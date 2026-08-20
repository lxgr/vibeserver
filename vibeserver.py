#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "llm>=0.32",
#   "llm-openrouter",
#   "dotenv"
# ]
# ///

#!/usr/bin/env python3
"""
HTTP server that forwards all requests to an LLM for creative responses.
Run with uv or `pip install llm`.
You can use any LLM backend that has a plugin for llm.
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import BoundedSemaphore
import llm
from dotenv import dotenv_values

env = dotenv_values()
PORT = int(env.get('PORT'))
MODEL_NAME = env.get('MODEL_NAME')
ENABLE_IMAGES = env.get('ENABLE_IMAGES', 'false').lower() == 'true'
MAX_THREADS = int(env.get('MAX_THREADS', '1'))
if MAX_THREADS < 1:
    raise ValueError("MAX_THREADS must be at least 1")

# Global model instance to keep in memory
MODEL_INSTANCE = None


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server with a fixed limit on concurrent handlers."""

    daemon_threads = True

    def __init__(self, server_address, request_handler_class, max_threads=1):
        self._thread_slots = BoundedSemaphore(max_threads)
        self.max_threads = max_threads
        super().__init__(server_address, request_handler_class)

    def process_request(self, request, client_address):
        self._thread_slots.acquire()
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._thread_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._thread_slots.release()

class PromptBuilder:
    """Builds prompts based on configuration and request context"""
    
    @staticmethod
    def get_base_instructions():
        """Core instructions that always apply"""
        return """You are an HTTP server responding to requests. Output ONLY a valid HTTP response with headers and body. No explanations, no commentary, just the raw HTTP response. NO MARKDOWN. You are speaking the WIRE protocol. No content-length; you'll likely get it wrong. Also no ``` before and after your output!

For API paths (like /api/, /users, /login, etc.), respond with JSON.
For regular paths, respond with HTML pages.
Make the content plausible and nice based on the request."""
    
    @staticmethod
    def get_html_instructions():
        """Instructions for HTML content generation"""
        return """When returning HTML websites, include links to other relevant pages, for example if you are returning a blog website,
link to previous and next posts and so on."""
    
    @staticmethod
    def get_image_instructions():
        """Instructions for image handling (only if enabled)"""
        return """You can include images in the HTML, but try to keep it limited to 2-3 per page as image generation is expensive. Don't use images for navigation icons etc., only for important content elements. Prefer CSS and dingbat fonts and what have you. The image links should all look like https://image.pollinations.ai/prompt/<prompt goes here>.

        If the request seems like it's for an image, and only then, you return a 302 and redirect to the following URL:
        https://image.pollinations.ai/prompt/<prompt goes here>, making up an appropriate prompt (URL escaped) as you see fit.
        Don't return any content, just the 302 redirect."""

    @staticmethod
    def get_no_image_instructions():
        """Don't try to manually generate images"""
        return """Don't include image references in HTML you're generating pointing to your own host. You can only generate text-based formats. SVG MIGHT be ok if it seems important, though.
        
        If you ever do receive a request that seems like it's for an image, return a 404."""
    
    @staticmethod
    def load_custom_prompt():
        """Load custom prompt from .prompt file if it exists"""
        try:
            with open('.prompt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Keep only lines that don't start with # (ignoring spaces)
                # but keep lines where # is escaped with \#
                content = ''.join(
                    line for line in lines 
                    if not line.lstrip().startswith('#') or line.lstrip().startswith('\\#')
                ).strip()
                if content:
                    print(f"📝 Loaded custom prompt from .prompt file ({len(content)} chars)")
                    return content
        except FileNotFoundError:
            pass  # File doesn't exist, that's fine
        except Exception as e:
            print(f"⚠️  Warning: Could not read .prompt file: {e}")
        return None

    
    @staticmethod
    def build_prompt(raw_http_request):
        """Build the complete prompt based on configuration"""
        sections = [
            PromptBuilder.get_base_instructions(),
            PromptBuilder.get_html_instructions()
        ]
        
        # Add conditional sections based on environment
        if ENABLE_IMAGES:
            sections.append(PromptBuilder.get_image_instructions())
        else:
            sections.append(PromptBuilder.get_no_image_instructions())

        # Load custom prompt if available (dynamically, no caching)
        custom_prompt = PromptBuilder.load_custom_prompt()
        if custom_prompt:
            sections.append(custom_prompt)
        
        # Join sections with newlines
        instructions = "\n\n".join(sections)
        
        # Add the request separator and actual request
        prompt = f"""{instructions}

HTTP request starts after the separator:
--- REQUEST ---
{raw_http_request}

Your response is: """
        
        return prompt

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
        response_started = False
        try:
            # Get request details
            method = self.command
            path = self.path
            if path == '/favicon.ico':
                self.send_response(404)
                self.end_headers()
                return

            # Filter out Tailscale headers
            headers = {k: v for k, v in self.headers.items() if not k.lower().startswith('tailscale-')}

            
            # Read body if present
            content_length = int(headers.get('Content-Length', 0))
            body = ""
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
            
            # Print request details
            print(f"\n=== Request Headers ===")
            for header, value in headers.items():
                print(f"{header}: {value}")
            if body:
                print(f"\n=== Request Body ===\n{body}")
            
            # Format raw HTTP request for LLM
            raw_http_request = f"{method} {path} HTTP/1.1\r\n"
            for header_name, header_value in headers.items():
                raw_http_request += f"{header_name}: {header_value}\r\n"
            raw_http_request += "\r\n"
            if body:
                raw_http_request += body
            
            # Prepare prompt for LLM
            prompt = PromptBuilder.build_prompt(raw_http_request)

            # Check if client is still connected before expensive LLM call
            try:
                # Attempt to write a zero-byte message to test connection
                self.wfile.write(b'')
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                print(f"Client disconnected before generation for {method} {path}")
                return
            
            # Get LLM response using cached model instance with streaming
            global MODEL_INSTANCE
            print(f"\n=== Generating response for {method} {path} ===")
            
            # Ask LLM to hide structured reasoning and stream only response text.
            response = MODEL_INSTANCE.prompt(
                prompt,
                stream=True,
                hide_reasoning=True,
            )

            # The LLM generates the status line and headers too, so buffer only
            # until their terminating blank line arrives. The body is forwarded
            # immediately after that, with the connection close marking its end.
            header_buffer = ""
            headers_sent = False

            for chunk in response:
                chunk_text = str(chunk)
                print(chunk_text, end='', flush=True)

                if not headers_sent:
                    header_buffer += chunk_text
                    # Models occasionally put blank lines before the HTTP status
                    # line. They are not part of the response and would otherwise
                    # look like an empty, complete header block.
                    header_buffer = header_buffer.lstrip('\r\n')
                    separator = '\r\n\r\n'
                    separator_index = header_buffer.find(separator)
                    if separator_index == -1:
                        separator = '\n\n'
                        separator_index = header_buffer.find(separator)

                    if separator_index == -1:
                        if len(header_buffer) > 65536:
                            raise ValueError("LLM response headers exceeded 64 KiB")
                        continue

                    headers_part = header_buffer[:separator_index]
                    body_part = header_buffer[separator_index + len(separator):]

                    status_line = headers_part.splitlines()[0].strip()
                    try:
                        status_code = int(status_line.split()[1])
                    except (IndexError, ValueError):
                        status_code = 200

                    self.send_response(status_code)
                    self.send_header('Connection', 'close')

                    # Content-Length cannot be known while streaming. Ignore all
                    # framing headers proposed by the LLM in favor of closing the
                    # connection when generation completes.
                    blocked_headers = {
                        'connection',
                        'content-length',
                        'transfer-encoding',
                    }
                    for line in headers_part.splitlines()[1:]:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            if key.lower() not in blocked_headers:
                                self.send_header(key, value.strip())

                    self.end_headers()
                    response_started = True
                    headers_sent = True
                    header_buffer = ""

                    if method != 'HEAD' and body_part:
                        self.wfile.write(body_part.encode('utf-8'))
                        self.wfile.flush()
                elif method != 'HEAD':
                    self.wfile.write(chunk_text.encode('utf-8'))
                    self.wfile.flush()

            if not headers_sent:
                raise ValueError("LLM response did not contain complete HTTP headers")

            print("\n=== End of generation ===\n")
            
        except (BrokenPipeError, ConnectionResetError) as e:
            print(f"Client disconnected during generation for {self.command} {self.path}: {e}")
        except Exception as e:
            if response_started:
                # Headers are already on the wire, so a second HTTP response
                # would corrupt the streamed body. Closing the connection is the
                # only valid way to signal that this response was interrupted.
                print(f"Error during streamed response: {e}")
                self.close_connection = True
                return

            # Handle errors gracefully
            error_message = f"Error processing request: {str(e)}"
            print(f"\n{error_message}", flush=True)
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
    server = BoundedThreadingHTTPServer(
        ('localhost', PORT),
        LLMHandler,
        max_threads=MAX_THREADS,
    )
    print(f"Starting LLM HTTP server on http://localhost:{PORT}")
    print(f"Using model: {MODEL_NAME}")
    print(f"Maximum concurrent requests: {server.max_threads}")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()

if __name__ == "__main__":
    main()
