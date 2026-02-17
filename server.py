# server.py
import sys
import os
import json
import asyncio
import shutil
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.config import SANDBOX_PATH
from app.logger import get_logger

# Configuration du path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
playground_dir = SANDBOX_PATH
os.makedirs(playground_dir, exist_ok=True)
from app.graph.graph import app as graph_app

app = FastAPI()
logger = get_logger("server")

# Autoriser le frontend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def safe_send(ws: WebSocket, data: dict) -> bool:
    """Returns False if connection is dead."""
    try:
        await ws.send_json(data)
        return True
    except (RuntimeError, WebSocketDisconnect):
        return False


@app.post("/api/cleanup")
async def cleanup_sandbox():
    """Delete all files in the sandbox."""
    sandbox = Path(SANDBOX_PATH)
    for item in sandbox.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    return {"status": "ok", "message": "Sandbox cleaned"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 Client connecté")

    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
        except Exception:
            pass

    heartbeat_task = asyncio.create_task(heartbeat())

    conversation_history = []
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data.get("message")
            
            if not user_input:
                continue

            conversation_history.append(HumanMessage(content=user_input))

            initial_state = {
                "messages": list(conversation_history),
                "root_dir": str(SANDBOX_PATH),
                "retry_count": 0,
                "plan_steps": [],
                "current_step": 0,
                "step_type": None,
            }
            
            logger.info(f"📨 Reçu : {user_input}")

            sent_answer = False
            last_sent_content = ""
            last_tool_output = ""  # Track last successful tool output for fallback

            async for event in graph_app.astream(initial_state):
                for node_name, node_content in event.items():
                    
                    response_data = {
                        "type": "log",
                        "node": node_name,
                        "content": ""
                    }
                    
                    if node_name == "planner":
                        response_data["content"] = f"🗺️ PLAN : {node_content.get('plan')}"
                    
                    elif node_name == "generator":
                        msg = node_content["messages"][-1]
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            tool = msg.tool_calls[0]
                            response_data["content"] = f"🤖 ACTION : {tool['name']}\nARGS: {json.dumps(tool['args'], indent=2)}"
                        else:
                            response_data["type"] = "answer"
                            response_data["content"] = msg.content
                            sent_answer = True
                            last_sent_content = msg.content
                            
                    elif node_name == "reviewer":
                        score = node_content.get("code_quality_score")
                        feedback = node_content.get("review_feedback")
                        status = "✅ Validé" if score == 10 else f"❌ Rejeté ({feedback})"
                        response_data["content"] = f"🧐 REVIEW : {status}"

                    elif node_name == "optimizer":
                        guidelines = node_content.get("dynamic_guidelines")
                        response_data["content"] = f"💉 OPTIMIZER : {guidelines}"
                        
                    elif node_name == "tools":
                        tool_msg = node_content["messages"][-1]
                        tool_content = tool_msg.content
                        response_data["content"] = f"🛠️ OUTIL RETOUR : {tool_content[:500]}..."
                        # Track successful tool outputs
                        if not any(kw in tool_content.lower() for kw in ["error", "erreur", "failed"]):
                            last_tool_output = tool_content[:300]
                        
                    elif node_name == "dispatcher":
                        step = node_content.get("step_type", "?")
                        idx = node_content.get("current_step", 0)
                        response_data["content"] = f"📍 STEP {idx + 1} → [{step.upper()}]"
                    
                    elif node_name == "search_agent":
                        msg = node_content["messages"][-1]
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            tool = msg.tool_calls[0]
                            response_data["content"] = f"🔍 SEARCH: {tool['name']}({tool['args']})"
                    
                    elif node_name == "coder_agent":
                        msg = node_content["messages"][-1]
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            tool = msg.tool_calls[0]
                            response_data["content"] = f"💻 CODE: {tool['name']}({tool['args']})"
                        else:
                            # Coder returned text instead of tool call — show it
                            if hasattr(msg, 'content') and msg.content:
                                response_data["content"] = f"💻 CODER: {msg.content[:300]}"
                    
                    elif node_name == "advance_step":
                        response_data["content"] = "✅ Step terminé, passage au suivant..."
                    
                    elif node_name == "fallback":
                        response_data["content"] = "🚑 FALLBACK: Erreur détectée, correction en cours..."

                    if not await safe_send(websocket, response_data):
                        break
                    
            # ═══ FIX: Plus de "c'est bon" mensonger ═══
            if not sent_answer:
                if last_tool_output:
                    # On a des résultats d'outils mais pas de synthèse
                    if not await safe_send(websocket, {
                        "type": "answer", 
                        "content": f"Task completed. Last tool output:\n{last_tool_output}"
                    }):
                        break
                else:
                    if not await safe_send(websocket, {
                        "type": "answer", 
                        "content": "⚠️ The agent encountered errors and couldn't complete the task. "
                                   "Check the thought process panel for details, then try rephrasing your request."
                    }):
                        break

            if sent_answer:
                conversation_history.append(AIMessage(content=last_sent_content))

            if len(conversation_history) > 30:
                conversation_history = conversation_history[:1] + conversation_history[-28:]

            await safe_send(websocket, {"type": "done"})
            
    except WebSocketDisconnect:
        logger.info("Client déconnecté")
    except Exception as e:
        logger.error(f"Erreur : {e}")
        try:
            await websocket.close()
        except RuntimeError:
            pass
    finally:
        heartbeat_task.cancel()