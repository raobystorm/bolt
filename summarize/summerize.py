import os
from langchain import OpenAI, PromptTemplate, LLMChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.mapreduce import MapReduceChain
from langchain.prompts import PromptTemplate

os.environ["OPENAI_API_KEY"] = "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"

prompt = "This is a test"

def main() -> None:
    