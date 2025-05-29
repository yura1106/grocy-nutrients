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

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Setup and Run

1. Clone the repository:
   ```
   git clone <repository-url>
   cd grocy_stat
   ```

2. (Optional) Create a `.env` file in the project root to override default settings:
   ```
   JWT_SECRET_KEY=your-super-secret-key
   ```

3. Build and start the application:
   ```
   docker-compose up -d --build
   ```

4. Access the application:
   - Frontend: http://localhost:8888
   - Backend API: http://localhost:8888/api
   - API documentation: http://localhost:8888/api/docs

### Development Setup

#### Backend

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

#### Frontend

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
