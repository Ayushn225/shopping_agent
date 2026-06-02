import streamlit as st
from PIL import Image
import os

from shopping_agent import agent

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Shopping Assistant",
    page_icon="🛍️",
    layout="wide"
)

# CHANGED: Target the 'resources' subfolder in the current working directory
TEMP_DIR = os.path.join(os.path.dirname(__file__), "resources") if "__file__" in locals() else "resources"
os.makedirs(TEMP_DIR, exist_ok=True)

st.title("🛍️ AI Shopping Assistant")
st.caption("Your personalized AI companion for finding the perfect products.")

# --- INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "type": "text", "content": "Hi there! I'm your shopping assistant. How can I help you today? You can type a question here or drop an image in the sidebar!"}
    ]

# --- SIDEBAR: SHOPPING BY IMAGE ---
with st.sidebar:
    st.header("📸 Search by Image")
    st.write("Upload a photo of an item, outfit, or style you like, and the AI will find matches!")
    
    sidebar_image = st.file_uploader(
        "Choose an image...", 
        type=["jpg", "jpeg", "png"], 
        key="sidebar_uploader"
    )
    
    if sidebar_image:
        img = Image.open(sidebar_image)
        st.image(img, caption="Target Product Preview", use_container_width=True)
        
        if st.button("🔍 Search this Style", use_container_width=True):
            # CHANGED: The file path now saves directly into the 'resources' folder
            temp_path = os.path.join(TEMP_DIR, sidebar_image.name)
            with open(temp_path, "wb") as f:
                f.write(sidebar_image.getbuffer())

            st.session_state.messages.append({
                "role": "user",
                "type": "image",
                "content": img
            })
            
            with st.spinner("Analyzing style image..."):
                agent_input = {
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Please find items matching this image file path: {temp_path}"
                        }
                    ]
                }
                result = agent.invoke(agent_input)
                assistant_response = result["messages"][-1].content
            
            st.session_state.messages.append({
                "role": "assistant",
                "type": "text",
                "content": assistant_response
            })
            
            st.rerun()

# --- MAIN CHAT INTERFACE ---

# 1. Render History with Friendly Labels
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["type"] == "text":
            st.write(message["content"])
        elif message["type"] == "image":
            st.info("🎨 *You initiated an image-based style search with the item below:*")
            st.image(message["content"], width=250)

# 2. Text Input Box for Chat
if user_text := st.chat_input("Ask about sizes, prices, or recommendations..."):
    with st.chat_message("user"):
        st.write(user_text)
    
    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": user_text
    })
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        with st.spinner("Thinking..."):
            history_payload = []
            for msg in st.session_state.messages[:-1]:
                if msg["type"] == "text":
                    history_payload.append({"role": msg["role"], "content": msg["content"]})
            
            history_payload.append({"role": "user", "content": user_text})

            # Send directly to the agent. No more frontend blocking!
            result = agent.invoke({"messages": history_payload})
            agent_response = result["messages"][-1].content
            
            response_placeholder.write(agent_response)
            
        st.session_state.messages.append({
            "role": "assistant",
            "type": "text",
            "content": agent_response
        })