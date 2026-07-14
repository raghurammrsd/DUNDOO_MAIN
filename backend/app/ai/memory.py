conversation_memory = {}
pending_actions = {}

def get_memory(user_id):
    return conversation_memory.get(user_id, [])

def update_memory(user_id, user_msg, ai_msg):
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []

    conversation_memory[user_id].append({
        "user": user_msg,
        "assistant": ai_msg
    })

    conversation_memory[user_id] = conversation_memory[user_id][-8:]


# NEW: pending action storage
def set_pending_action(user_id, action, data):
    pending_actions[user_id] = {
        "action": action,
        "data": data
    }

def get_pending_action(user_id):
    return pending_actions.get(user_id)

def clear_pending_action(user_id):
    if user_id in pending_actions:
        del pending_actions[user_id]