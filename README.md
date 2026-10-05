# QR Code Generator

A FastAPI service that generates QR codes from text strings or URLs.

## Features
- POST endpoint to receive data and return a PNG image.
- Customizable module foreground (`fill_color`) and canvas background (`back_color`) colors with contrast verification.
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
- `POST /generate_qr`: Generates and streams a PNG QR code via `multipart/form-data`.
  
  **Form Parameters:**
  - `url` *(required, text)*: The URL or text content to encode.
  - `fill_color` *(optional, text, default: `"black"`)*: Foreground color for QR modules. Supports hex codes (e.g. `#1A56DB`, `#000`) and standard CSS color names (`navy`, `darkblue`, etc.).
  - `back_color` *(optional, text, default: `"white"`)*: Canvas background color. Supports hex codes and CSS color names. Must contrast with `fill_color`.
  - `logo` *(optional, file)*: An image file (PNG, JPEG, etc., max 10 MB) to overlay at the center.
  - `logo_size_ratio` *(optional, float, default: `0.22`, range: `0.05`–`0.30`)*: Relative size of the center logo.
  - `add_logo_background` *(optional, bool, default: `true`)*: Adds a white padded background behind the logo for contrast.
  - `box_size` *(optional, int, default: `10`, range: `1`–`50`)*: Pixel size of each QR module.
  - `border` *(optional, int, default: `4`, range: `1`–`20`)*: Quiet zone border width.

  **cURL Example (Standard):**
  ```bash
  curl -X POST "http://127.0.0.1:8000/generate_qr" \
    -F "url=https://example.com" \
    --output qr.png
  ```

  **cURL Example (Custom Colors):**
  ```bash
  curl -X POST "http://127.0.0.1:8000/generate_qr" \
    -F "url=https://example.com" \
    -F "fill_color=#0055FF" \
    -F "back_color=#F3F4F6" \
    --output qr_colored.png
  ```

  **cURL Example (Custom Colors & Center Logo):**
  ```bash
  curl -X POST "http://127.0.0.1:8000/generate_qr" \
    -F "url=https://example.com" \
    -F "fill_color=navy" \
    -F "back_color=white" \
    -F "logo=@/path/to/logo.png" \
    -F "logo_size_ratio=0.22" \
    --output qr_branded.png
  ```

## Documentation

Once the server is running, you can access the interactive Swagger UI documentation at:
http://127.0.0.1:8000/docs

## Side Note
If you found this project helpful, please consider giving it a ⭐ and forking it if you'd like to contribute or customize it for your own use!
