import uvicorn

from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


FAPI = FastAPI(info=True)
FAPI.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@FAPI.get("/ping")
async def FAPI_PING(req:Request):
    return JSONResponse({}, status_code=200)

uvicorn.run(FAPI, port=12121)