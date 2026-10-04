# QR Code Generator

A FastAPI service that generates QR codes from text strings or URLs.

## Features
- POST endpoint to receive data and return a PNG image.
- Optional center logo overlay with automatic high error-correction (`ERROR_CORRECT_H`).
- Configurable logo ratio and background padding for scan reliability.
- GET health check endpoint.
- Automatic documentation via FastAPI (/docs).
- Deterministic automated test suite with pytest.

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
   pip install -r requirements-dev.txt
   ```

## Running Tests

Run the hermetic test suite:
```bash
pytest
```

## Usage

Start the server:
```bash
python main.py
```

The API will be available at http://127.0.0.1:8000.

### Endpoints

- `GET /health`: Returns service status.
- `POST /generate_qr`: Takes a JSON body and returns a PNG image stream.
  
  **Request Body Example (Standard):**
  ```json
  {
    "url": "https://example.com"
  }
  ```

  **Request Body Example (With Center Logo):**
  ```json
  {
    "url": "https://example.com",
    "logo_base64": "data:image/png;base64,iVBORw0KGgo...",
    "logo_size_ratio": 0.22,
    "add_logo_background": true
  }
  ```

## Documentation

Once the server is running, you can access the interactive Swagger UI documentation at:
http://127.0.0.1:8000/docs

## Side Note
If you found this project helpful, please consider giving it a ⭐ and forking it if you'd like to contribute or customize it for your own use!

