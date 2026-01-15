import fastapi
import uvicorn

from fastapi import FastAPI

App = FastAPI(debug=True)

print("Imports")

@App.get("/")
async def root():
    return {"message":"Hallo"}

if __name__ == "__main__":
    uvicorn.run(App, host="0.0.0.0", port=15248)