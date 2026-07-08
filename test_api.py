from pydantic import BaseModel
from fastapi import FastAPI

app = FastAPI()
class TopicRequest(BaseModel):
    topic: str

@app.post("/echo")
def echo(req: TopicRequest):
    return {"you_sent": req.topic, "length": len(req.topic)}