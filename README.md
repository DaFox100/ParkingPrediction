# HOW TO RUN

PART 1 - SET UP YOUR VENV AND INSTALL REQUIREMENTS - FASTAPI

1. Have python 3.12 installed on your system
2. Open cmd in backend so that it shows /Projects/ParkingPrediction/backend (or use cd to navigate directories)
3. Create a .venv using <python -m venv .venv>(if python 3.12 is your default)
- ALT - Create a .venv using <py -3.12 -m venv .venv>(if you have pylauncher and python 3.12)
- ALT - Do nothing and just using global python 3.12 version
4. Initialize the venv using the cmd by running <./.venv/Scripts/Activate.ps1>
5. We should still be in the \backend folder, run <pip install -r requirements.txt>
6. After installation is complete, run <python main.py> to start the fastAPI server

PART 2 - NODEJS FRONTEND

7. Have Node.js service installed on PC(or install it online)
8. Open cmd/terminal in the frontend folder so that it shows /Projects/ParkingPrediction/frontend
9. Run <npm install --force> and wait for installations
10. Run <npm run dev> to launch front end.
10. Open website with link or at 0.0.0.0:3000 OR http://localhost:3000/
