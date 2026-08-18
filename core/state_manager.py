import time
import asyncio

class AdminConversationState:
    def __init__(self, admin_id, command_name, input_ranges):
        self.admin_id = admin_id
        self.command = command_name
        self.input_ranges = input_ranges  # list of parsed dicts
        self.current_idx = 0
        self.episode_count = None
        self.anime_name = None
        self.custom_ranges = {}           # range_idx -> custom ranges list
        self.created_at = time.time()
        self.last_active = time.time()
        self.wizard_step = 1 # Step tracker
        self.responses = []  # collects answers per range

    def is_expired(self, timeout=300):
        return (time.time() - self.last_active) > timeout

    def update_activity(self):
        self.last_active = time.time()


class ConversationStateManager:
    def __init__(self):
        self._states = {}  # key: (bot_username, admin_id) -> AdminConversationState
        self._cleanup_task = None

    def start_cleanup_loop(self):
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(30)
            now = time.time()
            to_delete = []
            for key, state in list(self._states.items()):
                if state.is_expired():
                    to_delete.append(key)
            for key in to_delete:
                self._states.pop(key, None)

    def set_state(self, bot_username, admin_id, command_name, input_ranges):
        bot_username = bot_username.lower()
        state = AdminConversationState(admin_id, command_name, input_ranges)
        self._states[(bot_username, admin_id)] = state
        self.start_cleanup_loop()
        return state

    def get_state(self, bot_username, admin_id):
        bot_username = bot_username.lower()
        state = self._states.get((bot_username, admin_id))
        if state:
            if state.is_expired():
                self._states.pop((bot_username, admin_id), None)
                return None
            state.update_activity()
        return state

    def clear_state(self, bot_username, admin_id):
        bot_username = bot_username.lower()
        self._states.pop((bot_username, admin_id), None)

state_manager = ConversationStateManager()
