from fastapi import FastAPI
from app.routes import ping,projects
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend (Next.js on Vercel) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ping.router)
app.include_router(projects.router)

@app.get("/")
def root():
    return {"message": "GitGuide backend is alive!"}
