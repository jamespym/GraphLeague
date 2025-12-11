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

# Inject some custom CSS for a cleaner look
st.markdown("""
<style>
    .stChatInput {padding-bottom: 20px;}
    .block-container {padding-top: 2rem;}
    h1 {color: #C8AA6E;} /* LoL Gold Color */
</style>
""", unsafe_allow_html=True)

st.title("🛡️ League of Legends Strategy Coach")
st.markdown("---")

# Sidebar for controls and info
with st.sidebar:
    st.header("⚙️ System Controls")
    if st.button("Reset Knowledge Graph", help="Click if the database connection times out"):
        st.cache_resource.clear()
        st.success("Cache cleared! Services will restart on next prompt.")
    
    st.divider()
    st.info(
        """
        **How to use:**
        - "Who counters Aatrox top?"
        - "Which supports have anti-heal?"
        - "How do I beat Burst mages?"
        """
    )

# 3. Initialize Services (Cached to run once)
@st.cache_resource
def get_services():
    # These classes load their own .env files
    return Switchboard(), GraphRetriever(), Responder()

try:
    sb, graph, responder = get_services()
except Exception as e:
    st.error(f"❌ Failed to connect to backend: {e}")
    st.stop()

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Handle User Input
if prompt := st.chat_input("Ask about counters, mechanics, or strategy..."):
    # Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate AI Response
    with st.chat_message("assistant"):
        with st.spinner("⚔️ Analyzing Matchup data..."):
            try:
                # --- THE PIPELINE ---
                
                # 1. Logic & Retrieval
                # Note: graph_data is a LIST of dictionaries or "NA" string
                graph_data, context_str = sb.handle_query(prompt, graph)
                
                # 2. Synthesis (Gemini)
                full_response = responder.generate_response(graph_data, context_str, prompt)
                
                # 3. Display Text Response
                if full_response and full_response.text:
                    st.markdown(full_response.text)
                    st.session_state.messages.append({"role": "assistant", "content": full_response.text})
                else:
                    st.error("⚠️ The Coach is silent (Gemini API Error).")

                # 4. VISUALIZATION: The "Card" View
                # If we have valid list data (counters/search results), display them nicely
                if isinstance(graph_data, list) and len(graph_data) > 0:
                    st.write("") # Spacer
                    st.subheader("📊 Strategic Insights")
                    
                    # Create columns based on number of results (max 3 usually)
                    cols = st.columns(len(graph_data))
                    
                    for idx, item in enumerate(graph_data):
                        with cols[idx]:
                            # A bordered container acts as a "Card"
                            with st.container(border=True):
                                # Header: Champion Name
                                st.subheader(f"⚔️ {item.get('Champion')}")
                                
                                # Metric: Score (if available)
                                if 'Score' in item:
                                    st.markdown(f"**Advantage Score:** `{item.get('Score')}`")
                                
                                st.divider()
                                
                                # Section: PROS (Why it works)
                                if 'Reasoning' in item and item['Reasoning']:
                                    st.markdown("**:green[Why it works:]**")
                                    for reason in item['Reasoning']:
                                        st.markdown(f"- {reason}")
                                
                                # Section: CONS (Risks)
                                if 'Risks' in item and item['Risks']:
                                    st.write("") # Small gap
                                    st.markdown("**:red[Risks:]**")
                                    for risk in item['Risks']:
                                        st.caption(f"⚠️ {risk}")
                                        
                                # Handle 'Tool' (for mechanic search results like 'Who has Anti-Heal?')
                                if 'Tool' in item:
                                    st.markdown("**:blue[Ability Source:]**")
                                    st.info(item['Tool'])

            except Exception as e:
                st.error(f"Error during processing: {e}")
                # Optional: Print full traceback to console for debugging
                import traceback
                traceback.print_exc()