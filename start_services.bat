@echo off
cd C:\Users\ghane\Documents\ALL PROJECTS\DATA SCIENCE\onepiece\apps\identity
start /B python -m uvicorn worldview_identity.main:app --port 8001 --log-level info
echo Identity started on 8001

cd C:\Users\ghane\Documents\ALL PROJECTS\DATA SCIENCE\onepiece\apps\gateway
start /B python -m uvicorn worldview_gateway.main:app --port 8000 --log-level info
echo Gateway started on 8000

cd C:\Users\ghane\Documents\ALL PROJECTS\DATA SCIENCE\onepiece\apps\catalog
start /B python -m uvicorn worldview_catalog.main:app --port 8002 --log-level info
echo Catalog started on 8002

cd C:\Users\ghane\Documents\ALL PROJECTS\DATA SCIENCE\onepiece\apps\streaming
start /B python -m uvicorn worldview_streaming.main:app --port 8003 --log-level info
echo Streaming started on 8003

cd C:\Users\ghane\Documents\ALL PROJECTS\DATA SCIENCE\onepiece\apps\ai_guide
start /B python -m uvicorn worldview_ai_guide.main:app --port 8004 --log-level info
echo AI Guide started on 8004

echo.
echo All services started!
echo.
echo Access the web player at: http://localhost:5173
echo
pause