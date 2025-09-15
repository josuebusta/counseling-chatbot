# CHIA - Chatbot for HIV Intervention & Action

A comprehensive HIV/PREP counseling chatbot application with a Next.js frontend and FastAPI backend, featuring AI-powered counseling agents and document retrieval capabilities.

![Counseling Chatbot Screenshot 1](./CHIA_screenshot_1.png)
![Counseling Chatbot Screenshot 2](./CHIA_screenshot_2.png)

## Features

- **AI-Powered Counseling**: Multiple specialized counseling agents for HIV/PREP guidance
- **Document Retrieval**: RAG (Retrieval-Augmented Generation) system for accessing the latest HIV/PrEP research
- **Provider Search**: Find and connect with HIV/PrEP healthcare providers in your area
- **HIV Risk Assessment**: Risk evaluation and personalized recommendations
- **Contact Support**: Direct access to support resources and emergency contacts
- **Responsive UI**: Built with Next.js, React, and Tailwind CSS
- **Real-time Chat**: WebSocket-based communication between frontend and backend
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Prerequisites

Before installing the application, ensure you have the following installed on your system:

- **Python 3.11** - Required for the backend
- **Node.js 18+** - Required for the frontend
- **npm** - Package manager for Node.js
- **Git** - For cloning the repository
- **Supabase CLI** - For local development (optional but recommended)

## Installation

### 1. Clone the Repository

```bash
git clone <https://github.com/josuebusta/counseling-chatbot.git>
cd counseling-chatbot
```

### 2. Backend Setup

1. **Create and activate a Python virtual environment:**
   ```bash
   python3.11 -m venv counseling-env
   source counseling-env/bin/activate  # On Windows: counseling-env\Scripts\activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 3. Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Return to the root directory:**
   ```bash
   cd ..
   ```

### 4. Environment Configuration

Create a `.env` file in the root directory with the following required variables:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Other API keys as needed
```

**Note**: The `.env` file is not included in the repository for security reasons. You'll need to create this file with your actual API keys.

## Running the Application

### Development Mode

#### Option 1: Using npm scripts (Recommended)

From the root directory:

```bash
# Start backend (activates virtual environment and starts FastAPI)
npm run backend

# In a new terminal, start frontend (builds and starts Next.js)
npm run frontend
```

**Note**: The backend script automatically activates the virtual environment and starts the FastAPI server with auto-reload. The frontend script builds the Next.js application and starts it in production mode.

#### Option 2: Manual startup

**Backend:**
```bash
# Activate virtual environment
source counseling-env/bin/activate  # On Windows: counseling-env\Scripts\activate

# Start the backend server
cd backend
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run build
npm run start
```

### Production Mode with Docker

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Application Structure

```
counseling-chatbot/
├── backend/                 # FastAPI backend
│   ├── agents/             # AI counseling agents
│   │   ├── assistant_agent.py
│   │   ├── base_agent.py
│   │   ├── counselor_agent.py
│   │   └── rag_system.py
│   ├── components/         # Core components
│   │   ├── group_chat_manager.py
│   │   ├── rag_system.py
│   │   └── teachability_manager.py
│   ├── config/             # Configuration management
│   │   ├── model_config.py
│   │   └── settings.py
│   ├── services/           # Business logic services
│   │   └── counselor_session.py
│   ├── tools/              # Utility functions and tools
│   │   ├── chat_management.py
│   │   ├── hiv_assessment.py
│   │   ├── provider_search.py
│   │   └── support_system.py
│   ├── data/               # Vector store and data
│   ├── tests/              # Test files
│   ├── modified_packages/  # Custom autogen modifications
│   ├── main.py             # FastAPI application entry point
│   └── startup.py          # Application startup logic
├── frontend/               # Next.js frontend
│   ├── app/                # Next.js app directory
│   ├── components/         # React components
│   ├── lib/                # Utility libraries
│   ├── types/              # TypeScript type definitions
│   ├── db/                 # Database schemas and utilities
│   └── supabase/           # Supabase configuration
├── docker-compose.yml      # Docker configuration
├── requirements.txt        # Python dependencies
└── package.json           # Node.js dependencies and scripts
```

## Development Notes

- **Backend changes**: The backend runs with `--reload` flag, so changes are reflected immediately
- **Frontend changes**: After making frontend changes, you need to rebuild and restart:
  ```bash
  cd frontend
  npm run build
  npm run start
  ```
- **Virtual environment**: Always activate the virtual environment before working with the backend
- **Environment variables**: Ensure all required environment variables are set in the `.env` file
- **Supabase setup**: For local development, you may want to use Supabase CLI for local database management
- **Vector store**: The application uses ChromaDB for vector storage, which is automatically initialized

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000 and 8000 are available
2. **Python version**: Make sure you're using Python 3.11 specifically
3. **Node.js version**: Ensure you have Node.js 18 or higher
4. **Missing dependencies**: Run `pip install -r requirements.txt` and `npm install` in the respective directories
5. **Environment variables**: Ensure all required environment variables are set in the `.env` file
6. **Supabase connection**: Verify your Supabase URL and keys are correct
7. **Vector store initialization**: The vector store will be created automatically on first run

### Getting Help

If you encounter issues:
1. Check that all prerequisites are installed
2. Verify that the `.env` file contains all required variables
3. Ensure all dependencies are installed correctly
4. Check the console output for specific error messages

## Security Notes

- Never commit the `.env` file to version control
- Keep your API keys secure and rotate them regularly
- The `chatbot-docker.pem` file is for deployment access only
- Ensure your Supabase service role key is kept secure and not exposed to the frontend
- Use environment-specific configurations for different deployment environments 

