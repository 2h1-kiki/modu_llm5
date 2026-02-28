{
 "cells": [
  {
   "cell_type": "markdown",
   "id": "06b67f80",
   "metadata": {},
   "source": [
    "### LangChain이란?\n",
    "- LangChain : LLM 기반 어플리케이션 개발을 위한 프레임 워크\n",
    "- Chain : 작업을 순차적으로 실행하는 파이프라인 구조 제공\n",
    "- Agent : 자율적 의사결정 가능한 실행 단위\n",
    "\n",
    "### LangChain 컴포넌트\n",
    "- 언어처리 기능: LLM, ChatModel이 중심\n",
    "- 대화관리 : Prompt, Memory\n",
    "- 문서처리 검색 : Document Loader, Text Splitter, Embedding, VectorStore\t\n",
    "- 모듈성\n",
    "\t- 핵심 특징\n",
    "\t- 독립적인 컴포넌트들을 조합해 RAG와 같은 복잡한 시스템 구현 가능\n",
    "\n",
    "**1. Models**\n",
    "- LLM, ChatModel등으로 구분\n",
    "- 지원되는 모델 : OpenAI, Anthropic, Google 등\n",
    "- 역할 : 텍스트 생성, 대화, 요약 등 작업 수행\n",
    "\n",
    "**2. Messages**\n",
    "- Chat Model에서 사용할 수 있는 통합된 메시지 형식 제공\n",
    "- 각 모델 제공자의 특정 메시지 형식을 신경쓰지 않고, 다양한 채팅 모델 활용 가능\n",
    "- 종류\n",
    "\t1) HumanMessage\n",
    "\t\t- 사용자 역할에 해당 : user, human 등\n",
    "\t\t- 사용자의 입력 처리\n",
    "\t2) AIMessage\n",
    "\t\t- AI 모델의 응답 표현\n",
    "\t3) SystemMessage\n",
    "\t\t- 시스템 역할에 해당 : system, developer 등\n",
    "\t\t- AI 모델의 동작과 제약사항을 정의하는데 사용\n",
    "\n",
    "**3. Prompt Template**\n",
    "- https://reference.langchain.com/python/langchain_core/prompts/ 여기서 확인하기\n",
    "- 기능\n",
    "\t- Prompt Template을 통해 일관된 **입력 형식** 제공\n",
    "\t\t1. 사용자의 입력과 파라미터를 **언어 모델이 이해할 수 있는 형태로 변환**하는 도구\n",
    "\t\t2. 언어 모델에게 전달할 **지시문**을 만드는 틀\n",
    "\t- 변수를 포함한 동적 프롬프트 생성 가능\n",
    "\t\t1. 모든 템플릿은 딕셔너리 형태의 입력을 받아서 처리\n",
    "\t\t2. 출력은 PromptValue형태로 반환하며, 이는 문자열이나 메시지 리스트로 변환 가능\n",
    "- 종류\n",
    "\t1. String PromptTemplate : 문자열 프롬프트 템플릿\n",
    "\t\t- 가장 기본적인 형태\n",
    "\t\t- 단일 문자열을 형식화 하는데 사용\n",
    "\t\t```\n",
    "\t2. ChatPromptTemplate : 채팅 프롬프트 템플릿\n",
    "\t\t- 여러 메시지를 포함하는 대화형 템플릿을 만들 때 사용\n",
    "\n"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "d9f031da",
   "metadata": {},
   "source": []
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
