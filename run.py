import uvicorn
# Keep the default runner single-process; Windows reload workers require named-pipe
# permissions that are unavailable in some restricted execution environments.
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
