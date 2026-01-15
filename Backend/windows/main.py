import os
import fastapi
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

os.system("cls")

print("Imports")

# Not used as of now. Will be used as a IP whitelist
origins = [
    "http://127.0.0.1:15248"
]

App = FastAPI(debug=True)

App.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change later to IP whitelist          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@App.get("/ping")
async def root():
    return {"message":"Success"}

if __name__ == "__main__":
    print("Running main")
    uvicorn.run(App, host="127.0.0.1", port=15248)