---

# 🚀 FastAPI Project

This is a **FastAPI**-based backend project with configuration endpoints to manage your database easily.

---

## 🔧 Setup Instructions

### 1. ✅ Create and Activate a Virtual Environment

Before installing dependencies, make sure you are in a **virtual environment**:

**Windows:**

```bash
python -m venv .venv
venv\Scripts\activate
```

**Linux/MacOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 2. 📦 Install Dependencies

Once your virtual environment is activated, install dependencies:

```bash
pip install -r requirements.txt
```

> ⚠️ **Important:** If the installation fails due to compilation errors (especially on Windows), make sure you have *
*Visual Studio C++ Build Tools** installed.

**Download from:**  
👉 [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

---

### ENVIRONMENT VARIABLES

Create these environment variables to run the project:

- `DB_HOST`: The URL for your database connection.
- `DB_PORT`: The port for your database connection.
- `DB_NAME`: The name of your database.
- `DB_USER`: The username for your database.
- `DB_PASSWORD`: The password for your database.
- `SECRET_KEY`: A secret key for your application (e.g., for JWT tokens).
- `GEMINI_API_KEY`: Your API key for the Gemini API.

---

## 🚨 URGENT: Requirement Before Every Pull Request

Before making a **Pull Request**, **update `requirements.txt`** to make sure your changes are captured.

```bash
pip freeze > requirements.txt
```

---

## 🚀 Running the FastAPI Server

Make sure you're in the virtual environment and run:

```bash
uvicorn main:app --reload
```

---

## 🔐 Special Endpoints for Database Configuration

These endpoints are available under the `/config` prefix and should be used carefully, usually during development or
initial setup.

### POST `/config/create-tables`

Creates necessary tables in the database.

**Example Request:**

```http
POST /config/create-tables
```

**Response:**

```json
{
  "message": "Tables created successfully."
}
```

---

### POST `/config/reset-database`

Drops all data and resets the database to its initial state.

**Example Request:**

```http
POST /config/reset-database
```

**Response:**

```json
{
  "message": "Database reset successfully."
}
```

> ⚠️ **Use with caution** — this will erase all current data!

---

## 🌱Seed data

Currently when reset-database called there will be a dummy user created with the following credentials:

### User

- **Username:** `johndoe`
- **Password:** `123`

### Admin

- **Username:** `johnsmith`
- **Password:** `admin@123`

---

## 🧠 Tips

- Keep your virtual environment activated whenever you're working on the project.
- Use `pip freeze > requirements.txt` regularly to avoid dependency mismatches.
- Only use the config endpoints during development or initial deployment.

## Explainability

┌───────────────────────────────────────────────────────┐
│ Financial Risk Monitoring System │
├─────────────────┬─────────────────┬──────────────────┤
│ Risk Analysis │ Compliance Check │ Explainability │
└────────┬────────┴────────┬────────┴────────┬─────────┘
│ │ │
┌────────▼────────┐ ┌──────▼───────┐ ┌───────▼────────┐
│ FastAPI │ │ PostgreSQL │ │ Gemini API/ │
│ Backend │ │ Database │ │ Other XAI Tools│
└─────────────────┘ └──────────────┘ └────────────────┘
---