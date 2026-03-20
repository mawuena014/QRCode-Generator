# QR Code Generator

A FastAPI service that generates QR codes from text strings or URLs.

## Features
- POST endpoint to receive data and return a PNG image.
- GET health check endpoint.
- Automatic documentation via FastAPI (/docs).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mawuena014/QRCode-Generator.git
   cd QRCode-Generator
   ```

2. Create a virtual environment:
   
   **Windows:**
   ```bash
   python -m venv .venv
   ```

   **macOS/Linux:**
   ```bash
   python3 -m venv .venv
   ```


3. Activate the virtual environment:

   **Windows:**
   ```bash
   .venv\Scripts\activate
   ```

   **macOS/Linux:**
   ```bash
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Start the server:
```bash
python main.py
```

The API will be available at http://127.0.0.1:8000.

### Endpoints

- `GET /health`: Returns service status.
- `POST /generate_qr`: Takes a JSON body like `{"url": "string"}` and returns a PNG file.

## Documentation

Once the server is running, you can access the interactive Swagger UI documentation at:
http://127.0.0.1:8000/docs
