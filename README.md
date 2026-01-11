# Project Management System (PMS)

A full-stack, microservices-based web application designed for efficient project and team management. This system provides a collaborative platform for teams to track tasks, manage members, and communicate effectively, built with **Docker**, **FastAPI**, **PostgreSQL**, and **React**.

![PMS Logo](frontend/src/logo.svg)

## Features

- **Microservices Architecture:** Independent services for Users, Teams, and Tasks, routed via an Nginx API Gateway.
- **User Authentication & Authorization:**
  - Secure registration and login (JWT & bcrypt).
  - **Role-Based Access Control (RBAC):**
    - **Admin:** System-wide management. Activates accounts, manages teams. Protected against self-deletion.
    - **Team Leader:** Manages their specific team, adds members, creates tasks. Limited to leading one team.
    - **Member:** View and update assigned tasks.
- **Admin Panel:** Dashboard for activating users, managing roles, and overseeing system status.
- **Interactive UI with Visualizations:**
  - **Dynamic Charts:** Visual overview of task status, priority distribution, and user roles using interactive charts (Recharts).
  - **Dashboard:** "My Tasks" view with personalized statistics.
- **Task Management:** Create, assign, update priority/status, and set due dates.
- **Comments:** Real-time collaboration on tasks.
- **Database Management:**
  - **Self-Hosted PostgreSQL:** No external dependencies.
  - **NocoDB Integration:** Provides a spreadsheet-like UI for direct database management and inspection.

## Technology Stack

### Backend (Microservices)
- **Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL 15 (Dockerized)
- **ORM:** SQLAlchemy
- **Authentication:** JWT (PyJWT)
- **Gateway:** Nginx (Reverse Proxy & CORS handling)

### Frontend
- **Framework:** React.js
- **Routing:** React Router DOM
- **Charts:** Recharts
- **HTTP Client:** Axios
- **Styling:** CSS3 with a teal-based theme and responsive design

### DevOps & Infrastructure
- **Containerization:** Docker & Docker Compose
- **DB Management:** NocoDB
- **Deployment:** Google Cloud Platform (Compute Engine)

## Architecture

The system exposes only two ports to the outside world:

1.  **Frontend (Port 3000):** The React User Interface.
2.  **API Gateway (Port 80):** Nginx reverse proxy that routes requests to internal services.

Internal services (User: 8080, Team: 8081, Task: 8082) are hidden inside the Docker network.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

### 1. Clone the Repository

```bash
git clone https://github.com/FenrirRhogar/pms-system.git
cd pms-system
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory. You only need one variable now:

```env
# Security
JWT_SECRET=your-secure-random-string
```

### 3. Build and Run

```bash
docker-compose up --build -d
```

*Note: The database will automatically seed a default admin user on the first run.*

### 4. Access the Application

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **API Gateway:** `http://localhost:80`

**Default Admin Credentials:**
- **Email:** `admin@example.com`
- **Password:** `adminpassword`

**NocoDB Credentials:**
- **Email:** `admin@example.com`
- **Password:** `123456789`

## Deployment on Google Cloud (GCP)

This project is optimized for deployment on a standard Linux VM (e.g., e2-medium on Ubuntu).

1.  **Provision VM:** Create a Compute Engine instance. Allow HTTP/HTTPS traffic.
2.  **Firewall Rules:** Ensure specific ports are open in the VPC network:
    - `TCP: 3000` (Frontend)
    - `TCP: 80` (API Gateway)
    - `TCP: 8083` (NocoDB - Optional)
3.  **Setup Server:** SSH into the VM and install Docker & Git.
4.  **Deploy:**
    ```bash
    git clone <repo_url>
    cd pms-system
    echo "JWT_SECRET=supersecret" > .env
    docker-compose up -d --build
    ```
5.  **Disk Space Management:** If you deploy frequently, clean up old Docker artifacts to prevent disk space issues:
    ```bash
    docker system prune -a -f
    docker volume prune -f
    ```

## Project Structure

```
pms-system/
├── api-gateway/          # Nginx configuration (CORS, Routing)
├── backend/
│   ├── user-service/     # Auth, Roles, Profile
│   ├── team-service/     # Teams, Memberships
│   └── task-service/     # Tasks, Comments
├── frontend/             # React application
│   ├── public/           # Icons (favicon.svg) and static assets
│   └── src/              # React components, pages, charts
├── docker-compose.yml    # Full stack orchestration
└── README.md
```