# PR Agent

## Autonomous code review agent system that uses AI to analyze GitHub pull requests.


### Project Setup
1. clone `git clone https://github.com/rohit1kumar/pr-agent.git && cd pr-agent`
2. create `.env` using `cp .env.example .env` and update the values
    ```bash
    OPENAI_API_KEY=your_openai_token
    ```
3. run `docker-compose up --build` to start the services

### API Documentation
API docs are available at `http://localhost:8000/docs`

### Design Decisions
1. FastAPI for the API server with redis based rate limiting
2. Celery for background tasks and Redis as a message broker & backend
3. OpenAI API for the AI model
4. Docker for containerization

### Future Improvements
1. Adding better AI models for better code analysis
2. Creating GitHub App & responding to PRs using webhooks
