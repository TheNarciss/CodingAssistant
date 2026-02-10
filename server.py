# server.py
import sys
import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, ToolMessage
from app.config import SANDBOX_PATH
from app.logger import get_logger
from app.state.dev_state import make_initial_state

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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 Client connecté")
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data.get("message")
            
            if not user_input:
                continue

            initial_state = make_initial_state(
                messages=conversation_history + [HumanMessage(content=user_input)],
                root_dir=str(SANDBOX_PATH),
            )
            
            logger.info(f"📨 Reçu : {user_input}")

            sent_answer = False
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

                    await websocket.send_json(response_data)
                    
            # ═══ FIX: Plus de "c'est bon" mensonger ═══
            if not sent_answer:
                if last_tool_output:
                    # On a des résultats d'outils mais pas de synthèse
                    await websocket.send_json({
                        "type": "answer", 
                        "content": f"Task completed. Last tool output:\n{last_tool_output}"
                    })
                else:
                    await websocket.send_json({
                        "type": "answer", 
                        "content": "⚠️ The agent encountered errors and couldn't complete the task. "
                                   "Check the thought process panel for details, then try rephrasing your request."
                    })

            await websocket.send_json({"type": "done"})
            
    except WebSocketDisconnect:
        logger.info("Client déconnecté")
    except Exception as e:
        logger.error(f"Erreur : {e}")
        await websocket.close()