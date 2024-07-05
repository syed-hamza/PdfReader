import streamlit as st

# Initialize chat history
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# Function to handle user input
def handle_user_input():
    if st.session_state.user_input:
        # Simulate bot response (replace this with actual chatbot logic)
        bot_response = f"Bot: You said '{st.session_state.user_input}'"
        # Update chat history
        st.session_state.chat_history.append(f"You: {st.session_state.user_input}")
        st.session_state.chat_history.append(bot_response)
        # Clear the input box
        # st.session_state.user_input = ''

# Sidebar for chat history
st.sidebar.title("Chat History")
# Display chat history in the sidebar
for message in st.session_state.chat_history:
    st.sidebar.write(message)

# Main chat interface
st.title("Chatbot")

# Input text box and submit button
st.text_input("You:", key='user_input')
if st.button("Send"):
    handle_user_input()