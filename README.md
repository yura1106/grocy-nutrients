# Grocy Stat - Secure Full-Stack Web Application

A secure, full-stack web application demonstrating user authentication with FastAPI backend and Vue.js frontend.

## Features

- User registration and authentication
- JWT-based authentication
- Secure password hashing with bcrypt
- Protected routes and API endpoints
- User profile management
- Modern UI with Tailwind CSS

## Tech Stack

### Backend
- FastAPI (Python)
- PostgreSQL database
- SQLAlchemy ORM
- JWT authentication
- Pydantic for data validation

### Frontend
- Vue 3 with Composition API
- TypeScript
- Pinia for state management
- Vue Router
- Tailwind CSS
- Axios for API requests

### DevOps
- Docker and Docker Compose for containerization

## Security Features

- Password hashing with bcrypt
- JWT authentication
- CORS protection
- Input validation
- Protected routes
- Secure HTTP headers
- Environment variable configuration
- Themis for encrypting and decrypting external API keys in DB

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Setup and Run

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd grocy-reports
   ```

2. Configure environment variables:
   ```bash
   # Copy the example file and edit with your settings
   cp .env.backend.example .env.backend
   ```

   Edit `.env.backend` and set:
   - `JWT_SECRET_KEY` - Your secret key for JWT tokens
   - `GROCY_URL` - Your Grocy instance URL
   - Other settings as needed

3. Build and start the application:
   ```
   docker-compose up -d --build
   ```

4. Access the application:
   - Frontend: http://localhost:8888
   - Backend API: http://localhost:8888/api
   - API documentation: http://localhost:8888/api/docs

### Development Setup

#### Quick Start with Docker (Recommended)

Use the provided convenience script to start the development environment:

```bash
./dev.sh
```

This script:
- Starts all services using `docker-compose.dev.yml`
- Enables hot-reloading for both frontend and backend
- Automatically rebuilds containers if needed
- Press Ctrl+C to stop all containers gracefully

#### Backend Development

1. Create a virtual environment:
   ```
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the backend directory with your configuration.

4. Run the development server:
   ```
   python run.py
   ```

#### Frontend Development

1. Install dependencies:
   ```
   cd frontend
   npm install
   ```

2. Run the development server:
   ```
   npm run dev
   ```

## API Endpoints

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/logout` - Logout (client-side)
- `GET /api/users/me` - Get current user information
- `PUT /api/users/me` - Update current user information

## License

MIT # grocy-reports
