## [w3_1] 프롬프트 엔지니어링 - 효과적인 프롬프트 템플릿 설계

- 학습 목표
  - 효과적인 프롬프트 템플릿의 기본 구조와 설계 원칙을 이해한다.

- 참고링크 : [claude-best-practices](https://platform.claude.com/docs/ko/build-with-claude/prompt-engineering/claude-prompting-best-practices)

### 프롬프트 유형

- 종류 : 질문형, 지시형, 대화형, 조건부, 예시기반 등
- 이러한 프롬프트 유형들은 상황에 따라 조합하여 사용 가능
- 목적에 맞는 적절한 유형을 선택하는 것이 중요

(1) 질문형 프롬프트 Question Prompts

- 정보 추출에 효과적
- 구체적인 답변 유도 가능

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# LLM 설정
llm = ChatOpenAI(

)

# 단순 질문형
question_prompt = PromptTemplate(
  template="다음 주제에 대해 무엇을 알고 있나요?: {topic}",
  input_variables=["topic"]
)

#LCEL Chain구성
chain = quesion question_prompt
```
