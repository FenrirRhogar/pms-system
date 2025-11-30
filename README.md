# Project Management System

A full-stack web application designed for efficient project and team management. This system provides a collaborative platform for teams to track tasks, manage members, and communicate effectively.

## Features

- **User Authentication:** Secure user registration and login system with JWT-based authentication.
- **Role-Based Access Control:** Pre-defined user roles (Admin, Team Leader, Member) with distinct permissions.
- **Admin Panel:** Centralized dashboard for administrators to manage users, activate new accounts, and assign roles.
- **Team Management:**
  - Create and disband teams.
  - Assign Team Leaders.
  - Add or remove members from teams.
- **Task Management:**
  - Create, update, and delete tasks within a team.
  - Assign tasks to specific team members.
  - Set task priority, status (e.g., To-Do, In Progress, Done), and due dates.
- **Task-Based Commenting:** Facilitates discussion and collaboration directly on task pages.

## Technology Stack

### Backend
- **Framework:** FastAPI
- **Database:** Supabase (PostgreSQL)
- **Authentication:** JWT (PyJWT) with bcrypt for password hashing
- **ORM/Data Access:** Supabase-py
- **Server:** Uvicorn

### Frontend
- **Framework:** React.js
- **Routing:** React Router
- **HTTP Client:** Axios
- **Styling:** Plain CSS

### Deployment
- **Containerization:** Docker & Docker Compose

## Getting Started

Follow these instructions to get the project up and running on your local machine.

### Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) installed.
- A Supabase project. You will need the project URL and API keys.

### 1. Clone the Repository

```bash
git clone https://github.com/FenrirRhogar/pms-system.git
cd pms-system
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory of the project and add the following variables. Replace the placeholder values with your actual Supabase project credentials.

```env
# Supabase Credentials
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# JWT
JWT_SECRET=a_very_strong_and_secret_key_of_your_choice
```

**Note:** The `JWT_SECRET` can be any long, random string.

### 3. Build and Run the Application

Use Docker Compose to build the container images and start the services.

```bash
docker-compose up --build
```

The application will be available at the following URLs:
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Structure

```
pms-project/
├── backend/          # FastAPI application
│   ├── app.py        # Main API logic and endpoints
│   ├── models.py     # Pydantic models for request/response
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # React application
│   ├── src/
│   │   ├── pages/    # Main page components
│   │   ├── components/ # Reusable UI components
│   │   ├── api.js    # Axios instance for API calls
│   │   └── App.jsx   # Main router setup
│   ├── package.json
│   └── Dockerfile
├── .env              # Root environment variables
├── docker-compose.yml # Defines and configures all services
└── README.md         # This file
```
