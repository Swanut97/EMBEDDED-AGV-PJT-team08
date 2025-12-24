from pydantic import BaseModel, Field

class UserRequest(BaseModel):
    message: str

class Result(BaseModel):
    response: str = Field(description="사용자의 말에 대한 자연스러운 응답 텍스트")
    command: str = Field(description="AGV가 실행할 명령어. 반드시 다음 중 하나여야 함: [None, drink, no]")
