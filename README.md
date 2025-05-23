# HOW TO RUN

Environment: Windows(Linux would use the its corresponding console commands)

PART 1 - SET UP YOUR VENV AND INSTALL REQUIREMENTS - FASTAPI

1. Have python 3.12 installed on your system
2. Have MongoDB installed on your system, get it here https://www.mongodb.com/try/download/community
3. Open cmd in backend so that it shows /Projects/ParkingPrediction/backend (or use cd to navigate directories)
4. Create a .venv using <python -m venv .venv>(if python 3.12 is your default)
- ALT - Create a .venv using <py -3.12 -m venv .venv>(if you have pylauncher and python 3.12)
- ALT - Do nothing and just use global python 3.12 version
4. Initialize the venv using the cmd by running <./.venv/Scripts/Activate.ps1>
5. We should still be in the \backend folder, run <pip install -r requirements.txt>
6. Place given .env file with API key inside the root directory /ParkingPrediction
7. After installation is complete, return to the root directory via "cd .."(May not be needed) and run "python backend/main.py" to start the fastAPI server

PART 2 - NODEJS FRONTEND

8. Have Node.js service installed on PC(or install it online)
9. Open cmd/terminal in the frontend folder so that it shows /Projects/ParkingPrediction/frontend
10. Run <npm install --force> and wait for installations
11. Run "npm run dev" to launch front end.
12. Open website with link or at 0.0.0.0:3000 OR http://localhost:3000/

IMPORTANT NOTE - The backend takes a while to load, especially for the first time!
The frontend will not work properly until the backend is fully loaded and shows that uvicorn is running on localhost


