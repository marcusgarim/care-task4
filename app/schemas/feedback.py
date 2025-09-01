from pydantic import BaseModel

class FeedbackIn(BaseModel):
    messageId: int
    feedbackType: str
    sessionId: str

class RewriteIn(BaseModel):
    messageId: int
    rewrittenText: str
    sessionId: str

