import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.openai_agent import create_agent_executor
from app import state

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

context = '''
мій корабель Контікі. малий космічний корабель name=Контікі. 
Стан зберігається локально в агенті. Отримати стан можна за допомогою shipstate_tool
максимальний об'єм палива 2000 кг
паливо керосин
'''    
@app.post("/query")
async def query_agent(request: QueryRequest):
    if not state.agent_executor:
        state.agent_executor = create_agent_executor()
    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required")

    if state.agent_executor is None:
        return {"answer": "Вкажіть команду що треба зробити."}

    try:
        response = state.agent_executor.invoke(
            {"input": f"контікі {request.question}","context":context},
            config={"configurable": {"session_id": "default_session"}}
        )
        print(response)
        return {"answer": response["output"]}
    except Exception as e:
        logging.error(f"Error during agent execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))