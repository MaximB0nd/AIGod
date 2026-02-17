from enum import Enum

class MessageType(Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    NARRATOR = "narrator"
    CONTEXT_UPDATE = "context_update"
    SUMMARIZED = "summarized"
    
    def __str__(self):
        return self.value
