from pydantic import BaseModel


class ChatIn(BaseModel):
    message: str
    sessionId: str
    isFirst: bool = False

class FeedbackIn(BaseModel):
    messageId: int
    feedbackType: str
    sessionId: str

class RewriteIn(BaseModel):
    messageId: int
    rewrittenText: str
    sessionId: str

