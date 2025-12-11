import streamlit as st
import sys
import os

# 1. Add the parent directory to sys.path so we can import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.graph_retriever import Switchboard, GraphRetriever
from backend.responder import Responder

# 2. Page Config & Styling
st.set_page_config(
    page_title="GraphLeague Coach",
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .stChatInput {padding-bottom: 20px;}
    .block-container {padding-top: 2rem;}
    h1 {color: #C8AA6E;} /* LoL Gold Color */
    .stButton button {width: 100%; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# 3. Initialize Services (Cached to run once)
@st.cache_resource
def get_services():
    return Switchboard(), GraphRetriever(), Responder()

try:
    sb, graph, responder = get_services()
except Exception as e:
    st.error(f"❌ Failed to connect to backend: {e}")
    st.stop()

# 4. Sidebar: Logo & Controls
# Requires Streamlit 1.35+ for st.logo
try:
    st.logo("https://upload.wikimedia.org/wikipedia/commons/d/d8/League_of_Legends_2019_vector.svg", icon_image=None, size='large')
except:
    pass # Fallback for older versions

with st.sidebar:
    #st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/LoL_icon.svg/256px-LoL_icon.svg.png", width=100)
    #st.title("GraphLeague")
    st.markdown("<h1 style='font-size: 36px; color: #C8AA6E;'>GraphLeague</h1>", unsafe_allow_html=True)
    
    st.markdown("### ⚡ Quick Prompts")
    # We use these buttons to set the prompt text via session state
    if st.button("Who counters Aatrox top?"):
        st.session_state["forced_prompt"] = "Who counters Aatrox top?"
    if st.button("Which mid laners have anti-heal?"):
        st.session_state["forced_prompt"] = "Which mid laners have anti-heal?"
    if st.button("Picks against Juggernauts"):
        st.session_state["forced_prompt"] = "Picks against Juggernauts"
    
    st.divider()
    if st.button("🔄 Reset Connection"):
        st.cache_resource.clear()
        st.rerun()

# 5. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Input Handling (Check Chat Input OR Button Click)
user_input = st.chat_input("Ask about counters, mechanics, or strategy...")

# If a sidebar button was clicked, override the input
if "forced_prompt" in st.session_state:
    user_input = st.session_state["forced_prompt"]
    del st.session_state["forced_prompt"] # Clear it immediately

# Processing Logic
if user_input:
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Generate AI Response
    with st.chat_message("assistant"):
        with st.spinner("⚔️ Consulting the Archives..."):
            try:
                # --- A. QUERY PROCESSING ---
                graph_data, context_str = sb.handle_query(user_input, graph)

                # --- B. ERROR HANDLING (The "NA" Check) ---
                if graph_data == "NA":
                    # Hard stop for irrelevant queries
                    error_msg = "I can only answer questions about League of Legends strategy, counters, and mechanics."
                    st.warning(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
                else:
                    # --- C. VALID QUERY -> GENERATE RESPONSE ---
                    # Even if graph_data is empty [], we let Gemini explain that.
                    full_response = responder.generate_response(graph_data, context_str, user_input)
                    
                    if full_response and full_response.text:
                        st.markdown(full_response.text)
                        st.session_state.messages.append({"role": "assistant", "content": full_response.text})
                    else:
                        st.error("⚠️ The Coach is silent (Gemini API Error).")

                    # --- D. VISUALIZATION CARDS ---
                    # Display cards only if we have data
                    if isinstance(graph_data, list) and len(graph_data) > 0:
                        st.write("") 
                        st.subheader("📊 Strategic Insights")
                        
                        cols = st.columns(min(len(graph_data), 3))
                        
                        for idx, item in enumerate(graph_data):
                            # Limit columns to 3 to prevent squishing
                            if idx > 2: break
                                
                            with cols[idx]:
                                with st.container(border=True):
                                    # 1. Header & Score
                                    st.subheader(f"⚔️ {item.get('Champion')}")
                                    
                                    # Optional Metadata Display
                                    if 'Score' in item:
                                        st.markdown(f"**Advantage Score:** `{item.get('Score')}`")
                                    elif 'Class' in item:
                                        st.caption(f"Archetype: {item.get('Class')}")

                                    st.divider()
                                    
                                    # 2. Reasoning (Now Uniform across all types)
                                    # It works for Tools (Mechanics), Strategies (Archetypes), and Counter Reasons
                                    if item.get('Reasoning'):
                                        st.markdown("**:green[Why it works:]**")
                                        for reason in item['Reasoning']:
                                            st.markdown(f"- {reason}")

                                    # 3. Risks (Only displays if the key exists)
                                    if item.get('Risks'):
                                        st.write("") # Spacer
                                        st.markdown("**:red[Risks:]**")
                                        for risk in item['Risks']:
                                            st.caption(f"⚠️ {risk}")

            except Exception as e:
                st.error(f"Error during processing: {e}")
                # Print full traceback to console for debugging
                import traceback
                traceback.print_exc()