# Project Management System (PMS)

A full-stack, microservices-based web application designed for efficient project and team management. This system provides a collaborative platform for teams to track tasks, manage members, and communicate effectively, built with Docker, FastAPI, and React.

## Features

- **Microservices Architecture:** Independent services for Users, Teams, and Tasks, routed via an API Gateway.
- **User Authentication & Authorization:**
  - Secure registration and login (JWT & bcrypt).
  - **Role-Based Access Control (RBAC):**
    - **Admin:** System-wide management (Users, Teams, Tasks). Activates new accounts.
    - **Team Leader:** Manages their own team's members and tasks.
    - **Member:** View and update assigned tasks.
- **Admin Panel:** Comprehensive dashboard for administrators to manage users (activate/deactivate/delete), teams, and oversee all tasks.
- **Team Management:**
  - Create and delete teams.
  - Assign Team Leaders.
  - Add or remove members from teams.
- **Task Management:**
  - Create, update, delete tasks.
  - Assign tasks to specific team members.
  - Set attributes: Priority (Low/Medium/High/Urgent), Status (Todo/In Progress/Completed/On Hold), Due Dates.
  - **Dashboard:** "My Tasks" view for users to see everything assigned to them across teams.
- **Collaboration:**
  - **Task Comments:** Users can discuss specific tasks directly on the task card.

## Technology Stack

### Backend (Microservices)
- **Framework:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL)
- **Authentication:** JWT (PyJWT)
- **Gateway:** Nginx (API Gateway)

### Frontend
- **Framework:** React.js
- **Routing:** React Router DOM
- **HTTP Client:** Axios
- **Styling:** Plain CSS with responsive design

### DevOps
- **Containerization:** Docker & Docker Compose

## Getting Started

Follow these instructions to get the project up and running on your local machine.

### Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) installed.
- A [Supabase](https://supabase.com/) project (Free tier works). You will need the Project URL and API Keys.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd pms-project
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory of the project and add your credentials:

```env
# Supabase Credentials (found in Project Settings -> API)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-secret

# Security
JWT_SECRET=your-secure-random-string
```

### 3. Build and Run

Use Docker Compose to build and start the entire system:

```bash
docker-compose up --build -d
```

### 4. Access the Application

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **API Gateway:** `http://localhost:80`
- **Service Documentation (Swagger UI):**
  - User Service: [http://localhost:8080/docs](http://localhost:8080/docs)
  - Team Service: [http://localhost:8081/docs](http://localhost:8081/docs)
  - Task Service: [http://localhost:8082/docs](http://localhost:8082/docs)

## Project Structure

```
pms-project/
├── api-gateway/          # Nginx configuration for routing requests
├── backend/
│   ├── user-service/     # Auth & User management
│   ├── team-service/     # Team management
│   └── task-service/     # Task & Comment management
├── frontend/             # React application
│   ├── src/
│   │   ├── pages/        # App pages (Dashboard, Admin, Tasks...)
│   │   ├── components/   # Reusable UI components
│   │   └── styles/       # CSS files
├── .env                  # Environment variables
├── docker-compose.yml    # Service orchestration
└── README.md
```

## User Roles & Workflow

1.  **Sign Up:** New users sign up but remain **Inactive** by default.
2.  **Activation:** An **Admin** must log in and activate the new user via the Admin Panel.
3.  **Team Creation:** Admins create Teams and assign a **Team Leader**.
4.  **Team Management:** The Team Leader logs in, goes to their team, and adds **Members**.
5.  **Task Assignment:** The Team Leader creates tasks and assigns them to Members.
6.  **Work:** Members log in, check "My Tasks", update status, and add comments.

## API Endpoints Overview

Requests are routed via the API Gateway (port 80).

- **Users:** `/api/users/*`
  - `POST /signup`, `POST /login`, `GET /me`
  - `GET /` (Admin list), `PATCH /{id}/activate`, `DELETE /{id}`
- **Teams:** `/api/teams/*`
  - `GET /mine/member` (My teams)
  - `POST /` (Create), `DELETE /{id}`
  - `POST /{id}/members` (Add member)
- **Tasks:** `/api/tasks/*`
  - `GET /team/{team_id}` (List tasks)
  - `POST /team/{team_id}` (Create task)
  - `PATCH /{id}` (Update status/details)
- **Comments:** `/api/comments/*`
  - `POST /task/{task_id}`, `GET /task/{task_id}`