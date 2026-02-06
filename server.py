# server.py
import sys
import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

# Import de ton graphe existant
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
playground_dir = os.path.join(base_dir, "PlaygroudForCodingAssistant")
os.makedirs(playground_dir, exist_ok=True)
from app.graph.graph import app as graph_app

app = FastAPI()

# Autoriser le frontend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En dev, on autorise tout
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔌 Client connecté")
    
    try:
        while True:
            # 1. Attendre le message du Frontend (JSON)
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data.get("message")
            
            if not user_input:
                continue

            # 2. État initial pour LangGraph
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "root_dir": playground_dir,
                "retry_count": 0,
                "plan_steps": [],
                "current_step": 0,
                "step_type": None,
            }
            
            print(f"📨 Reçu : {user_input}")

            sent_answer = False

            # 3. Lancer le graphe et streamer les événements
            async for event in graph_app.astream(initial_state):
                for node_name, node_content in event.items():
                    
                    response_data = {
                        "type": "log", # Par défaut, c'est du log interne
                        "node": node_name,
                        "content": ""
                    }
                    
                    # Logique d'affichage selon le nœud
                    if node_name == "planner":
                        response_data["content"] = f"🗺️ PLAN : {node_content.get('plan')}"
                    
                    elif node_name == "generator":
                        msg = node_content["messages"][-1]
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            tool = msg.tool_calls[0]
                            response_data["content"] = f"🤖 ACTION : {tool['name']}\nARGS: {json.dumps(tool['args'], indent=2)}"
                        else:
                            # C'est la réponse finale textuelle pour l'utilisateur
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
                        response_data["content"] = f"🛠️ OUTIL RETOUR : {tool_msg.content}..."
                        
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
                    
                    elif node_name == "advance_step":
                        response_data["content"] = "✅ Step terminé, passage au suivant..."
                    # Envoyer au frontend
                    await websocket.send_json(response_data)
                    
            # Si aucune réponse utilisateur n'a été envoyée, on envoie un message par défaut
            if not sent_answer:
                await websocket.send_json({"type": "answer", "content": "c'est bon"})

            # Signaler la fin
            await websocket.send_json({"type": "done"})
            
    except WebSocketDisconnect:
        print("Client déconnecté")
    except Exception as e:
        print(f"Erreur : {e}")
        await websocket.close()