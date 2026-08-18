class BatchBotError(Exception):
    def __init__(self, message, display_text=None):
        super().__init__(message)
        self.display_text = display_text or message

class InvalidLinkError(BatchBotError):
    pass

class MessageInaccessibleError(BatchBotError):
    pass

class EmptyRangeError(BatchBotError):
    pass

class DBResolutionError(BatchBotError):
    pass

def format_error_message(exc: Exception):
    if isinstance(exc, InvalidLinkError):
        return (
            "❌ <b>Invalid Telegram Link.</b>\n\n"
            "Please use a valid format like:\n"
            "<code>https://t.me/channel/123</code>"
        )
    if isinstance(exc, MessageInaccessibleError):
        return (
            "❌ <b>Unable to access message.</b>\n"
            "The message may be deleted, restricted, or inaccessible."
        )
    if isinstance(exc, EmptyRangeError):
        return "❌ <b>No valid messages were found in this range.</b>"
    if isinstance(exc, DBResolutionError):
        return "❌ <b>No configured DB bot or channel was found for this source.</b>"
    if isinstance(exc, BatchBotError):
        return f"❌ <b>{exc.display_text}</b>"

    return f"❌ <b>An unexpected error occurred:</b> <code>{str(exc)}</code>"
