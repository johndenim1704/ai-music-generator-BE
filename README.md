## Steps to run locally:

### Version

- Python 3.10.12

### System Requirements

Before running the application, ensure you have the following installed:

1.  **FFmpeg**: Required for audio and video processing.
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add the `bin` folder to your System PATH.
    *   **Mac**: `brew install ffmpeg`
    *   **Linux**: `sudo apt install ffmpeg`
    *   Verify installation by running `ffmpeg -version` in your terminal.

2.  **Ollama**: Required for AI text and image generation features.
    *   Download and install from [ollama.com](https://ollama.com).
    *   Start the Ollama server.
    *   Pull the required model:
        ```bash
        ollama pull llama3.2:latest
        ```

### Clone the repository

`git clone`

### Make venv

`python -m venv venv`

`source venv/bin/activate`

### Install Dependencies
- `pip install -r requirements.txt`

### Make New Database User if needed:

`SELECT user, host FROM mysql.user;`

`CREATE USER 'music'@'localhost' IDENTIFIED BY 'music';`

`CREATE DATABASE aimusicgeneration;`

`GRANT ALL PRIVILEGES ON aimusicgeneration.* TO 'music'@'localhost';`

`FLUSH PRIVILEGES;`

`mysql -h localhost -u music -p`

### Initial Migration on new DB:

`alembic init alembic`

`example: alembic revision --autogenerate -m "Add new_column to your_table_name"`

`please check version migrations file then applied alembic upgrade head`

`alembic upgrade head`

### Run Server Locally:

- **Update Local Environment Files**: Make sure to update the `.env` file locally.

- `uvicorn main:app --reload`

- You can now access you backend at port 8000.
